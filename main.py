import os
import logging
import threading
import time
from bot import start_bot
from dotenv import load_dotenv
from flask import Flask, jsonify

# Load environment variables from .env file
load_dotenv()

# Configure logging
logging.basicConfig(
    level=logging.DEBUG,  # Set to DEBUG for more detailed logs
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

logger = logging.getLogger(__name__)

# Initialize a minimal Flask app for compatibility with gunicorn
app = Flask(__name__)

# Add a simple health endpoint 
@app.route('/')
def health():
    return jsonify({
        "status": "healthy",
        "service": "Phantom Discord Ticket Bot",
        "message": "The bot is running in the background. Dashboard has been removed as requested."
    })

# Track bot status
bot_status = {
    "online": False,
    "last_start": None,
    "startup_attempts": 0
}

def run_bot():
    """Run the bot in a separate thread with auto-restart capability"""
    while True:
        try:
            token = os.environ.get("BOT_TOKEN")
            if not token:
                logger.error("No bot token found in environment variables. Please set BOT_TOKEN.")
                time.sleep(30)  # Wait before trying again
                continue
            
            bot_status["startup_attempts"] += 1
            bot_status["last_start"] = time.time()
            logger.info(f"Starting bot (attempt #{bot_status['startup_attempts']})")
            
            # Mark as online
            bot_status["online"] = True
            
            # Start the bot (this will block until the bot disconnects)
            start_bot(token)
            
        except Exception as e:
            logger.error(f"Bot crashed: {e}")
            bot_status["online"] = False
        
        # Wait before restarting the bot to avoid rapid restarts
        logger.info("Restarting bot in 15 seconds...")
        time.sleep(15)

# Set the primary bot instance flag for hosting environments
# Remove secondary instance detection since we're simplifying to a single-instance model
os.environ['PRIMARY_BOT_INSTANCE'] = 'true'
logger.info("Setting primary bot instance flag for all instances")

# Start bot thread
bot_thread = threading.Thread(target=run_bot, daemon=True)
bot_thread.start()

# Entry point for direct execution
if __name__ == "__main__":
    # Simply keep the main thread alive to keep the daemon bot thread running
    while True:
        try:
            # Sleep to prevent high CPU usage
            time.sleep(60)
        except KeyboardInterrupt:
            logger.info("Bot process terminated by user")
            break
        except Exception as e:
            logger.error(f"Error in main thread: {e}")
            time.sleep(5)  # Sleep briefly and continue
