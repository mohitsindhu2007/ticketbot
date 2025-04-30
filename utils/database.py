import os
import sqlite3
import logging
from pathlib import Path

# Set up logging
logger = logging.getLogger(__name__)

# Database file path
DB_PATH = "data/ticket_bot.db"

def get_db_connection():
    """Create a connection to the SQLite database"""
    # Ensure data directory exists
    os.makedirs(os.path.dirname(DB_PATH), exist_ok=True)

    conn = None
    try:
        conn = sqlite3.connect(DB_PATH)
        conn.row_factory = sqlite3.Row  # Return rows as dictionaries
        return conn
    except sqlite3.Error as e:
        logger.error(f"Database connection error: {e}")
        if conn:
            conn.close()
        raise

def initialize_database():
    """Initialize the database with necessary tables"""
    logger.info("Initializing database...")

    conn = None
    try:
        conn = get_db_connection()
        cursor = conn.cursor()

        # Create table for ticket configurations
        cursor.execute('''
        CREATE TABLE IF NOT EXISTS ticket_configs (
            guild_id INTEGER PRIMARY KEY,
            category_id INTEGER,
            log_channel_id INTEGER,
            admin_role_id INTEGER,
            support_role_id INTEGER,
            max_tickets INTEGER DEFAULT 5,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
        ''')

        # Create table for ticket panels
        cursor.execute('''
        CREATE TABLE IF NOT EXISTS ticket_panels (
            panel_id INTEGER PRIMARY KEY AUTOINCREMENT,
            guild_id INTEGER NOT NULL,
            channel_id INTEGER NOT NULL,
            message_id INTEGER NOT NULL,
            panel_title TEXT,
            panel_description TEXT,
            panel_color INTEGER,
            button_text TEXT,
            button_emoji TEXT,
            image_url TEXT,
            header_image_url TEXT,
            footer_image_url TEXT,
            close_button_text TEXT DEFAULT 'Close Ticket',
            close_button_emoji TEXT DEFAULT '🔒',
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (guild_id) REFERENCES ticket_configs (guild_id)
        )
        ''')

        # Create table for active tickets
        cursor.execute('''
        CREATE TABLE IF NOT EXISTS tickets (
            ticket_id INTEGER PRIMARY KEY AUTOINCREMENT,
            guild_id INTEGER NOT NULL,
            channel_id INTEGER NOT NULL,
            user_id INTEGER NOT NULL,
            panel_id INTEGER,
            status TEXT CHECK(status IN ('open', 'closed', 'archived')) DEFAULT 'open',
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            closed_at TIMESTAMP,
            FOREIGN KEY (guild_id) REFERENCES ticket_configs (guild_id),
            FOREIGN KEY (panel_id) REFERENCES ticket_panels (panel_id)
        )
        ''')

        # Create table for ticket counts (to track user limits)
        cursor.execute('''
        CREATE TABLE IF NOT EXISTS ticket_counts (
            guild_id INTEGER NOT NULL,
            user_id INTEGER NOT NULL,
            count INTEGER DEFAULT 1,
            PRIMARY KEY (guild_id, user_id),
            FOREIGN KEY (guild_id) REFERENCES ticket_configs (guild_id)
        )
        ''')

        conn.commit()
        logger.info("Database initialized successfully")
    except sqlite3.Error as e:
        logger.error(f"Database initialization error: {e}")
        if conn:
            conn.rollback()
    finally:
        if conn:
            conn.close()

# Guild configuration functions
def get_guild_config(guild_id):
    """Get the ticket configuration for a guild"""
    conn = get_db_connection()
    try:
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM ticket_configs WHERE guild_id = ?", (guild_id,))
        result = cursor.fetchone()
        return dict(result) if result else None
    finally:
        conn.close()

