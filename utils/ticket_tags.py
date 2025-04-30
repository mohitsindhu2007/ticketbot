import logging
from utils.database import get_db_connection
import sqlite3

# Set up logging
logger = logging.getLogger(__name__)

# Define default tags with colors
DEFAULT_TAGS = {
    "urgent": 0xFF0000,       # Red
    "waiting": 0xFFA500,      # Orange
    "solved": 0x00FF00,       # Green
    "needs_info": 0xFFFF00,   # Yellow
    "vip": 0xA020F0,          # Purple
    "refund": 0x0000FF,       # Blue
    "escalated": 0xFF00FF,    # Magenta
    "feedback": 0x808080,     # Gray
    "bug": 0x8B4513,          # Brown
    "feature": 0x00FFFF       # Cyan
}

def initialize_tags():
    """Initialize the tags table in the database"""
    conn = None
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        
        # Create tags table
        cursor.execute('''
        CREATE TABLE IF NOT EXISTS ticket_tags (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            color INTEGER NOT NULL,
            guild_id INTEGER NOT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            UNIQUE(name, guild_id)
        )
        ''')
        
        # Create ticket-tag relationship table
        cursor.execute('''
        CREATE TABLE IF NOT EXISTS ticket_tag_relations (
            ticket_id INTEGER NOT NULL,
            tag_id INTEGER NOT NULL,
            added_by INTEGER NOT NULL,
            added_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            PRIMARY KEY (ticket_id, tag_id),
            FOREIGN KEY (tag_id) REFERENCES ticket_tags(id) ON DELETE CASCADE
        )
        ''')
        
        conn.commit()
        
        # Add default tags if they don't exist
        for guild_id in _get_all_guild_ids(conn):
            _ensure_default_tags(conn, guild_id)
            
        logger.info("Tag system initialized successfully")
        
    except Exception as e:
        logger.error(f"Error initializing tag system: {e}")
        if conn:
            conn.rollback()
    finally:
        if conn:
            conn.close()

def _get_all_guild_ids(conn):
    """Get all guild IDs from the database"""
    cursor = conn.cursor()
    cursor.execute("SELECT DISTINCT guild_id FROM guild_config")
    return [row[0] for row in cursor.fetchall()]

def _ensure_default_tags(conn, guild_id):
    """Ensure default tags exist for a guild"""
    cursor = conn.cursor()
    
    for tag_name, color in DEFAULT_TAGS.items():
        cursor.execute('''
        INSERT OR IGNORE INTO ticket_tags (name, color, guild_id)
        VALUES (?, ?, ?)
        ''', (tag_name, color, guild_id))
    
    conn.commit()

def get_all_tags(guild_id):
    """Get all available tags for a guild"""
    conn = None
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        
        cursor.execute('''
        SELECT id, name, color
        FROM ticket_tags
        WHERE guild_id = ?
        ORDER BY name
        ''', (guild_id,))
        
        tags = [{"id": row[0], "name": row[1], "color": row[2]} for row in cursor.fetchall()]
        return tags
        
    except Exception as e:
        logger.error(f"Error getting tags: {e}")
        return []
    finally:
        if conn:
            conn.close()

def add_tag(guild_id, tag_name, color=None):
    """Add a new tag for a guild"""
    conn = None
    try:
        # Use a default color if none provided
        if color is None:
            # Generate a random color if tag name not in defaults
            if tag_name.lower() in DEFAULT_TAGS:
                color = DEFAULT_TAGS[tag_name.lower()]
            else:
                import random
                color = random.randint(0, 0xFFFFFF)
        
        conn = get_db_connection()
        cursor = conn.cursor()
        
        cursor.execute('''
        INSERT OR REPLACE INTO ticket_tags (name, color, guild_id)
        VALUES (?, ?, ?)
        ''', (tag_name.lower(), color, guild_id))
        
        conn.commit()
        return True
        
    except Exception as e:
        logger.error(f"Error adding tag: {e}")
        if conn:
            conn.rollback()
        return False
    finally:
        if conn:
            conn.close()

