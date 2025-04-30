import os
import json
import logging
from pathlib import Path

# Set up logging
logger = logging.getLogger(__name__)

# Config file path
CONFIG_PATH = "data/config.json"

# Default configuration
DEFAULT_CONFIG = {
    "default_panel_title": "『🎯』𝐏𝐇𝐀𝐍𝐓𝐎𝐌 𝐂𝐇𝐄𝐀𝐓𝐒 𝐏𝐑𝐄𝐌𝐈𝐔𝐌『💫』",
    "default_panel_description": "{image_url}\n\n╭────━━━━━━━━[ 🎯 ]━━━━━━━━────╮\n› 🎟️ 𝘾𝙧𝙚𝙖𝙩𝙚 𝙖 𝙏𝙞𝙘𝙠𝙚𝙩 𝙩𝙤 𝙂𝙚𝙩 𝙎𝙩𝙖𝙧𝙩𝙚𝙙\n› 📱 𝘾𝙤𝙣𝙣𝙚𝙘𝙩 𝙬𝙞𝙩𝙝 𝙐𝙨 𝙛𝙤𝙧 𝙎𝙪𝙥𝙥𝙤𝙧𝙩\n\n╭─────༺ 🎯 𝐂𝐎𝐍𝐓𝐀𝐂𝐓 𝐔𝐒 🎯 ༻─────╮\n› 📱 𝙄𝙣𝙨𝙩𝙖𝙜𝙧𝙖𝙢: @phantom_cheats\n› ⭐ 𝙑𝙄𝙋 𝙎𝙚𝙧𝙫𝙞𝙘𝙚 & 𝙎𝙪𝙥𝙥𝙤𝙧𝙩\n\n{footer_image_url}",
    "default_button_text": "🎯 Create Ticket 🎯",
    "default_button_emoji": "🎫",
    "default_panel_color": 0x5865F2,  # Discord Blurple
    "default_ticket_message": "Thank you for contacting Phantom Cheats support. Please describe your issue and wait for a staff member to assist you.",
    "default_close_message": "╭────━━━━━━━━[ 🎯 ]━━━━━━━━────╮\nThis ticket has been closed.\nThe channel will be deleted in 30 seconds.\n╰────━━━━━━━━━━━━━━━━━━━━────╯",
    "ticket_naming_format": "ticket-{user}",
    "welcome_message": "⭐ **Welcome to your support ticket, {user}!** ⭐\n\n**Please describe your issue with Phantom Cheats in detail and our team will assist you shortly.**\n\n*Your ticket ID is: #{ticket_id}*",
    "max_user_tickets": 3,
    "ticket_close_delay": 30,  # 30 seconds
    "auto_responses": {
        "gaming": "Thank you for contacting Gaming Support! Please provide:\n- Game Name\n- Issue Description\n- Screenshots/Videos (if applicable)",
        "billing": "Thank you for contacting Billing Support! Please provide:\n- Transaction ID\n- Payment Method\n- Issue Description",
        "general": "Thank you for contacting Support! Please describe your issue in detail."
    },
    "ticket_tags": ["urgent", "pending", "resolved", "bug", "feature", "billing", "gaming"],
    "panel_templates": {
        "gaming": {
            "title": "『🎮』𝐏𝐇𝐀𝐍𝐓𝐎𝐌 𝐂𝐇𝐄𝐀𝐓𝐒 𝐆𝐀𝐌𝐈𝐍𝐆 𝐒𝐔𝐏𝐏𝐎𝐑𝐓『🎮』",
            "description": "⭐ 𝙿𝚛𝚎𝚖𝚒𝚞𝚖 𝙶𝚊𝚖𝚒𝚗𝚐 𝚂𝚘𝚕𝚞𝚝𝚒𝚘𝚗𝚜 ⭐\n\n🎮 𝚃𝚑𝚎 𝚄𝚕𝚝𝚒𝚖𝚊𝚝𝚎 𝙶𝚊𝚖𝚒𝚗𝚐 𝙴𝚡𝚙𝚎𝚛𝚒𝚎𝚗𝚌𝚎 🎮\n🌟 Premium Products | ⚡ Fast Delivery | 💫 24/7 Support\n\n╭────━━━━━━━━[ 🎯 ]━━━━━━━━────╮\n› 🎟️ 𝘾𝙧𝙚𝙖𝙩𝙚 𝙖 𝙏𝙞𝙘𝙠𝙚𝙩 𝙛𝙤𝙧 𝙂𝙖𝙢𝙞𝙣𝙜 𝙎𝙪𝙥𝙥𝙤𝙧𝙩",
            "color": 0xED4245,  # Discord Red
            "button_text": "🎮 Gaming Support 🎮",
            "button_emoji": "🎮"
        },
        "billing": {
            "title": "『💰』𝐏𝐇𝐀𝐍𝐓𝐎𝐌 𝐂𝐇𝐄𝐀𝐓𝐒 𝐁𝐈𝐋𝐋𝐈𝐍𝐆 𝐒𝐔𝐏𝐏𝐎𝐑𝐓『💰』",
            "description": "⭐ 𝙿𝚛𝚎𝚖𝚒𝚞𝚖 𝙿𝚊𝚢𝚖𝚎𝚗𝚝 𝚂𝚞𝚙𝚙𝚘𝚛𝚝 ⭐\n\n💳 𝚂𝚎𝚌𝚞𝚛𝚎 𝙿𝚊𝚢𝚖𝚎𝚗𝚝𝚜 | 🛡️ 𝚁𝚎𝚕𝚒𝚊𝚋𝚕𝚎 𝚂𝚎𝚛𝚟𝚒𝚌𝚎 | 💫 24/7 𝚂𝚞𝚙𝚙𝚘𝚛𝚝\n\n╭────━━━━━━━━[ 🎯 ]━━━━━━━━────╮\n› 🎟️ 𝘾𝙧𝙚𝙖𝙩𝙚 𝙖 𝙏𝙞𝙘𝙠𝙚𝙩 𝙛𝙤𝙧 𝙋𝙖𝙮𝙢𝙚𝙣𝙩 𝙄𝙨𝙨𝙪𝙚𝙨",
            "color": 0x57F287,  # Discord Green
            "button_text": "💰 Billing Support 💰",
            "button_emoji": "💰"
        },
        "general": {
            "title": "『❓』𝐏𝐇𝐀𝐍𝐓𝐎𝐌 𝐂𝐇𝐄𝐀𝐓𝐒 𝐆𝐄𝐍𝐄𝐑𝐀𝐋 𝐒𝐔𝐏𝐏𝐎𝐑𝐓『❓』",
            "description": "⭐ 𝙿𝚛𝚎𝚖𝚒𝚞𝚖 𝙲𝚞𝚜𝚝𝚘𝚖𝚎𝚛 𝙲𝚊𝚛𝚎 ⭐\n\n❓ 𝙶𝚎𝚗𝚎𝚛𝚊𝚕 𝚀𝚞𝚎𝚜𝚝𝚒𝚘𝚗𝚜 | 📋 𝙰𝚌𝚌𝚘𝚞𝚗𝚝 𝙷𝚎𝚕𝚙 | 💫 24/7 𝚂𝚞𝚙𝚙𝚘𝚛𝚝\n\n╭────━━━━━━━━[ 🎯 ]━━━━━━━━────╮\n› 🎟️ 𝘾𝙧𝙚𝙖𝙩𝙚 𝙖 𝙏𝙞𝙘𝙠𝙚𝙩 𝙛𝙤𝙧 𝙂𝙚𝙣𝙚𝙧𝙖𝙡 𝙎𝙪𝙥𝙥𝙤𝙧𝙩",
            "color": 0xFEE75C,  # Discord Yellow
            "button_text": "❓ General Support ❓",
            "button_emoji": "❓"
        }
    }
}