def save_guild_config(guild_id, category_id=None, log_channel_id=None, 
                     admin_role_id=None, support_role_id=None, max_tickets=5):
    """Save the ticket configuration for a guild"""
    conn = get_db_connection()
    try:
        cursor = conn.cursor()
        # Check if config exists
        cursor.execute("SELECT 1 FROM ticket_configs WHERE guild_id = ?", (guild_id,))
        if cursor.fetchone():
            # Update existing config
            cursor.execute('''
            UPDATE ticket_configs 
            SET category_id = ?, log_channel_id = ?, admin_role_id = ?, 
                support_role_id = ?, max_tickets = ?
            WHERE guild_id = ?
            ''', (category_id, log_channel_id, admin_role_id, support_role_id, max_tickets, guild_id))
        else:
            # Insert new config
            cursor.execute('''
            INSERT INTO ticket_configs 
            (guild_id, category_id, log_channel_id, admin_role_id, support_role_id, max_tickets)
            VALUES (?, ?, ?, ?, ?, ?)
            ''', (guild_id, category_id, log_channel_id, admin_role_id, support_role_id, max_tickets))
        conn.commit()
        return True
    except sqlite3.Error as e:
        logger.error(f"Error saving guild config: {e}")
        conn.rollback()
        return False
    finally:
        conn.close()

# Ticket panel functions
def create_ticket_panel(guild_id, channel_id, message_id, panel_title, panel_description, 
                       panel_color, button_text, button_emoji, image_url=None, 
                       header_image_url=None, footer_image_url=None,
                       close_button_text="Close Ticket", close_button_emoji="🔒"):
    """Create a new ticket panel"""
    conn = get_db_connection()
    try:
        cursor = conn.cursor()
        cursor.execute('''
        INSERT INTO ticket_panels 
        (guild_id, channel_id, message_id, panel_title, panel_description, 
         panel_color, button_text, button_emoji, image_url, header_image_url, footer_image_url, close_button_text, close_button_emoji)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''', (guild_id, channel_id, message_id, panel_title, panel_description, 
              panel_color, button_text, button_emoji, image_url, header_image_url, footer_image_url, close_button_text, close_button_emoji))
        conn.commit()
        return cursor.lastrowid
    except sqlite3.Error as e:
        logger.error(f"Error creating ticket panel: {e}")
        conn.rollback()
        return None
    finally:
        conn.close()

def update_ticket_panel(guild_id, message_id, panel_title=None, panel_description=None, 
                        panel_color=None, button_text=None, button_emoji=None, image_url=None,
                        header_image_url=None, footer_image_url=None,
                        close_button_text=None, close_button_emoji=None):
    """Update an existing ticket panel"""
    conn = get_db_connection()
    try:
        # First get existing panel data
        cursor = conn.cursor()
        cursor.execute('''
        SELECT * FROM ticket_panels 
        WHERE guild_id = ? AND message_id = ?
        ''', (guild_id, message_id))
        panel = cursor.fetchone()

        if not panel:
            return False

        # Prepare update query with only provided values
        update_fields = []
        params = []

        if panel_title is not None:
            update_fields.append("panel_title = ?")
            params.append(panel_title)

        if panel_description is not None:
            update_fields.append("panel_description = ?")
            params.append(panel_description)

        if panel_color is not None:
            update_fields.append("panel_color = ?")
            params.append(panel_color)

        if button_text is not None:
            update_fields.append("button_text = ?")
            params.append(button_text)

        if button_emoji is not None:
            update_fields.append("button_emoji = ?")
            params.append(button_emoji)

        if image_url is not None:
            update_fields.append("image_url = ?")
            params.append(image_url)

        if header_image_url is not None:
            update_fields.append("header_image_url = ?")
            params.append(header_image_url)

        if footer_image_url is not None:
            update_fields.append("footer_image_url = ?")
            params.append(footer_image_url)


        if close_button_text is not None:
            update_fields.append("close_button_text = ?")
            params.append(close_button_text)

        if close_button_emoji is not None:
            update_fields.append("close_button_emoji = ?")
            params.append(close_button_emoji)

        # If no fields to update, return
        if not update_fields:
            return True

        # Add query parameters
        params.extend([guild_id, message_id])

        # Execute update query
        cursor.execute(f'''
        UPDATE ticket_panels 
        SET {", ".join(update_fields)}
        WHERE guild_id = ? AND message_id = ?
        ''', params)

        conn.commit()
        return cursor.rowcount > 0
    except sqlite3.Error as e:
        logger.error(f"Error updating ticket panel: {e}")
        conn.rollback()
        return False
    finally:
        conn.close()

def get_panel_by_message(guild_id, message_id):
    """Get a ticket panel by message ID"""
    conn = get_db_connection()
    try:
        cursor = conn.cursor()
        cursor.execute('''
        SELECT * FROM ticket_panels 
        WHERE guild_id = ? AND message_id = ?
        ''', (guild_id, message_id))
        result = cursor.fetchone()
        return dict(result) if result else None
    finally:
        conn.close()

