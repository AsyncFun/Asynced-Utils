from discord.ext import commands
import discord
from discord import app_commands
import GenHelp as gh
from . import LogsHelp as lh
import json
import traceback
import asyncio


guilds = gh.get_whitelisted_guilds("joinleave")
class JoinLeave(commands.Cog):
    async def cog_check(self, ctx: commands.Context):
        allowed_guilds = gh.get_whitelisted_guilds("joinleave")
        return ctx.guild is not None and ctx.guild.id in allowed_guilds
    

    def __init__(self, bot: discord.Client):
        self.bot = bot

    join = app_commands.Group(
        name="join-messages",
        description="Join message commands",
        guild_ids=(guilds)
    )

    leave = app_commands.Group(
        name="leave-messages",
        description="Leave message commands",
        guild_ids=(guilds)
    )

    @commands.Cog.listener()
    async def on_message(self, message: discord.Message):
        if message.author.bot or message.guild is None:
            return

        if message.author.id not in lh.pending_message_edits:
            return

        if message.channel.id != lh.pending_message_edits[message.author.id]["channel_id"]:
            return

        data = lh.pending_message_edits[message.author.id]

        try:
            parsed = json.loads(message.content)

            if not isinstance(parsed, dict):
                parsed = {
                    "content": message.content,
                    "embeds": []
                }

        except Exception:
            parsed = {
                "content": message.content,
                "embeds": []
            }

        if "content" not in parsed:
            parsed["content"] = ""

        if "embeds" not in parsed:
            parsed["embeds"] = []

        preview_data = lh.parse_placeholders(parsed, message.author)

        embeds = [
            discord.Embed.from_dict(embed)
            for embed in preview_data.get("embeds", [])
        ]
        

        embeds[0].set_thumbnail(url=message.author.display_avatar.url)

        await message.delete()

        preview_message = await message.channel.send(
            content=preview_data.get("content") or None,
            embeds=embeds
        )

        confirm_message = await message.channel.send(
            "React with ✅ to confirm this message, or ❌ to cancel."
        )

        await confirm_message.add_reaction("✅")
        await confirm_message.add_reaction("❌")

        def check(reaction, user):
            return (
                user.id == message.author.id
                and reaction.message.id == confirm_message.id
                and str(reaction.emoji) in ["✅", "❌"]
            )

        try:
            reaction, user = await self.bot.wait_for(
                "reaction_add",
                timeout=30,
                check=check
            )

        except asyncio.TimeoutError:
            lh.pending_message_edits.pop(message.author.id, None)

            await confirm_message.edit(
                content=f"{gh.FAIL} Message update timed out."
            )
            return

        if str(reaction.emoji) == "❌":
            lh.pending_message_edits.pop(message.author.id, None)

            await confirm_message.edit(
                content=f"{gh.FAIL} Message update cancelled."
            )
            return

        guild_id = str(data["guild_id"])
        joinleave = gh.load_data(lh.JOIN_LEAVE_FILE, {"guilds": {}})

        if guild_id not in joinleave["guilds"]:
            joinleave["guilds"][guild_id] = {}

        if data["type"] == "join":
            if "join" not in joinleave["guilds"][guild_id]:
                joinleave["guilds"][guild_id]["join"] = {
                    "enabled": True,
                    "channel": message.channel.id,
                    "message_data": lh.DEFAULT_JOIN_MESSAGE
                }

            joinleave["guilds"][guild_id]["join"]["message_data"] = parsed
            data["view"].message_data = parsed

            title = "Join message updated"

        else:
            if "leave" not in joinleave["guilds"][guild_id]:
                joinleave["guilds"][guild_id]["leave"] = {
                    "enabled": True,
                    "channel": message.channel.id,
                    "message_data": lh.DEFAULT_LEAVE_MESSAGE
                }

            joinleave["guilds"][guild_id]["leave"]["message_data"] = parsed
            data["view"].message_data = parsed

            title = "Leave message updated"

        gh.save_data(lh.JOIN_LEAVE_FILE, joinleave)
        lh.pending_message_edits.pop(message.author.id, None)

        await confirm_message.edit(
            content=f"{gh.SUCCESS} {title}."
        )

    @commands.Cog.listener()
    async def on_member_join(self, member: discord.Member):
        joinleave_data = gh.load_data(lh.JOIN_LEAVE_FILE, {"guilds": {}})
        gid = str(member.guild.id)

        if gid not in joinleave_data["guilds"]:
            return

        if "join" not in joinleave_data["guilds"][gid]:
            return

        config = joinleave_data["guilds"][gid]["join"]

        if not config["enabled"]:
            return

        channel = member.guild.get_channel(config["channel"])

        if channel is None:
            return

        message_data = lh.parse_placeholders(config["message_data"], member)

        embeds = [
            discord.Embed.from_dict(embed)
            for embed in message_data.get("embeds", [])
        ]

        if embeds:
            embeds[0].set_thumbnail(url=member.display_avatar.url)

        await channel.send(
            content=message_data.get("content"),
            embeds=embeds
        )

    @commands.Cog.listener()
    async def on_member_remove(self, member: discord.Member):
        joinleave_data = gh.load_data(lh.JOIN_LEAVE_FILE, {"guilds": {}})
        gid = str(member.guild.id)

        if gid not in joinleave_data["guilds"]:
            return

        if "leave" not in joinleave_data["guilds"][gid]:
            return

        config = joinleave_data["guilds"][gid]["leave"]

        if not config["enabled"]:
            return

        channel = member.guild.get_channel(config["channel"])

        if channel is None:
            return

        message_data = lh.parse_placeholders(config["message_data"], member)

        embeds = [
            discord.Embed.from_dict(embed)
            for embed in message_data.get("embeds", [])
        ]

        if embeds:
            embeds[0].set_thumbnail(url=member.display_avatar.url)

        await channel.send(
            content=message_data.get("content"),
            embeds=embeds
        )

    @join.command(name="setup", description="Setup join messages")
    @app_commands.checks.has_permissions(administrator=True)
    async def join_setup(
        self,
        interaction: discord.Interaction,
        channel: discord.TextChannel = None
    ):
        if channel is None:
            preview_channel = "#joins"
            create_channel = True
        else:
            preview_channel = channel.mention
            create_channel = False

        embed = discord.Embed(
            title="Setup Join Messages",
            description=(
                f"Are you sure you want to setup "
                f"join messages in {preview_channel}?\n"
            ),
            color=discord.Color.green()
        )

        data = gh.load_data(lh.JOIN_LEAVE_FILE, {"guilds": {}})
        gid = str(interaction.guild.id)

        if gid not in data["guilds"]:
            data["guilds"][gid] = {}

        if "join" not in data["guilds"][gid]:
            data["guilds"][gid]["join"] = {
                "enabled": False,
                "channel": None,
                "message_data": lh.DEFAULT_JOIN_MESSAGE
            }
            gh.save_data(lh.JOIN_LEAVE_FILE, data)

        message_data = data["guilds"][gid]["join"]["message_data"]
        content, embeds = lh.parse_message_data(message_data=message_data, join=True)
        for emb in embeds:
            emb.set_thumbnail(url=interaction.user.display_avatar.url)

        await interaction.response.send_message(embed=embed, ephemeral=False)
        await interaction.channel.send(content="## Join message preview:")
        await interaction.channel.send(
            content=content,
            embeds=embeds,
            view=lh.JoinMessageSetupView(
                author_id=interaction.user.id,
                channel=channel,
                create_channel=create_channel,
                message_data=message_data
            )
        )

    @join.command(name="disable", description="Disable join messages")
    @app_commands.checks.has_permissions(administrator=True)
    async def join_disable(self, interaction: discord.Interaction):
        data = gh.load_data(lh.JOIN_LEAVE_FILE, {"guilds": {}})
        gid = str(interaction.guild.id)

        if gid not in data["guilds"]:
            data["guilds"][gid] = {}

        if "join" not in data["guilds"][gid]:
            data["guilds"][gid]["join"] = {
                "enabled": False,
                "channel": None,
                "message_data": lh.DEFAULT_JOIN_MESSAGE
            }
        else:
            data["guilds"][gid]["join"]["enabled"] = False

        gh.save_data(lh.JOIN_LEAVE_FILE, data)

        await interaction.response.send_message(
            f"{gh.SUCCESS} Join messages have been disabled.",
            ephemeral=True
        )

    @leave.command(name="setup", description="Setup leave messages")
    @app_commands.checks.has_permissions(administrator=True)
    async def leave_setup(
        self,
        interaction: discord.Interaction,
        channel: discord.TextChannel = None
    ):
        if channel is None:
            preview_channel = "#leaves"
            create_channel = True
        else:
            preview_channel = channel.mention
            create_channel = False

        embed = discord.Embed(
            title="Setup Leave Messages",
            description=(
                f"Are you sure you want to setup "
                f"leave messages in {preview_channel}?\n"
            ),
            color=discord.Color.green()
        )

        data = gh.load_data(lh.JOIN_LEAVE_FILE, {"guilds": {}})
        gid = str(interaction.guild.id)

        if gid not in data["guilds"]:
            data["guilds"][gid] = {}

        if "leave" not in data["guilds"][gid]:
            data["guilds"][gid]["leave"] = {
                "enabled": False,
                "channel": None,
                "message_data": lh.DEFAULT_LEAVE_MESSAGE
            }
            gh.save_data(lh.JOIN_LEAVE_FILE, data)

        message_data = data["guilds"][gid]["leave"]["message_data"]
        content, embeds = lh.parse_message_data(message_data=message_data, leave=True)

        await interaction.response.send_message(embed=embed, ephemeral=False)
        await interaction.channel.send(content="## Leave message preview:")
        await interaction.channel.send(
            content=content,
            embeds=embeds,
            view=lh.LeaveMessageSetupView(
                author_id=interaction.user.id,
                channel=channel,
                create_channel=create_channel,
                message_data=message_data
            )
        )

    @leave.command(name="disable", description="Disable leave messages")
    @app_commands.checks.has_permissions(administrator=True)
    async def leave_disable(self, interaction: discord.Interaction):
        data = gh.load_data(lh.JOIN_LEAVE_FILE, {"guilds": {}})
        gid = str(interaction.guild.id)

        if gid not in data["guilds"]:
            data["guilds"][gid] = {}

        if "leave" not in data["guilds"][gid]:
            data["guilds"][gid]["leave"] = {
                "enabled": False,
                "channel": None,
                "message_data": lh.DEFAULT_LEAVE_MESSAGE
            }
        else:
            data["guilds"][gid]["leave"]["enabled"] = False

        gh.save_data(lh.JOIN_LEAVE_FILE, data)

        await interaction.response.send_message(
            f"{gh.SUCCESS} Leave messages have been disabled.",
            ephemeral=True
        )


async def setup(bot):
    try:
        await bot.add_cog(JoinLeave(bot))
    except Exception:
        print("=========== JOINLEAVE COG SETUP ERROR ===========")
        traceback.print_exc()