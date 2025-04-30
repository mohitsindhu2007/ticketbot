
import discord
from discord import app_commands
from discord.ext import commands
import re
import logging
from utils.database import get_db_connection

# Set up logging
logger = logging.getLogger(__name__)

class LinkFilter(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        # Improved URL pattern to detect more links
        self.url_pattern = re.compile(
            r'(https?:\/\/(?:www\.|(?!www))[a-zA-Z0-9][a-zA-Z0-9-]+[a-zA-Z0-9]\.[^\s]{2,}|www\.[a-zA-Z0-9][a-zA-Z0-9-]+[a-zA-Z0-9]\.[^\s]{2,}|https?:\/\/(?:www\.|(?!www))[a-zA-Z0-9]+\.[^\s]{2,}|www\.[a-zA-Z0-9]+\.[^\s]{2,}|discord\.gg\/\w+)'
        )
        
        # Create table if not exists in main database
        conn = get_db_connection()
        try:
            cursor = conn.cursor()
            cursor.execute('''
            CREATE TABLE IF NOT EXISTS link_filter_roles (
                guild_id INTEGER,
                role_id INTEGER,
                added_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                PRIMARY KEY (guild_id, role_id)
            )
            ''')
            conn.commit()
            logger.info("Link filter database initialized successfully")
        except Exception as e:
            logger.error(f"Error initializing link filter database: {e}")
            if conn:
                conn.rollback()
        finally:
            if conn:
                conn.close()

    @app_commands.command(name="linkfilter", description="Enable or disable link filter for a role")
    @app_commands.describe(
        action="Enable or disable link permissions",
        role="The role to update permissions for"
    )
    @app_commands.choices(action=[
        app_commands.Choice(name="enable", value="enable"),
        app_commands.Choice(name="disable", value="disable")
    ])
    async def linkfilter(self, interaction: discord.Interaction, action: str, role: discord.Role):
        # Check for admin permissions
        try:
            if not interaction.user.guild_permissions.administrator:
                await interaction.response.send_message("You need administrator permissions to manage link filter!", ephemeral=True)
                return
        except (discord.errors.NotFound, discord.errors.InteractionResponded):
            logger.warning("Interaction already acknowledged in linkfilter permission check")
            return

        # Safely defer response to prevent timeout
        try:
            await interaction.response.defer(ephemeral=True)
            response_deferred = True
        except (discord.errors.NotFound, discord.errors.InteractionResponded):
            # If interaction is already acknowledged or not found, we'll use followup
            response_deferred = False
            logger.warning("Interaction already acknowledged in linkfilter defer")
        
        conn = None
        try:
            conn = get_db_connection()
            cursor = conn.cursor()

            if action == "enable":
                cursor.execute('''
                INSERT OR REPLACE INTO link_filter_roles (guild_id, role_id)
                VALUES (?, ?)
                ''', (interaction.guild.id, role.id))
                conn.commit()
                await interaction.followup.send(
                    f"✅ **Link Permission Granted**: {role.mention} can now send links in this server.", 
                    ephemeral=True
                )
                logger.info(f"Enabled link filter for role {role.id} in guild {interaction.guild.id}")
            else:
                cursor.execute('''
                DELETE FROM link_filter_roles 
                WHERE guild_id = ? AND role_id = ?
                ''', (interaction.guild.id, role.id))
                conn.commit()
                await interaction.followup.send(
                    f"❌ **Link Permission Revoked**: {role.mention} can no longer send links in this server.", 
                    ephemeral=True
                )
                logger.info(f"Disabled link filter for role {role.id} in guild {interaction.guild.id}")
        except Exception as e:
            logger.error(f"Error updating link filter: {e}")
            if conn:
                conn.rollback()
            await interaction.followup.send(
                f"❌ **Error**: Failed to update link filter settings. Please try again.",
                ephemeral=True
            )
        finally:
            if conn:
                conn.close()

    @app_commands.command(name="listlinkroles", description="List roles that can send links")
    async def list_link_roles(self, interaction: discord.Interaction):
        """List all roles that can send links"""
        # Safely defer response to prevent timeout
        try:
            await interaction.response.defer(ephemeral=True)
            response_deferred = True
        except (discord.errors.NotFound, discord.errors.InteractionResponded):
            # If interaction is already acknowledged or not found, we'll use followup
            response_deferred = False
            logger.warning("Interaction already acknowledged in list_link_roles")
        
        conn = None
        try:
            conn = get_db_connection()
            cursor = conn.cursor()
            
            cursor.execute('''
            SELECT role_id FROM link_filter_roles 
            WHERE guild_id = ?
            ''', (interaction.guild.id,))
            allowed_role_ids = [row[0] for row in cursor.fetchall()]
            
            if not allowed_role_ids:
                await interaction.followup.send(
                    "🔍 There are no roles configured for link permissions. All members can send links.",
                    ephemeral=True
                )
                return
                
            # Get actual role objects from IDs
            allowed_roles = []
            for role_id in allowed_role_ids:
                role = interaction.guild.get_role(role_id)
                if role:
                    allowed_roles.append(role.mention)
            
            # Create embed with list of roles
            embed = discord.Embed(
                title="🔗 Link Permission Roles",
                description="The following roles can send links in this server:",
                color=0x3498db
            )
            embed.add_field(
                name="Allowed Roles",
                value="\n".join(allowed_roles) if allowed_roles else "No valid roles found"
            )
            embed.set_footer(text="Users without these roles cannot send links if link filtering is enabled")
            
            await interaction.followup.send(embed=embed, ephemeral=True)
            
        except Exception as e:
            logger.error(f"Error listing link roles: {e}")
            await interaction.followup.send(
                "❌ **Error**: Failed to retrieve link filter roles. Please try again.",
                ephemeral=True
            )
        finally:
            if conn:
                conn.close()

    @commands.Cog.listener()
    async def on_message(self, message: discord.Message):
        """Check messages for links and filter if needed"""
        # Ignore messages from bots or DMs
        if message.author.bot or not message.guild:
            return
            
        # Check if message contains a URL
        if not self.url_pattern.search(message.content):
            return
            
        # Allow server admins and moderators to post links regardless of roles
        if message.author.guild_permissions.administrator or message.author.guild_permissions.manage_messages:
            return
            
        conn = None
        try:
            conn = get_db_connection()
            cursor = conn.cursor()
            
            # Get allowed roles for this guild
            cursor.execute('''
            SELECT role_id FROM link_filter_roles 
            WHERE guild_id = ?
            ''', (message.guild.id,))
            allowed_roles = [row[0] for row in cursor.fetchall()]
            
            # If no roles are set up, allow all links
            if not allowed_roles:
                return

            # Check if user has any of the allowed roles
            user_roles = [role.id for role in message.author.roles]
            can_post_links = any(role_id in user_roles for role_id in allowed_roles)
            
            # If user can't post links, delete the message and notify
            if not can_post_links:
                try:
                    await message.delete()
                    warning = await message.channel.send(
                        f"⚠️ {message.author.mention} You don't have permission to send links in this channel!",
                        delete_after=5
                    )
                    logger.info(f"Deleted link message from {message.author.id} in guild {message.guild.id}")
                except discord.Forbidden:
                    logger.warning(f"No permission to delete message in guild {message.guild.id}")
                except Exception as e:
                    logger.error(f"Error deleting link message: {e}")
        except Exception as e:
            logger.error(f"Error checking link permissions: {e}")
        finally:
            if conn:
                conn.close()

async def setup(bot):
    """Add the cog to the bot"""
    await bot.add_cog(LinkFilter(bot))
    logger.info("Link Filter cog loaded successfully")
