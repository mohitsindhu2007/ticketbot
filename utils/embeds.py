import discord
import datetime
import re
from utils.config import get_config

# Brand color (Discord Blurple)
BRAND_COLOR = 0x5865F2

def create_ticket_panel_embed(title=None, description=None, color=None, image_url=None, guild=None, header_image_url=None, footer_image_url=None):
    """
    Create an embed for a ticket panel with improved image handling
    
    This function creates Discord embeds for ticket panels, with optimized
    handling of images to ensure they don't waste space in the embed.
    """
    config = get_config()
    
    # Use provided values or defaults
    title = title or config.get("default_panel_title")
    description = description or config.get("default_panel_description")
    color = color or config.get("default_panel_color", BRAND_COLOR)
    
    # Clean up description text - remove multiple newlines to save space
    if description:
        # Replace multiple newlines with a maximum of two
        description = re.sub(r'\n{3,}', '\n\n', description)
        
        # Make sure the description doesn't exceed 4096 characters (Discord limit)
        if len(description) > 4000:
            description = description[:3997] + "..."
    
    # Create the base embed
    embed = discord.Embed(
        title=title,
        description=description,
        color=color,
        timestamp=datetime.datetime.now()
    )
    
    # Add header image (thumbnail) with fallback to guild icon
    if header_image_url and header_image_url.strip():
        embed.set_thumbnail(url=header_image_url)
    elif guild and guild.icon:
        embed.set_thumbnail(url=guild.icon.url)
    
    # Add main image with fallback to guild banner
    # Only if there's a valid URL to avoid empty space
    if image_url and image_url.strip():
        embed.set_image(url=image_url)
    elif guild and guild.banner:
        embed.set_image(url=guild.banner.url)
    
    # Add footer image as a hyperlink in the description 
    # Only if footer_image_url is provided and not empty
    if footer_image_url and footer_image_url.strip():
        # Use a zero-width space as link text to minimize the impact on the description
        # This adds a subtle visual separator without taking too much space
        embed.description = f"{embed.description}\n\n[⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯]({footer_image_url})"
    
    # Add footer
    embed.set_footer(text="✧ 𝙿𝙷𝙰𝙽𝚃𝙾𝙼 𝙲𝙷𝙴𝙰𝚃𝚂 - 𝙿𝚛𝚎𝚖𝚒𝚞𝚖 𝙶𝚊𝚖𝚒𝚗𝚐 𝙿𝚛𝚘𝚍𝚞𝚌𝚝𝚜 ✧", 
                    icon_url="https://i.imgur.com/6YToyEF.png")
    
    return embed

def create_ticket_embed(user, guild, ticket_id):
    """Create an embed for a new ticket"""
    config = get_config()
    
    # Format the welcome message
    welcome_message = config.get("welcome_message", "").format(
        user=user.display_name,
        user_id=user.id,
        guild=guild.name,
        ticket_id=ticket_id
    )
    
    embed = discord.Embed(
        title=f"『🎯』𝐓𝐢𝐜𝐤𝐞𝐭 #{ticket_id}『🎯』",
        description=welcome_message,
        color=BRAND_COLOR,
        timestamp=datetime.datetime.now()
    )
    
    # Add user information
    embed.add_field(name="🧑‍💻 Created By", value=f"{user.mention} ({user.name})")
    embed.add_field(name="🆔 User ID", value=user.id)
    embed.add_field(name="📅 Account Created", 
                   value=discord.utils.format_dt(user.created_at, style='R'))
    
    # Add footer
    embed.set_footer(text="✧ 𝙿𝙷𝙰𝙽𝚃𝙾𝙼 𝙲𝙷𝙴𝙰𝚃𝚂 - 𝙿𝚛𝚎𝚖𝚒𝚞𝚖 𝙶𝚊𝚖𝚒𝚗𝚐 𝙿𝚛𝚘𝚍𝚞𝚌𝚝𝚜 ✧", 
                    icon_url="https://i.imgur.com/6YToyEF.png")
    
    # Add user avatar as thumbnail
    embed.set_thumbnail(url=user.display_avatar.url)
    
    return embed

def create_ticket_closed_embed(closer, reason=None):
    """Create an embed for when a ticket is closed"""
    config = get_config()
    close_message = config.get("default_close_message", "")
    
    embed = discord.Embed(
        title="『🔒』𝐓𝐢𝐜𝐤𝐞𝐭 𝐂𝐥𝐨𝐬𝐞𝐝『🔒』",
        description=close_message,
        color=0xED4245,  # Discord Red
        timestamp=datetime.datetime.now()
    )
    
    # Add closer information
    embed.add_field(name="👤 Closed By", value=f"{closer.mention} ({closer.name})")
    
    if reason:
        embed.add_field(name="📝 Reason", value=reason)
    
    # Add fancy border
    border = "╭────━━━━━━━━[ 🎯 ]━━━━━━━━────╮"
    embed.description = f"{border}\n{embed.description}\n╰────━━━━━━━━━━━━━━━━━━━━────╯"
    
    # Add footer
    embed.set_footer(text="✧ 𝙿𝙷𝙰𝙽𝚃𝙾𝙼 𝙲𝙷𝙴𝙰𝚃𝚂 - 𝙿𝚛𝚎𝚖𝚒𝚞𝚖 𝙶𝚊𝚖𝚒𝚗𝚐 𝙿𝚛𝚘𝚍𝚞𝚌𝚝𝚜 ✧", 
                    icon_url="https://i.imgur.com/6YToyEF.png")
    
    # Add thumbnail
    embed.set_thumbnail(url="https://i.imgur.com/6YToyEF.png")
    
    return embed

