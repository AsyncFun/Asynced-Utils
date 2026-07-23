import discord
from discord.ext import commands
from discord import app_commands
import datetime
import asyncio
import json
import os 
import re
import time
import GenHelp as gh
import traceback as tb
SUCCESS = '<:Success:1481222312345862215>'
FAIL = '<:Fail:1481222299381272696>'
LOL = '<:LOL:1481628689899720726>'
USER_PERMISSION_ERROR = discord.Embed(
                    title=f"{FAIL} Missing Permissions",
                    description="> You do not have the permission to execute that!",
                    color=discord.Color.red())

BOT_PERMS_ERROR = discord.Embed(
                    title=f"{FAIL} Could not execute command!", 
                    description=f"> It looks like I do not have enough permissions.\n"
                                "> Try checking if my role is high enough or if I have permissions.",
                    color=discord.Color.red())
WARNS_FILE = "Data/Moderation/warns.json"
LOGS_FILE = "Data/Logs/log_channels.json"
# Interaction classes
class MessageResponseAdapter:
    def __init__(self, message: discord.Message):
        self._message = message

    async def send_message(self, content=None, *, embed=None, **kwargs):
        await self._message.reply(content=content, embed=embed, mention_author=False, **kwargs)

class MessageInteractionAdapter:
    def __init__(self, message: discord.Message):
        self.guild = message.guild
        self.user = message.author
        self.channel = message.channel
        self.response = MessageResponseAdapter(message)

#=========================================
# Checkers
#=========================================
def is_aura():
    try:
        async def predicate(ctx):
            return ctx.author.id == 1308381209507921950 or ctx.author.id == 893866153196261376
        return commands.check(predicate)
    except Exception:
        print("=========== ERROR WHILE CHECKING AURA ===========")
        tb.print_exc()

def can_warn():
    try:
        print("Warn check 1")
        async def predicate(ctx: commands.Context):
            print("warn check predicate was run [1]")
            is_mod = ctx.author.guild_permissions.moderate_members #or ctx.author.guild_permissions.administrator
            print(f"Is mod or admin?: {is_mod}")
            has_warn_role = False
            data = gh.load_data(WARNS_FILE, {"guilds": {}})
            if str(ctx.guild.id) in data["guilds"]:
                if "RolesAllwd" in data["guilds"][str(ctx.guild.id)]:
                    for role_id in data["guilds"][str(ctx.guild.id)]["RolesAllwd"]:
                        role = await ctx.guild.get_role(role_id)                                          
                        if role in ctx.author.roles:
                            print("Users has a warn role")
                            has_warn_role = True
                            break

            print(is_mod or has_warn_role)
            return (is_mod or has_warn_role)
        return commands.check(predicate)
    except Exception:
        print("=========== WARN CHECK ERROR ===========")
        tb.print_exc()

#==================================================================================================

#------------------------------------------
# Small Helpers
#------------------------------------------
async def resolve_args(message: discord.Message, args: list):
    # 1. If args exist → try resolving from args FIRST
    if len(args) > 0:
        target = await resolve_member(message.guild, args[0]) 
        if target:
            return target, args[1:]  # remaining args

    # 2. If replying → use replied user
    if message.reference and message.reference.message_id:
        try:
            replied_msg = await message.channel.fetch_message(message.reference.message_id)
            return replied_msg.author, args
        except:
            pass

    # 3. Nothing worked
    return None, args
#------------
async def resolve_member(guild: discord.Guild, raw: str):
    if raw.startswith("<@") and raw.endswith(">"):
        raw = raw.replace("<@", "").replace("!", "").replace(">", "")
    if not raw.isdigit():
        for member in guild.members:
            if member.name.lower() == raw.lower():
                return member
        return None
    
    member_id = int(raw)
    member = guild.get_member(member_id)
    if member is not None:
        return member
    try:
        return await guild.fetch_member(member_id)
    except (discord.NotFound, discord.HTTPException):
        return None
#-----------
async def get_args(ctx: commands.Context):
    if ctx.interaction == None and ctx.message:
        interaction = MessageInteractionAdapter(ctx.message)
        prefix, command_name, args = gh.parse_prefixed_content(ctx.message.content, gh.get_guild_prefixes(ctx.guild.id))
        print(f"Args: {args}")
        target, args = await resolve_args(ctx.message, args)
        return target, args
