import discord
from discord.ext import commands
from discord import app_commands
from typing import Optional
import re
import GenHelp as gh
import json
import os
import asyncio

# ------------------------------------
# Confirmation View
# ------------------------------------
CONFIG_FILE = "Data/Customised/GarfieldGang/autoping_config.json"

class AutoPingSetupView(discord.ui.View):
    def __init__(
        self,
        author: discord.Member,
        guild: discord.Guild,
        channels: list[discord.TextChannel],
        dms: bool
    ):
        super().__init__(timeout=30)

        self.author = author
        self.guild = guild
        self.channels = channels
        self.dms = dms

        self.value = None

    async def interaction_check(self, interaction: discord.Interaction) -> bool:
        if interaction.user.id != self.author.id:
            await interaction.response.send_message(
                "❌ Only the command invoker can use these buttons.",
                ephemeral=True
            )
            return False

        return True

    async def disable_buttons(self):
        for item in self.children:
            item.disabled = True

    async def on_timeout(self):
        await self.disable_buttons()

    @discord.ui.button(
        label="Confirm",
        style=discord.ButtonStyle.green
    )
    async def confirm(
        self,
        interaction: discord.Interaction,
        button: discord.ui.Button
    ):
        self.value = True

        await self.disable_buttons()


        config_data = gh.load_data(CONFIG_FILE, {"guilds": {}})
        if str(self.guild.id) not in config_data["guilds"]: config_data["guilds"][str(self.guild.id)] = {}
        config_data["guilds"][str(self.guild.id)] = {
            "channels": [channel.id for channel in self.channels],
            "dms": self.dms
        }

        gh.save_data(CONFIG_FILE, config_data)

        await interaction.response.edit_message(
            content="✅ AutoPing configuration saved.",
            embed=None,
            view=self
        )

        self.stop()

    @discord.ui.button(
        label="Cancel",
        style=discord.ButtonStyle.red
    )
    async def cancel(
        self,
        interaction: discord.Interaction,
        button: discord.ui.Button
    ):
        self.value = False

        await self.disable_buttons()

        await interaction.response.edit_message(
            content="❌ AutoPing setup cancelled.",
            embed=None,
            view=self
        )

        self.stop()


# ------------------------------------
# Cog
# ------------------------------------

