from discord.ext import commands
import discord
from discord import app_commands
import GenHelp as gh
from . import TicketsHelp as th
import traceback
import asyncio
import copy
import io
import datetime

guilds = th.get_tickets_guilds()
if guilds == None:
    guilds = [1479749743784493128]

class Tickets(commands.Cog):
    async def cog_check(self, ctx: commands.Context):
        allowed = th.get_tickets_guilds()
        return ctx.guild is not None and ctx.guild.id in allowed

    def __init__(self, bot: discord.Client):
        self.bot = bot

    tickets = app_commands.Group(
        name="tickets",
        description="Ticket system commands",
        guild_ids=guilds
    )

    panel = app_commands.Group(
        name="panel",
        description="Manage ticket panels",
        parent=tickets,
        guild_ids=guilds
    )

    async def cog_load(self):
        th.register_persistent_views(self.bot)

    # ------------------------------------------
    # Panel commands
    # ------------------------------------------

    @panel.command(name="create", description="Create a new ticket panel")
    @app_commands.checks.has_permissions(administrator=True)
    @app_commands.describe(panel_name="Unique name for this panel")
    async def panel_create(self, interaction: discord.Interaction, panel_name: str):
        key = panel_name.lower()
        data, gdata = th.get_guild_ticket_data(interaction.guild.id, create=True)

        if key in gdata["panels"]:
            return await interaction.response.send_message(
                embed=gh.fail("Panel exists", f"> A panel named **{panel_name}** already exists."),
                ephemeral=True
            )

        panel = copy.deepcopy(th.DEFAULT_PANEL)
        panel["message_data"] = copy.deepcopy(th.DEFAULT_PANEL_MESSAGE)
        panel["ticket_types"]["default_type"] = {
            "id": "default_type",
            "name": "Support",
            "emoji": "💬",
            "style": "primary",
            "category_id": None,
            "ticket_roles": [],
            "opening_template_id": None,
            "modal_questions": []
        }
        gdata["panels"][key] = panel
        th.save_tickets(data)

        await interaction.response.send_message(
            embed=gh.success("Panel created", f"> Panel **{panel_name}** has been created."),
            ephemeral=True
        )

    @panel.command(name="delete", description="Delete a ticket panel")
    @app_commands.checks.has_permissions(administrator=True)
    @app_commands.describe(panel_name="Panel to delete")
    async def panel_delete(self, interaction: discord.Interaction, panel_name: str):
        data, gdata, panel = th.get_panel(interaction.guild.id, panel_name)
        if not panel:
            return await interaction.response.send_message(
                embed=gh.fail("Not found", f"> Panel **{panel_name}** does not exist."),
                ephemeral=True
            )

        del gdata["panels"][panel_name.lower()]
        th.save_tickets(data)

        await interaction.response.send_message(
            embed=gh.success("Panel deleted", f"> Panel **{panel_name}** has been deleted."),
            ephemeral=True
        )

    @panel.command(name="list", description="List all ticket panels")
    @app_commands.checks.has_permissions(administrator=True)
    async def panel_list(self, interaction: discord.Interaction):
        data, gdata = th.get_guild_ticket_data(interaction.guild.id)
        if not gdata or not gdata["panels"]:
            return await interaction.response.send_message(
                embed=gh.fail("No panels", "> No ticket panels configured."),
                ephemeral=True
            )

        lines = []
        for name, panel in gdata["panels"].items():
            types = len(panel.get("ticket_types", {}))
            lines.append(f"• **{name}** — {types} ticket type(s)")

        embed = discord.Embed(
            title="Ticket Panels",
            description="\n".join(lines),
            color=discord.Color.blurple()
        )
        await interaction.response.send_message(embed=embed, ephemeral=True)

    @panel.command(name="info", description="View panel information")
    @app_commands.checks.has_permissions(administrator=True)
    @app_commands.describe(panel_name="Panel to inspect")
    async def panel_info(self, interaction: discord.Interaction, panel_name: str):
        data, gdata, panel = th.get_panel(interaction.guild.id, panel_name)
        if not panel:
            return await interaction.response.send_message(
                embed=gh.fail("Not found", f"> Panel **{panel_name}** does not exist."),
                ephemeral=True
            )

        transcript = panel.get("transcript_channel")
        category = panel.get("category_id")
        ping_roles = panel.get("ping_roles", [])

        embed = discord.Embed(title=f"Panel: {panel_name}", color=th.PANEL_COLOR)
        embed.add_field(name="Counter", value=str(panel.get("counter", 0)), inline=True)
        embed.add_field(name="Ticket Types", value=str(len(panel.get("ticket_types", {}))), inline=True)
        embed.add_field(
            name="Transcript Channel",
            value=f"<#{transcript}>" if transcript else "Not set",
            inline=True
        )
        embed.add_field(
            name="Category",
            value=f"<#{category}>" if category else "Not set",
            inline=True
        )
        embed.add_field(
            name="Ping Roles",
            value=", ".join(f"<@&{r}>" for r in ping_roles) or "None",
            inline=False
        )

        type_lines = []
        for tid, ttype in panel.get("ticket_types", {}).items():
            emoji = ttype.get("emoji") or ""
            type_lines.append(f"{emoji} **{ttype.get('name')}** (`{tid}`)")

        if type_lines:
            embed.add_field(name="Types", value="\n".join(type_lines), inline=False)

        await interaction.response.send_message(embed=embed, ephemeral=True)

    @panel.command(name="edit", description="Edit a ticket panel's types")
    @app_commands.checks.has_permissions(administrator=True)
    @app_commands.describe(panel_name="Panel to edit")
    async def panel_edit(self, interaction: discord.Interaction, panel_name: str):
        data, gdata, panel = th.get_panel(interaction.guild.id, panel_name)
        if not panel:
            return await interaction.response.send_message(
                embed=gh.fail("Not found", f"> Panel **{panel_name}** does not exist."),
                ephemeral=True
            )

        if not panel.get("ticket_types"):
            return await interaction.response.send_message(
                embed=gh.fail("No types", "> This panel has no ticket types."),
                ephemeral=True
            )

        view = discord.ui.View(timeout=120)
        view.add_item(th.TicketTypeSelect(panel_name.lower(), interaction.guild.id, panel))
        await interaction.response.send_message(
            "Select a ticket type to configure:",
            view=view,
            ephemeral=True
        )

    @panel.command(name="message-setup", description="Configure a panel's message")
    @app_commands.checks.has_permissions(administrator=True)
    @app_commands.describe(panel_name="Panel to configure")
    async def panel_message_setup(self, interaction: discord.Interaction, panel_name: str):
        data, gdata, panel = th.get_panel(interaction.guild.id, panel_name, create=True)
        message_data = panel.get("message_data") or th.DEFAULT_PANEL_MESSAGE

        content, embeds = th.build_panel_preview(interaction.user, message_data)

        await interaction.response.send_message(
            content="## Panel Message Preview",
            ephemeral=False
        )
        await interaction.channel.send(
            content=content,
            embeds=embeds,
            view=th.PanelMessageSetupView(
                interaction.user.id,
                interaction.guild.id,
                panel_name.lower(),
                panel
            )
        )

    @panel.command(name="message-send", description="Send the panel message to a channel")
    @app_commands.checks.has_permissions(administrator=True)
    @app_commands.describe(panel_name="Panel to send", channel="Channel to send the panel to")
    async def panel_message_send(
        self,
        interaction: discord.Interaction,
        panel_name: str,
        channel: discord.TextChannel
    ):
        data, gdata, panel = th.get_panel(interaction.guild.id, panel_name)
        if not panel:
            return await interaction.response.send_message(
                embed=gh.fail("Not found", f"> Panel **{panel_name}** does not exist."),
                ephemeral=True
            )

        message_data = panel.get("message_data") or th.DEFAULT_PANEL_MESSAGE
        parsed = th.parse_ticket_placeholders(copy.deepcopy(message_data), interaction.user)
        content = parsed.get("content") or None
        embeds = th.build_embeds_from_data(parsed.get("embeds", []))
        buttons = parsed.get("buttons", [])

        view = th.PanelPersistentView(interaction.guild.id, panel_name.lower(), buttons)
        self.bot.add_view(view)

        msg = await channel.send(content=content, embeds=embeds or None, view=view)

        panel["panel_message_id"] = msg.id
        panel["panel_channel_id"] = channel.id
        th.save_panel(interaction.guild.id, panel_name, panel)

        await interaction.response.send_message(
            embed=gh.success("Panel sent", f"> Panel sent to {channel.mention}"),
            ephemeral=True
        )

    # ------------------------------------------
    # Open message command
    # ------------------------------------------

    @tickets.command(name="open-message", description="Configure ticket opening messages")
    @app_commands.checks.has_permissions(administrator=True)
    @app_commands.describe(template_name="Name for this opening message template")
    async def open_message(self, interaction: discord.Interaction, template_name: str):
        data, gdata = th.get_guild_ticket_data(interaction.guild.id, create=True)
        tid = template_name.lower().replace(" ", "_")

        if tid not in gdata["opening_templates"]:
            gdata["opening_templates"][tid] = {
                "name": template_name,
                "message_data": copy.deepcopy(th.DEFAULT_OPEN_MESSAGE),
                "panels": []
            }
            th.save_tickets(data)

        template = gdata["opening_templates"][tid]
        message_data = template.get("message_data", th.DEFAULT_OPEN_MESSAGE)

        content, embeds = th.build_panel_preview(interaction.user, message_data)
        embeds = th.apply_button_author(embeds, [
            {"emoji": "🙋", "label": "Claim"},
            {"emoji": "🔒", "label": "Close"}
        ])

        await interaction.response.send_message(content="## Opening Message Preview", ephemeral=False)
        await interaction.channel.send(
            content=content,
            embeds=embeds,
            view=th.OpenMessageSetupView(
                interaction.user.id,
                interaction.guild.id,
                tid,
                template
            )
        )

    # ------------------------------------------
    # Ticket commands
    # ------------------------------------------

    @commands.hybrid_command(name="claim", description="Claim the current ticket")
    @app_commands.guilds(*guilds)
    async def claim(self, ctx: commands.Context):
        if not isinstance(ctx.channel, discord.TextChannel):
            return

        data, gdata, ticket = th.get_active_ticket(ctx.channel.id)
        if not ticket:
            return await ctx.reply(embed=gh.fail("Not a ticket", "> This is not an active ticket channel."))

        panel = gdata["panels"].get(ticket["panel_name"])
        ticket_type = panel["ticket_types"].get(ticket["type_id"], {})

        if not th.is_ticket_staff(ctx.author, panel, ticket_type):
            return await ctx.reply(embed=gh.USER_PERMISSION_ERROR)

        if ticket.get("claimed_by"):
            return await ctx.reply(embed=gh.fail("Already claimed", f"> Claimed by <@{ticket['claimed_by']}>"))

        ticket["claimed_by"] = ctx.author.id
        gdata["active_tickets"][str(ctx.channel.id)] = ticket
        th.save_tickets(data)

        await ctx.send(embed=discord.Embed(
            description=f"🙋 Claimed by {ctx.author.mention}",
            color=discord.Color.green()
        ))

        await self._log_ticket_event(
            ctx.guild, panel, ticket,
            "Ticket Claimed",
            f"> Claimed by {ctx.author.mention}"
        )

        try:
            async for msg in ctx.channel.history(limit=20):
                if msg.author.id == self.bot.user.id and msg.components:
                    view = th.TicketControlView(ctx.channel.id, claimed=True)
                    self.bot.add_view(view)
                    await msg.edit(view=view)
                    break
        except Exception:
            pass

    @commands.hybrid_command(name="close", description="Close the current ticket")
    @app_commands.guilds(*guilds)
    @app_commands.describe(reason="Reason for closing")
    async def close(self, ctx: commands.Context, *, reason: str = "Not provided"):
        if not isinstance(ctx.channel, discord.TextChannel):
            return

        data, gdata, ticket = th.get_active_ticket(ctx.channel.id)
        if not ticket:
            return await ctx.reply(embed=gh.fail("Not a ticket", "> This is not an active ticket channel."))

        panel = gdata["panels"].get(ticket["panel_name"])
        ticket_type = panel["ticket_types"].get(ticket["type_id"], {})

        if not th.is_ticket_staff(ctx.author, panel, ticket_type):
            return await ctx.reply(embed=gh.USER_PERMISSION_ERROR)

        await ctx.reply(embed=gh.success("Closing", f"> Ticket closing in 5 seconds...\n> Reason: {reason}"))
        await self._close_ticket(ctx.channel, ctx.author, reason)

    @commands.hybrid_command(name="closerequest", description="Request ticket closure from the opener")
    @app_commands.guilds(*guilds)
    @app_commands.describe(reason="Reason for closing")
    async def closerequest(self, ctx: commands.Context, *, reason: str = "Not provided"):
        if not isinstance(ctx.channel, discord.TextChannel):
            return

        data, gdata, ticket = th.get_active_ticket(ctx.channel.id)
        if not ticket:
            return await ctx.reply(embed=gh.fail("Not a ticket", "> This is not an active ticket channel."))

        panel = gdata["panels"].get(ticket["panel_name"])
        ticket_type = panel["ticket_types"].get(ticket["type_id"], {})

        if not th.is_ticket_staff(ctx.author, panel, ticket_type):
            return await ctx.reply(embed=gh.USER_PERMISSION_ERROR)

        opener = ctx.guild.get_member(ticket["opener_id"])
        if not opener:
            return await ctx.reply(embed=gh.fail("User left", "> Ticket opener is no longer in the server."))

        embed = discord.Embed(
            title="Close Request",
            description=(
                f"> {ctx.author.mention} has requested to close this ticket.\n"
                f"> **Reason:** {reason}\n\n"
                "Do you want to close this ticket?"
            ),
            color=discord.Color.orange()
        )

        view = th.CloseRequestView(ctx.channel.id, opener.id)
        await ctx.send(embed=embed, view=view, content=opener.mention)
        await view.wait()

        if view.result:
            await self._close_ticket(ctx.channel, ctx.author, reason)

    # ------------------------------------------
    # Interaction listener (persistent buttons)
    # ------------------------------------------

    @commands.Cog.listener()
    async def on_interaction(self, interaction: discord.Interaction):
        if interaction.type != discord.InteractionType.component:
            return
        if not interaction.data or "custom_id" not in interaction.data:
            return

        cid = interaction.data["custom_id"]
        if not cid.startswith("tkt:"):
            return

        parts = cid.split(":")
        action = parts[1]

        if action == "panel":
            await self._handle_panel_button(interaction, parts[2], parts[3], parts[4])
        elif action == "claim":
            await self._handle_claim_button(interaction, int(parts[2]))
        elif action == "close":
            await self._handle_close_button(interaction, int(parts[2]))

    # ------------------------------------------
    # Ticket event listeners
    # ------------------------------------------

    @commands.Cog.listener()
    async def on_guild_channel_update(self, before: discord.TextChannel, after: discord.TextChannel):
        if before.name == after.name:
            return
        data, gdata, ticket = th.get_active_ticket(after.id)
        if not ticket:
            return
        panel = gdata["panels"].get(ticket["panel_name"])
        await self._log_ticket_event(
            after.guild, panel, ticket,
            "Ticket Renamed",
            f"> `{before.name}` → `{after.name}`"
        )

    @commands.Cog.listener()
    async def on_member_update(self, before: discord.Member, after: discord.Member):
        if set(before.roles) == set(after.roles):
            return

        data, gdata = th.get_guild_ticket_data(after.guild.id)
        if not gdata:
            return

        for ch_id, ticket in gdata.get("active_tickets", {}).items():
            channel = after.guild.get_channel(int(ch_id))
            if not channel:
                continue

            before_access = channel.permissions_for(before).view_channel
            after_access = channel.permissions_for(after).view_channel

            if before_access != after_access:
                panel = gdata["panels"].get(ticket["panel_name"])
                if after_access:
                    await self._log_ticket_event(
                        after.guild, panel, ticket,
                        "User Added",
                        f"> {after.mention} was given access."
                    )
                else:
                    await self._log_ticket_event(
                        after.guild, panel, ticket,
                        "User Removed",
                        f"> {after.mention} lost access."
                    )

    # ------------------------------------------
    # Core ticket logic
    # ------------------------------------------

    async def _handle_panel_button(
        self,
        interaction: discord.Interaction,
        guild_id: str,
        panel_name: str,
        type_id: str
    ):
        if interaction.guild is None:
            return

        data, gdata, panel = th.get_panel(int(guild_id), panel_name)
        print(panel)
        if not panel:
            return await interaction.response.send_message("Panel not found.", ephemeral=True)

        print(type_id)
        ticket_type = panel["ticket_types"][type_id]
        # ticket_type = None
        # for btn in buttons:
        #     if btn["type_id"]: 
        #         get_type_id = btn["type_id"]
        #         if type_id != get_type_id: continue
        #         else: ticket_type = get_type_id

        # print(ticket_type)
        if not ticket_type:
            return await interaction.response.send_message("Ticket type not found.", ephemeral=True)

        max_tickets = gdata.get("max_tickets_per_user", 2)
        open_count = th.count_user_open_tickets(interaction.guild.id, interaction.user.id)
        if open_count >= max_tickets:
            return await interaction.response.send_message(
                embed=gh.fail(
                    "Ticket limit",
                    f"> You already have **{open_count}** open ticket(s). Maximum is **{max_tickets}**."
                ),
                ephemeral=True
            )

        if ticket_type.get("modal_questions"):
            await interaction.response.send_modal(
                TicketQuestionsModal(self, panel_name, type_id, ticket_type)
            )
            return

        await interaction.response.defer(ephemeral=True)
        channel = await self._create_ticket_channel(interaction, panel_name, panel, ticket_type)
        if channel:
            await interaction.followup.send(
                embed=gh.success("Ticket created", f"> Your ticket: {channel.mention}"),
                ephemeral=True
            )

    async def _handle_claim_button(self, interaction: discord.Interaction, channel_id: int):
        data, gdata, ticket = th.get_active_ticket(channel_id)
        if not ticket:
            return await interaction.response.send_message("Not a ticket.", ephemeral=True)

        panel = gdata["panels"].get(ticket["panel_name"])
        ticket_type = panel["ticket_types"].get(ticket["type_id"], {})

        if not th.is_ticket_staff(interaction.user, panel, ticket_type):
            return await interaction.response.send_message(embed=gh.USER_PERMISSION_ERROR, ephemeral=True)

        if ticket.get("claimed_by"):
            return await interaction.response.send_message(
                f"Already claimed by <@{ticket['claimed_by']}>.",
                ephemeral=True
            )

        ticket["claimed_by"] = interaction.user.id
        gdata["active_tickets"][str(channel_id)] = ticket
        th.save_tickets(data)

        await interaction.response.send_message(
            embed=discord.Embed(description=f"🙋 Claimed by {interaction.user.mention}", color=discord.Color.green())
        )

        await self._log_ticket_event(
            interaction.guild, panel, ticket,
            "Ticket Claimed",
            f"> Claimed by {interaction.user.mention}"
        )

        channel = interaction.guild.get_channel(channel_id)
        if channel and interaction.message:
            view = th.TicketControlView(channel_id, claimed=True)
            self.bot.add_view(view)
            await interaction.message.edit(view=view)

    async def _handle_close_button(self, interaction: discord.Interaction, channel_id: int):
        data, gdata, ticket = th.get_active_ticket(channel_id)
        if not ticket:
            return await interaction.response.send_message("Not a ticket.", ephemeral=True)

        panel = gdata["panels"].get(ticket["panel_name"])
        ticket_type = panel["ticket_types"].get(ticket["type_id"], {})

        if not th.is_ticket_staff(interaction.user, panel, ticket_type):
            return await interaction.response.send_message(embed=gh.USER_PERMISSION_ERROR, ephemeral=True)

        await interaction.response.send_message(
            embed=gh.success("Closing", "> Ticket closing in 5 seconds..."),
            ephemeral=True
        )

        channel = interaction.guild.get_channel(channel_id)
        if channel:
            await self._close_ticket(channel, interaction.user, "Not provided")

    async def _create_ticket_channel(
        self,
        interaction: discord.Interaction,
        panel_name: str,
        panel: dict,
        ticket_type: dict,
        modal_answers: dict = None
    ) -> discord.TextChannel | None:
        guild = interaction.guild
        user = interaction.user

        panel["counter"] = panel.get("counter", 0) + 1
        counter = panel["counter"]
        type_name = th.sanitize_channel_name(ticket_type.get("name", "ticket"))
        channel_name = f"{type_name}-{counter:04d}"

        category_id = ticket_type.get("category_id") or panel.get("category_id")
        category = guild.get_channel(category_id) if category_id else None

        overwrites = {
            guild.default_role: discord.PermissionOverwrite(view_channel=False),
            user: discord.PermissionOverwrite(view_channel=True, send_messages=True, attach_files=True, embed_links=True),
            guild.me: discord.PermissionOverwrite(view_channel=True, send_messages=True, manage_channels=True, manage_messages=True)
        }

        staff_roles = th.get_ticket_staff_roles(panel, ticket_type)
        for rid in staff_roles:
            role = guild.get_role(rid)
            if role:
                overwrites[role] = discord.PermissionOverwrite(view_channel=True, send_messages=True)

        try:
            if category:
                channel = await guild.create_text_channel(
                    channel_name,
                    category=category,
                    overwrites=overwrites,
                    topic=f"Ticket opened by {user} | Type: {ticket_type.get('name')}"
                )
            else:
                channel = await guild.create_text_channel(
                    channel_name,
                    overwrites=overwrites,
                    topic=f"Ticket opened by {user} | Type: {ticket_type.get('name')}"
                )
        except discord.Forbidden:
            return None

        th.save_panel(guild.id, panel_name, panel)

        opened_at = discord.utils.utcnow().isoformat()
        data, gdata = th.get_guild_ticket_data(guild.id, create=True)

        ticket_record = {
            "panel_name": panel_name,
            "type_id": ticket_type["id"],
            "opener_id": user.id,
            "opened_at": opened_at,
            "claimed_by": None,
            "ticket_number": counter,
            "ticket_name": channel_name,
            "modal_answers": modal_answers or {}
        }
        gdata["active_tickets"][str(channel.id)] = ticket_record
        uid = str(user.id)
        gdata.setdefault("user_open_tickets", {}).setdefault(uid, []).append(str(channel.id))
        th.save_tickets(data)

        ticket_info = {
            "ticket_type": ticket_type.get("name", "Ticket"),
            "ticket_name": channel_name,
            "ticket_roles": staff_roles,
            "opened_at": gh.format_dt(discord.utils.utcnow()),
            "claimed_by": "Unclaimed",
            "closed_by": "Not closed"
        }

        template_id = ticket_type.get("opening_template_id")
        if template_id and template_id in gdata.get("opening_templates", {}):
            message_data = gdata["opening_templates"][template_id]["message_data"]
        else:
            message_data = th.DEFAULT_OPEN_MESSAGE

        parsed = th.parse_ticket_placeholders(copy.deepcopy(message_data), user, ticket_info, guild)
        content = parsed.get("content") or None
        embeds = th.build_embeds_from_data(parsed.get("embeds", []))

        view = th.TicketControlView(channel.id, claimed=False)
        self.bot.add_view(view)
        await channel.send(content=content, embeds=embeds or None, view=view)

        ping_parts = [user.mention]
        for rid in panel.get("ping_roles", []):
            role = guild.get_role(rid)
            if role:
                ping_parts.append(role.mention)
        if len(ping_parts) > 1 or panel.get("ping_roles"):
            await channel.send(" ".join(ping_parts))

        if modal_answers:
            answer_lines = [f"**{k}:** {v}" for k, v in modal_answers.items()]
            await channel.send(
                embed=discord.Embed(
                    title="Ticket Form Responses",
                    description="\n".join(answer_lines),
                    color=discord.Color.blurple()
                )
            )

        await self._log_ticket_event(
            guild, panel, ticket_record,
            "Ticket Opened",
            f"> Opened by {user.mention}\n> Type: **{ticket_type.get('name')}**\n> Channel: {channel.mention}"
        )

        return channel

    async def _close_ticket(self, channel: discord.TextChannel, closer: discord.Member, reason: str):
        data, gdata, ticket = th.get_active_ticket(channel.id)
        if not ticket:
            return

        panel = gdata["panels"].get(ticket["panel_name"], {})
        ticket_type = panel.get("ticket_types", {}).get(ticket.get("type_id"), {})

        opener = channel.guild.get_member(ticket["opener_id"])
        claimed = ticket.get("claimed_by")
        opened_at = ticket.get("opened_at", "")

        await self._log_ticket_event(
            channel.guild, panel, ticket,
            "Ticket Closed",
            f"> Closed by {closer.mention}\n> Reason: {reason}"
        )

        transcript_channel_id = panel.get("transcript_channel")
        if transcript_channel_id:
            transcript_ch = channel.guild.get_channel(transcript_channel_id)
            if transcript_ch:
                html_content = await th.generate_transcript_html(channel)
                file = discord.File(
                    io.BytesIO(html_content.encode("utf-8")),
                    filename=f"transcript-{channel.name}.html"
                )

                opener_mention = opener.mention if opener else f"<@{ticket['opener_id']}>"
                claimed_text = f"<@{claimed}>" if claimed else "Unclaimed"

                embed = discord.Embed(
                    title="Ticket Closed",
                    color=discord.Color.red()
                )
                embed.add_field(name="Opened Time", value=gh.format_dt(datetime.datetime.fromisoformat(opened_at)) if opened_at else "Unknown", inline=True)
                embed.add_field(name="Opened By", value=opener_mention, inline=True)
                embed.add_field(name="Closed By", value=closer.mention, inline=True)
                embed.add_field(name="Reason", value=reason, inline=False)
                embed.add_field(name="Ticket Type", value=ticket_type.get("name", "Unknown"), inline=True)
                embed.add_field(name="Claimed By", value=claimed_text, inline=True)
                embed.add_field(name="Duration", value=th.format_duration(opened_at), inline=True)

                await transcript_ch.send(embed=embed, file=file)

        if opener:
            dm_embed = discord.Embed(
                title="Your Ticket Was Closed",
                description=(
                    f"> **Server:** {channel.guild.name}\n"
                    f"> **Ticket:** `{channel.name}`\n"
                    f"> **Type:** {ticket_type.get('name', 'Unknown')}\n"
                    f"> **Closed by:** {closer.mention}\n"
                    f"> **Reason:** {reason}"
                ),
                color=discord.Color.orange()
            )
            await gh.dm(opener, dm_embed)

        uid = str(ticket["opener_id"])
        if uid in gdata.get("user_open_tickets", {}):
            ch_list = gdata["user_open_tickets"][uid]
            if str(channel.id) in ch_list:
                ch_list.remove(str(channel.id))

        gdata["active_tickets"].pop(str(channel.id), None)
        th.save_tickets(data)

        await asyncio.sleep(5)
        try:
            await channel.delete(reason=f"Ticket closed by {closer} — {reason}")
        except discord.Forbidden:
            pass

    async def _log_ticket_event(self, guild: discord.Guild, panel: dict, ticket: dict, title: str, description: str):
        transcript_channel_id = panel.get("transcript_channel") if panel else None
        if not transcript_channel_id:
            return

        log_ch = guild.get_channel(transcript_channel_id)
        if not log_ch:
            return

        embed = discord.Embed(title=title, description=description, color=discord.Color.blurple())
        embed.set_footer(text=f"Ticket: {ticket.get('ticket_name', 'unknown')}")
        embed.timestamp = discord.utils.utcnow()

        try:
            await log_ch.send(embed=embed)
        except discord.Forbidden:
            pass