def create_ticket_log_embed(ticket_type, user, ticket_id, channel_name, action, mod=None, reason=None):
    """Create an embed for logging ticket actions"""
    if action == "created":
        color = 0x57F287  # Discord Green
        title = f"Ticket Created: #{ticket_id}"
    elif action == "closed":
        color = 0xED4245  # Discord Red
        title = f"Ticket Closed: #{ticket_id}"
    elif action == "reopened":
        color = 0xFEE75C  # Discord Yellow
        title = f"Ticket Reopened: #{ticket_id}"
    else:
        color = BRAND_COLOR
        title = f"Ticket Action: #{ticket_id}"
    
    embed = discord.Embed(
        title=title,
        color=color,
        timestamp=datetime.datetime.now()
    )
    
    # Add ticket information
    embed.add_field(name="User", value=f"{user.mention} ({user.name})")
    embed.add_field(name="User ID", value=user.id)
    embed.add_field(name="Channel", value=f"#{channel_name}")
    
    if ticket_type:
        embed.add_field(name="Type", value=ticket_type)
    
    if mod:
        embed.add_field(name="Moderator", value=f"{mod.mention} ({mod.name})")
    
    if reason:
        embed.add_field(name="Reason", value=reason)
    
    # Add footer
    embed.set_footer(text="Phantom Cheats Support System", 
                    icon_url="https://cdn.discordapp.com/emojis/860926301175013387.png")
    
    # Add user avatar as thumbnail
    embed.set_thumbnail(url=user.display_avatar.url)
    
    return embed

def create_error_embed(title, description):
    """Create an embed for error messages"""
    embed = discord.Embed(
        title=title,
        description=description,
        color=0xED4245,  # Discord Red
        timestamp=datetime.datetime.now()
    )
    
    embed.set_footer(text="Phantom Cheats Support System")
    
    return embed

def create_success_embed(title, description):
    """Create an embed for success messages"""
    embed = discord.Embed(
        title=title,
        description=description,
        color=0x57F287,  # Discord Green
        timestamp=datetime.datetime.now()
    )
    
    embed.set_footer(text="Phantom Cheats Support System")
    
    return embed

def create_error_embed(title, description):
    """Create an embed for error messages"""
    embed = discord.Embed(
        title=title,
        description=description,
        color=0xED4245  # Discord Red
    )
    return embed

def create_success_embed(title, description):
    """Create an embed for success messages"""
    embed = discord.Embed(
        title=title,
        description=description,
        color=0x57F287  # Discord Green
    )
    return embed

def create_settings_embed(guild_config):
    """Create an embed showing the current ticket settings"""
    embed = discord.Embed(
        title="Ticket System Settings",
        description="Current configuration for the ticket system in this server.",
        color=BRAND_COLOR,
        timestamp=datetime.datetime.now()
    )
    
    # Add settings information
    if guild_config:
        category_status = f"<#{guild_config['category_id']}>" if guild_config.get('category_id') else "Not Set"
        log_channel = f"<#{guild_config['log_channel_id']}>" if guild_config.get('log_channel_id') else "Not Set"
        admin_role = f"<@&{guild_config['admin_role_id']}>" if guild_config.get('admin_role_id') else "Not Set"
        support_role = f"<@&{guild_config['support_role_id']}>" if guild_config.get('support_role_id') else "Not Set"
        max_tickets = guild_config.get('max_tickets', "Not Set")
        
        embed.add_field(name="Ticket Category", value=category_status)
        embed.add_field(name="Log Channel", value=log_channel)
        embed.add_field(name="Admin Role", value=admin_role)
        embed.add_field(name="Support Role", value=support_role)
        embed.add_field(name="Max Tickets Per User", value=max_tickets)
    else:
        embed.description = "No settings configured yet. Use `/setup` to configure the ticket system."
    
    # Add footer
    embed.set_footer(text="Phantom Cheats Support System", 
                    icon_url="https://cdn.discordapp.com/emojis/860926301175013387.png")
    
    return embed

def create_help_embed():
    """Create an embed showing help information"""
    embed = discord.Embed(
        title="Phantom Cheats Ticket System Help",
        description="Here are the available commands for the ticket system:",
        color=BRAND_COLOR
    )
    
    # Add command sections
    embed.add_field(
        name="📋 Setup Commands", 
        value=(
            "`/setup` - Configure the ticket system\n"
            "`/settings` - View current settings"
        ),
        inline=False
    )
    
    embed.add_field(
        name="🎫 Ticket Panel Commands", 
        value=(
            "`/createpanel` - Create a ticket panel\n"
            "`/editpanel` - Edit an existing panel\n"
            "`/deletepanel` - Delete a ticket panel"
        ),
        inline=False
    )
    
    embed.add_field(
        name="🛠️ Ticket Management", 
        value=(
            "`/close` - Close a ticket\n"
            "`/reopen` - Reopen a closed ticket\n"
            "`/add` - Add a user to a ticket\n"
            "`/remove` - Remove a user from a ticket"
        ),
        inline=False
    )
    
    # Add footer
    embed.set_footer(text="Phantom Cheats Support System", 
                    icon_url="https://cdn.discordapp.com/emojis/860926301175013387.png")
    
    return embed
