import discord
from discord.ext import commands
from discord import app_commands
from dotenv import load_dotenv
import traceback
import json
import os
import random
from discord.ext import tasks
import GenHelp as gh
import asyncio
import sys
import time

load_dotenv()
intents = discord.Intents.all()

GUILD_IDS = [
    1479749743784493128,
    1490059335005507614,
    1487851692748963992,
    1444647745510965391,
    1519377441783550012
]

GUILDS = [discord.Object(id=g) for g in GUILD_IDS]
invites_cache = {}

def get_prefix(bot, message):
    prefixes = gh.get_guild_prefixes(message.guild.id)
    return prefixes or 'n!'

class MyBot(commands.Bot):
    
    async def setup_hook(self):
        print("Loading Moderation Cog")
        await self.load_extension("Cogs.Moderation.moderation")
        print("Successfully loaded Moderation Cog")

        print("Loading Logs Cog")
        await self.load_extension("Cogs.Logs.logs")
        print("Successfully loaded Logs Cog")

        print("Loading JL Cog")
        await self.load_extension("Cogs.Logs.joinleave")
        print("Successfully loaded JL Cog")

        print("Loading Util Cog")
        await self.load_extension("Cogs.Util.utility")
        print("Successfully loaded util Cog")

        print("Loading Role Cog")
        await self.load_extension("Cogs.Util.role")
        print("Successfully loaded Roles Cog")

        print("Loading Getter Cog")
        await self.load_extension("Cogs.Util.get")
        print("Successfully loaded Getter Cog")

        print("Loading Help Cog")
        await self.load_extension("Cogs.Util.help")
        print("Successfully loaded Help Cog")

        print("Loading Config Cog")
        await self.load_extension("config")
        print("Successfully loaded congif Cog")

        print("Loading Garfield Cog")
        await self.load_extension("Customised.GarfieldGang.autoping")
        print("Successfully loaded congif Cog")

        print("Loading Tickets Cog")
        await self.load_extension("Cogs.Tickets.tickets")
        print("Successfully loaded Tickets Cog")


bot = MyBot(command_prefix=get_prefix, intents=intents, strip_after_prefix=True, help_command=None)

statuses = [
    "Made by kitnapwastaken",
    "Also try ℌ𝔬𝔯𝔰𝔢'𝔰 𝔘𝔱𝔦𝔩𝔰",
    "🍞 Bread.",
    "Have a break, have a kitnap",
    "Also try the Moon Bot",
    "Hardcoded",
    "🪑 Chair.",
    "/sybau for a cookie",
    "Not for begooners",
    "/stfu for a nose bump",
    "Ping me",
    "Ez"
]


@tasks.loop(seconds=30)
async def random_status():
    random_status_ = random.randint(0, 10)
    status = statuses[random_status_]
    await bot.change_presence(status=discord.Status.dnd, activity=discord.Game(name=status))
    
@bot.event
async def on_ready():
    if not random_status.is_running():
        random_status.start()
    try:
        print(f"Logged in as {bot.user}")
        await gh.sync_commands(bot)
    except Exception:
        print("=========== COMMAND SYNC ERROR ===========")
        traceback.print_exc()

    for guild in bot.guilds:
        invites = await guild.invites()
        invites_cache[guild.id] = {invite.code: invite.uses for invite in invites}
        gh.update_invites_cache(invites_cache)

@bot.group(name='reload')
async def reload(ctx):
    pass

@gh.is_creator()
@reload.command(name='mod')
async def mod(ctx: commands.Context):
    print(f'{ctx.author.name} ran reload moderation')
    await ctx.message.add_reaction('<a:loading:1504726464057053255>')
    try:
        await bot.reload_extension("Cogs.Moderation.moderation")
        print('Extension reloaded')
        await asyncio.gather(
            ctx.message.remove_reaction('<a:loading:1504726464057053255>', bot.user),
            ctx.message.add_reaction('<:Success:1481222312345862215>')
            )
        
    except Exception:
        await print('============= RELAOD MOD ERROR =============')
        traceback.print_exc()
        await ctx.message.remove_reaction('<a:loading:1504726464057053255>', bot.user)
        await ctx.message.add_reaction('<:Fail:1481222299381272696>')

@gh.is_creator()
@reload.command(name='log', aliases=['logs'])
async def log(ctx: commands.Context):
    print(f'{ctx.author.name} ran reload logs')
    await ctx.message.add_reaction('<a:loading:1504726464057053255>')
    try:
        await bot.reload_extension("Cogs.Logs.logs")
        print('Extension reloaded')
        await ctx.message.remove_reaction('<a:loading:1504726464057053255>', bot.user)
        await ctx.message.add_reaction('<:Success:1481222312345862215>')
    except Exception:
        await print('============= RELAOD LOGS ERROR =============')
        traceback.print_exc()
        await ctx.message.remove_reaction('<a:loading:1504726464057053255>', bot.user)
        await ctx.message.add_reaction('<:Fail:1481222299381272696>')