#-----------
async def log_moderation(interaction: discord.Interaction, member: discord.Member, moderator: discord.Member, action: str, duration = "N/A"):
        data = gh.load_data(LOGS_FILE, {"guilds": {}})
        gid = str(interaction.guild.id)
        if gid not in data["guilds"]:
            data["guilds"][gid] = {
                "message": -1,
                "member": -1,
                "roles": -1,
                "channels": -1}
        if data["guilds"][gid]["member"] == -1:
            return
        if duration != None and duration != "N/A":
            duration = f"{duration} seconds"
        else:
            duration = "N/A"

        if isinstance(member, str):
            member = await interaction.guild.fetch_member(member)

        log_channel = await interaction.guild.fetch_channel(data["guilds"][gid]["member"])
        embed = discord.Embed(title=f"Member {action}: ", color=discord.Color.red())
        embed.add_field(name="Moderated by: ", value=moderator.mention, inline=False)
        embed.add_field(name="Member: ", value=member.mention, inline=False)
        embed.add_field(name="Duration: ", value=f"{duration} seconds", inline=False)
        embed.timestamp = discord.utils.utcnow()

        await log_channel.send(embed=embed)

#-----------

async def userPermsError(interaction: discord.Interaction = None):
    if interaction!=None:
        await interaction.response.send_message(embed=USER_PERMISSION_ERROR)
        if interaction.user.id != 1308381209507921950 and interaction.user.id != 893866153196261376:
            await interaction.channel.send(f'{LOL}')
            return
        return

    else:
        raise NotEnoughArgs("Function takes in atleast one argument!")
        return
    
#-----------

async def botPermsError(interaction: discord.Interaction = None, message: discord.Message = None):
    if interaction != None:
        await interaction.response.send_message(embed=BOT_PERMS_ERROR)

#-----------

async def selfPunishmentError(interaction: discord.Interaction = None, message: discord.Message = None):
    await gh.send(gh.fail(f'You cannot punish yourself!'), interaction, message)

#-----------

async def powerCheck(guild: discord.Guild, executor: discord.Member, executed_on: discord.Member = None, interaction: discord.Interaction = None, message: discord.Message = None):
    # Return codes:
    # -1: guild owner (allowed)
    # 10: admin (allowed)
    # 5: moderator (allowed)
    # 0: executor cannot act on target (role hierarchy)
    # 1: bot cannot act on target (role hierarchy / missing perms)
    # -5: self-punish
    if executed_on != None:
        # Self-punish check should always run first
        if executor == executed_on:
            await selfPunishmentError(interaction, message)
            return -5
        
        if executed_on.id == guild.owner_id:
            await userPermsError(interaction=interaction)
            return 0
        
    # Owner bypasses user hierarchy checks
    if executor == guild.owner:
        return 50
    
    if executed_on != None:
    # If executor isn't admin, ensure they outrank the target
        if not executor.guild_permissions.administrator:
            if executor.top_role <= executed_on.top_role:
                await userPermsError(interaction)
                return 0

    # Always ensure the bot outranks the target before allowing the action
    if executed_on != None:
        me = interaction.guild.me if interaction != None else message.guild.me
        if me is not None and me.top_role <= executed_on.top_role:
            await botPermsError(interaction, message)
            return -1

    if executor.guild_permissions.administrator:
        return 10
    if executor.guild_permissions.kick_members:
        return 7
    if executor.guild_permissions.moderate_members:
        return 5

    return 0

#-----------

async def auto_unban(guild, user_id, seconds):
    await asyncio.sleep(seconds)
    try:
        await guild.fetch_ban(discord.Object(id=user_id))
        await guild.unban(discord.Object(id=user_id))
    except discord.NotFound:
        pass  

def parse_duration(time: str):
    units = {'s': 1, 'm': 60, 'h': 3600, 'd': 86400}
    if time[-1] not in units or time == "":
        return None
    try:
        return datetime.timedelta(seconds=int(time[:-1]) * units[time[-1]])
    except ValueError:
        return None
    
async def invalidDuration(interaction: discord.Interaction):
    await interaction.response.send_message(embed=discord.Embed(
                        title=f"{FAIL} Invalid Duration",
                        description="> Please use a valid duration format.",
                        color=discord.Color.red())
                        )
#============================
# Moderation Helpers
#============================

