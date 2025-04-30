import discord
from discord import app_commands
from discord.ext import commands
import logging
import asyncio
import os
from datetime import datetime
from typing import Optional, Literal
from utils.database import (
    get_guild_config, get_panel_by_message, create_ticket,
    get_ticket_by_channel, close_ticket, get_active_ticket_count,
    archive_ticket, delete_ticket_data, get_db_connection
)
from utils.embeds import (
    create_ticket_embed, create_ticket_closed_embed,
    create_ticket_log_embed, create_error_embed
)
from utils.config import get_config

# Set up logging
logger = logging.getLogger(__name__)

class TicketHandlers(commands.Cog):
    """Event handlers for ticket interactions"""

    def __init__(self, bot):
        self.bot = bot
        # Store ticket close tasks to cancel them if reopened
        self.close_tasks = {}

    # Listen for button clicks
    @commands.Cog.listener()
    async def on_interaction(self, interaction: discord.Interaction):
        """Handle button interactions"""
        if not interaction.type == discord.InteractionType.component:
            return

        # Get the custom ID
        custom_id = interaction.data.get('custom_id', '')

        # Create a unique identifier for the interaction to prevent multiple instances from handling it
        interaction_id = f"{interaction.id}_{interaction.user.id}"
        
        # Use a file-based mutex system for handling interactions
        mutex_dir = ".interaction_locks"
        os.makedirs(mutex_dir, exist_ok=True)
        mutex_file = f"{mutex_dir}/{interaction_id}.lock"
        
        # Check if another instance is already handling this interaction
        if os.path.exists(mutex_file):
            logger.info(f"Another instance is already handling interaction {interaction_id}")
            return
            
        try:
            # Create a lock file to indicate we're handling this interaction
            with open(mutex_file, 'w') as f:
                f.write(str(datetime.now()))
                
            # Handle ticket creation button
            if custom_id.startswith('create_ticket:'):
                await self.handle_create_ticket(interaction)

            # Handle ticket close button
            elif custom_id == 'close_ticket':
                await self.handle_close_ticket(interaction)

            # Handle ticket reopen button
            elif custom_id == 'reopen_ticket':
                await self.handle_reopen_ticket(interaction)
        except discord.errors.NotFound:
            logger.warning(f"Interaction not found error when handling {custom_id}")
        except discord.errors.InteractionResponded:
            logger.warning(f"Interaction already responded for {custom_id}")
        except Exception as e:
            logger.error(f"Error handling interaction {custom_id}: {e}")
            try:
                # Try to respond with an error message if we haven't responded yet
                if not interaction.response.is_done():
                    await interaction.response.send_message(
                        "An error occurred while processing this action. Please try again.", 
                        ephemeral=True
                    )
            except:
                # If we can't respond, ignore and log
                logger.error("Could not send error message for interaction")
                pass
        finally:
            # Remove the lock file to allow future interactions
            try:
                if os.path.exists(mutex_file):
                    os.remove(mutex_file)
            except Exception as e:
                logger.error(f"Error removing lock file: {e}")

    async def handle_create_ticket(self, interaction: discord.Interaction):
        """Handle ticket creation button click with auto-response"""
        # Get guild ID from custom ID
        guild_id = int(interaction.data['custom_id'].split(':')[1])

        # Safely defer the response to avoid timeout
        try:
            await interaction.response.defer(ephemeral=True)
            response_deferred = True
        except (discord.errors.NotFound, discord.errors.InteractionResponded):
            # If interaction is already acknowledged or not found, we'll use followup
            response_deferred = False
            logger.warning("Interaction was already acknowledged in handle_create_ticket")

        # Get guild config
        guild_config = get_guild_config(guild_id)
        if not guild_config or not guild_config.get('category_id'):
            await interaction.followup.send(
                embed=create_error_embed(
                    "Setup Required",
                    "The ticket system has not been properly set up. Please contact an administrator."
                ),
                ephemeral=True
            )
            return

        # Check if user has reached the maximum number of tickets
        max_tickets = guild_config.get('max_tickets', 3)
        active_tickets = get_active_ticket_count(guild_id, interaction.user.id)

        if active_tickets >= max_tickets:
            await interaction.followup.send(
                embed=create_error_embed(
                    "Too Many Tickets",
                    f"You already have {active_tickets} open tickets. Please close some before creating new ones."
                ),
                ephemeral=True
            )
            return

        # Get panel information
        panel = get_panel_by_message(guild_id, interaction.message.id)
        panel_id = panel['panel_id'] if panel else None

        # Get ticket configuration
        config = get_config()
        ticket_naming_format = config.get('ticket_naming_format', 'ticket-{user}')

        # Create channel name
        channel_name = ticket_naming_format.format(
            user=interaction.user.name.lower(),
            user_id=interaction.user.id,
            count=active_tickets + 1
        )
        # Remove any characters that aren't allowed in channel names
        channel_name = ''.join(c for c in channel_name if c.isalnum() or c in '-_')

        # Get category
        category = interaction.guild.get_channel(guild_config['category_id'])
        if not category:
            await interaction.followup.send(
                embed=create_error_embed(
                    "Category Not Found",
                    "The ticket category could not be found. Please contact an administrator."
                ),
                ephemeral=True
            )
            return

        try:
            # Create permission overwrites
            overwrites = {
                interaction.guild.default_role: discord.PermissionOverwrite(read_messages=False),
                interaction.user: discord.PermissionOverwrite(read_messages=True, send_messages=True),
                interaction.guild.me: discord.PermissionOverwrite(read_messages=True, send_messages=True)
            }

            # Add support role permissions if configured
            if guild_config.get('support_role_id'):
                support_role = interaction.guild.get_role(guild_config['support_role_id'])
                if support_role:
                    overwrites[support_role] = discord.PermissionOverwrite(read_messages=True, send_messages=True)

            # Add admin role permissions if configured
            if guild_config.get('admin_role_id'):
                admin_role = interaction.guild.get_role(guild_config['admin_role_id'])
                if admin_role:
                    overwrites[admin_role] = discord.PermissionOverwrite(read_messages=True, send_messages=True)

            # Create the ticket channel
            channel = await category.create_text_channel(
                name=channel_name,
                overwrites=overwrites,
                topic=f"Ticket for {interaction.user.name} | User ID: {interaction.user.id}"
            )

            # Create ticket in database
            ticket_id = create_ticket(guild_id, channel.id, interaction.user.id, panel_id)

            if not ticket_id:
                # Failed to create ticket in database
                await channel.delete(reason="Failed to create ticket record in database")
                await interaction.followup.send(
                    embed=create_error_embed(
                        "Error",
                        "Failed to create ticket. Please try again later."
                    ),
                    ephemeral=True
                )
                return

            # Create ticket embed
            ticket_embed = create_ticket_embed(interaction.user, interaction.guild, ticket_id)

            # Get custom close button text/emoji if available from panel
            close_button_text = "Close Ticket"
            close_button_emoji = "🔒"

            if panel:
                close_button_text = panel.get('close_button_text', close_button_text)
                close_button_emoji = panel.get('close_button_emoji', close_button_emoji)

            # Create close button with custom or default text/emoji
            close_button = discord.ui.Button(
                style=discord.ButtonStyle.danger,
                label=close_button_text,
                emoji=close_button_emoji,
                custom_id="close_ticket"
            )

            # Create view with close button
            view = discord.ui.View(timeout=None)
            view.add_item(close_button)

            # Get auto-response based on panel type
            panel_type = "general"
            if panel and 'panel_title' in panel:
                if "GAMING" in panel['panel_title'].upper():
                    panel_type = "gaming"
                elif "BILLING" in panel['panel_title'].upper():
                    panel_type = "billing"
            
            # Import and use the auto-response module
            from utils.auto_responses import get_response
            auto_response = get_response(panel_type)

            # Send ticket message with auto-response
            await channel.send(
                f"{interaction.user.mention} {self._get_support_mentions(guild_config, interaction.guild)}", 
                embed=ticket_embed,
                view=view
            )

            if auto_response:
                response_embed = discord.Embed(
                    description=auto_response,
                    color=0x5865F2
                )
                await channel.send(embed=response_embed)

            # Send success message to user
            await interaction.followup.send(
                embed=discord.Embed(
                    title="Ticket Created",
                    description=f"Your ticket has been created in {channel.mention}",
                    color=0x57F287  # Discord Green
                ),
                ephemeral=True
            )

            # Log ticket creation if log channel is configured
            if guild_config.get('log_channel_id'):
                log_channel = interaction.guild.get_channel(guild_config['log_channel_id'])
                if log_channel:
                    panel_type = panel['panel_title'] if panel else "Standard Ticket"
                    log_embed = create_ticket_log_embed(
                        panel_type, interaction.user, ticket_id, channel.name, "created"
                    )
                    await log_channel.send(embed=log_embed)

        except Exception as e:
            logger.error(f"Error creating ticket channel: {e}")
            await interaction.followup.send(
                embed=create_error_embed(
                    "Error",
                    f"An error occurred while creating your ticket: {str(e)}"
                ),
                ephemeral=True
            )

    def _get_support_mentions(self, guild_config, guild):
        """Get mentions for support staff"""
        mentions = []

        # Add support role mention if configured
        if guild_config.get('support_role_id'):
            support_role = guild.get_role(guild_config['support_role_id'])
            if support_role:
                mentions.append(support_role.mention)

        # Return mentions as a string
        return " ".join(mentions)

    async def handle_close_ticket(self, interaction: discord.Interaction):
        """Handle ticket close button click"""
        # Only one instance should handle the interaction - we'll remove the check so one instance always processes it
        # since the PRIMARY_BOT_INSTANCE flag may not be properly set in all environments
            
        # Safely defer the response to avoid timeout and handle already acknowledged errors
        try:
            await interaction.response.defer(ephemeral=False)
            response_deferred = True
        except (discord.errors.NotFound, discord.errors.InteractionResponded) as e:
            # If interaction is already acknowledged or not found, we'll use followup
            logger.warning(f"Error handling close_ticket interaction: {e}")
            response_deferred = False
            
        # Get ticket info
        ticket = get_ticket_by_channel(interaction.guild.id, interaction.channel.id)
        if not ticket:
            try:
                if response_deferred:
                    await interaction.followup.send(
                        embed=create_error_embed(
                            "Not a Ticket",
                            "This channel is not a ticket channel."
                        )
                    )
                else:
                    await interaction.channel.send(
                        embed=create_error_embed(
                            "Not a Ticket",
                            "This channel is not a ticket channel."
                        )
                    )
            except Exception as e:
                logger.error(f"Error sending ticket info message: {e}")
            return

        # Check if ticket is already closed
        if ticket['status'] != 'open':
            await interaction.followup.send(
                embed=create_error_embed(
                    "Already Closed",
                    "This ticket is already closed."
                )
            )
            return

        # Close the ticket
        success = close_ticket(interaction.guild.id, interaction.channel.id)
        if not success:
            await interaction.followup.send(
                embed=create_error_embed(
                    "Error",
                    "Failed to close the ticket. Please try again."
                )
            )
            return

        # Create closed embed
        closed_embed = discord.Embed(
            title="『🔒』𝐓𝐈𝐂𝐊𝐄𝐓 𝐂𝐋𝐎𝐒𝐄𝐃『🔒』",
            description=f"╭────━━━━━━━━[ 🎯 ]━━━━━━━━────╮\nThis ticket has been closed.\nThe channel will be deleted in 30 seconds.\n╰────━━━━━━━━━━━━━━━━━━━━────╯",
            color=0xFF0000
        )

        # Create reopen button
        reopen_button = discord.ui.Button(
            style=discord.ButtonStyle.success,
            label="Reopen Ticket",
            emoji="🔓",
            custom_id="reopen_ticket"
        )

        # Create view with reopen button
        view = discord.ui.View(timeout=None)
        view.add_item(reopen_button)

        # Send closed message
        await interaction.followup.send(embed=closed_embed, view=view)

        # Update channel permissions for the ticket creator
        creator = interaction.guild.get_member(ticket['user_id'])
        if creator:
            await interaction.channel.set_permissions(
                creator,
                read_messages=True,
                send_messages=False
            )

        # Log ticket closure
        guild_config = get_guild_config(interaction.guild.id)
        if guild_config and guild_config.get('log_channel_id'):
            log_channel = interaction.guild.get_channel(guild_config['log_channel_id'])
            if log_channel:
                panel_type = "Unknown"
                if ticket['panel_id']:
                    panel = self._get_panel_by_id(ticket['panel_id'])
                    panel_type = panel['panel_title'] if panel else "Standard Ticket"

                log_embed = create_ticket_log_embed(
                    panel_type, creator or await self.bot.fetch_user(ticket['user_id']), 
                    ticket['ticket_id'], interaction.channel.name, "closed",
                    interaction.user
                )
                await log_channel.send(embed=log_embed)

        # Schedule ticket deletion
        config = get_config()
        close_delay = 30  # Force 30 seconds delay

        # Cancel any existing task for this channel
        if interaction.channel.id in self.close_tasks:
            self.close_tasks[interaction.channel.id].cancel()

        # Schedule new deletion task
        task = asyncio.create_task(self._delete_ticket_channel(interaction.channel, close_delay))
        self.close_tasks[interaction.channel.id] = task

    def _get_panel_by_id(self, panel_id):
        """Get panel information by ID"""
        conn = get_db_connection()
        try:
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM ticket_panels WHERE panel_id = ?", (panel_id,))
            result = cursor.fetchone()
            return dict(result) if result else None
        finally:
            conn.close()

    async def _delete_ticket_channel(self, channel, delay):
        """Delete a ticket channel after a delay"""
        try:
            # Wait for the specified delay
            await asyncio.sleep(delay)

            # Archive the ticket
            guild_id = channel.guild.id
            channel_id = channel.id
            archive_ticket(guild_id, channel_id)

            # Delete the channel
            await channel.delete(reason="Ticket closed and auto-deleted")

            # Remove from close tasks
            if channel_id in self.close_tasks:
                del self.close_tasks[channel_id]

            # Delete ticket data
            delete_ticket_data(guild_id, channel_id)

        except asyncio.CancelledError:
            # Task was cancelled, probably because ticket was reopened
            pass
        except discord.NotFound:
            # Channel already deleted
            pass
        except Exception as e:
            logger.error(f"Error deleting ticket channel: {e}")

    async def handle_reopen_ticket(self, interaction: discord.Interaction):
        """Handle ticket reopen button click"""
        # Only one instance should handle the interaction - we'll remove the check so one instance always processes it
        # since the PRIMARY_BOT_INSTANCE flag may not be properly set in all environments
            
        # Safely defer the response to avoid timeout and handle already acknowledged errors
        try:
            await interaction.response.defer(ephemeral=False)
            response_deferred = True
        except (discord.errors.NotFound, discord.errors.InteractionResponded) as e:
            # If interaction is already acknowledged or not found, we'll use followup
            logger.warning(f"Error handling reopen_ticket interaction: {e}")
            response_deferred = False
            
        # Get ticket info
        ticket = get_ticket_by_channel(interaction.guild.id, interaction.channel.id)
        if not ticket:
            try:
                if response_deferred:
                    await interaction.followup.send(
                        embed=create_error_embed(
                            "Not a Ticket",
                            "This channel is not a ticket channel."
                        )
                    )
                else:
                    await interaction.channel.send(
                        embed=create_error_embed(
                            "Not a Ticket",
                            "This channel is not a ticket channel."
                        )
                    )
            except Exception as e:
                logger.error(f"Error sending ticket info message: {e}")
            return

        # Check if ticket is closed
        if ticket['status'] != 'closed':
            await interaction.followup.send(
                embed=create_error_embed(
                    "Not Closed",
                    "This ticket is not closed, so it cannot be reopened."
                )
            )
            return

        # Reopen the ticket in the database
        conn = get_db_connection()
        try:
            cursor = conn.cursor()
            cursor.execute('''
            UPDATE tickets 
            SET status = 'open', closed_at = NULL
            WHERE guild_id = ? AND channel_id = ? AND status = 'closed'
            ''', (interaction.guild.id, interaction.channel.id))
            conn.commit()
            success = cursor.rowcount > 0
        except Exception as e:
            logger.error(f"Error reopening ticket: {e}")
            success = False
            conn.rollback()
        finally:
            conn.close()

        if not success:
            await interaction.followup.send(
                embed=create_error_embed(
                    "Error",
                    "Failed to reopen the ticket. Please try again."
                )
            )
            return

        # Cancel the deletion task if it exists
        if interaction.channel.id in self.close_tasks:
            self.close_tasks[interaction.channel.id].cancel()
            del self.close_tasks[interaction.channel.id]

        # Update channel permissions for the ticket creator
        creator = interaction.guild.get_member(ticket['user_id'])
        if creator:
            await interaction.channel.set_permissions(
                creator,
                read_messages=True,
                send_messages=True
            )

        # Create reopen embed
        reopen_embed = discord.Embed(
            title="Ticket Reopened",
            description=f"This ticket has been reopened by {interaction.user.mention}.",
            color=0xFEE75C  # Discord Yellow
        )

        # Create close button
        close_button = discord.ui.Button(
            style=discord.ButtonStyle.danger,
            label="Close Ticket",
            emoji="🔒",
            custom_id="close_ticket"
        )

        # Create view with close button
        view = discord.ui.View(timeout=None)
        view.add_item(close_button)

        # Send reopened message
        await interaction.followup.send(embed=reopen_embed, view=view)

        # Log ticket reopening
        guild_config = get_guild_config(interaction.guild.id)
        if guild_config and guild_config.get('log_channel_id'):
            log_channel = interaction.guild.get_channel(guild_config['log_channel_id'])
            if log_channel:
                panel_type = "Unknown"
                if ticket['panel_id']:
                    panel = self._get_panel_by_id(ticket['panel_id'])
                    panel_type = panel['panel_title'] if panel else "Standard Ticket"

                log_embed = create_ticket_log_embed(
                    panel_type, creator or await self.bot.fetch_user(ticket['user_id']), 
                    ticket['ticket_id'], interaction.channel.name, "reopened",
                    interaction.user
                )
                await log_channel.send(embed=log_embed)

    @commands.Cog.listener()
    async def on_raw_reaction_add(self, payload):
        """Handle ticket closing via reaction"""
        # Ignore bot reactions
        if payload.member and payload.member.bot:
            return

        # Check if the reaction is the close emoji
        if str(payload.emoji) != "🔒":
            return

        # Get the channel
        channel = self.bot.get_channel(payload.channel_id)
        if not channel:
            return

        # Check if this is a ticket channel
        ticket = get_ticket_by_channel(payload.guild_id, payload.channel_id)
        if not ticket or ticket['status'] != 'open':
            return

        # Get the guild config
        guild_config = get_guild_config(payload.guild_id)
        if not guild_config:
            return

        # Check if the user has permission to close tickets
        member = channel.guild.get_member(payload.user_id)
        can_close = False

        # Ticket creator can close
        if member.id == ticket['user_id']:
            can_close = True

        # Server admins can close
        elif member.guild_permissions.administrator:
            can_close = True

        # Support role can close
        elif guild_config.get('support_role_id'):
            support_role = channel.guild.get_role(guild_config['support_role_id'])
            if support_role and support_role in member.roles:
                can_close = True

        # Admin role can close
        elif guild_config.get('admin_role_id'):
            admin_role = channel.guild.get_role(guild_config['admin_role_id'])
            if admin_role and admin_role in member.roles:
                can_close = True

        if not can_close:
            return

        # Create a mock interaction for the close handler
        class MockInteraction:
            def __init__(self, user, guild, channel):
                self.user = user
                self.guild = guild
                self.channel = channel
                self.data = {"custom_id": "close_ticket"}

            # Define response and followup as properties instead of async methods
            @property
            def response(self):
                class MockResponse:
                    async def defer(self, ephemeral=False):
                        pass
                return MockResponse()

            @property
            def followup(self):
                class MockFollowup:
                    async def send(self, embed=None, view=None):
                        if embed and view:
                            await channel.send(embed=embed, view=view)
                        elif embed:
                            await channel.send(embed=embed)
                return MockFollowup()

        # Create mock interaction - properties are accessed directly
        mock_interaction = MockInteraction(member, channel.guild, channel)

        # Handle the close ticket
        await self.handle_close_ticket(mock_interaction)

    # Command to tag a ticket
    @app_commands.command(name="tag", description="Add or remove a tag from the ticket")
    @app_commands.describe(
        action="Whether to add or remove the tag",
        tag="The tag to add/remove"
    )
    @app_commands.choices(
        action=[
            app_commands.Choice(name="add", value="add"),
            app_commands.Choice(name="remove", value="remove")
        ]
    )
    async def tag_ticket_command(
        self,
        interaction: discord.Interaction,
        action: Literal["add", "remove"],
        tag: str
    ):
        """Add or remove a tag from a ticket"""
        await interaction.response.defer(ephemeral=True)
        
        # Get ticket info
        ticket = get_ticket_by_channel(interaction.guild.id, interaction.channel.id)
        if not ticket:
            await interaction.followup.send(
                embed=create_error_embed(
                    "Not a Ticket",
                    "This channel is not a ticket channel."
                ),
                ephemeral=True
            )
            return
            
        # Import the tag utilities
        from utils.ticket_tags import add_tag_to_ticket, remove_tag_from_ticket, get_ticket_tags
        
        if action == "add":
            # Add the tag to the ticket
            result = add_tag_to_ticket(
                ticket["id"], 
                tag.lower(), 
                interaction.guild.id,
                interaction.user.id
            )
            
            if result:
                await interaction.followup.send(
                    embed=discord.Embed(
                        title="Tag Added",
                        description=f"The tag `{tag}` has been added to this ticket.",
                        color=0x57F287  # Discord Green
                    ),
                    ephemeral=True
                )
                
                # Update the channel name to include the tag if it's the first tag
                all_tags = get_ticket_tags(ticket["id"])
                if len(all_tags) == 1:  # Only one tag, which means it's the one we just added
                    try:
                        # Format: ticket-0001-tagname
                        current_name = interaction.channel.name
                        if "-" in current_name:
                            parts = current_name.split("-", 2)
                            if len(parts) == 2:  # ticket-0001
                                new_name = f"{parts[0]}-{parts[1]}-{tag.lower()}"
                                await interaction.channel.edit(name=new_name)
                    except Exception as e:
                        logger.error(f"Error updating channel name with tag: {e}")
            else:
                await interaction.followup.send(
                    embed=create_error_embed(
                        "Error",
                        f"Failed to add tag `{tag}` to the ticket."
                    ),
                    ephemeral=True
                )
        else:  # Remove
            # Remove the tag from the ticket
            result = remove_tag_from_ticket(ticket["id"], tag.lower(), interaction.guild.id)
            
            if result:
                await interaction.followup.send(
                    embed=discord.Embed(
                        title="Tag Removed",
                        description=f"The tag `{tag}` has been removed from this ticket.",
                        color=0x57F287  # Discord Green
                    ),
                    ephemeral=True
                )
            else:
                await interaction.followup.send(
                    embed=create_error_embed(
                        "Error",
                        f"Failed to remove tag `{tag}` from the ticket. The tag may not exist."
                    ),
                    ephemeral=True
                )
                
    @app_commands.command(name="close", description="Close the current ticket")
    @app_commands.describe(reason="The reason for closing the ticket")
    async def close_command(self, interaction: discord.Interaction, reason: Optional[str] = None):
        """Close a ticket via command"""
        # Get ticket info
        ticket = get_ticket_by_channel(interaction.guild.id, interaction.channel.id)
        if not ticket:
            try:
                await interaction.response.send_message(
                    embed=create_error_embed(
                        "Not a Ticket",
                        "This command can only be used in a ticket channel."
                    ),
                    ephemeral=True
                )
            except Exception as e:
                logger.error(f"Error sending ticket not found message: {e}")
                try:
                    await interaction.channel.send(
                        embed=create_error_embed(
                            "Not a Ticket",
                            "This command can only be used in a ticket channel."
                        )
                    )
                except:
                    pass
            return

        # Check if ticket is already closed
        if ticket['status'] != 'open':
            try:
                await interaction.response.send_message(
                    embed=create_error_embed(
                        "Already Closed",
                        "This ticket is already closed."
                    ),
                    ephemeral=True
                )
            except Exception as e:
                logger.error(f"Error sending already closed message: {e}")
                try:
                    await interaction.channel.send(
                        embed=create_error_embed(
                            "Already Closed",
                            "This ticket is already closed."
                        )
                    )
                except:
                    pass
            return

        # Safely defer the response
        try:
            await interaction.response.defer(ephemeral=False)
            response_deferred = True
        except (discord.errors.NotFound, discord.errors.InteractionResponded):
            response_deferred = False

        # Close the ticket
        success = close_ticket(interaction.guild.id, interaction.channel.id)
        if not success:
            await interaction.followup.send(
                embed=create_error_embed(
                    "Error",
                    "Failed to close the ticket. Please try again."
                )
            )
            return

        # Create closed embed
        closed_embed = create_ticket_closed_embed(interaction.user, reason)

        # Create reopen button
        reopen_button = discord.ui.Button(
            style=discord.ButtonStyle.success,
            label="Reopen Ticket",
            emoji="🔓",
            custom_id="reopen_ticket"
        )

        # Create view with reopen button
        view = discord.ui.View(timeout=None)
        view.add_item(reopen_button)

        # Send closed message
        await interaction.followup.send(embed=closed_embed, view=view)

        # Update channel permissions for the ticket creator
        creator = interaction.guild.get_member(ticket['user_id'])
        if creator:
            await interaction.channel.set_permissions(
                creator,
                read_messages=True,
                send_messages=False
            )

        # Log ticket closure
        guild_config = get_guild_config(interaction.guild.id)
        if guild_config and guild_config.get('log_channel_id'):
            log_channel = interaction.guild.get_channel(guild_config['log_channel_id'])
            if log_channel:
                panel_type = "Unknown"
                if ticket['panel_id']:
                    panel = self._get_panel_by_id(ticket['panel_id'])
                    panel_type = panel['panel_title'] if panel else "Standard Ticket"

                log_embed = create_ticket_log_embed(
                    panel_type, creator or await self.bot.fetch_user(ticket['user_id']), 
                    ticket['ticket_id'], interaction.channel.name, "closed",
                    interaction.user, reason
                )
                await log_channel.send(embed=log_embed)

        # Schedule ticket deletion
        config = get_config()
        close_delay = 30  # Force 30 seconds delay

        # Cancel any existing task for this channel
        if interaction.channel.id in self.close_tasks:
            self.close_tasks[interaction.channel.id].cancel()

        # Schedule new deletion task
        task = asyncio.create_task(self._delete_ticket_channel(interaction.channel, close_delay))
        self.close_tasks[interaction.channel.id] = task

    # Command to reopen a ticket via command
    @app_commands.command(name="reopen", description="Reopen the current ticket")
    async def reopen_command(self, interaction: discord.Interaction):
        """Reopen a ticket via command"""
        # Get ticket info
        ticket = get_ticket_by_channel(interaction.guild.id, interaction.channel.id)
        if not ticket:
            try:
                await interaction.response.send_message(
                    embed=create_error_embed(
                        "Not a Ticket",
                        "This command can only be used in a ticket channel."
                    ),
                    ephemeral=True
                )
            except Exception as e:
                logger.error(f"Error sending ticket not found message: {e}")
                try:
                    await interaction.channel.send(
                        embed=create_error_embed(
                            "Not a Ticket",
                            "This command can only be used in a ticket channel."
                        )
                    )
                except:
                    pass
            return

        # Check if ticket is closed
        if ticket['status'] != 'closed':
            try:
                await interaction.response.send_message(
                    embed=create_error_embed(
                        "Not Closed",
                        "This ticket is not closed, so it cannot be reopened."
                    ),
                    ephemeral=True
                )
            except Exception as e:
                logger.error(f"Error sending not closed message: {e}")
                try:
                    await interaction.channel.send(
                        embed=create_error_embed(
                            "Not Closed",
                            "This ticket is not closed, so it cannot be reopened."
                        )
                    )
                except:
                    pass
            return

        # Safely defer the response
        try:
            await interaction.response.defer(ephemeral=False)
            response_deferred = True
        except (discord.errors.NotFound, discord.errors.InteractionResponded):
            response_deferred = False

        # Reopen the ticket in the database
        conn = get_db_connection()
        try:
            cursor = conn.cursor()
            cursor.execute('''
            UPDATE tickets 
            SET status = 'open', closed_at = NULL
            WHERE guild_id = ? AND channel_id = ? AND status = 'closed'
            ''', (interaction.guild.id, interaction.channel.id))
            conn.commit()
            success = cursor.rowcount > 0
        except Exception as e:
            logger.error(f"Error reopening ticket: {e}")
            success = False
            conn.rollback()
        finally:
            conn.close()

        if not success:
            await interaction.followup.send(
                embed=create_error_embed(
                    "Error",
                    "Failed to reopen the ticket. Please try again."
                )
            )
            return

        # Cancel the deletion task if it exists
        if interaction.channel.id in self.close_tasks:
            self.close_tasks[interaction.channel.id].cancel()
            del self.close_tasks[interaction.channel.id]

        # Update channel permissions for the ticket creator
        creator = interaction.guild.get_member(ticket['user_id'])
        if creator:
            await interaction.channel.set_permissions(
                creator,
                read_messages=True,
                send_messages=True
            )

        # Create reopen embed
        reopen_embed = discord.Embed(
            title="Ticket Reopened",
            description=f"This ticket has been reopened by {interaction.user.mention}.",
            color=0xFEE75C  # Discord Yellow
        )

        # Create close button
        close_button = discord.ui.Button(
            style=discord.ButtonStyle.danger,
            label="Close Ticket",
            emoji="🔒",
            custom_id="close_ticket"
        )

        # Create view with close button
        view = discord.ui.View(timeout=None)
        view.add_item(close_button)

        # Send reopened message
        await interaction.followup.send(embed=reopen_embed, view=view)

        # Log ticket reopening
        guild_config = get_guild_config(interaction.guild.id)
        if guild_config and guild_config.get('log_channel_id'):
            log_channel = interaction.guild.get_channel(guild_config['log_channel_id'])
            if log_channel:
                panel_type = "Unknown"
                if ticket['panel_id']:
                    panel = self._get_panel_by_id(ticket['panel_id'])
                    panel_type = panel['panel_title'] if panel else "Standard Ticket"

                log_embed = create_ticket_log_embed(
                    panel_type, creator or await self.bot.fetch_user(ticket['user_id']), 
                    ticket['ticket_id'], interaction.channel.name, "reopened",
                    interaction.user
                )
                await log_channel.send(embed=log_embed)

async def setup(bot):
    """Add the cog to the bot"""
    await bot.add_cog(TicketHandlers(bot))