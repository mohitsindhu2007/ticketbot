import logging
import sqlite3
import datetime
import json
from utils.database import get_db_connection

# Set up logging
logger = logging.getLogger(__name__)

def get_ticket_counts(guild_id, days=30):
    """Get ticket counts for the last X days"""
    conn = None
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        
        # Calculate the start date
        start_date = datetime.datetime.now() - datetime.timedelta(days=days)
        start_date_str = start_date.strftime("%Y-%m-%d 00:00:00")
        
        # Get daily ticket creation counts
        cursor.execute('''
        SELECT 
            DATE(created_at) as date,
            COUNT(*) as count
        FROM tickets
        WHERE guild_id = ? AND created_at >= ?
        GROUP BY DATE(created_at)
        ORDER BY date
        ''', (guild_id, start_date_str))
        
        created_data = {}
        for row in cursor.fetchall():
            created_data[row[0]] = row[1]
        
        # Get daily ticket closure counts
        cursor.execute('''
        SELECT 
            DATE(closed_at) as date,
            COUNT(*) as count
        FROM tickets
        WHERE guild_id = ? AND closed_at >= ? AND status = 'closed'
        GROUP BY DATE(closed_at)
        ORDER BY date
        ''', (guild_id, start_date_str))
        
        closed_data = {}
        for row in cursor.fetchall():
            closed_data[row[0]] = row[1]
        
        # Fill in missing dates
        date_range = []
        current_date = start_date
        end_date = datetime.datetime.now()
        
        while current_date <= end_date:
            date_str = current_date.strftime("%Y-%m-%d")
            date_range.append(date_str)
            
            if date_str not in created_data:
                created_data[date_str] = 0
                
            if date_str not in closed_data:
                closed_data[date_str] = 0
                
            current_date += datetime.timedelta(days=1)
        
        # Sort the data by date
        created_series = [created_data.get(date, 0) for date in date_range]
        closed_series = [closed_data.get(date, 0) for date in date_range]
        
        return {
            "dates": date_range,
            "created": created_series,
            "closed": closed_series
        }
        
    except Exception as e:
        logger.error(f"Error getting ticket counts: {e}")
        return {
            "dates": [],
            "created": [],
            "closed": []
        }
    finally:
        if conn:
            conn.close()

def get_ticket_type_distribution(guild_id, days=30):
    """Get ticket type distribution"""
    conn = None
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        
        # Calculate the start date
        start_date = datetime.datetime.now() - datetime.timedelta(days=days)
        start_date_str = start_date.strftime("%Y-%m-%d 00:00:00")
        
        # Get ticket counts by type
        cursor.execute('''
        SELECT 
            COALESCE(panel_id, 'unknown') as panel_type,
            COUNT(*) as count
        FROM tickets
        WHERE guild_id = ? AND created_at >= ?
        GROUP BY panel_id
        ORDER BY count DESC
        ''', (guild_id, start_date_str))
        
        types = []
        counts = []
        
        for row in cursor.fetchall():
            # Get panel name from panels table if available
            panel_id = row[0]
            if panel_id != 'unknown':
                cursor.execute('''
                SELECT panel_title FROM panels
                WHERE id = ?
                ''', (panel_id,))
                panel_result = cursor.fetchone()
                if panel_result:
                    panel_name = panel_result[0]
                else:
                    panel_name = f"Panel {panel_id}"
            else:
                panel_name = "Unknown"
                
            types.append(panel_name)
            counts.append(row[1])
        
        return {
            "types": types,
            "counts": counts
        }
        
    except Exception as e:
        logger.error(f"Error getting ticket type distribution: {e}")
        return {
            "types": [],
            "counts": []
        }
    finally:
        if conn:
            conn.close()

