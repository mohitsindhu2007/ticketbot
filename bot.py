import asyncio
import discord
from discord.ext import commands
import logging
import os
import sys
import time
import traceback
import sqlite3
from utils.database import initialize_database, get_db_connection
from utils.config import initialize_config

# Set up logging
logger = logging.getLogger(__name__)

# Global variable to store the bot instance
_BOT_INSTANCE = None

async def setup_bot(bot):
    """Load all cogs for the bot"""
    try:
        await bot.load_extension("cogs.ticket_commands")
        await bot.load_extension("cogs.ticket_handlers")
        await bot.load_extension("cogs.link_filter")
        logger.info("All extensions loaded successfully")
    except Exception as e:
        logger.error(f"Error loading extensions: {e}")
        traceback.print_exc()

def get_bot_stats():
    """Get statistics about the bot operation"""
    global _BOT_INSTANCE
    
    if not _BOT_INSTANCE or not _BOT_INSTANCE.is_ready():
        return {
            "guild_count": 0,
            "user_count": 0,
            "command_count": 0,
            "active_tickets": 0,
            "total_tickets": 0,
            "latency_ms": 0
        }
    
    # Count active tickets
    active_tickets = 0
    total_tickets = 0
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT COUNT(*) FROM tickets WHERE status = 'open'")
        active_tickets = cursor.fetchone()[0]
        cursor.execute("SELECT COUNT(*) FROM tickets")
        total_tickets = cursor.fetchone()[0]
        conn.close()
    except Exception as e:
        logger.error(f"Error counting tickets: {e}")
    
    # Get total users across all guilds
    user_count = 0
    for guild in _BOT_INSTANCE.guilds:
        user_count += guild.member_count
    
    return {
        "guild_count": len(_BOT_INSTANCE.guilds),
        "user_count": user_count,
        "command_count": len(_BOT_INSTANCE.tree.get_commands()),
        "active_tickets": active_tickets,
        "total_tickets": total_tickets,
        "latency_ms": round(_BOT_INSTANCE.latency * 1000, 2)
    }

def start_bot(token):
    """Initialize and start the Discord bot"""
    global _BOT_INSTANCE
    
    # Set up intents to receive all events we need
    intents = discord.Intents.default()
    intents.message_content = True
    intents.members = True
    intents.guilds = True

    # Initialize the bot with slash command support and longer timeouts
    bot = commands.Bot(
        command_prefix="!",
        intents=intents,
        command_timeout=60.0,  # Increase command timeout to 60 seconds
        max_messages=10000,    # Cache more messages to improve performance
    )
    
    # Store the bot instance globally
    _BOT_INSTANCE = bot

    # Initialize database and configuration
    initialize_database()
    initialize_config()

    @bot.event
    async def on_ready():
        """Event triggered when the bot is ready"""
        logger.info(f"Bot is ready! Logged in as {bot.user} (ID: {bot.user.id})")
        logger.info(f"Bot is in {len(bot.guilds)} guild(s)")
        
        # Set bot status
        activity = discord.Activity(
            type=discord.ActivityType.watching,
            name="for tickets | /help"
        )
        await bot.change_presence(activity=activity)
        
        # Sync slash commands with Discord (only in the main process)
        # Check if this is the primary instance or if we're running in a module
        # We use an environment variable to set a "primary" flag
        is_primary = os.environ.get('PRIMARY_BOT_INSTANCE', 'false').lower() == 'true'
        
        # Only sync commands if this is the primary instance or we're not in a module
        if __name__ == "__main__" or is_primary:
            try:
                synced = await bot.tree.sync()
                logger.info(f"Synced {len(synced)} command(s)")
            except Exception as e:
                logger.error(f"Failed to sync commands: {e}")
                traceback.print_exc()
        else:
            logger.info("Skipping command sync in secondary instance")

    @bot.event
    async def on_error(event, *args, **kwargs):
        """Handle errors globally to prevent crashes"""
        logger.error(f"Error in event {event}")
        error_type, error, tb = sys.exc_info()
        traceback.print_exception(error_type, error, tb)

    @bot.event
    async def on_application_command_error(ctx, error):
        """Handle slash command errors"""
        if isinstance(error, commands.CommandOnCooldown):
            await ctx.response.send_message(
                f"⏳ Command on cooldown. Try again in {error.retry_after:.2f} seconds.", 
                ephemeral=True
            )
        elif isinstance(error, commands.MissingPermissions):
            await ctx.response.send_message(
                "❌ You don't have permission to use this command.", 
                ephemeral=True
            )
        elif isinstance(error, discord.app_commands.CommandInvokeError):
            # Log the original error
            logger.error(f"Command error: {error.original}")
            traceback.print_exception(type(error.original), error.original, error.original.__traceback__)
            
            # Send a user-friendly message
            try:
                await ctx.response.send_message(
                    "⚠️ An error occurred while processing this command. Please try again later.", 
                    ephemeral=True
                )
            except discord.InteractionResponded:
                try:
                    await ctx.followup.send(
                        "⚠️ An error occurred while processing this command. Please try again later.", 
                        ephemeral=True
                    )
                except:
                    pass
        else:
            # Log unknown errors
            logger.error(f"Unknown command error: {error}")
            traceback.print_exception(type(error), error, error.__traceback__)
            
            # Try to respond to the user
            try:
                await ctx.response.send_message(
                    "⚠️ An unexpected error occurred. Please try again later.", 
                    ephemeral=True
                )
            except:
                pass

    # Run the bot with cog setup
    bot.setup_hook = lambda: setup_bot(bot)
    
    # Run the bot with advanced settings for better reliability
    try:
        logger.info("Starting bot...")
        bot.run(
            token,
            reconnect=True,                # Auto-reconnect on disconnect
            log_handler=None,              # Use our own logging setup
            log_level=logging.INFO,        # Log level for discord.py
            root_logger=False,             # Don't modify the root logger
        )
    except discord.errors.LoginFailure:
        logger.error("Invalid bot token. Please check your token and try again.")
        return False
    except Exception as e:
        logger.error(f"An error occurred while starting the bot: {e}")
        traceback.print_exc()
        return False
    
    return True
