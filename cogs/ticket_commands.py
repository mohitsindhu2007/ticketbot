import discord
from discord import app_commands
from discord.ext import commands
import logging
from typing import Optional, Literal
import asyncio
from utils.database import (
    get_guild_config, save_guild_config, create_ticket_panel,
    get_panel_by_message, get_guild_panels, update_ticket_panel, get_db_connection
)
from utils.embeds import (
    create_ticket_panel_embed, create_settings_embed,
    create_error_embed, create_success_embed, create_help_embed
)
from utils.config import get_config, get_template

# Set up logging
logger = logging.getLogger(__name__)

class TicketCommands(commands.Cog):
    """Commands for setting up and managing the ticket system"""

    def __init__(self, bot):
        self.bot = bot

    # Checks if the user has admin permissions
    async def is_admin(self, interaction: discord.Interaction) -> bool:
        """Check if the user has admin permissions or the admin role"""
        # Always allow server owner
        if interaction.guild.owner_id == interaction.user.id:
            return True

        # Check for administrator permission
        if interaction.user.guild_permissions.administrator:
            return True

        # Check for the configured admin role
        guild_config = get_guild_config(interaction.guild.id)
        if guild_config and guild_config.get('admin_role_id'):
            admin_role = interaction.guild.get_role(guild_config['admin_role_id'])
            if admin_role and admin_role in interaction.user.roles:
                return True

        return False

    # Setup command group
    setup_group = app_commands.Group(
        name="setup",
        description="Commands to set up the ticket system"
    )

    @setup_group.command(name="category", description="Set the category for ticket channels")
    @app_commands.describe(category="The category to create ticket channels in")
    async def setup_category(self, interaction: discord.Interaction, category: discord.CategoryChannel):
        """Set the category for ticket channels"""
        try:
            if not await self.is_admin(interaction):
                await interaction.response.send_message(
                    embed=create_error_embed("Permission Denied", "You need to be an administrator to use this command."),
                    ephemeral=True
                )
                return
        except (discord.errors.NotFound, discord.errors.InteractionResponded):
            logger.warning("Interaction already acknowledged in setup_category permission check")
            return

        guild_config = get_guild_config(interaction.guild.id) or {}
        save_guild_config(
            interaction.guild.id,
            category_id=category.id,
            log_channel_id=guild_config.get('log_channel_id'),
            admin_role_id=guild_config.get('admin_role_id'),
            support_role_id=guild_config.get('support_role_id'),
            max_tickets=guild_config.get('max_tickets', 3)
        )

        try:
            await interaction.response.send_message(
                embed=create_success_embed(
                    "Category Set",
                    f"Ticket channels will now be created in the {category.name} category."
                ),
                ephemeral=True
            )
        except (discord.errors.NotFound, discord.errors.InteractionResponded):
            logger.warning("Interaction already acknowledged in setup_category response")
            try:
                await interaction.followup.send(
                    embed=create_success_embed(
                        "Category Set",
                        f"Ticket channels will now be created in the {category.name} category."
                    ),
                    ephemeral=True
                )
            except Exception as e:
                logger.error(f"Error sending followup in setup_category: {e}")

    @setup_group.command(name="logchannel", description="Set the channel for ticket logs")
    @app_commands.describe(channel="The channel to send ticket logs to")
    async def setup_log_channel(self, interaction: discord.Interaction, channel: discord.TextChannel):
        """Set the channel for ticket logs"""
        try:
            if not await self.is_admin(interaction):
                await interaction.response.send_message(
                    embed=create_error_embed("Permission Denied", "You need to be an administrator to use this command."),
                    ephemeral=True
                )
                return
        except (discord.errors.NotFound, discord.errors.InteractionResponded):
            logger.warning("Interaction already acknowledged in setup_log_channel permission check")
            return

        guild_config = get_guild_config(interaction.guild.id) or {}
        save_guild_config(
            interaction.guild.id,
            category_id=guild_config.get('category_id'),
            log_channel_id=channel.id,
            admin_role_id=guild_config.get('admin_role_id'),
            support_role_id=guild_config.get('support_role_id'),
            max_tickets=guild_config.get('max_tickets', 3)
        )

        try:
            await interaction.response.send_message(
                embed=create_success_embed(
                    "Log Channel Set",
                    f"Ticket logs will now be sent to {channel.mention}."
                ),
                ephemeral=True
            )
        except (discord.errors.NotFound, discord.errors.InteractionResponded):
            logger.warning("Interaction already acknowledged in setup_log_channel response")
            try:
                await interaction.followup.send(
                    embed=create_success_embed(
                        "Log Channel Set",
                        f"Ticket logs will now be sent to {channel.mention}."
                    ),
                    ephemeral=True
                )
            except Exception as e:
                logger.error(f"Error sending followup in setup_log_channel: {e}")

    @setup_group.command(name="adminrole", description="Set the admin role for ticket management")
    @app_commands.describe(role="The role that will have full access to tickets")
    async def setup_admin_role(self, interaction: discord.Interaction, role: discord.Role):
        """Set the admin role for ticket management"""
        try:
            if not await self.is_admin(interaction):
                await interaction.response.send_message(
                    embed=create_error_embed("Permission Denied", "You need to be an administrator to use this command."),
                    ephemeral=True
                )
                return
        except (discord.errors.NotFound, discord.errors.InteractionResponded):
            logger.warning("Interaction already acknowledged in setup_admin_role permission check")
            return

        guild_config = get_guild_config(interaction.guild.id) or {}
        save_guild_config(
            interaction.guild.id,
            category_id=guild_config.get('category_id'),
            log_channel_id=guild_config.get('log_channel_id'),
            admin_role_id=role.id,
            support_role_id=guild_config.get('support_role_id'),
            max_tickets=guild_config.get('max_tickets', 3)
        )

        try:
            await interaction.response.send_message(
                embed=create_success_embed(
                    "Admin Role Set",
                    f"{role.mention} has been set as the admin role for tickets."
                ),
                ephemeral=True
            )
        except (discord.errors.NotFound, discord.errors.InteractionResponded):
            logger.warning("Interaction already acknowledged in setup_admin_role response")
            try:
                await interaction.followup.send(
                    embed=create_success_embed(
                        "Admin Role Set",
                        f"{role.mention} has been set as the admin role for tickets."
                    ),
                    ephemeral=True
                )
            except Exception as e:
                logger.error(f"Error sending followup in setup_admin_role: {e}")

    @setup_group.command(name="supportrole", description="Set the support role for ticket access")
    @app_commands.describe(role="The role that will have access to all tickets")
    async def setup_support_role(self, interaction: discord.Interaction, role: discord.Role):
        """Set the support role for ticket access"""
        try:
            if not await self.is_admin(interaction):
                await interaction.response.send_message(
                    embed=create_error_embed("Permission Denied", "You need to be an administrator to use this command."),
                    ephemeral=True
                )
                return
        except (discord.errors.NotFound, discord.errors.InteractionResponded):
            logger.warning("Interaction already acknowledged in setup_support_role permission check")
            return

        guild_config = get_guild_config(interaction.guild.id) or {}
        save_guild_config(
            interaction.guild.id,
            category_id=guild_config.get('category_id'),
            log_channel_id=guild_config.get('log_channel_id'),
            admin_role_id=guild_config.get('admin_role_id'),
            support_role_id=role.id,
            max_tickets=guild_config.get('max_tickets', 3)
        )

        try:
            await interaction.response.send_message(
                embed=create_success_embed(
                    "Support Role Set",
                    f"{role.mention} has been set as the support role for tickets."
                ),
                ephemeral=True
            )
        except (discord.errors.NotFound, discord.errors.InteractionResponded):
            logger.warning("Interaction already acknowledged in setup_support_role response")
            try:
                await interaction.followup.send(
                    embed=create_success_embed(
                        "Support Role Set",
                        f"{role.mention} has been set as the support role for tickets."
                    ),
                    ephemeral=True
                )
            except Exception as e:
                logger.error(f"Error sending followup in setup_support_role: {e}")

    @setup_group.command(name="maxtickets", description="Set the maximum number of tickets per user")
    @app_commands.describe(limit="The maximum number of open tickets a user can have")
    async def setup_max_tickets(self, interaction: discord.Interaction, limit: int):
        """Set the maximum number of tickets per user"""
        try:
            if not await self.is_admin(interaction):
                await interaction.response.send_message(
                    embed=create_error_embed("Permission Denied", "You need to be an administrator to use this command."),
                    ephemeral=True
                )
                return
        except (discord.errors.NotFound, discord.errors.InteractionResponded):
            logger.warning("Interaction already acknowledged in setup_max_tickets permission check")
            return

        try:
            if limit < 1 or limit > 10:
                await interaction.response.send_message(
                    embed=create_error_embed("Invalid Limit", "The limit must be between 1 and 10."),
                    ephemeral=True
                )
                return
        except (discord.errors.NotFound, discord.errors.InteractionResponded):
            logger.warning("Interaction already acknowledged in setup_max_tickets limit check")
            return

        guild_config = get_guild_config(interaction.guild.id) or {}
        save_guild_config(
            interaction.guild.id,
            category_id=guild_config.get('category_id'),
            log_channel_id=guild_config.get('log_channel_id'),
            admin_role_id=guild_config.get('admin_role_id'),
            support_role_id=guild_config.get('support_role_id'),
            max_tickets=limit
        )

        try:
            await interaction.response.send_message(
                embed=create_success_embed(
                    "Max Tickets Set",
                    f"Users can now have a maximum of {limit} open tickets."
                ),
                ephemeral=True
            )
        except (discord.errors.NotFound, discord.errors.InteractionResponded):
            logger.warning("Interaction already acknowledged in setup_max_tickets response")
            try:
                await interaction.followup.send(
                    embed=create_success_embed(
                        "Max Tickets Set",
                        f"Users can now have a maximum of {limit} open tickets."
                    ),
                    ephemeral=True
                )
            except Exception as e:
                logger.error(f"Error sending followup in setup_max_tickets: {e}")

    @app_commands.command(name="editpanel", description="Edit an existing ticket panel")
    @app_commands.describe(
        channel="The channel where the panel is located",
        message_id="The message ID of the panel to edit",
        title="The new title of the panel (optional)",
        description="The new description of the panel (optional)",
        button_text="The new text on the ticket button (optional)",
        button_emoji="The new emoji on the ticket button (optional)",
        close_button_text="The new text on the close button (optional)",
        close_button_emoji="The new emoji on the close button (optional)",
        image_url="New image URL to add to the panel (PNG, JPG, GIF) (optional)"
    )
    async def edit_panel(
        self,
        interaction: discord.Interaction,
        channel: discord.TextChannel,
        message_id: str,
        title: Optional[str] = None,
        description: Optional[str] = None,
        button_text: Optional[str] = None,
        button_emoji: Optional[str] = None,
        close_button_text: Optional[str] = None,
        close_button_emoji: Optional[str] = None,
        image_url: Optional[str] = None
    ):
        """Edit an existing ticket panel"""
        try:
            if not await self.is_admin(interaction):
                await interaction.response.send_message(
                    embed=create_error_embed("Permission Denied", "You need to be an administrator to use this command."),
                    ephemeral=True
                )
                return
        except (discord.errors.NotFound, discord.errors.InteractionResponded):
            logger.warning("Interaction already acknowledged in edit_panel permission check")
            return

        try:
            # Convert message_id to integer
            message_id = int(message_id)

            # Get panel data
            panel = get_panel_by_message(interaction.guild.id, message_id)
            if not panel:
                await interaction.response.send_message(
                    embed=create_error_embed(
                        "Panel Not Found", 
                        "No ticket panel was found with that message ID."
                    ),
                    ephemeral=True
                )
                return

            # Update panel in database
            update_success = update_ticket_panel(
                interaction.guild.id,
                message_id,
                panel_title=title,
                panel_description=description,
                button_text=button_text,
                button_emoji=button_emoji,
                close_button_text=close_button_text,
                close_button_emoji=close_button_emoji,
                image_url=image_url
            )

            if not update_success:
                await interaction.response.send_message(
                    embed=create_error_embed(
                        "Update Failed",
                        "Failed to update the panel in the database."
                    ),
                    ephemeral=True
                )
                return

            # Try to get the message to update it
            try:
                message = await channel.fetch_message(message_id)
            except discord.NotFound:
                await interaction.response.send_message(
                    embed=create_error_embed(
                        "Message Not Found", 
                        "The panel message could not be found in the specified channel."
                    ),
                    ephemeral=True
                )
                return

            # Get updated panel data
            updated_panel = get_panel_by_message(interaction.guild.id, message_id)

            # Create embed with updated values
            embed = create_ticket_panel_embed(
                title=updated_panel.get("panel_title"),
                description=updated_panel.get("panel_description"),
                color=updated_panel.get("panel_color"),
                image_url=updated_panel.get("image_url")
            )

            # Create the button with updated values
            class TicketButton(discord.ui.Button):
                def __init__(self, button_text, button_emoji):
                    super().__init__(
                        style=discord.ButtonStyle.primary,
                        label=button_text,
                        emoji=button_emoji,
                        custom_id=f"ticket_create_{panel['panel_id']}"
                    )

            view = discord.ui.View(timeout=None)
            view.add_item(TicketButton(
                updated_panel.get("button_text", "Open Ticket"),
                updated_panel.get("button_emoji", "🎫")
            ))

            # Update the message
            await message.edit(embed=embed, view=view)

            await interaction.response.send_message(
                embed=create_success_embed(
                    "Panel Updated",
                    "The ticket panel has been updated successfully."
                ),
                ephemeral=True
            )

        except ValueError:
            await interaction.response.send_message(
                embed=create_error_embed(
                    "Invalid Message ID",
                    "Please provide a valid message ID (numeric value)."
                ),
                ephemeral=True
            )
        except Exception as e:
            logger.error(f"Error updating panel: {e}")
            await interaction.response.send_message(
                embed=create_error_embed(
                    "Error",
                    f"An error occurred: {str(e)}"
                ),
                ephemeral=True
            )

    @app_commands.command(name="settings", description="View the current ticket system settings")
    async def settings(self, interaction: discord.Interaction):
        """View the current ticket system settings"""
        try:
            if not await self.is_admin(interaction):
                await interaction.response.send_message(
                    embed=create_error_embed("Permission Denied", "You need to be an administrator to use this command."),
                    ephemeral=True
                )
                return
        except (discord.errors.NotFound, discord.errors.InteractionResponded):
            logger.warning("Interaction already acknowledged in settings permission check")
            return

        guild_config = get_guild_config(interaction.guild.id)

        try:
            await interaction.response.send_message(
                embed=create_settings_embed(guild_config),
                ephemeral=True
            )
        except (discord.errors.NotFound, discord.errors.InteractionResponded):
            logger.warning("Interaction already acknowledged in settings response")
            try:
                await interaction.followup.send(
                    embed=create_settings_embed(guild_config),
                    ephemeral=True
                )
            except Exception as e:
                logger.error(f"Error sending followup in settings: {e}")

    @app_commands.command(name="createpanel", description="Create a ticket panel")
    @app_commands.describe(
        channel="The channel to send the panel to",
        template="The template to use for the panel",
        title="The title of the panel (optional)",
        description="The description of the panel (optional)",
        button_text="The text on the ticket button (optional)",
        button_emoji="The emoji on the ticket button (optional)",
        close_button_text="The text on the close button (optional)",
        close_button_emoji="The emoji on the close button (optional)",
        image_url="Image URL to add to the panel (PNG, JPG, GIF)",
        header_image_url="Header Image URL (optional)",
        footer_image_url="Footer Image URL (optional)"
    )
    async def create_panel(
        self, 
        interaction: discord.Interaction, 
        channel: discord.TextChannel,
        template: Optional[Literal["gaming", "billing", "general"]] = None,
        title: Optional[str] = None,
        description: Optional[str] = None,
        button_text: Optional[str] = None,
        button_emoji: Optional[str] = None,
        close_button_text: Optional[str] = None,
        close_button_emoji: Optional[str] = None,
        image_url: Optional[str] = None,
        header_image_url: Optional[str] = None,
        footer_image_url: Optional[str] = None
    ):
        """Create a ticket panel in a channel"""
        try:
            if not await self.is_admin(interaction):
                await interaction.response.send_message(
                    embed=create_error_embed("Permission Denied", "You need to be an administrator to use this command."),
                    ephemeral=True
                )
                return
        except (discord.errors.NotFound, discord.errors.InteractionResponded):
            logger.warning("Interaction already acknowledged in create_panel permission check")
            return

        # Check if guild is configured
        guild_config = get_guild_config(interaction.guild.id)
        if not guild_config or not guild_config.get('category_id'):
            await interaction.response.send_message(
                embed=create_error_embed(
                    "Setup Required",
                    "Please set up the ticket system first with the `/setup` commands."
                ),
                ephemeral=True
            )
            return

        # Get template data if specified
        template_data = {}
        if template:
            template_data = get_template(template)

        config = get_config()

        # Use provided values, template values, or defaults
        panel_title = title or template_data.get('title', config.get('default_panel_title'))
        panel_description = description or template_data.get('description', config.get('default_panel_description'))
        panel_color = template_data.get('color', config.get('default_panel_color'))
        panel_button_text = button_text or template_data.get('button_text', config.get('default_button_text'))
        panel_button_emoji = button_emoji or template_data.get('button_emoji', config.get('default_button_emoji'))

        # Create the embed
        embed = create_ticket_panel_embed(
            title=panel_title,
            description=panel_description,
            color=panel_color,
            image_url=image_url,
            header_image_url=header_image_url,
            footer_image_url=footer_image_url,
            guild=interaction.guild
        )

        # Create the stylish button with dynamic color based on template
        button_style = discord.ButtonStyle.primary  # Default blue style

        # Set button style based on template type
        if template == "gaming":
            button_style = discord.ButtonStyle.danger  # Red for gaming
        elif template == "billing":
            button_style = discord.ButtonStyle.success  # Green for billing
        elif template == "general":
            button_style = discord.ButtonStyle.secondary  # Gray for general

        button = discord.ui.Button(
            style=button_style,
            label=panel_button_text,
            emoji=panel_button_emoji,
            custom_id=f"create_ticket:{interaction.guild.id}"
        )

        # Create the view
        view = discord.ui.View(timeout=None)
        view.add_item(button)

        # Defer the response first
        await interaction.response.defer(ephemeral=True)

        try:
            # Send the panel message
            panel_message = await channel.send(embed=embed, view=view)

            # Use default or custom close button text/emoji
            panel_close_button_text = close_button_text or template_data.get('close_button_text', "Close Ticket")
            panel_close_button_emoji = close_button_emoji or template_data.get('close_button_emoji', "🔒")

            # Save the panel to the database
            panel_id = create_ticket_panel(
                guild_id=interaction.guild.id,
                channel_id=channel.id,
                message_id=panel_message.id,
                panel_title=panel_title,
                panel_description=panel_description,
                panel_color=panel_color,
                button_text=panel_button_text,
                button_emoji=panel_button_emoji,
                image_url=image_url,
                close_button_text=panel_close_button_text,
                close_button_emoji=panel_close_button_emoji,
                header_image_url=header_image_url,
                footer_image_url=footer_image_url
            )

            if panel_id:
                # Send success message
                await interaction.followup.send(
                    embed=create_success_embed(
                        "Panel Created",
                        f"Ticket panel created successfully in {channel.mention}!"
                    ),
                    ephemeral=True
                )
                return
            
            # Failed to save panel
            await interaction.followup.send(
                embed=create_error_embed(
                    "Error",
                    "Failed to create ticket panel. Please try again."
                ),
                ephemeral=True
            )
            if panel_message:
                await panel_message.delete()
                await panel_message.delete()
        except Exception as e:
            logger.error(f"Error creating panel: {e}")
            await interaction.followup.send(
                embed=create_error_embed(
                    "Error",
                    f"An error occurred: {str(e)}"
                ),
                ephemeral=True
            )

    @app_commands.command(name="deletepanel", description="Delete a ticket panel")
    @app_commands.describe(channel="The channel containing the panel", message_id="The message ID of the panel")
    async def delete_panel(
        self, 
        interaction: discord.Interaction, 
        channel: discord.TextChannel,
        message_id: str
    ):
        """Delete a ticket panel"""
        try:
            if not await self.is_admin(interaction):
                await interaction.response.send_message(
                    embed=create_error_embed("Permission Denied", "You need to be an administrator to use this command."),
                    ephemeral=True
                )
                return
        except (discord.errors.NotFound, discord.errors.InteractionResponded):
            logger.warning("Interaction already acknowledged in delete_panel permission check")
            return

        try:
            # Convert message ID to int
            message_id = int(message_id)

            # Check if panel exists
            panel = get_panel_by_message(interaction.guild.id, message_id)
            if not panel:
                await interaction.response.send_message(
                    embed=create_error_embed(
                        "Panel Not Found",
                        "No ticket panel found with that message ID."
                    ),
                    ephemeral=True
                )
                return

            # Try to delete the message
            try:
                message = await channel.fetch_message(message_id)
                await message.delete()
            except discord.NotFound:
                # Message already deleted, that's fine
                pass
            except Exception as e:
                logger.error(f"Error deleting panel message: {e}")
                # We'll continue with removing from DB even if message delete fails

            # Delete panel from database (implement this function in database.py)
            conn = get_db_connection()
            try:
                cursor = conn.cursor()
                cursor.execute(
                    "DELETE FROM ticket_panels WHERE guild_id = ? AND message_id = ?",
                    (interaction.guild.id, message_id)
                )
                conn.commit()
                success = cursor.rowcount > 0
            finally:
                conn.close()

            if success:
                await interaction.response.send_message(
                    embed=create_success_embed(
                        "Panel Deleted",
                        "The ticket panel has been deleted successfully."
                    ),
                    ephemeral=True
                )
            else:
                await interaction.response.send_message(
                    embed=create_error_embed(
                        "Error",
                        "Failed to delete the ticket panel. Please try again."
                    ),
                    ephemeral=True
                )
        except ValueError:
            await interaction.response.send_message(
                embed=create_error_embed(
                    "Invalid Message ID",
                    "Please provide a valid message ID (numeric value)."
                ),
                ephemeral=True
            )
        except Exception as e:
            logger.error(f"Error deleting panel: {e}")
            await interaction.response.send_message(
                embed=create_error_embed(
                    "Error",
                    f"An error occurred: {str(e)}"
                ),
                ephemeral=True
            )

    @app_commands.command(name="help", description="Show help information for the ticket system")
    async def help_command(self, interaction: discord.Interaction):
        """Show help information for the ticket system"""
        await interaction.response.send_message(
            embed=create_help_embed(),
            ephemeral=True
        )

    # Add user to a ticket command
    @app_commands.command(name="add", description="Add a user to a ticket")
    @app_commands.describe(user="The user to add to the ticket")
    async def add_user(self, interaction: discord.Interaction, user: discord.User):
        """Add a user to a ticket"""
        # Get ticket info for the channel
        from utils.database import get_ticket_by_channel
        ticket = get_ticket_by_channel(interaction.guild.id, interaction.channel.id)

        # Check if this is a ticket channel
        if not ticket:
            await interaction.response.send_message(
                embed=create_error_embed(
                    "Not a Ticket Channel",
                    "This command can only be used in a ticket channel."
                ),
                ephemeral=True
            )
            return

        # Check if user has permission to add users
        guild_config = get_guild_config(interaction.guild.id)
        is_support = False

        if guild_config:
            # Check if user is admin or has support role
            if guild_config.get('admin_role_id'):
                admin_role = interaction.guild.get_role(guild_config['admin_role_id'])
                if admin_role and admin_role in interaction.user.roles:
                    is_support = True

            if guild_config.get('support_role_id'):
                support_role = interaction.guild.get_role(guild_config['support_role_id'])
                if support_role and support_role in interaction.user.roles:
                    is_support = True

        # Allow ticket creator to add users too
        is_creator = ticket['user_id'] == interaction.user.id

        if not (is_support or is_creator or interaction.user.guild_permissions.administrator):
            await interaction.response.send_message(
                embed=create_error_embed(
                    "Permission Denied",
                    "You don't have permission to add users to this ticket."
                ),
                ephemeral=True
            )
            return

        # Add user to the channel
        try:
            await interaction.channel.set_permissions(
                user,
                read_messages=True,
                send_messages=True
            )

            await interaction.response.send_message(
                embed=create_success_embed(
                    "User Added",
                    f"{user.mention} has been added to the ticket."
                )
            )
        except Exception as e:
            logger.error(f"Error adding user to ticket: {e}")
            await interaction.response.send_message(
                embed=create_error_embed(
                    "Error",
                    f"Failed to add user to the ticket: {str(e)}"
                ),
                ephemeral=True
            )

    # Remove user from a ticket command
    @app_commands.command(name="remove", description="Remove a user from a ticket")
    @app_commands.describe(user="The user to remove from the ticket")
    async def remove_user(self, interaction: discord.Interaction, user: discord.User):
        """Remove a user from a ticket"""
        # Get ticket info for the channel
        from utils.database import get_ticket_by_channel
        ticket = get_ticket_by_channel(interaction.guild.id, interaction.channel.id)

        # Check if this is a ticket channel
        if not ticket:
            await interaction.response.send_message(
                embed=create_error_embed(
                    "Not a Ticket Channel",
                    "This command can only be used in a ticket channel."
                ),
                ephemeral=True
            )
            return

        # Check if user has permission to remove users
        guild_config = get_guild_config(interaction.guild.id)
        is_support = False

        if guild_config:
            # Check if user is admin or has support role
            if guild_config.get('admin_role_id'):
                admin_role = interaction.guild.get_role(guild_config['admin_role_id'])
                if admin_role and admin_role in interaction.user.roles:
                    is_support = True

            if guild_config.get('support_role_id'):
                support_role = interaction.guild.get_role(guild_config['support_role_id'])
                if support_role and support_role in interaction.user.roles:
                    is_support = True

        # Don't allow removing the ticket creator
        if user.id == ticket['user_id']:
            await interaction.response.send_message(
                embed=create_error_embed(
                    "Cannot Remove Creator",
                    "You cannot remove the ticket creator from the ticket."
                ),
                ephemeral=True
            )
            return

        if not (is_support or interaction.user.guild_permissions.administrator):
            await interaction.response.send_message(
                embed=create_error_embed(
                    "Permission Denied",
                    "You don't have permission to remove users from this ticket."
                ),
                ephemeral=True
            )
            return

        # Remove user from the channel
        try:
            await interaction.channel.set_permissions(
                user,
                overwrite=None
            )

            await interaction.response.send_message(
                embed=create_success_embed(
                    "User Removed",
                    f"{user.mention} has been removed from the ticket."
                )
            )
        except Exception as e:
            logger.error(f"Error removing user from ticket: {e}")
            await interaction.response.send_message(
                embed=create_error_embed(
                    "Error",
                    f"Failed to remove user from the ticket: {str(e)}"
                ),
                ephemeral=True
            )
            
    @app_commands.command(name="autoresponse", description="Manage auto-responses for tickets")
    @app_commands.describe(
        action="Action to perform",
        ticket_type="The type of ticket to modify responses for",
        response_text="The auto-response text to add"
    )
    @app_commands.choices(
        action=[
            app_commands.Choice(name="add", value="add"),
            app_commands.Choice(name="remove", value="remove"),
            app_commands.Choice(name="list", value="list")
        ],
        ticket_type=[
            app_commands.Choice(name="gaming", value="gaming"),
            app_commands.Choice(name="billing", value="billing"),
            app_commands.Choice(name="general", value="general"),
            app_commands.Choice(name="custom", value="custom")
        ]
    )
    async def autoresponse_command(
        self, 
        interaction: discord.Interaction, 
        action: str, 
        ticket_type: str,
        response_text: Optional[str] = None,
        index: Optional[int] = None
    ):
        """Manage auto-responses for tickets"""
        # Check if user has admin permissions
        if not await self.is_admin(interaction):
            await interaction.response.send_message(
                "You need administrator permissions to manage auto-responses.",
                ephemeral=True
            )
            return

        # Import the auto-response utilities
        from utils.auto_responses import (
            get_all_responses, add_custom_response, 
            remove_custom_response, get_response
        )
        
        # Handle LIST action
        if action == "list":
            all_responses = get_all_responses()
            
            # Get responses for the requested type, or all if type is "custom"
            if ticket_type == "custom":
                # Filter only custom types (not in the default list)
                custom_types = {k: v for k, v in all_responses.items() 
                               if k not in ["gaming", "billing", "general"]}
                
                if not custom_types:
                    await interaction.response.send_message(
                        "No custom auto-responses have been added yet.",
                        ephemeral=True
                    )
                    return
                
                # Create embed with all custom types
                embed = discord.Embed(
                    title="Custom Auto-Responses",
                    description="Here are all custom auto-response types:",
                    color=0x5865F2
                )
                
                for type_name, responses in custom_types.items():
                    responses_text = "\n\n".join([f"{i+1}. {r[:100]}..." for i, r in enumerate(responses)])
                    embed.add_field(
                        name=f"Type: {type_name}",
                        value=responses_text or "No responses for this type.",
                        inline=False
                    )
            else:
                # Get specific type responses
                type_responses = all_responses.get(ticket_type, [])
                
                if not type_responses:
                    await interaction.response.send_message(
                        f"No auto-responses found for type: {ticket_type}",
                        ephemeral=True
                    )
                    return
                
                # Create embed with responses for the requested type
                embed = discord.Embed(
                    title=f"Auto-Responses for {ticket_type.capitalize()}",
                    description=f"Here are all configured auto-responses for {ticket_type} tickets:",
                    color=0x5865F2
                )
                
                responses_text = "\n\n".join([f"{i+1}. {r[:200]}..." for i, r in enumerate(type_responses)])
                embed.add_field(
                    name="Responses",
                    value=responses_text,
                    inline=False
                )
            
            await interaction.response.send_message(embed=embed, ephemeral=True)
            
        # Handle ADD action
        elif action == "add":
            if not response_text:
                await interaction.response.send_message(
                    "Response text is required for adding a new auto-response.",
                    ephemeral=True
                )
                return
                
            # Add the response
            success = add_custom_response(ticket_type, response_text)
            
            if success:
                await interaction.response.send_message(
                    f"Auto-response added successfully for ticket type: {ticket_type}",
                    ephemeral=True
                )
            else:
                await interaction.response.send_message(
                    "Failed to add auto-response. Please try again.",
                    ephemeral=True
                )
                
        # Handle REMOVE action
        elif action == "remove":
            if index is None:
                await interaction.response.send_message(
                    "Index is required for removing an auto-response.",
                    ephemeral=True
                )
                return
                
            # Remove the response
            removed = remove_custom_response(ticket_type, index - 1)  # Convert to 0-based index
            
            if removed:
                await interaction.response.send_message(
                    f"Auto-response removed successfully from ticket type: {ticket_type}",
                    ephemeral=True
                )
            else:
                await interaction.response.send_message(
                    f"Failed to remove auto-response. Invalid index or ticket type.",
                    ephemeral=True
                )
                
    @app_commands.command(name="translation", description="Configure translation settings")
    @app_commands.describe(
        action="Action to perform",
        user_id="User ID to set language for (admin only)",
        language="Language code (e.g., en, es, fr)"
    )
    @app_commands.choices(
        action=[
            app_commands.Choice(name="set_user", value="set_user"),
            app_commands.Choice(name="set_guild", value="set_guild"),
            app_commands.Choice(name="list", value="list")
        ]
    )
    async def translation_command(
        self, 
        interaction: discord.Interaction, 
        action: str,
        language: Optional[str] = None,
        user_id: Optional[str] = None,
        auto_translate: Optional[bool] = False
    ):
        """Configure translation settings"""
        # Import translation utilities
        from utils.translator import (
            get_supported_languages, set_user_language,
            get_user_language, set_guild_language,
            get_guild_language
        )
        
        # Handle LIST action
        if action == "list":
            languages = get_supported_languages()
            
            # Create embed with all supported languages
            embed = discord.Embed(
                title="Supported Languages",
                description="Here are all supported languages for translation:",
                color=0x5865F2
            )
            
            # Sort languages by name
            sorted_langs = sorted(languages.items(), key=lambda x: x[1])
            
            # Build language list in columns
            lang_chunks = [sorted_langs[i:i+10] for i in range(0, len(sorted_langs), 10)]
            
            for i, chunk in enumerate(lang_chunks):
                lang_text = "\n".join([f"`{code}` - {name}" for code, name in chunk])
                embed.add_field(
                    name=f"Languages {i+1}",
                    value=lang_text,
                    inline=True
                )
            
            # Add user's current language
            user_lang = get_user_language(interaction.user.id)
            embed.add_field(
                name="Your Language",
                value=f"`{user_lang['language_code']}` - {user_lang['language_name']}\nAuto-translate: {'Enabled' if user_lang['auto_translate'] else 'Disabled'}",
                inline=False
            )
            
            await interaction.response.send_message(embed=embed, ephemeral=True)
            
        # Handle SET_USER action
        elif action == "set_user":
            # Check if setting for another user (admin only)
            if user_id and user_id != str(interaction.user.id):
                if not await self.is_admin(interaction):
                    await interaction.response.send_message(
                        "You need administrator permissions to set language for other users.",
                        ephemeral=True
                    )
                    return
                target_id = int(user_id)
            else:
                target_id = interaction.user.id
            
            # Check if language is provided
            if not language:
                await interaction.response.send_message(
                    "Language code is required. Use `/translation list` to see supported languages.",
                    ephemeral=True
                )
                return
                
            # Check if language is supported
            languages = get_supported_languages()
            if language not in languages:
                await interaction.response.send_message(
                    f"Unsupported language code: {language}. Use `/translation list` to see supported languages.",
                    ephemeral=True
                )
                return
                
            # Set user language
            success = set_user_language(target_id, language, auto_translate)
            
            if success:
                await interaction.response.send_message(
                    f"Language set to {languages[language]} for {'you' if target_id == interaction.user.id else f'user {target_id}'}.\nAuto-translate: {'Enabled' if auto_translate else 'Disabled'}",
                    ephemeral=True
                )
            else:
                await interaction.response.send_message(
                    "Failed to set language. Please try again.",
                    ephemeral=True
                )
                
        # Handle SET_GUILD action
        elif action == "set_guild":
            # Check if user has admin permissions
            if not await self.is_admin(interaction):
                await interaction.response.send_message(
                    "You need administrator permissions to set guild language.",
                    ephemeral=True
                )
                return
                
            # Check if language is provided
            if not language:
                await interaction.response.send_message(
                    "Language code is required. Use `/translation list` to see supported languages.",
                    ephemeral=True
                )
                return
                
            # Check if language is supported
            languages = get_supported_languages()
            if language not in languages:
                await interaction.response.send_message(
                    f"Unsupported language code: {language}. Use `/translation list` to see supported languages.",
                    ephemeral=True
                )
                return
                
            # Set guild language
            success = set_guild_language(interaction.guild.id, language, auto_translate)
            
            if success:
                await interaction.response.send_message(
                    f"Default guild language set to {languages[language]}.\nAuto-translate: {'Enabled' if auto_translate else 'Disabled'}",
                    ephemeral=True
                )
            else:
                await interaction.response.send_message(
                    "Failed to set guild language. Please try again.",
                    ephemeral=True
                )

async def setup(bot):
    """Add the cog to the bot"""
    await bot.add_cog(TicketCommands(bot))