def get_response_time_metrics(guild_id, days=30):
    """Get average response times"""
    conn = None
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        
        # Calculate the start date
        start_date = datetime.datetime.now() - datetime.timedelta(days=days)
        start_date_str = start_date.strftime("%Y-%m-%d 00:00:00")
        
        # We would typically analyze message timestamps here
        # For this demo, we'll return placeholder data
        # In a real implementation, you would analyze messages in the ticket channels
        
        # Example query to get first staff response time if message data was available:
        """
        SELECT 
            t.id,
            t.created_at,
            MIN(m.timestamp) as first_response
        FROM tickets t
        JOIN messages m ON t.channel_id = m.channel_id
        WHERE t.guild_id = ? AND t.created_at >= ?
            AND m.author_id != t.user_id
        GROUP BY t.id
        """
        
        # For now, return a simple structure with hourly buckets
        hours = ["0-1", "1-2", "2-4", "4-8", "8-24", "24+"]
        counts = [0, 0, 0, 0, 0, 0]
        
        return {
            "hours": hours,
            "counts": counts
        }
        
    except Exception as e:
        logger.error(f"Error getting response time metrics: {e}")
        return {
            "hours": [],
            "counts": []
        }
    finally:
        if conn:
            conn.close()

def get_ticket_resolution_rate(guild_id, days=30):
    """Get ticket resolution rate"""
    conn = None
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        
        # Calculate the start date
        start_date = datetime.datetime.now() - datetime.timedelta(days=days)
        start_date_str = start_date.strftime("%Y-%m-%d 00:00:00")
        
        # Get total tickets
        cursor.execute('''
        SELECT COUNT(*) FROM tickets
        WHERE guild_id = ? AND created_at >= ?
        ''', (guild_id, start_date_str))
        
        total = cursor.fetchone()[0]
        
        # Get closed tickets
        cursor.execute('''
        SELECT COUNT(*) FROM tickets
        WHERE guild_id = ? AND created_at >= ? AND status = 'closed'
        ''', (guild_id, start_date_str))
        
        closed = cursor.fetchone()[0]
        
        # Calculate resolution rate
        resolution_rate = (closed / total * 100) if total > 0 else 0
        
        return {
            "total": total,
            "closed": closed,
            "resolution_rate": round(resolution_rate, 2)
        }
        
    except Exception as e:
        logger.error(f"Error getting ticket resolution rate: {e}")
        return {
            "total": 0,
            "closed": 0,
            "resolution_rate": 0
        }
    finally:
        if conn:
            conn.close()

def get_user_metrics(guild_id, days=30, limit=10):
    """Get metrics for most active users creating tickets"""
    conn = None
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        
        # Calculate the start date
        start_date = datetime.datetime.now() - datetime.timedelta(days=days)
        start_date_str = start_date.strftime("%Y-%m-%d 00:00:00")
        
        # Get users with most tickets
        cursor.execute('''
        SELECT 
            user_id,
            COUNT(*) as ticket_count
        FROM tickets
        WHERE guild_id = ? AND created_at >= ?
        GROUP BY user_id
        ORDER BY ticket_count DESC
        LIMIT ?
        ''', (guild_id, start_date_str, limit))
        
        users = []
        counts = []
        
        for row in cursor.fetchall():
            users.append(str(row[0]))  # Convert to string for chart compatibility
            counts.append(row[1])
        
        return {
            "users": users,
            "counts": counts
        }
        
    except Exception as e:
        logger.error(f"Error getting user metrics: {e}")
        return {
            "users": [],
            "counts": []
        }
    finally:
        if conn:
            conn.close()

def get_full_analytics_data(guild_id, days=30):
    """Get all analytics data in one call"""
    return {
        "ticket_counts": get_ticket_counts(guild_id, days),
        "type_distribution": get_ticket_type_distribution(guild_id, days),
        "response_times": get_response_time_metrics(guild_id, days),
        "resolution_rate": get_ticket_resolution_rate(guild_id, days),
        "user_metrics": get_user_metrics(guild_id, days)
    }