async def mute(user: discord.Member,
               reason: str,
               duration: str = '28d',
               interaction: discord.Interaction = None,
               message: discord.Message = None):
    
    
    permCheck = await powerCheck(interaction.guild, interaction.user, user, interaction, message)
    if permCheck <= 0 and permCheck != -5:
        return
    if permCheck == -5:
        return
    else:
        if interaction!=None:        
            duration = parse_duration(duration)
            if duration == None:
                await invalidDuration(interaction)
                return
            else:
                pass
        try:
            await user.timeout(duration, reason=reason)
            await gh.send(gh.success(f"  {user.name} was muted", f"> Duration: {duration} seconds \n> Reason: {reason}"), interaction)
            await log_moderation(interaction=interaction, member=user, moderator=interaction.user, action="muted", duration=duration)
            try:
                await gh.dm(user, gh.fail('You have been muted!', f"> Duration: {duration} seconds"), interaction=interaction)   
            except Exception as e:
                pass


        except discord.Forbidden as e:
            await botPermsError(interaction=interaction)
            return
        except discord.HTTPException as e:
            await gh.send(gh.fail(f"Failed to execute", f"More info: {e}"), interaction)
            return
        
async def unmute(user: discord.Member,
                 reason: str = "Good Boi",
                 interaction: discord.Interaction = None,
                 message: discord.Message = None):
    if interaction!=None:
        power = await powerCheck(interaction.guild, interaction.user, user, interaction)
        if power <= 0:
            return
       
        user = await interaction.guild.fetch_member(user.id)
        if not user.is_timed_out():
            await gh.send(gh.fail(f"   Failed to unmute", "> This user is not muted!"), interaction)
            return
        else:
            await user.timeout(None)
            await gh.send(gh.success(f"  User unmuted", f"> {user.mention} has been unmuted."), interaction)
            await log_moderation(interaction=interaction, member=user, moderator=interaction.user, action="unmuted")
        try:
            await gh.dm(user, gh.success(f"You have been unmuted!", f"> Reason: {reason}"), interaction=interaction)
        except Exception as e:
            pass

async def kick(user: discord.Member, interaction: discord.Interaction = None, reason: str = 'Not Provided', message: discord.Message = None):
    if interaction!=None:
        permCheck = await powerCheck(interaction.guild, interaction.user, user, interaction)
        if permCheck < 7 and not interaction.user.top_role.permissions.kick_members:
            if permCheck > 0 and permCheck < 7:
               await userPermsError(interaction)
            return
        
        try:
            try:
                await gh.dm(user, gh.fail(f"You have been kicked from {interaction.guild}!", f"> Reason: {reason}"), interaction=interaction)
            except Exception as e:
                pass
            await user.kick()
            await gh.send(gh.success(f"  Member kicked", f"> {user.mention} has been kicked from the server\n> Reason: {reason}"), interaction)
            await log_moderation(interaction=interaction, member=user, moderator=interaction.user, action="kicked")
        except KeyError:
            pass
        except Exception as e:            
            await gh.send(gh.fail(f" Issue encountered", f"> More info: {e}"), interaction)

async def ban(user: discord.User, duration: str, reason: str, interaction: discord.Interaction = None, message: discord.Message = None):
    if interaction!=None:
        try:
            permCheck = await powerCheck(interaction.guild, interaction.user, user, interaction)
            if permCheck < 10:
                if permCheck > 0:
                    await userPermsError(interaction)
                return
        except AttributeError:
            pass
        
        try:
            if duration == None:
                try:
                    await gh.dm(user, gh.fail(f"You have been Banned from {interaction.guild}!", f"> Duration: Permanent\n> Reason: {reason}"), interaction=interaction)
                except Exception as e:
                    pass
                try:
                    await gh.send(gh.success(f"{user.name} was banned!", f"> Duration: Permanent\n> Reason: {reason}"), interaction)
                    await interaction.guild.ban(user=user, reason=f"Banned by {interaction.user.name}: `{reason}`") 
                    await log_moderation(interaction=interaction, member=user, moderator=interaction.user, action="banned", duration=duration)
                except discord.NotFound:
                    await gh.send((gh.fail(f" Could not ban user", f"> User does not existor is already banned!")))

            else:
                duration = parse_duration(duration)
                if duration == None:
                    await invalidDuration(interaction)
                    return
                seconds = duration.total_seconds()
                try:
                    await gh.dm(user, gh.fail(f"You have been Banned from {interaction.guild}!", f"> Duration: {duration} seconds\n> Reason: {reason}"), interaction=interaction)
                except Exception:
                    pass
                await user.ban()
                await gh.send(gh.success(f"  {user.name} was banned!", f"> Duration: {duration} seconds\n> Reason: {reason}"), interaction)
                asyncio.create_task(auto_unban(interaction.guild, user.id, seconds))

        except discord.HTTPException as e:
            await gh.send(gh.fail(f" Failed to execute command", f"> {e}"), interaction)

