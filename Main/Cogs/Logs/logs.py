from discord.ext import commands
import discord
import GenHelp as gh
import json
from discord import app_commands
from . import LogsHelp as lh
import asyncio

class Logs(commands.Cog):
    guilds = gh.get_whitelisted_guilds("logs")
    async def cog_checker(self, guild: discord.Guild):
        allowed_guilds = gh.get_whitelisted_guilds("logs")
        print(guild is not None and guild.id in allowed_guilds)
        return guild is not None and guild.id in allowed_guilds
        

    def __init__(self, bot: discord.Client):
        self.bot = bot
    
    @commands.Cog.listener()
    async def on_message_edit(self, before: discord.Message, after: discord.Message):
        if not await self.cog_checker(before.guild):
            return
            
        if before.author.bot:
            return
        if not (before.stickers and before.attachments and after.stickers and after.attachments):
            if before.content == after.content:
                return
        
        data = gh.load_data(lh.LOGS_FILE, {"guilds": {}})
        gid = str(before.guild.id)
        if gid not in data["guilds"]:
            data["guilds"][gid] = {
                "message": -1,
                "member": -1,
                "roles": -1,
                "channels": -1}
            
        if data["guilds"][gid]["message"] == -1:
            return

        log_channel = await self.bot.fetch_channel(data["guilds"][gid]["message"])
        embed = discord.Embed(
            title=f"Messages edited: ",
            description=f"> Edited by: {before.author.mention}\n> Edited in: <#{before.channel.id}>\n> [Jump to message](https://discord.com/channels/{before.guild.id}/{before.channel.id}/{before.id})",
            color=discord.Color.blue()
        )

        event_time = discord.utils.utcnow()
        
        before_content = before.content
        after_content = after.content

        if before.attachments:
            attachment_links = "\n".join(a.url for a in before.attachments)
            before_content += f"\n\n**Attachments:**\n{attachment_links}"

        if before.stickers:
            sticker_urls = ", ".join(s.url for s in before.stickers)
            after_content += f"\n\n**Stickers:** {sticker_urls}"

        if after.attachments:
            attachment_links = "\n".join(a.url for a in after.attachments)
            after_content += f"\n\n**Attachments:**\n{attachment_links}"

        if after.stickers:
            sticker_urls = ", ".join(s.url for s in after.stickers)
            after_content += f"\n\n**Stickers:** {sticker_urls}"


        embed.add_field(name="Before: ", value=before_content, inline=False)
        embed.add_field(name="After: ", value=after_content, inline=False)
        embed.timestamp = event_time
        await log_channel.send(embed=embed)
        

    @commands.Cog.listener()
    async def on_message_delete(self, message: discord.Message):
        if not await self.cog_checker(message.guild):
            return
        
        if message.author.bot:
            return

        data = gh.load_data(lh.LOGS_FILE, {"guilds": {}})
        gid = str(message.guild.id)
        if gid not in data["guilds"]:
            data["guilds"][gid] = {
                "message": -1,
                "member": -1,
                "roles": -1,
                "channels": -1}
            
        if data["guilds"][gid]["message"] == -1:
            return

        log_channel = await self.bot.fetch_channel(data["guilds"][gid]["message"])

        guild = message.guild
        deleter = None
        await asyncio.sleep(0.2)
        async for entry in guild.audit_logs(limit=1, action=discord.AuditLogAction.message_delete):

            if (
                entry.target.id == message.author.id and
                entry.extra.channel.id == message.channel.id
            ):
                event_time = entry.created_at
                print(deleter.mention)
                break

        if deleter is None:
            deleter = message.author # self-delete
            print(deleter.mention)

        embed = discord.Embed(
            title=f"Message deleted: ",
            description=f"> Sent by: {message.author.mention}\n> Deleted by: {deleter.mention}\n> Deleted in: <#{message.channel.id}>\n> [Jump to channel](https://discord.com/channels/{message.guild.id}/{message.channel.id}/{message.id})",
            color=discord.Color.red()
        )
        content = message.content

        if message.attachments:
            attachment_links = "\n".join(a.url for a in message.attachments)
            content += f"\n\n**Attachments:**\n{attachment_links}"

        if message.stickers:
            sticker_urls = ", ".join(s.url for s in message.stickers)
            content += f"\n\n**Stickers:** {sticker_urls}"

        embed.add_field(name="Deleted message: ", value=content, inline=False)
        embed.timestamp = discord.utils.utcnow()
        await log_channel.send(embed=embed)
    

    @commands.Cog.listener()
    async def on_bulk_message_delete(self, messages: list[discord.Message]):
        if not await self.cog_checker(messages[0].guild):
            return
        
        data = gh.load_data(lh.LOGS_FILE, {"guilds": {}})
        gid = str(messages[0].guild.id)
        if gid not in data["guilds"]:
            data["guilds"][gid] = {
                "message": -1,
                "member": -1,
                "roles": -1,
                "channels": -1}
            
        if data["guilds"][gid]["message"] == -1:
            return

        log_channel = await self.bot.fetch_channel(data["guilds"][gid]["message"])

        guild = messages[0].guild
        channel = messages[0].channel
        count = len(messages)

        await asyncio.sleep(1)  # ⏱ wait for audit log

        purger = None
        event_time = None
        await asyncio.sleep(0.2)
        async for entry in guild.audit_logs(limit=1, action=discord.AuditLogAction.message_bulk_delete):
            purger = entry.user
            event_time = entry.created_at
            break
        # fallback
        if purger is None:
            purger = "Unknown"

        messages_info = ""
        for m in messages:
            messages_info += f"<{m.author.name}>: {m.content}\n"
        embed = discord.Embed(
            title=f"Messages purged: ",
            description=f"> Bulk deletion detected in <#{channel.id}>!\n## Deleted messages: \n{messages_info}",
            color=discord.Color.red()
        )
        embed.add_field(name=f"Purged by: ", value=f"{purger.mention}", inline=False)
        embed.add_field(name=f"Purged in: ", value=f"<#{channel.id}>", inline=False)
        embed.timestamp = event_time
        await log_channel.send(embed=embed)
    
    @commands.Cog.listener()
    async def on_member_join(self, member: discord.Member):
        if not await self.cog_checker(member.guild):
            return
        
        data = gh.load_data(lh.LOGS_FILE, {"guilds": {}})
        gid = str(member.guild.id)
        if gid not in data["guilds"]:
            data["guilds"][gid] = {
                "message": -1,
                "member": -1,
                "roles": -1,
                "channels": -1}
        if "member" not in data["guilds"][gid]: data["guilds"][gid]["member"] = -1 
            
        if data["guilds"][gid]["member"] == -1:
            return
        # Get the inviter
        inviter = await gh.get_inviter(member = member)
        if inviter != None:
            pass
        else:
            inviter = f"Vanity Invite/Unknown"
        # Updating and saving the invites data
        ## Creating a structure
        m_id = str(member.id)
        i_id = str(inviter.id)
        invites_data = gh.load_data(lh.INVITES_FILE, {"guilds": {}})
        if gid not in invites_data["guilds"]: invites_data["guilds"][gid] = {}
        if "members" not in invites_data["guilds"][gid]: invites_data["guilds"][gid]["members"] = {}
        if i_id not in invites_data["guilds"][gid]["members"]: invites_data["guilds"][gid]["members"][i_id] = {}
        if m_id not in invites_data["guilds"][gid]["members"]: invites_data["guilds"][gid]["members"][m_id] = {"inviter": i_id,
                                                                                                                "joins": 0,
                                                                                                                "leaves": 0,
                                                                                                                "total": 0}

        # Logging the member's join action
        log_channel = await self.bot.fetch_channel(data["guilds"][gid]["member"])

        account_age_timestamp = int(member.created_at.timestamp())
        embed = discord.Embed(title=f"Member joined:", color=discord.Color.green())
        embed.add_field(name="Member", value=member.mention, inline=False)
        embed.add_field(name=f"Age of account:", value=f"<t:{account_age_timestamp}:D> (<t:{account_age_timestamp}:R>)", inline=False)
        embed.add_field(name="Invited by:", value=inviter, inline=False)
        embed.add_field(name="Member count:", value=member.guild.member_count, inline=False)

        embed.set_thumbnail(url="https://example.com/image.png")
        embed.timestamp = discord.utils.utcnow()
        await log_channel.send(embed=embed)


    @commands.Cog.listener()
    async def on_member_remove(self, member: discord.Member):
        if not await self.cog_checker(member.guild):
            return
        
        data = gh.load_data(lh.LOGS_FILE, {"guilds": {}})
        gid = str(member.guild.id)
        if gid not in data["guilds"]:
            data["guilds"][gid] = {
                "message": -1,
                "member": -1,
                "roles": -1,
                "channels": -1}
        if data["guilds"][gid]["member"] < 0:
            return
        log_channel = await self.bot.fetch_channel(data["guilds"][gid]["member"])
            
        if data["guilds"][gid]["member"] == -1:
            return

        inviter = await gh.get_inviter(member)
        if inviter != None:
            inviter = inviter.name
        else:
            inviter = f"Vanity Invite/Unknown"
        
        account_age_timestamp = int(member.created_at.timestamp())
        embed = discord.Embed(title=f"Member left:", color=discord.Color.red())
        embed.add_field(name="Member", value=member.name, inline=False)
        embed.add_field(name=f"Age of account:", value=f"<t:{account_age_timestamp}:D> (<t:{account_age_timestamp}:R>)", inline=False)
        embed.add_field(name="Invited by:", value=inviter, inline=False)
        embed.add_field(name="Member count:", value=member.guild.member_count, inline=False)
        embed.set_thumbnail(url="https://example.com/image.png")
        embed.timestamp = discord.utils.utcnow()
        await log_channel.send(embed=embed)

    @commands.Cog.listener()
    async def on_member_ban(self, guild: discord.Guild, member: discord.Member):
        if not await self.cog_checker(guild):
            return
        
        data = gh.load_data(lh.LOGS_FILE, {"guilds": {}})
        gid = str(member.guild.id)
        if gid not in data["guilds"]:
            data["guilds"][gid] = {
                "message": -1,
                "member": -1,
                "roles": -1,
                "channels": -1}
        if data["guilds"][gid]["member"] < 0: return
        log_channel = await self.bot.fetch_channel(data["guilds"][gid]["member"])
            
        if data["guilds"][gid]["member"] == -1:
            return

        inviter = await gh.get_inviter(member)
        if inviter != None:
            inviter = inviter.name
        else:
            inviter = f"Vanity Invite/Unknown"
        
        ban_entry = None
        async for bans in guild.bans():
            if bans.user.id == member.id:
                ban_entry = bans

        reason = ban_entry.reason
        user = ban_entry.user.name

        account_age_timestamp = int(member.created_at.timestamp())
        embed = discord.Embed(title=f"User banned:", color=discord.Color.red())
        embed.add_field(name="User", value=user, inline=False)
        embed.add_field(name="Reason", value=reason, inline=False)
        embed.add_field(name=f"Age of account:", value=f"<t:{account_age_timestamp}:D> (<t:{account_age_timestamp}:R>)", inline=False)
        embed.add_field(name="Invited by:", value=inviter, inline=False)
        embed.add_field(name="Member count:", value=member.guild.member_count, inline=False)
        embed.set_thumbnail(url="https://example.com/image.png")
        embed.timestamp = discord.utils.utcnow()
        await log_channel.send(embed=embed)

    @commands.Cog.listener()
    async def on_member_unban(self, guild: discord.Guild, member: discord.Member):
        if not await self.cog_checker(guild):
            return
        
        data = gh.load_data(lh.LOGS_FILE, {"guilds": {}})
        gid = str(member.guild.id)
        if gid not in data["guilds"]:
            data["guilds"][gid] = {
                "message": -1,
                "member": -1,
                "roles": -1,
                "channels": -1}
        if data["guilds"][gid]["member"] < 0: return
        log_channel = await self.bot.fetch_channel(data["guilds"][gid]["member"])
            
        if data["guilds"][gid]["member"] == -1:
            return
        asyncio.sleep(0.5)
        moderator = None
        reason = "Not Provided"
        async for entry in guild.audit_logs(limit=5, action=discord.AuditLogAction.unban):
            if entry.target.id != member.id:
                continue
            if (discord.utils.utcnow() - entry.created_at).total_seconds() > 5:
                continue
            moderator = entry.user
            reason = entry.reason
        
        if reason == member.name:
            reason = 'Not Provided'
        account_age_timestamp = int(member.created_at.timestamp())
        embed = discord.Embed(title=f"User unbanned:", color=discord.Color.red())
        embed.add_field(name="User", value=member, inline=False)
        embed.add_field(name="Unbanned by: ", value=moderator.name, inline=False)
        embed.add_field(name="Reason: ", value=reason, inline=False)
        embed.timestamp = discord.utils.utcnow()
        await log_channel.send(embed=embed)

    @commands.Cog.listener()
    async def on_member_update(self, before: discord.Member, after: discord.Member):
        if not await self.cog_checker(before.guild):
            return
        
        print(f"Member update was run in {before.guild.name}")
        data = gh.load_data(lh.LOGS_FILE, {"guilds": {}})
        gid = str(after.guild.id)
        if gid not in data["guilds"]:
            data["guilds"][gid] = {
                "message": -1,
                "member": -1,
                "roles": -1,
                "channels": -1}
        if data["guilds"][gid]["member"] == -1: return
        log_channel = await self.bot.fetch_channel(data["guilds"][gid]["member"])
        
        roles_added = []
        roles_removed = []

        moderator =  None
        await asyncio.sleep(0.2)
        async for entry in before.guild.audit_logs(limit=100, action=discord.AuditLogAction.member_role_update):
            if entry.target.id == after.id:
                moderator = entry.user
        embed = None
        if len(before.roles) > len(after.roles):
            for b in before.roles:
                if b not in after.roles:
                    roles_removed.append(b.mention)
            roles_removed_str = ", ".join(roles_removed)
            embed = discord.Embed(description=f"## User lost roles\n> User: {after.mention}\n> Removed by: {moderator.mention}\n> Roles removed: {roles_removed_str}", colour=discord.Colour.green())
        if len(before.roles) < len(after.roles):
            for a in after.roles:
                if a not in before.roles:
                    roles_added.append(a.mention)
            roles_added_str = ", ".join(roles_added)
            embed = discord.Embed(description=f"## User got roles\n> User: {after.mention}\n> Added by: {moderator.mention}\n> Roles added: {roles_added_str}", colour=discord.Colour.green())
        embed.timestamp = discord.utils.utcnow()
        await log_channel.send(embed=embed)

    @commands.Cog.listener()
    async def on_guild_role_create(self, role: discord.Role):
        if not await self.cog_checker(role.guild):
            return
        
        data = gh.load_data(lh.LOGS_FILE, {"guilds": {}})
        gid = str(role.guild.id)

        if gid not in data["guilds"]:
            return

        if data["guilds"][gid]["roles"] == -1:
            return

        log_channel = await self.bot.fetch_channel(data["guilds"][gid]["roles"])

        executor = None
        await asyncio.sleep(0.2)
        async for entry in role.guild.audit_logs(limit=1, action=discord.AuditLogAction.role_create):
            if entry.target.id != role.id:
                continue
            if (discord.utils.utcnow() - entry.created_at).total_seconds() > 5:
                continue
            executor = entry.user
            break


        embed = discord.Embed(title=f"New role created", description=f"## Role info:", color=role.color)
        embed.add_field(name=f"Created by", value=executor.mention, inline=False)
        embed.add_field(name=f"Name", value=role.name, inline=True)
        embed.add_field(name=f"Color [Hex]", value=f"#{role.color.value:06x}", inline=True)
        embed.add_field(name=f"Mentionable", value=role.mentionable, inline=True)
        embed.add_field(name=f"Hoist", value=role.hoist, inline=True)
        embed.add_field(name=f"Is Admin?", value=role.permissions.administrator, inline=True)
        embed.add_field(name=f"Is Moderator?", value=role.permissions.moderate_members, inline=True)
    
        embed.timestamp = discord.utils.utcnow()

        await log_channel.send(embed=embed)


    @commands.Cog.listener()
    async def on_guild_role_delete(self, role: discord.Role):
        if not await self.cog_checker(role.guild):
            return
        
        data = gh.load_data(lh.LOGS_FILE, {"guilds": {}})
        gid = str(role.guild.id)

        if gid not in data["guilds"]:
            return

        if data["guilds"][gid]["roles"] == -1:
            return

        log_channel = await self.bot.fetch_channel(data["guilds"][gid]["roles"])

        executor = None
        await asyncio.sleep(0.2)
        async for entry in role.guild.audit_logs(limit=1, action=discord.AuditLogAction.role_delete):
            if entry.target.id != role.id:
                continue
            if (discord.utils.utcnow() - entry.created_at).total_seconds() > 5:
                continue
            executor = entry.user
            break


        embed = discord.Embed(title=f"Role deleted", description=f"## Role info:", color=role.color)
        embed.add_field(name=f"Deleted by", value=executor.mention, inline=False)
        embed.add_field(name=f"Name", value=role.name, inline=True)
        embed.add_field(name=f"Color [Hex]", value=f"#{role.color.value:06x}", inline=True)
        embed.add_field(name=f"Mentionable", value=role.mentionable, inline=True)
        embed.add_field(name=f"Hoist", value=role.hoist, inline=True)
        embed.add_field(name=f"Was Admin?", value=role.permissions.administrator, inline=True)
        embed.add_field(name=f"Was Moderator?", value=role.permissions.moderate_members, inline=True)
    
        embed.timestamp = discord.utils.utcnow()

        await log_channel.send(embed=embed)


    @commands.Cog.listener()
    async def on_guild_role_update(self, before: discord.Role, after: discord.Role):
        if not await self.cog_checker(before.guild):
            return
        
        print("Role update was run")
        data = gh.load_data(lh.LOGS_FILE, {"guilds": {}})
        gid = str(before.guild.id)

        if gid not in data["guilds"]:
            return

        if data["guilds"][gid]["roles"] == -1:
            return

        log_channel = await self.bot.fetch_channel(data["guilds"][gid]["roles"])
        # Checking for all changes.
        changes = []

        if before.name != after.name:
            changes.append(f"**Name:** `{before.name}` → `{after.name}`")
        if before.color != after.color:
            changes.append(f"**Color:** `{before.color}` → `{after.color}`")
        if before.color != after.color:
            changes.append(f"**Mentionable:** `{before.mentionable}` → `{after.mentionable}`")
        if before.hoist != after.hoist:
            changes.append(f"**Hoisted:** `{before.hoist}` → `{after.hoist}`")


        # Checking permissions
        if before.permissions != after.permissions:
            added = []
            removed = []

            for perm, value in after.permissions:
                before_value = getattr(before.permissions, perm)

                if value and not before_value:
                    added.append(perm)

                elif not value and before_value:
                    removed.append(perm)

            if added:
                changes.append(f"**Permissions Added:** {', '.join(added)}")

            if removed:
                changes.append(f"**Permissions Removed:** {', '.join(removed)}")
            
        # Getting the user responsible for the change(s)
        executor = None
        await asyncio.sleep(0.2)
        async for entry in before.guild.audit_logs(limit=1, action=discord.AuditLogAction.role_update):

            if entry.target.id != before.id:
                continue
            if (discord.utils.utcnow() - entry.created_at).total_seconds() > 5:
                continue
            executor = entry.user
            break

        # Final embedding
        if not changes:
            return

        embed = discord.Embed(
            title="Role Updated",
            description=f"> Role: {after.mention}\n"
                        f"> Updated by: {executor.mention if executor else 'Unknown'}",
            color=after.color if after.color.value != 0 else discord.Color.yellow()
        )

        embed.add_field(
            name="Changes:",
            value="\n".join(changes),
            inline=False
        )

        embed.timestamp = discord.utils.utcnow()
        await log_channel.send(embed=embed)

    @commands.Cog.listener()
    async def on_guild_channel_create(self, channel: discord.abc.GuildChannel):
        if not await self.cog_checker(channel.guild):
            return
        
        print(f"Channel was created in {channel.guild.name}")
        data = gh.load_data(lh.LOGS_FILE, {"guilds": {}})
        gid = str(channel.guild.id)

        if gid not in data["guilds"] or data["guilds"][gid]["channels"] == -1:
            return

        log_channel = await self.bot.fetch_channel(data["guilds"][gid]["channels"])

        # 🔍 Get who created it
        creator = None
        await asyncio.sleep(0.2)
        async for entry in channel.guild.audit_logs(limit=1, action=discord.AuditLogAction.channel_create):
            if entry.target.id == channel.id:
                creator = entry.user
                break

        embed = discord.Embed(
            title="Channel Created",
            description=f"> Channel: {channel.mention}\n"
                        f"> Created by: {creator.mention if creator else 'Unknown'}",
            color=discord.Color.green()
        )

        embed.timestamp = discord.utils.utcnow()
        await log_channel.send(embed=embed)

    @commands.Cog.listener()
    async def on_guild_channel_delete(self, channel: discord.abc.GuildChannel):
        if not await self.cog_checker(channel.guild):
            return
        
        print(f"Channel was deleted in {channel.guild.name}")
        data = gh.load_data(lh.LOGS_FILE, {"guilds": {}})
        gid = str(channel.guild.id)

        if gid not in data["guilds"] or data["guilds"][gid]["channels"] == -1:
            return

        log_channel = await self.bot.fetch_channel(data["guilds"][gid]["channels"])

        deleter = None
        await asyncio.sleep(0.2)
        async for entry in channel.guild.audit_logs(limit=1, action=discord.AuditLogAction.channel_delete):
            if entry.target.id == channel.id:
                deleter = entry.user
                break

        embed = discord.Embed(
            title="Channel Deleted",
            description=f"> Channel: `{channel.name}`\n"
                        f"> Deleted by: {deleter.mention if deleter else 'Unknown'}",
            color=discord.Color.red()
        )
        embed.timestamp = discord.utils.utcnow()
        await log_channel.send(embed=embed)


    @commands.Cog.listener()
    async def on_guild_channel_update(self, before: discord.abc.GuildChannel, after: discord.abc.GuildChannel):
        if not await self.cog_checker(before.guild):
            return
        
        print(f"Channel was updated in {before.guild.name}")
        data = gh.load_data(lh.LOGS_FILE, {"guilds": {}})
        gid = str(before.guild.id)
    
        if gid not in data["guilds"] or data["guilds"][gid]["channels"] == -1:
            return

        log_channel = await self.bot.fetch_channel(data["guilds"][gid]["channels"])

        changes = []
        before_topic = before.topic or ""
        after_topic = after.topic or ""
        if before_topic != after_topic:
            changes.append(f"**Name:** `{before.name}` → `{after.name}`")

        if hasattr(before, "topic") and before.topic != after.topic:
            changes.append(f"**Topic:** {f"`{before.topic}`" if before.topic else f"{"Empty"}"} → {f"`{after.topic}`" if after.topic else f"{"Removed"}"}")

        if hasattr(before, "nsfw") and before.nsfw != after.nsfw:
            changes.append(f"**NSFW:** `{before.nsfw}` → `{after.nsfw}`")

        if hasattr(before, "slowmode_delay") and before.slowmode_delay != after.slowmode_delay:
            changes.append(f"**Slowmode:** `{before.slowmode_delay}` → `{after.slowmode_delay}`")

        if before.overwrites != after.overwrites:
            changes.append("### Permissions updated")

        if not changes:
            return
        
        if before.overwrites != after.overwrites:

            overwrite_changes = []

            before_ow = before.overwrites
            after_ow = after.overwrites

            # get all targets (roles/users)
            all_targets = set(before_ow.keys()) | set(after_ow.keys())

            for target in all_targets:

                before_perms = before_ow.get(target)
                after_perms = after_ow.get(target)

                target_name = target.mention if hasattr(target, "mention") else str(target)

                if before_perms is None and after_perms is not None:
                    perms = [p for p, v in after_perms if v is True]
                    overwrite_changes.append(
                        f"<:Added:1501271054369165375> **{target_name} granted:** {', '.join(perms) or 'None'}"
                    )
                    continue

                # ❌ Overwrite removed
                if before_perms is not None and after_perms is None:
                    overwrite_changes.append(f"<:Minus:1501271056735015044> **{target_name} overwrite removed**")
                    continue

                # 🔁 Modified overwrite
                added = []
                removed = []
                reset = []

                for perm, value in after_perms:
                    before_value = getattr(before_perms, perm)

                    if value is True and before_value is not True:
                        added.append(perm)

                    elif value is False and before_value is not False:
                        removed.append(perm)

                    elif value is None and before_value is not None:
                        reset.append(perm)

                if added or removed or reset:
                    text = f"**{target_name}:**"

                    if added:
                        text += f"\n  <:Added:1501271054369165375> **Allowed**: {', '.join(added)}"

                    if removed:
                        text += f"\n  <:Minus:1501271056735015044> **Denied**: {', '.join(removed)}"

                    if reset:
                        text += f"\n  <:Neutral:1501271058886688778> *Reset*: {', '.join(reset)}"

                    overwrite_changes.append(text)

            if overwrite_changes:
                changes.append("- **Permission Overwrites Updated:**\n" + "\n".join(overwrite_changes))

        updater = None
        await asyncio.sleep(1) 
        async for entry in before.guild.audit_logs(limit=1, action=discord.AuditLogAction.channel_update):
            if entry.target.id == before.id:
                updater = entry.user
                break

        embed = discord.Embed(
            title="Channel Updated",
            description=f"> Channel: {after.mention}\n"
                        f"> Updated by: {updater.mention if updater else 'Unknown'}\n"
                        f"## Changes\n"
                        f"{"\n".join(changes)}",
            color=discord.Color.orange()
        )
        embed.timestamp = discord.utils.utcnow()
        await log_channel.send(embed=embed)



    @app_commands.command(name='setup-logs', description= 'Setup logs for this server.')
    @app_commands.guilds(*guilds)
    @commands.has_permissions(administrator=True)
    async def setupLogs(self, interaction: discord.Interaction):
        await interaction.response.send_message(
        "Select which logs to setup:",
        view=lh.CategoryView(),
        ephemeral=True
    )
    
    @app_commands.command(name="disable-logs", description="Disable all logging from the server")
    @app_commands.guilds(*guilds)
    @app_commands.checks.has_permissions(administrator=True)
    async def disablelogs(self, interaction: discord.Interaction):
        data = gh.load_data(lh.LOGS_FILE, {"guilds": {}})
        gid = str(interaction.guild.id)
        data["guilds"][gid] = {
            "message": -1,
            "member": -1,
            "roles": -1,
            "channels": -1}
        gh.save_data(lh.LOGS_FILE, data) 

async def setup(bot):
    await bot.add_cog(Logs(bot))


    