class TicketQuestionsModal(discord.ui.Modal):
    def __init__(self, cog, panel_name: str, type_id: str, ticket_type: dict):
        super().__init__(title=f"Open {ticket_type.get('name', 'Ticket')}")
        self.cog = cog
        self.panel_name = panel_name
        self.type_id = type_id
        self.ticket_type = ticket_type
        self.answers = {}

        for i, q in enumerate(ticket_type.get("modal_questions", [])[:5]):
            self.add_item(discord.ui.TextInput(
                label=q.get("label", f"Question {i + 1}")[:45],
                placeholder=q.get("placeholder", "")[:100] or None,
                required=q.get("required", True),
                style=discord.TextStyle.paragraph if q.get("style") == "paragraph" else discord.TextStyle.short,
                max_length=1024
            ))

    async def on_submit(self, interaction: discord.Interaction):
        answers = {}
        for item in self.children:
            answers[item.label] = item.value

        data, gdata, panel = th.get_panel(interaction.guild.id, self.panel_name)
        ticket_type = panel["ticket_types"][self.type_id]

        await interaction.response.defer(ephemeral=True)
        channel = await self.cog._create_ticket_channel(
            interaction, self.panel_name, panel, ticket_type, modal_answers=answers
        )
        if channel:
            await interaction.followup.send(
                embed=gh.success("Ticket created", f"> Your ticket: {channel.mention}"),
                ephemeral=True
            )
        else:
            await interaction.followup.send(
                embed=gh.fail("Failed", "> Could not create ticket channel."),
                ephemeral=True
            )


async def setup(bot):
    try:
        await bot.add_cog(Tickets(bot))
    except Exception:
        print("=========== TICKETS COG SETUP ERROR ===========")
        traceback.print_exc()
