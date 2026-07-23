import discord
from discord.ext import commands
import json
import os
import time


DEFAULT_PREFIXES = ['n!']
MAX_PREFIXES_PER_GUILD = 5
PREFIX_FILE = "Data/prefixes.json"


SUCCESS = '<:Success:1481222312345862215>'
FAIL = '<:Fail:1481222299381272696>'
LOL = '<:LOL:1481628689899720726>'
SUCCESS_ID = 1481222312345862215
FAIL_ID = 1481222299381272696


invites_cache = {}


def to_guild_object_list(guild_ids: list[int]):
    return [discord.Object(id=gid) for gid in guild_ids]

GUILD_IDS = [1444647745510965391, 
             1479749743784493128, 
             1490059335005507614, 
             1487851692748963992, 
             1519377441783550012]

GUILDS = to_guild_object_list(GUILD_IDS)
GUILDS_FILE = "Data/guild_config.json"


USER_PERMISSION_ERROR = discord.Embed(
                    title=f"{FAIL} Missing Permissions",
                    description="> You do not have the permission to execute that!",
                    color=discord.Color.red())

#------------------------------------------
# The thing for the bot uptime
#------------------------------------------
        
BOT_START_TIME = time.time()

def get_uptime():

    seconds = int(time.time() - BOT_START_TIME)

    days, seconds = divmod(seconds, 86400)
    hours, seconds = divmod(seconds, 3600)
    minutes, seconds = divmod(seconds, 60)

    return f"{days}d {hours}h {minutes}m {seconds}s"

#--------------
# Checks
#--------------
def is_creator():
    async def predicate(ctx):
        return ctx.author.id == 893866153196261376
    return commands.check(predicate)


def get_whitelisted_guilds(cog: str):
        data = load_data(GUILDS_FILE, {"guilds": {}})
        guilds = []

        for x in data["guilds"]:
            try:
                if data["guilds"][x][cog]:
                    guilds.append(int(x))
            except KeyError:
                continue
            else:
                continue
        print(guilds)
        return guilds
    
    

#--------------
# Help Embeds
#--------------
def fail(title: str, description: str = '> Command not executed'):
    return discord.Embed(title=f"{FAIL}{title}", description=f"{description}", color=discord.Color.red())

def success(title: str, description: str):
    return discord.Embed(title=f"{SUCCESS}{title}", description=f"{description}", color=discord.Color.green())

async def send(embed: discord.Embed, interaction: discord.Interaction = None, message: discord.Message = None):
    if interaction!=None:
        await interaction.response.send_message(embed=embed)
    else:
        await message.channel.send(embed=embed)

async def dm(user, embed: discord.Embed, empheral = False, interaction: discord.Interaction = None):
    try:
        await user.send(embed=embed)
    except discord.Forbidden:
        pass

#---------------
# Helper functions
#---------------
async def sync_commands(bot: discord.Client):
    try:
        synced = await bot.tree.sync()
        print(f"Synced {len(synced)} global commands.")

        for guild in GUILDS:
            try:
                synced = await bot.tree.sync(guild=guild)
                print(f"Synced {len(synced)} commands in {guild.id}")
            
            except discord.Forbidden as e:
                print("\033[31m" + "Ignoring Forbidden Exception while syncing guild commands: " + "\033[0m" + f"{e}\n Guild has been skipped.")
            
    except discord.Forbidden as e:
        print("\033[31m" + "Ignoring Forbidden Exception while syncing commands: " + "\033[0m" + f"{e}")

async def sync_guild(bot: discord.Client, guild_id: int):
    guild = discord.Object(id=guild_id)
    synced = await bot.tree.sync(guild=guild)

    print(
        f"Synced {len(synced)} commands in {guild_id}"
    )

    return synced


def format_permissions(perms):

    allowed = []

    for perm, value in perms:

        if value:
            allowed.append(
                perm.replace("_", " ").title()
            )

    return allowed


def format_dt(dt):
    return discord.utils.format_dt(dt, style="F")


def format_relative(dt):
    return discord.utils.format_dt(dt, style="R")


def user_badges(member: discord.Member):

    badges = []

    if member.guild.owner_id == member.id:
        badges.append("<:Crown:1519359031070691338> Owner")

    if member.bot:
        badges.append("<:Computer:1519361209877532822> Bot")

    if member.premium_since:
        badges.append("<:Diamond:1519358725125832864> Booster")

    return ", ".join(badges) or "None"