class AutoPing(commands.Cog):

    def __init__(self, bot):
        self.bot = bot
        self.config_path = "Main/Customised/GarfieldGang/autoping_config.json"

    # Slash command group
    autoping = app_commands.Group(
        name="autoping",
        description="Configure automatic join pings.",
        guild_ids=[1444647745510965391, 1479749743784493128]
    )


    @autoping.command(
        name="setup",
        description="Configure AutoPing."
    )
    @app_commands.checks.has_permissions(administrator=True)
    @app_commands.describe(
        channels="Mention one or more channels.",
        dm="Whether to DM the joining member."
    )
    async def setup(
        self,
        interaction: discord.Interaction,
        channels: str,
        dm: Optional[bool] = True
    ):
        """
        Example:

        /autoping setup
        channels:
        #rules #shop #roles

        dm:
        True
        """

        found_channels = []

        ids = re.findall(r"<#(\d+)>", channels)

        for cid in ids:
            channel = interaction.guild.get_channel(int(cid))

            if isinstance(channel, discord.TextChannel):
                found_channels.append(channel)

        if not found_channels:
            await interaction.response.send_message(
                "❌ You must mention at least one valid text channel.",
                ephemeral=True
            )
            return

        embed = discord.Embed(
            title="AutoPing Setup",
            colour=discord.Colour.blurple()
        )

        embed.description = (
            "**Channels:**\n"
            + "\n".join(f"• {c.mention}" for c in found_channels)
            + f"\n\n**DM Members:** {'✅ Yes' if dm else '❌ No'}"
            + "\n\nPress **Confirm** to save this configuration."
        )

        view = AutoPingSetupView(
            interaction.user,
            interaction.guild,
            found_channels,
            dm
        )

        await interaction.response.send_message(
            embed=embed,
            view=view,
            ephemeral=True
        )


    @autoping.command(
        name="remove",
        description="Disable AutoPing for specific channels or all channels."
    )
    @app_commands.checks.has_permissions(administrator=True)
    @app_commands.describe(
        channels="Mention the channels to remove. Leave blank to remove all."
    )
    async def remove(
        self,
        interaction: discord.Interaction,
        channels: Optional[str] = None
    ):
        config = gh.load_data(CONFIG_FILE, {"guilds": {}})

        guild_data = config["guilds"].get(str(interaction.guild.id))

        if guild_data is None:
            await interaction.response.send_message(
                "❌ This server has no AutoPing configuration.",
                ephemeral=True
            )
            return

        if channels is None:
            description = (
                "You are about to **disable AutoPing completely** for this server.\n\n"
                "React with ✅ to confirm or ❌ to cancel."
            )
        else:
            ids = re.findall(r"<#(\d+)>", channels)

            found = []

            for cid in ids:
                channel = interaction.guild.get_channel(int(cid))
                if isinstance(channel, discord.TextChannel):
                    found.append(channel)

            if not found:
                await interaction.response.send_message(
                    "❌ No valid channels were provided.",
                    ephemeral=True
                )
                return

            description = (
                "You are about to remove AutoPing from:\n\n"
                + "\n".join(f"• {c.mention}" for c in found)
                + "\n\nReact with ✅ to confirm or ❌ to cancel."
            )

        embed = discord.Embed(
            title="Confirm AutoPing Removal",
            description=description,
            colour=discord.Colour.orange()
        )

        await interaction.response.send_message(embed=embed)

        message = await interaction.original_response()

        await message.add_reaction("✅")
        await message.add_reaction("❌")

        def check(reaction: discord.Reaction, user: discord.Member):
            return (
                user.id == interaction.user.id
                and reaction.message.id == message.id
                and str(reaction.emoji) in ("✅", "❌")
            )

        try:
            reaction, user = await self.bot.wait_for(
                "reaction_add",
                timeout=30,
                check=check
            )

        except asyncio.TimeoutError:
            embed.colour = discord.Colour.red()
            embed.title = "Timed Out"
            embed.description = "AutoPing removal timed out."

            await message.edit(embed=embed)

            try:
                await message.clear_reactions()
            except discord.Forbidden:
                pass

            return

        if str(reaction.emoji) == "❌":
            embed.colour = discord.Colour.red()
            embed.title = "❌ Cancelled"
            embed.description = "AutoPing removal was cancelled."

            await message.edit(embed=embed)

            try:
                await message.clear_reactions()
            except discord.Forbidden:
                pass

            return

        # User confirmed with ✅

        if channels is None:
            config["guilds"].pop(str(interaction.guild.id), None)

        else:
            ids_to_remove = {
                int(cid)
                for cid in re.findall(r"<#(\d+)>", channels)
            }

            guild_data["channels"] = [
                cid
                for cid in guild_data["channels"]
                if cid not in ids_to_remove
            ]

            if not guild_data["channels"]:
                config["guilds"].pop(str(interaction.guild.id), None)

        gh.save_data(CONFIG_FILE, config)

        embed.colour = discord.Colour.green()
        embed.title = "✅ AutoPing Updated"

        if channels is None:
            embed.description = "AutoPing has been completely disabled for this server."
        else:
            embed.description = "The selected channels have been removed from AutoPing."

        await message.edit(embed=embed)

        try:
            await message.clear_reactions()
        except discord.Forbidden:
            pass

    
    @autoping.command(
        name="view",
        description="View the current AutoPing configuration."
    )
    @app_commands.checks.has_permissions(administrator=True)
    async def view(
        self,
        interaction: discord.Interaction
    ):
        config = gh.load_data(CONFIG_FILE, {"guilds": {}})

        guild_data = config["guilds"].get(str(interaction.guild.id))

        if guild_data is None:
            await interaction.response.send_message(
                "❌ AutoPing has not been configured for this server.",
                ephemeral=True
            )
            return

        channel_ids = guild_data.get("channels", [])
        dms = guild_data.get("dms", True)

        valid_channels = []
        invalid_channels = 0

        for channel_id in channel_ids:
            channel = interaction.guild.get_channel(channel_id)

            if isinstance(channel, discord.TextChannel):
                valid_channels.append(channel)
            else:
                invalid_channels += 1

        embed = discord.Embed(
            title="📢 AutoPing Configuration",
            colour=discord.Colour.blurple()
        )

        embed.add_field(
            name="DM New Members",
            value="✅ Enabled" if dms else "❌ Disabled",
            inline=False
        )

        if valid_channels:
            embed.add_field(
                name=f"Configured Channels ({len(valid_channels)})",
                value="\n".join(
                    f"• {channel.mention}"
                    for channel in valid_channels
                ),
                inline=False
            )
        else:
            embed.add_field(
                name="Configured Channels",
                value="*No valid channels configured.*",
                inline=False
            )

        if invalid_channels:
            embed.add_field(
                name="Invalid Channels",
                value=f"⚠️ {invalid_channels} configured channel(s) no longer exist.",
                inline=False
            )

        embed.set_footer(
            text="Use /autoping setup to modify this configuration."
        )

        await interaction.response.send_message(
            embed=embed,
            ephemeral=True
        )


    @commands.Cog.listener()
    async def on_member_join(self, member: discord.Member):
        config = gh.load_data(CONFIG_FILE, {"guilds": {}})

        guild_data = config["guilds"].get(str(member.guild.id))
        if guild_data is None:
            return

        channel_ids = guild_data.get("channels", [])
        dm_enabled = guild_data.get("dms", True)

        pinged_channels = []

        for channel_id in channel_ids:
            channel = member.guild.get_channel(channel_id)

            if not isinstance(channel, discord.TextChannel):
                continue

            try:
                msg = await channel.send(member.mention)
                await msg.delete()

                pinged_channels.append(channel)

            except (discord.Forbidden, discord.HTTPException):
                continue

        if not dm_enabled or not pinged_channels:
            return

        embed = discord.Embed(
            colour=discord.Colour.blurple()
        )

        embed.description = (
            f"Welcome to **{member.guild.name}**!\n\n"
            "To help you get started, I've pinged you in the following important channels:"
        )

        channel_text = "\n".join(
            f"🔹 {channel.mention} • [Jump]({channel.jump_url})"
            for channel in pinged_channels
        )

        embed.add_field(
            name="Important Channels",
            value=channel_text[:1024],  # Discord field limit
            inline=False
        )

        embed.set_footer(
            text="Have fun and enjoy your stay!"
        )

        try:
            await member.send(embed=embed)
        except discord.Forbidden:
            pass

async def setup(bot):
    await bot.add_cog(AutoPing(bot))