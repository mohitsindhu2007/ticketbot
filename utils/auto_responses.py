import logging
import json
import os
import random
from utils.config import get_config, save_config

logger = logging.getLogger(__name__)

# Default responses for different ticket types
DEFAULT_RESPONSES = {
    "gaming": [
        "Hello! Thanks for contacting Phantom Cheats gaming support. Could you please provide details about the game and issue you're experiencing?",
        "Welcome to gaming support! We're here to help with your game-related issues. What specific game are you having trouble with?",
        "Hi there! I'll be assisting you with your gaming concerns today. To better help you, could you share which game and what type of issue you're facing?"
    ],
    "billing": [
        "Hello! Thanks for contacting our billing department. Could you please provide your order number or transaction ID so we can assist you better?",
        "Welcome to Phantom Cheats billing support! To help with your inquiry, please share details about your payment method and when the transaction occurred.",
        "Hi there! I'll be helping with your billing question today. Could you please let me know what specific billing issue you're experiencing?"
    ],
    "general": [
        "Hello! Thanks for contacting Phantom Cheats support. How can I assist you today?",
        "Welcome to Phantom Cheats support! I'm here to help with your questions or concerns. Please let me know what you need assistance with.",
        "Hi there! Thanks for reaching out to our support team. Please describe your issue, and I'll do my best to help you."
    ]
}

def load_responses():
    """Load custom responses from config or use defaults"""
    try:
        config = get_config()
        if 'auto_responses' not in config:
            # Initialize with default responses
            config['auto_responses'] = DEFAULT_RESPONSES.copy()
            save_config()
        
        return config['auto_responses']
    except Exception as e:
        logger.error(f"Error loading auto-responses: {e}")
        return DEFAULT_RESPONSES.copy()

def get_response(ticket_type):
    """Get a random response for the specified ticket type"""
    responses = load_responses()
    
    # If the ticket type exists and has responses, return a random one
    if ticket_type in responses and responses[ticket_type]:
        return random.choice(responses[ticket_type])
    
    # Otherwise, return a generic response
    return random.choice(responses.get("general", ["Hello! How can I help you today?"]))

def add_custom_response(ticket_type, response_text):
    """Add a custom response for a ticket type"""
    try:
        config = get_config()
        
        # Initialize auto_responses if not present
        if 'auto_responses' not in config:
            config['auto_responses'] = DEFAULT_RESPONSES.copy()
        
        # Initialize ticket type if not present
        if ticket_type not in config['auto_responses']:
            config['auto_responses'][ticket_type] = []
        
        # Add the response
        config['auto_responses'][ticket_type].append(response_text)
        
        # Save the updated config
        save_config()
        
        return True
    except Exception as e:
        logger.error(f"Error adding custom response: {e}")
        return False

def remove_custom_response(ticket_type, index):
    """Remove a custom response by index"""
    try:
        config = get_config()
        
        # Check if auto_responses and ticket type exist
        if ('auto_responses' not in config or 
            ticket_type not in config['auto_responses'] or
            index < 0 or 
            index >= len(config['auto_responses'][ticket_type])):
            return False
        
        # Remove the response
        config['auto_responses'][ticket_type].pop(index)
        
        # Save the updated config
        save_config()
        
        return True
    except Exception as e:
        logger.error(f"Error removing custom response: {e}")
        return False

def get_all_responses():
    """Get all available responses grouped by type"""
    return load_responses()