def get_guild_panels(guild_id):
    """Get all ticket panels for a guild"""
    conn = get_db_connection()
    try:
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM ticket_panels WHERE guild_id = ?", (guild_id,))
        results = cursor.fetchall()
        return [dict(row) for row in results]
    finally:
        conn.close()

# Ticket management functions
def create_ticket(guild_id, channel_id, user_id, panel_id=None):
    """Create a new ticket record"""
    conn = get_db_connection()
    try:
        cursor = conn.cursor()
        # Create the ticket
        cursor.execute('''
        INSERT INTO tickets (guild_id, channel_id, user_id, panel_id)
        VALUES (?, ?, ?, ?)
        ''', (guild_id, channel_id, user_id, panel_id))

        # Update user's ticket count
        cursor.execute('''
        INSERT INTO ticket_counts (guild_id, user_id, count)
        VALUES (?, ?, 1)
        ON CONFLICT(guild_id, user_id) DO UPDATE
        SET count = count + 1
        ''', (guild_id, user_id))

        conn.commit()
        ticket_id = cursor.lastrowid
        return ticket_id
    except sqlite3.Error as e:
        logger.error(f"Error creating ticket: {e}")
        conn.rollback()
        return None
    finally:
        conn.close()

def close_ticket(guild_id, channel_id):
    """Close a ticket by channel ID"""
    conn = get_db_connection()
    try:
        cursor = conn.cursor()
        cursor.execute('''
        UPDATE tickets 
        SET status = 'closed', closed_at = CURRENT_TIMESTAMP
        WHERE guild_id = ? AND channel_id = ? AND status = 'open'
        ''', (guild_id, channel_id))
        conn.commit()
        return cursor.rowcount > 0
    except sqlite3.Error as e:
        logger.error(f"Error closing ticket: {e}")
        conn.rollback()
        return False
    finally:
        conn.close()

def archive_ticket(guild_id, channel_id):
    """Archive a closed ticket"""
    conn = get_db_connection()
    try:
        cursor = conn.cursor()
        cursor.execute('''
        UPDATE tickets 
        SET status = 'archived'
        WHERE guild_id = ? AND channel_id = ? AND status = 'closed'
        ''', (guild_id, channel_id))
        conn.commit()
        return cursor.rowcount > 0
    except sqlite3.Error as e:
        logger.error(f"Error archiving ticket: {e}")
        conn.rollback()
        return False
    finally:
        conn.close()

def get_ticket_by_channel(guild_id, channel_id):
    """Get ticket information by channel ID"""
    conn = get_db_connection()
    try:
        cursor = conn.cursor()
        cursor.execute('''
        SELECT * FROM tickets 
        WHERE guild_id = ? AND channel_id = ?
        ''', (guild_id, channel_id))
        result = cursor.fetchone()
        return dict(result) if result else None
    finally:
        conn.close()

def get_user_tickets(guild_id, user_id):
    """Get all tickets created by a user"""
    conn = get_db_connection()
    try:
        cursor = conn.cursor()
        cursor.execute('''
        SELECT * FROM tickets 
        WHERE guild_id = ? AND user_id = ?
        ORDER BY created_at DESC
        ''', (guild_id, user_id))
        results = cursor.fetchall()
        return [dict(row) for row in results]
    finally:
        conn.close()

def get_active_ticket_count(guild_id, user_id):
    """Get the number of active tickets a user has"""
    conn = get_db_connection()
    try:
        cursor = conn.cursor()
        cursor.execute('''
        SELECT COUNT(*) as count FROM tickets 
        WHERE guild_id = ? AND user_id = ? AND status = 'open'
        ''', (guild_id, user_id))
        result = cursor.fetchone()
        return result['count'] if result else 0
    finally:
        conn.close()

def delete_ticket_data(guild_id, channel_id):
    """Delete a ticket record when the channel is deleted"""
    conn = get_db_connection()
    try:
        cursor = conn.cursor()
        cursor.execute('''
        DELETE FROM tickets 
        WHERE guild_id = ? AND channel_id = ?
        ''', (guild_id, channel_id))
        conn.commit()
        return cursor.rowcount > 0
    except sqlite3.Error as e:
        logger.error(f"Error deleting ticket data: {e}")
        conn.rollback()
        return False
    finally:
        conn.close()