async def unban(user, reason: str = 'Good boy', interaction: discord.Interaction = None, message: discord.Message = None):
    if not interaction.user.guild_permissions.administrator:
        await userPermsError(interaction)
        return
    
    if interaction != None:
        try:
            await interaction.guild.unban(discord.Object(id=int(user)), reason=reason)
            await gh.send(gh.success(f" User has been unbanned", description= ""), interaction, message)
            await log_moderation(interaction=interaction, member=user, moderator=interaction.user, action="unbanned")
        except discord.NotFound: 
            await gh.send(gh.fail(' Could not unban user!', '> The user either does not exist or is already unbanned!'), interaction, message)
        except Exception as e:
            await gh.send(gh.fail(f' Could not unban user!',f'> {e}'), interaction, message)

async def warnperms(action, role: discord.Role, interaction: discord.Interaction= None, message: discord.Message = None):
    power = await powerCheck(interaction.guild, executor=interaction.user, interaction=interaction, message=message)
    if power < 10:
        if power > 0:
            await userPermsError()
        return
# 1. Standardize the action input to a string
    if isinstance(action, list):
        action_str = action[0]
    elif hasattr(action, 'value'): # For Slash Command Choice objects
        action_str = action.value
    else:
        action_str = action

    # 2. Map prefix symbols to 'Add' or 'Remove'
    if action_str in ['+', 'add', 'Add']: 
        action_str = 'Add'
    elif action_str in ['-', 'remove', 'Remove']: 
        action_str = 'Remove'
    else:
        # If it's none of the above, the command shouldn't proceed
        return
    if not interaction.user.guild_permissions.administrator:
        await userPermsError()
        return

    data = gh.load_data(WARNS_FILE, {"guilds": {}})
    gid, rid = str(interaction.guild.id), str(role.id)
    # Creating the json outline if it doesnt exist
    if gid not in data['guilds']: data['guilds'][gid] = {}
    if "RolesAllwd" not in data['guilds'][gid]: data['guilds'][gid]['RolesAllwd'] = []
    # Add role
    if action_str == 'Add':
        # Add role only if it exists (To prevent doble entries)
        if rid not in data['guilds'][gid]['RolesAllwd']:
            data['guilds'][gid]['RolesAllwd'].append(rid)
            await gh.send(gh.success(" Role added", f"> Members with role <@&{rid}> can now issue warns!"), interaction=interaction, message=message)
        else:
            await gh.send(gh.fail(" Could not add role", '> The role is already included!'), interaction=interaction, message=message)
    
    if action_str == 'Remove':
        if rid in data['guilds'][gid]['RolesAllwd']:
            data['guilds'][gid]['RolesAllwd'].remove(rid)
            await gh.send(gh.success(" Role removed", f"> Members with role <@&{rid}> can no longer issue warns!"), interaction=interaction, message=message)
        else:
            await gh.send(gh.fail(" Could not remove role", '> The role is already excluded!'), interaction=interaction, message=message)

    gh.save_data(WARNS_FILE, data)
