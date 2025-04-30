# This file is just a simple wrapper around main.py for deployment purposes
# This avoids circular import issues and works better with Replit's deployment

# Import the Flask app from main.py
from main import app, bot_thread

# This entry point is used by gunicorn in the Replit deployment
if __name__ == "__main__":
    # The bot thread is already started in main.py
    # Just run the Flask app
    import os
    app.run(host='0.0.0.0', port=int(os.environ.get('PORT', 5000)), debug=True)