@gh.is_creator()
@reload.command(name='joinleave', aliases=['jl', 'JoinLeave', 'JL'])
async def JoinLeave(ctx: commands.Context):
    print(f'{ctx.author.name} ran reload JoinLeave')
    await ctx.message.add_reaction('<a:loading:1504726464057053255>')
    try:
        await bot.reload_extension("Cogs.Logs.joinleave")
        print('Extension reloaded')
        await ctx.message.remove_reaction('<a:loading:1504726464057053255>', bot.user)
        await ctx.message.add_reaction('<:Success:1481222312345862215>')
    except Exception:
        await print('============= RELAOD JL ERROR =============')
        traceback.print_exc()
        await ctx.message.remove_reaction('<a:loading:1504726464057053255>', bot.user)
        await ctx.message.add_reaction('<:Fail:1481222299381272696>')

@gh.is_creator()
@reload.command(name='util', aliases=['ut', 'utility'])
async def utility(ctx: commands.Context):
    print(f'{ctx.author.name} ran reload util')
    await ctx.message.add_reaction('<a:loading:1504726464057053255>')
    try:
        await bot.reload_extension("Cogs.Util.utility")
        print('Extension reloaded')
        await ctx.message.remove_reaction('<a:loading:1504726464057053255>', bot.user)
        await ctx.message.add_reaction('<:Success:1481222312345862215>')
    except Exception:
        print('============= RELAOD UTIL ERROR =============')
        traceback.print_exc()
        await ctx.message.remove_reaction('<a:loading:1504726464057053255>', bot.user)
        await ctx.message.add_reaction('<:Fail:1481222299381272696>')

@gh.is_creator()
@reload.command(name='role', aliases=['r', 'roles'])
async def utility(ctx: commands.Context):
    print(f'{ctx.author.name} ran reload roles')
    await ctx.message.add_reaction('<a:loading:1504726464057053255>')
    try:
        await bot.reload_extension("Cogs.Util.role")
        print('Extension reloaded')
        await ctx.message.remove_reaction('<a:loading:1504726464057053255>', bot.user)
        await ctx.message.add_reaction('<:Success:1481222312345862215>')
    except Exception:
        print('============= RELAOD ROLES ERROR =============')
        traceback.print_exc()
        await ctx.message.remove_reaction('<a:loading:1504726464057053255>', bot.user)
        await ctx.message.add_reaction('<:Fail:1481222299381272696>')

@gh.is_creator()
@reload.command(name='getter', aliases=['get', 'getters'])
async def utility(ctx: commands.Context):
    print(f'{ctx.author.name} ran reload getters')
    await ctx.message.add_reaction('<a:loading:1504726464057053255>')
    try:
        await bot.reload_extension("Cogs.Util.get")
        print('Extension reloaded')
        await ctx.message.remove_reaction('<a:loading:1504726464057053255>', bot.user)
        await ctx.message.add_reaction('<:Success:1481222312345862215>')
    except Exception:
        print('============= RELAOD GETTERS ERROR =============')
        traceback.print_exc()
        await ctx.message.remove_reaction('<a:loading:1504726464057053255>', bot.user)
        await ctx.message.add_reaction('<:Fail:1481222299381272696>')

@gh.is_creator()
@reload.command(name="sync", aliases=["commands", "cmds"])
async def re_sync(ctx: commands.Context):
    await gh.sync_commands(bot)

@gh.is_creator()
@reload.command(name='all')
async def reload_all(ctx: commands.Context):
    print(f'{ctx.author.name} ran reboot')
    await ctx.message.add_reaction('<a:loading:1504726464057053255>')

    for x in list(bot.extensions.keys()):
        print(f"Reloading {x} extension")
        await bot.reload_extension(x)
        print("Successful")

    await ctx.message.remove_reaction('<a:loading:1504726464057053255>', bot.user)
    await ctx.message.add_reaction('<:Success:1481222312345862215>')

@gh.is_creator()
@commands.command(name="reboot")
async def reboot(ctx: commands.Context):
    print(f'{ctx.author.name} ran reboot')
    await ctx.message.add_reaction('<a:loading:1504726464057053255>')

    for x in list(bot.extensions.keys()):
        print(f"Reloading {x} extension")
        await bot.reload_extension(x)
        print("Successful")

    await gh.sync_commands(bot)

    await ctx.message.remove_reaction('<a:loading:1504726464057053255>', bot.user)
    await ctx.message.add_reaction('<:Success:1481222312345862215>')
    

token = os.getenv("DISCORD_BOT_TOKEN")
gh.BOT_START_TIME = time.time()
bot.run(token)