async def warn(executed_on: discord.Member = None, reason: str = "Not Provided", interaction: discord.Interaction = None, message: discord.Message = None):
    try:    
        data = gh.load_data(WARNS_FILE, {"guilds": {}})
        gid, rid, uid = str(interaction.guild.id), str(interaction.user.top_role.id), str(executed_on.id)

        # Creating the json outline if it doesnt exist
        if gid not in data['guilds']: data['guilds'][gid] = {}
        if "RolesAllwd" not in data['guilds'][gid]: data['guilds'][gid]['RolesAllwd'] = []
        if "warns" not in data['guilds'][gid]: data['guilds'][gid]['warns'] = {}
        if uid not in data['guilds'][gid]['warns']: data['guilds'][gid]['warns'][uid] = []
        
        # Get the list of allowed role IDs from your JSON (these are strings)
        allowed_role_ids = data['guilds'].get(gid, {}).get("RolesAllwd", [])
        
        power = await powerCheck(interaction.guild, executor=interaction.user, executed_on=executed_on, interaction=interaction, message=message)
        if power < 5:
            if power > 0:
                await userPermsError(interaction=interaction)
            return
            
        if power == -5:
            return
    
        now = datetime.datetime.now()
        timestamp = int(now.timestamp())
        discord_time_format = f"<t:{timestamp}:R>"
        warn_details = {"Responsible": interaction.user.id,
                        "Reason": reason,
                        "Time": discord_time_format
                    }
        data['guilds'][gid]['warns'][uid].append(warn_details)
        gh.save_data(file=WARNS_FILE, data=data)

        await interaction.response.send_message(embed=gh.success(f" {executed_on.name} has been warned", f"> Reason: {reason}\n> -# {executed_on.name} has been warned {len(data['guilds'][gid]['warns'][uid])} time(s)."))
    #    await log_moderation(interaction=interaction, member=executed_on, moderator=interaction.user, action="warned")
        try:
            await gh.dm(executed_on, embed=discord.Embed(
                title=f"You have been warned in {interaction.guild.name}!",
                description=f"> Reason: {reason}",
                color=discord.Color.red()), interaction=interaction)
        except Exception:
            pass
    except Exception:
        tb.print_exc()
async def warns(user: discord.Member = None, interaction: discord.Interaction = None, message: discord.Message = None):
    data = gh.load_data(WARNS_FILE, {"guilds": {}})
    guild = interaction.guild if interaction else message.guild
    gid = str(guild.id)

    # Ensure structure
    if gid not in data['guilds']:
        data['guilds'][gid] = {}
    if "warns" not in data['guilds'][gid]:
        data['guilds'][gid]['warns'] = {}

    warns_data = data['guilds'][gid]['warns']

    # =========================================================
    # 🔹 CASE 1: NO USER → SHOW ALL USERS + WARN COUNT
    # =========================================================
    if user is None:
        if len(warns_data) == 0:
            embed = gh.fail(" No warns data found for this server.")
            if interaction:
                await interaction.response.send_message(embed=embed)
            else:
                await message.channel.send(embed=embed)
            return

        # Build list
        lines = []
        for uid, warns_list in warns_data.items():
            if len(warns_list) == 0:
                continue
            lines.append((uid, len(warns_list)))

        if len(lines) == 0:
            embed = gh.fail(" No users currently have warns.")
            if interaction:
                await interaction.response.send_message(embed=embed)
            else:
                await message.channel.send(embed=embed)
            return

        # Sort by highest warns
        lines.sort(key=lambda x: x[1], reverse=True)

        desc = "**User — Warns**\n\n"
        for uid, count in lines:
            desc += f"<@{uid}> — **{count}**\n"

        embed = discord.Embed(
            title="📊 Warn Leaderboard",
            description=desc,
            color=discord.Color.orange()
        )

        if interaction:
            await interaction.response.send_message(embed=embed)
        else:
            await message.channel.send(embed=embed)
        return

    # =========================================================
    # 🔹 CASE 2: SPECIFIC USER → YOUR EXISTING PAGINATED VIEW
    # =========================================================

    uid = str(user.id)

    if uid not in warns_data:
        warns_data[uid] = []

    warns_list = warns_data[uid]

    if len(warns_list) == 0:
        embed = gh.fail(f" No warns found for {user.name}!")
        if interaction:
            await interaction.response.send_message(embed=embed)
        else:
            await message.channel.send(embed=embed)
        return

    warns_list = warns_list[::-1]

    per_page = 8
    pages = []

    for i in range(0, len(warns_list), per_page):
        chunk = warns_list[i:i + per_page]

        desc = ""
        for j, warn in enumerate(chunk, start=i + 1):
            desc += (
                f"**Warn {j}**\n"
                f"> 👮 <@{warn['Responsible']}>\n"
                f"> 📝 {warn['Reason']}\n"
                f"> ⏰ {warn['Time']}\n\n"
            )

        embed = discord.Embed(
            title=f"{user.name} • {len(warns_list)} warns",
            description=desc,
            color=discord.Color.orange()
        )

        embed.set_footer(text=f"Page {i//per_page + 1}/{(len(warns_list)-1)//per_page + 1}")
        pages.append(embed)

    if len(pages) == 1:
        if interaction:
            await interaction.response.send_message(embed=pages[0])
        else:
            await message.channel.send(embed=pages[0])
        return

    # 🔘 Buttons
    current_page = 0
    view = discord.ui.View(timeout=60)

    async def prev_callback(inter):
        nonlocal current_page
        if inter.user != (interaction.user if interaction else message.author):
            return await inter.response.send_message("Not your menu.", ephemeral=True)

        if current_page > 0:
            current_page -= 1
        await inter.response.edit_message(embed=pages[current_page], view=view)

    async def next_callback(inter):
        nonlocal current_page
        if inter.user != (interaction.user if interaction else message.author):
            return await inter.response.send_message("Not your menu.", ephemeral=True)

        if current_page < len(pages) - 1:
            current_page += 1
        await inter.response.edit_message(embed=pages[current_page], view=view)

    prev_btn = discord.ui.Button(label="◀", style=discord.ButtonStyle.secondary)
    next_btn = discord.ui.Button(label="▶", style=discord.ButtonStyle.secondary)

    prev_btn.callback = prev_callback
    next_btn.callback = next_callback

    view.add_item(prev_btn)
    view.add_item(next_btn)

    if interaction:
        await interaction.response.send_message(embed=pages[0], view=view)
        msg = await interaction.original_response()
    else:
        msg = await message.channel.send(embed=pages[0], view=view)

    await view.wait()
    for item in view.children:
        item.disabled = True
    await msg.edit(view=view)
    