def load_data(file, default):
    if not os.path.exists(file) or os.path.getsize(file) == 0: return default
    with open(file, "r") as f: return json.load(f)


def save_data(file, data):
    with open(file, "w") as f: json.dump(data, f, indent=4)


def load_prefix_data():
    if not os.path.exists(PREFIX_FILE):
        return {"default_prefixes": DEFAULT_PREFIXES, "guild_prefixes": {}}
    try:
        with open(PREFIX_FILE, "r", encoding="utf-8") as f:
            data = json.load(f)
    except (json.JSONDecodeError, OSError):
        data = {"default_prefixes": DEFAULT_PREFIXES, "guild_prefixes": {}}

    if "default_prefixes" not in data or not isinstance(data['default_prefixes'], list):
        data['default_prefixes'] = DEFAULT_PREFIXES
    if "guild_prefixes" not in data or not isinstance(data['guild_prefixes'], dict):
        data['guild_prefixes'] = {}
    return data


def save_prefix_data(data):
    with open(PREFIX_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2)


def get_guild_prefixes(guild_id: int):
    data = load_prefix_data()
    prefixes = data['guild_prefixes'].get(str(guild_id), data['default_prefixes'])
    prefixes = [p for p in prefixes if isinstance(p, str) and p.strip()]
    return prefixes or DEFAULT_PREFIXES


def set_guild_prefixes(guild_id: int, prefixes):
    data = load_prefix_data()
    cleaned = []
    for p in prefixes:
        p = p.strip()
        if p and p not in cleaned:
            cleaned.append(p)
    if not cleaned:
        cleaned = DEFAULT_PREFIXES.copy()
    data['guild_prefixes'][str(guild_id)] = cleaned[:MAX_PREFIXES_PER_GUILD]
    save_prefix_data(data)
    return data['guild_prefixes'][str(guild_id)]


def parse_prefixed_content(content: str, prefixes): 
    for prefix in sorted(prefixes, key=len, reverse=True):
        for x in prefixes: print(x)
        if content.startswith(prefix):
            remaining = content[len(prefix):].lstrip()
            print(f"Remaining: {remaining}")
            if not remaining:
                return prefix, "", []
            parts = remaining.split()
            print(prefix)
            print(parts[0].lower())
            print((parts[1:] or ""))
            return prefix, parts[0].lower(), parts[1:]
    return None, None, None


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
    

async def resolve_user(bot: discord.Client, raw):
    if isinstance(raw, str):
        return await bot.fetch_user(int(raw))

    if isinstance(raw, int):
        return await bot.fetch_user(raw)
    
    if isinstance(raw, discord.Member) or isinstance(raw, discord.User):
        return raw

    return None


async def resolve_user(bot: discord.Client, raw: str):
    if raw.startswith("<@") and raw.endswith(">"):
        raw = raw.replace("<@", "").replace("!", "").replace(">", "")
    if not raw.isdigit():
        for user in bot.users:
            if user.name.lower() == raw.lower():
                return user
        return None
    
    user_id = int(raw)
    user = await bot.fetch_user(user_id)
    if user is not None:
        return user
    try:
        return await bot.fetch_user(user_id)
    except (discord.NotFound, discord.HTTPException):
        return None


async def resolve_user_id(bot: discord.Client, user):
        return user.id


async def resolve_channel(guild: discord.Guild, raw: str):
    print("Resolving channel...")
    if raw.startswith("<#") and raw.endswith(">"):
        raw = raw.replace("<#", "").replace("!", "").replace(">", "")
    if not raw.isdigit():
        for channel in guild.channels:
            if channel.name.lower() == raw.lower():
                return channel
        return None
    print(f"RAW: {raw}")
    channel_id = int(raw)
    channel = guild.get_channel(channel_id)
    print(f"Channel: {channel}")
    if channel is not None:
        return channel
    try:
        return await guild.fetch_channel(channel_id)
    except (discord.NotFound, discord.HTTPException):
        return None
    

def update_invites_cache(updated_invites_cache):
    invites_cache = updated_invites_cache


async def get_inviter( member: discord.Member):
    guild = member.guild

    new_invites = await guild.invites()
    old_invites = invites_cache.get(guild.id, {})

    used_invite = None

    for invite in new_invites:
        old_uses = old_invites.get(invite.code, 0)

        if invite.uses > old_uses:
            used_invite = invite
            break

    # update cache
    invites_cache[guild.id] = {i.code: i.uses for i in new_invites}
    return used_invite.inviter if used_invite else None