def remove_tag(guild_id, tag_name):
    """Remove a tag for a guild"""
    conn = None
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        
        cursor.execute('''
        DELETE FROM ticket_tags
        WHERE guild_id = ? AND name = ?
        ''', (guild_id, tag_name.lower()))
        
        conn.commit()
        return cursor.rowcount > 0
        
    except Exception as e:
        logger.error(f"Error removing tag: {e}")
        if conn:
            conn.rollback()
        return False
    finally:
        if conn:
            conn.close()

def add_tag_to_ticket(ticket_id, tag_name, guild_id, user_id):
    """Add a tag to a ticket"""
    conn = None
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        
        # Get the tag ID
        cursor.execute('''
        SELECT id FROM ticket_tags
        WHERE guild_id = ? AND name = ?
        ''', (guild_id, tag_name.lower()))
        
        tag_result = cursor.fetchone()
        if not tag_result:
            # Create the tag if it doesn't exist
            add_tag(guild_id, tag_name)
            
            # Get the new tag ID
            cursor.execute('''
            SELECT id FROM ticket_tags
            WHERE guild_id = ? AND name = ?
            ''', (guild_id, tag_name.lower()))
            tag_result = cursor.fetchone()
            
        tag_id = tag_result[0]
        
        # Add the tag to the ticket
        cursor.execute('''
        INSERT OR REPLACE INTO ticket_tag_relations (ticket_id, tag_id, added_by)
        VALUES (?, ?, ?)
        ''', (ticket_id, tag_id, user_id))
        
        conn.commit()
        return True
        
    except Exception as e:
        logger.error(f"Error adding tag to ticket: {e}")
        if conn:
            conn.rollback()
        return False
    finally:
        if conn:
            conn.close()

def remove_tag_from_ticket(ticket_id, tag_name, guild_id):
    """Remove a tag from a ticket"""
    conn = None
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        
        # Get the tag ID
        cursor.execute('''
        SELECT id FROM ticket_tags
        WHERE guild_id = ? AND name = ?
        ''', (guild_id, tag_name.lower()))
        
        tag_result = cursor.fetchone()
        if not tag_result:
            return False
            
        tag_id = tag_result[0]
        
        # Remove the tag from the ticket
        cursor.execute('''
        DELETE FROM ticket_tag_relations
        WHERE ticket_id = ? AND tag_id = ?
        ''', (ticket_id, tag_id))
        
        conn.commit()
        return cursor.rowcount > 0
        
    except Exception as e:
        logger.error(f"Error removing tag from ticket: {e}")
        if conn:
            conn.rollback()
        return False
    finally:
        if conn:
            conn.close()

def get_ticket_tags(ticket_id):
    """Get all tags for a ticket"""
    conn = None
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        
        cursor.execute('''
        SELECT t.name, t.color
        FROM ticket_tag_relations tr
        JOIN ticket_tags t ON tr.tag_id = t.id
        WHERE tr.ticket_id = ?
        ORDER BY t.name
        ''', (ticket_id,))
        
        return [{"name": row[0], "color": row[1]} for row in cursor.fetchall()]
        
    except Exception as e:
        logger.error(f"Error getting ticket tags: {e}")
        return []
    finally:
        if conn:
            conn.close()

def get_tickets_by_tag(guild_id, tag_name):
    """Get all tickets with a specific tag"""
    conn = None
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        
        cursor.execute('''
        SELECT t.channel_id, t.user_id, t.created_at, t.status
        FROM tickets t
        JOIN ticket_tag_relations tr ON t.id = tr.ticket_id
        JOIN ticket_tags tags ON tr.tag_id = tags.id
        WHERE t.guild_id = ? AND tags.name = ?
        ORDER BY t.created_at DESC
        ''', (guild_id, tag_name.lower()))
        
        tickets = []
        for row in cursor.fetchall():
            tickets.append({
                "channel_id": row[0],
                "user_id": row[1],
                "created_at": row[2],
                "status": row[3]
            })
            
        return tickets
        
    except Exception as e:
        logger.error(f"Error getting tickets by tag: {e}")
        return []
    finally:
        if conn:
            conn.close()

# Initialize tags on module import
initialize_tags()