async def unwarn(user: discord.Member, interaction: discord.Interaction, reason: str = 'Not provided'):
    data = gh.load_data(WARNS_FILE, {"guilds": {}})
    gid, rid, uid = str(interaction.guild.id), str(interaction.user.top_role.id), str(user.id)
    # Creating the json outline if it doesnt exist
    if gid not in data['guilds']: data['guilds'][gid] = {}
    if "RolesAllwd" not in data['guilds'][gid]: data['guilds'][gid]['RolesAllwd'] = []
    if "warns" not in data['guilds'][gid]: data['guilds'][gid]['warns'] = {}
    if uid not in data['guilds'][gid]['warns']: data['guilds'][gid]['warns'][uid] = []
    
    power = await powerCheck(interaction.guild, executor=interaction.user, executed_on=user, interaction=interaction)
    if power < 5:
        if power > 0:
            print("error in mh")
            await userPermsError(interaction=interaction)
        return
    
    # Get the list of allowed role IDs from your JSON (these are strings)
    allowed_role_ids = data['guilds'].get(gid, {}).get("RolesAllwd", [])
    has_permission = any(str(role.id) in allowed_role_ids for role in interaction.user.roles)
    is_admin_or_mod = interaction.user.guild_permissions.moderate_members or interaction.user.guild_permissions.administrator
    # Does the executor have the permission to execute this command?
    if not has_permission and not is_admin_or_mod:
        await userPermsError(interaction=interaction)
        return
    
    if len(data['guilds'][gid]['warns'][uid]) == 0:
        await interaction.response.send_message(embed=gh.fail(f" No warns found for {user.name}!"))
    else:
        data['guilds'][gid]['warns'][uid].clear()
        gh.save_data(WARNS_FILE, data=data)
        await gh.send(gh.success(f" {user.name} has been unwarned.", f"> Reason: {reason}\n> -# All warns have been cleared for {user.mention}!"), interaction=interaction)
        await log_moderation(interaction=interaction, member=user, moderator=interaction.user, action="warns cleared")
        try:
            await gh.dm(user=user, embed=gh.success(f" You have been unwarned!", f"> Reason: {reason}\n> All of your warns have been cleared in {interaction.guild.name}"),interaction=interaction)
        except Exception:
            pass

#=============================================================================================================================================================================================
#=============================================================================================================================================================================================

async def send_membercount(interaction: discord.Interaction):
    guild = interaction.guild
    bots = 0
    humans = 0
    total = 0

    for m in guild.members:
        if m.bot:
            bots+=1
        else:
            humans+=1

        total+=1

    embed = discord.Embed(description=f"### {interaction.guild.name} Member Count:", color=discord.Color.blue())
    embed.add_field(name="Total", value=total, inline=True)
    embed.add_field(name="Humans", value=humans, inline=True)
    embed.add_field(name="Bots", value=bots, inline=True)
    embed.set_thumbnail(url=interaction.guild.icon.url)

    await interaction.response.send_message(embed=embed)