from discord.ext import commands
import discord
import GenHelp as gh
import json
from discord import app_commands
import asyncio
from . import UtilHelp as uh
from Cogs.Moderation import ModHelp as mh
import re

guilds = gh.get_whitelisted_guilds("utility")
class Util(commands.Cog):
    def __init__(self, bot: discord.Client):
        self.bot = bot
    @commands.hybrid_command(name='membercount', description="Display the server's member count", aliases=['mc', 'memberc', 'mcount'])
    @app_commands.guilds(*guilds)
    async def membercount(self, ctx: commands.Context):
        interaction = ctx.interaction if ctx.interaction != None else mh.MessageInteractionAdapter(ctx.message)
        await uh.send_membercount(interaction=interaction)

    @commands.hybrid_group(name='prefix', description='Group of commands to setup prefixes', aliases = ['prefixes', 'pf'])
    @app_commands.guilds(*guilds)
    @commands.has_guild_permissions(moderate_members=True)
    async def prefix(self, ctx: commands.Context):
        g_prefixes = gh.get_guild_prefixes(ctx.guild.id)
        prefixes_string = '`, `'.join(g_prefixes)
        embed = discord.Embed(title='Prefixes', description=f'> Active prefixes for this server:\n> `{prefixes_string}`', color=discord.Color.green())
        await ctx.channel.send(embed=embed, reference=ctx.message, mention_author=False)

    @prefix.command(name='add', description='Add command prefixes for this server (Admin only)', aliases=['a'])
    @commands.has_guild_permissions(administrator=True)
    async def add_prefixes(self, ctx: commands.Context, *, prefixes: str = None):
        interaction = mh.MessageInteractionAdapter(ctx.message) or ctx.interaction
        if prefixes == None:
            await interaction.response.send_message(
                embed=gh.fail(
                    title=' Failed to update prefixes', 
                    description='> You need to provide atleast one prefix!')
            )
            return
        
        data = gh.load_data(gh.PREFIX_FILE, 
                            {
                            "default_prefixes": [
                                "n!"
                            ],
                            "guild_prefixes": {}
                            })
        gid = str(ctx.guild.id)
        prefixes_list = prefixes.split()
        if gid not in data["guild_prefixes"]: data["guild_prefixes"][gid] = []

        current_prefix_list = data["guild_prefixes"][gid]
        current_prefix_list.extend(prefixes_list)
        updated_prefix_list = list(dict.fromkeys(current_prefix_list))

        data["guild_prefixes"][gid] = updated_prefix_list
        gh.save_data(gh.PREFIX_FILE, data)

        prefixes_string = '`, `'.join(updated_prefix_list)
        embed = discord.Embed(title='Prefixes updated', description=f'> Active prefixes for this server:\n> `{prefixes_string}`', color=discord.Color.green())
    
        await interaction.response.send_message(embed=embed)
        gh.save_data(gh.PREFIX_FILE, data)

    @prefix.command(name='remove', description='Remove command prefixes for this server (Admin only)', aliases=['r'])
    @commands.has_guild_permissions(administrator=True)
    async def remove_prefixes(self, ctx: commands.Context, *, prefixes: str = None):
        interaction = mh.MessageInteractionAdapter(ctx.message) or ctx.interaction
        if prefixes == None:
            await interaction.response.send_message(
                embed=gh.fail(
                    title=' Failed to update prefixes', 
                    description='> You need to provide atleast one prefix!')
            )
            return
        data = gh.load_data(gh.PREFIX_FILE, 
                            {
                            "default_prefixes": [
                                "n!"
                            ],
                            "guild_prefixes": {}
                            })
        gid = str(ctx.guild.id)
        remove_prefixes_list = prefixes.split()
        if gid not in data["guild_prefixes"]: data["guild_prefixes"][gid] = []

        current_prefix_list = data["guild_prefixes"][gid]
        set_remove_prefixes = set(remove_prefixes_list)
        updated_prefix_list = [item for item in current_prefix_list if item not in set_remove_prefixes]

        data["guild_prefixes"][gid] = updated_prefix_list
        gh.save_data(gh.PREFIX_FILE, data)

        prefixes_string = '`, `'.join(updated_prefix_list)
        embed = discord.Embed(title='Prefixes updated', description=f'> Active prefixes for this server:\n> `{prefixes_string}`', color=discord.Color.green())
        await interaction.response.send_message(embed=embed)
        gh.save_data(gh.PREFIX_FILE, data)

    @commands.hybrid_command(
        name="reset-prefixes",
        description="Reset this server's prefixes back to default",
        aliases=["resetprefixes", "resetpf", "rpf", 'rpfs', 'resetpfs'])
    @app_commands.guilds(*guilds)
    @commands.has_guild_permissions(administrator=True)
    @app_commands.checks.has_permissions(administrator=True)
    async def reset_prefixes(self, ctx: commands.Context):
        data = gh.load_data(
            gh.PREFIX_FILE,
            {
                "default_prefixes": ["n!"],
                "guild_prefixes": {}
            })

        gid = str(ctx.guild.id)
        if gid in data["guild_prefixes"]:
            del data["guild_prefixes"][gid]
        gh.save_data(gh.PREFIX_FILE, data)

        embed = discord.Embed(
            title="Prefixes reset",
            description="> This server's prefixes have been reset to the default prefix.\n> Default prefix: `n!`",
            color=discord.Color.green())
        
        if ctx.interaction is not None:
            await ctx.interaction.response.send_message(embed=embed, ephemeral=False)
        else:
            await ctx.channel.send(embed=embed, reference=ctx.message, mention_author=False)
        
    @prefix.error
    async def prefix_error(self, ctx: commands.Context, error):
        interaction = mh.MessageInteractionAdapter(ctx.message) or ctx.interaction
        await gh.userPermsError(interaction=interaction)
        
    @add_prefixes.error
    async def add_prefix_error(self, ctx: commands.Context, error):
        interaction = mh.MessageInteractionAdapter(ctx.message) or ctx.interaction
        await gh.userPermsError(interaction=interaction)

    @remove_prefixes.error
    async def remove_prefix_error(self, ctx: commands.Context, error):
        interaction = mh.MessageInteractionAdapter(ctx.message) or ctx.interaction
        await gh.userPermsError(interaction=interaction)
    
    @reset_prefixes.error
    async def reset_prefix_error(self, ctx: commands.Context, error):
        interaction = mh.MessageInteractionAdapter(ctx.message) or ctx.interaction
        await gh.userPermsError(interaction=interaction)

async def setup(bot):
    await bot.add_cog(Util(bot))