# Global config variable
_config = {}

def initialize_config():
    """Initialize the configuration"""
    global _config
    
    # Ensure data directory exists
    os.makedirs(os.path.dirname(CONFIG_PATH), exist_ok=True)
    
    # Check if config file exists
    if os.path.exists(CONFIG_PATH):
        try:
            with open(CONFIG_PATH, 'r') as f:
                _config = json.load(f)
                logger.info("Configuration loaded from file")
        except json.JSONDecodeError as e:
            logger.error(f"Error parsing config file: {e}")
            _config = DEFAULT_CONFIG.copy()
            save_config()
    else:
        # Create default config
        _config = DEFAULT_CONFIG.copy()
        save_config()
        logger.info("Created default configuration")

def save_config():
    """Save the configuration to file"""
    try:
        with open(CONFIG_PATH, 'w') as f:
            json.dump(_config, indent=4, sort_keys=True, fp=f)
        logger.info("Configuration saved to file")
        return True
    except Exception as e:
        logger.error(f"Error saving config: {e}")
        return False

def get_config():
    """Get the current configuration"""
    global _config
    if not _config:
        initialize_config()
    return _config

def update_config(new_config):
    """Update the configuration"""
    global _config
    _config.update(new_config)
    return save_config()

def get_template(template_name):
    """Get a specific panel template"""
    config = get_config()
    templates = config.get("panel_templates", {})
    return templates.get(template_name, templates.get("general", {}))

def add_template(name, title, description, color, button_text, button_emoji):
    """Add a new panel template"""
    global _config
    if "panel_templates" not in _config:
        _config["panel_templates"] = {}
    
    _config["panel_templates"][name] = {
        "title": title,
        "description": description,
        "color": color,
        "button_text": button_text,
        "button_emoji": button_emoji
    }
    
    return save_config()

def remove_template(name):
    """Remove a panel template"""
    global _config
    if "panel_templates" in _config and name in _config["panel_templates"]:
        del _config["panel_templates"][name]
        return save_config()
    return False
