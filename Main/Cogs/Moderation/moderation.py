from discord.ext import commands
import discord
from . import ModHelp as mh
import GenHelp as gh
import json
import traceback
from discord import app_commands
import asyncio

WARNS_FILE = "Data/Moderation/warns.json"
member_converter = commands.MemberConverter()
guilds = gh.get_whitelisted_guilds("moderation")
class Moderation(commands.Cog):
    async def cog_check(self, ctx: commands.Context):
        allowed_guilds = gh.get_whitelisted_guilds("moderation")
        return ctx.guild is not None and ctx.guild.id in allowed_guilds


    def __init__(self, bot: discord.Client):
        self.bot = bot
#------------------------
    @commands.hybrid_command(name="sybau", description="Shut someones ahh up")
    @app_commands.guilds(*guilds)
    @mh.is_aura()
    async def sybau(self, ctx: commands.Context):
        try:
                print(f"{ctx.author.name} ran sybau")
                await ctx.message.channel.send(content=f"{ctx.message.mentions[0].mention} sybau bih") if ctx.message.mentions else await ctx.message.channel.send("sybau bih")
        except Exception:
            print("=========== SYBAU ERROR ===========")
            traceback.print_exc()
#---
    @sybau.error
    async def sybau_error(self, ctx: commands.Context, error):
        if ctx.message:
            interaction = mh.MessageInteractionAdapter(ctx.message)
        await mh.userPermsError(interaction=interaction)
#------------------------

    @commands.hybrid_command(name="warn", description="Warn a member")
    @app_commands.guilds(*guilds)
    @mh.can_warn()
    async def warn(self, ctx: commands.Context, member: str = None, *, reason: str = None):
        target = member
        args = None
        interaction = None
        try:    
            print("Warn command was run")
            if ctx.interaction:
                interaction = ctx.interaction
                target = member
                args = reason
            elif ctx.message:
                print("Message confirmed")
                interaction = mh.MessageInteractionAdapter(ctx.message)
                target, args = await mh.get_args(ctx)

                print("Message interaction made")
            print(f"Target: {target}\nArgs: {args}")
            if target == None:
                await gh.send(gh.fail(title=f" Could not resolve member", 
                                description= f"> Please provide a valid member\n"
                                            "> Usage: `warn <user> [reason]`"), interaction=interaction)
                return
            reason = (" ".join(args) if isinstance(args, list) else args) or "Not Provided"
            print(f"reason attached: \n{reason}")
            await mh.warn(executed_on=target, reason=reason, interaction=interaction)
            print("warning issued")
        except Exception:
            print("=========== WARN ERROR ===========")
            traceback.print_exc()
    @warn.error
    async def warn_error(self, ctx: commands.Context, error):
        interaction = ctx.interaction if ctx.interaction else mh.MessageInteractionAdapter(ctx.message)
        await mh.userPermsError(interaction)


    @commands.hybrid_command(name="unwarn", description="Clear all warns for a user")
    @app_commands.guilds(*guilds)
    @mh.can_warn()
    async def unwarn(self, ctx: commands.Context, member: str = None, *, reason: str = None):
        try:    
            print("unwarn command was run")
            if ctx.interaction:
                interaction = ctx.interaction
                target = await mh.resolve_member(interaction.guild, member)
                args = reason
            elif ctx.message:
                print("Message confirmed")
                interaction = mh.MessageInteractionAdapter(ctx.message)
                target, args = await mh.get_args(ctx)

                print("Message interaction made")
            print(f"Target: {target}\nArgs: {args}")
            if target == None:
                await gh.send(gh.fail(title=f" Could not resolve member", 
                                description= f"> Please provide a valid member\n"
                                            "> Usage: `unwarn <user> [reason]`"), interaction=interaction)
                return
            reason = (" ".join(args) if isinstance(args, list) else args) or "Not Provided"
            print(f"reason attached: \n{reason}")
            await mh.unwarn(user = target, interaction=interaction, reason=reason)
            print("user unwarned")
        except Exception:
            print("=========== UNWARN ERROR ===========")
            traceback.print_exc()

    @unwarn.error
    async def unwarn_error(self, ctx: commands.Context, error):
        print("error in main")
        interaction = ctx.interaction if ctx.interaction else mh.MessageInteractionAdapter(ctx.message)
        await mh.userPermsError(interaction)

    @commands.hybrid_command(name='warns', description='Show the list of warns for all, or specific users.')
    @app_commands.guilds(*guilds)
    @commands.has_permissions(moderate_members=True)
    async def warns(self, ctx: commands.Context, member: str = None):
        interaction = ctx.interaction if ctx.interaction else mh.MessageInteractionAdapter(ctx.message)
        if member != None:
            member = await mh.resolve_member(ctx.guild, member)
            if member == None:
                await gh.send(gh.fail(f" Could not resolve member", description='> Enter a valid name\nHere are all the warns anyways:'), interaction)

        await mh.warns(user=member, interaction=interaction)

    @warns.error
    async def warns_error(self, ctx: commands.Context):
        interaction = ctx.interaction if ctx.interaction else mh.MessageInteractionAdapter(ctx.message)
        await mh.userPermsError(interaction=interaction)
        return


    @commands.hybrid_command(name="kick", description="Kick a member from the server")
    @app_commands.guilds(*guilds)
    @commands.has_permissions(kick_members=True)
    async def kick(self, ctx: commands.Context, member: str = None, *, reason: str = None):
        try:    
            print("kick command was run")
            if ctx.interaction:
                interaction = ctx.interaction
                target = await mh.resolve_member(interaction.guild, member)
                args = reason
            elif ctx.message:
                print("Message confirmed")
                interaction = mh.MessageInteractionAdapter(ctx.message)
                target, args = await mh.get_args(ctx)

                print("Message interaction made")
            print(f"Target: {target}\nArgs: {args}")
            if target == None:
                await gh.send(gh.fail(title=f" Could not resolve member", 
                                description= f"> Please provide a valid member\n"
                                            "> Usage: `kick <user> [reason]`"), interaction=interaction)
                return
            reason = (" ".join(args) if isinstance(args, list) else args) or "Not Provided"
            print(f"reason attached: \n{reason}")
            await mh.kick(user=target, interaction=interaction, reason=reason)
            print("user unwarned")
        except Exception:
            print("=========== KICK ERROR ===========")
            traceback.print_exc()

    @kick.error
    async def kick_error(self, ctx: commands.Context, error):
        print("error in main")
        interaction = ctx.interaction if ctx.interaction else mh.MessageInteractionAdapter(ctx.message)
        await mh.userPermsError(interaction)

    @commands.hybrid_command(name='mute', description='a user for a given time (Empty -> 28days)')
    @app_commands.guilds(*guilds)
    @commands.has_permissions(moderate_members=True)
    async def mute(self, ctx: commands.Context, member: str = None, dur: str = '28d', *, reason: str = None):
        try:
            reason = 'Not Provided'
            duration = '28d'
            if ctx.interaction:
                interaction = ctx.interaction
                target = await member_converter.convert(ctx, member)
                duration = mh.parse_duration(dur)
                args = [target, duration] + reason.split()
                print(args)

            elif ctx.message:
                interaction = mh.MessageInteractionAdapter(ctx.message)
                target, args = await mh.get_args(ctx)
            
            if target == None:
                embed = gh.fail(title=f" Cannot resolve member", description=f"> Please provide a valid member\n> Usage: `mute <target> [duration] [reason]`")
                await interaction.response.send_message(embed=embed)
                return
            if len(args) > 0:
                if mh.parse_duration(args[0]) == None:
                    duration = '28d'
                    reason = " ".join(args) or 'Not Provided'

                elif mh.parse_duration(args[0]) != None:
                    duration = args[0]
                    reason = " ".join(args[1:]) or 'Not Provided'
            
            await mh.mute(user=target, reason=reason, duration=duration, interaction=interaction)
        except Exception:

            print("============ MUTE ERROR ============")
            traceback.print_exc()

    @mute.error
    async def mute_error(self, ctx: commands.Context, error):
        interaction = ctx.interaction if ctx.interaction else mh.MessageInteractionAdapter(ctx.message)
        await mh.userPermsError(interaction)


    @commands.hybrid_command(name="unmute", description="Unmute a muted member")
    @app_commands.guilds(*guilds)
    @commands.has_permissions(moderate_members=True)
    async def unmute(self, ctx: commands.Context, member: str = None, *, reason: str = None):
        try:    
            print("unmute command was run")
            if ctx.interaction:
                interaction = ctx.interaction
                target = await mh.resolve_member(interaction.guild, member)
                args = reason
            elif ctx.message:
                print("Message confirmed")
                interaction = mh.MessageInteractionAdapter(ctx.message)
                target, args = await mh.get_args(ctx)

                print("Message interaction made")
            print(f"Target: {target}\nArgs: {args}")
            if target == None:
                await gh.send(gh.fail(title=f" Could not resolve member", 
                                description= f"> Please provide a valid member\n"
                                            "> Usage: `unmute <user> [reason]`"), interaction=interaction)
                return
            reason = (" ".join(args) if isinstance(args, list) else args) or "Not Provided"
            print(f"reason attached: \n{reason}")
            await mh.unmute(user=target, reason=reason, interaction=interaction)
            print("user unmuted")
        except Exception:
            print("=========== KICK ERROR ===========")
            traceback.print_exc()

    @unmute.error
    async def unmute_error(self, ctx: commands.Context, error):
        print("error in main")
        interaction = ctx.interaction if ctx.interaction else mh.MessageInteractionAdapter(ctx.message)
        await mh.userPermsError(interaction)

    @commands.hybrid_command(name='ban', description='Ban a user from the guild- They cannot join back unless unbanned.')
    @app_commands.guilds(*guilds)
    @commands.has_permissions(administrator=True)
    async def ban(self, ctx: commands.Context, member: str = None, dur: str = None, *, reason: str = None):
        if ctx.interaction == None:
            if member == None:
                member = ctx.message.mentions[0].mention if ctx.message.mentions else None

        print(f"member: {member}")
        interaction = ctx.interaction if ctx.interaction != None else mh.MessageInteractionAdapter(ctx.message)
        if member == None:
            embed = gh.fail(title= f' Invalid syntax', description= f'> Could not resolve user.')
            await interaction.response.send_message(embed=embed)
            return
        
        try:
            reason = 'Not Provided'
            duration = None
            if ctx.interaction:
                interaction = ctx.interaction
                target = await mh.resolve_member(ctx.guild, member)
                duration = mh.parse_duration(dur)
                args = duration + reason

            elif ctx.message:
                interaction = mh.MessageInteractionAdapter(ctx.message)
                target, args = await mh.get_args(ctx)
                target = target.mention
            target = await gh.resolve_user(self.bot, target)

            if target == None:
                embed = gh.fail(title=f" Cannot resolve member", description=f"> Please provide a valid member\n> Usage: `ban <target> [duration] [reason]`")
                await interaction.response.send_message(embed=embed)
                return
            if len(args) > 0:
                if mh.parse_duration(args[0]) == None:
                    duration = None
                    reason = " ".join(args) or 'Not Provided'

                elif mh.parse_duration(args[0]) != None:
                    duration = args[0]
                    reason = " ".join(args[1:]) or 'Not Provided'
            
            await mh.ban(user=target, reason=reason, duration=duration, interaction=interaction)
        except Exception:

            print("============ BAN ERROR ============")
            traceback.print_exc()

    # @ban.error
    # async def ban_error(self, ctx: commands.Context, error):
    #     interaction = ctx.interaction if ctx.interaction else mh.MessageInteractionAdapter(ctx.message)
    #     await mh.userPermsError(interaction)

    @commands.hybrid_command(name="unban", description="Unban a banned member")
    @app_commands.guilds(*guilds)
    @commands.has_permissions(administrator=True)
    async def unban(self, ctx: commands.Context, user_id: str = None, *, reason: str = None):
        try:    
            print("unban command was run")
            if ctx.interaction:
                interaction = ctx.interaction
                target = user_id
                args = reason
            elif ctx.message:
                print("Message confirmed")
                interaction = mh.MessageInteractionAdapter(ctx.message)
                target, args = await mh.get_args(ctx)
                print(f"Target before resolve: {target}")
                target = await gh.resolve_user(self.bot, user_id)

                print("Message interaction made")

            print(f"Target: {target}\nArgs: {args}")
            if target == None:
                await gh.send(gh.fail(title=f" Could not resolve member", 
                                description=f"> Please provide a valid member\n"
                                             "> Usage: `unban <user> [reason]`"), interaction=interaction)
                return
            reason = (" ".join(args) if isinstance(args, list) else args) or "Not Provided"
            print(f"reason attached: \n{reason}")
            print(target)
            await mh.unban(user=target.id, reason=f'Unbanned by {interaction.user.name}: `{reason}`', interaction=interaction)
            print("user unbanned")
        
        except Exception:
            print("=========== UNBAN ERROR ===========")
            traceback.print_exc()

    @unban.error
    async def unban_error(self, ctx: commands.Context, error):
        print("error in main")
        interaction = ctx.interaction if ctx.interaction else mh.MessageInteractionAdapter(ctx.message)
        await mh.userPermsError(interaction)

    @commands.hybrid_command(name="slowmode", description="Set a slowmode for that or other channel.", aliases=["sm", "slowm", "smode"])
    @app_commands.guilds(*guilds)
    @commands.has_permissions(moderate_members = True)
    async def slowmode(self, ctx: commands.Context, channel = None, duration = None):
        try:
            if channel != None:
                print(f"Channel is not none: {channel}")

                if mh.parse_duration(channel) != None:
                    print(f"Channel parameter is a duration tocken: {channel}")
                    duration = mh.parse_duration(channel)
                    channel = ctx.channel
                else:
                    print(f"Channel parameter is NOT a duration tocken: {channel}")
                    channel = await gh.resolve_channel(ctx.guild, channel) or ctx.channel
                    print(f"channel after resolving: {channel}")
                    duration = mh.parse_duration(duration) if duration != None else duration
            else:
                print(f"Channel parameter is None: {channel}")
                channel = ctx.channel

            # if channel != None:
            #     duration = mh.parse_duration(channel) or mh.parse_duration(duration)
            #     channel = await gh.resolve_channel(ctx.guild, channel) or ctx.channel
            
            current_sm = ctx.channel.slowmode_delay
            old_slowmode_stat = 'off' if current_sm == 0 else f'{current_sm}s'
            try:
                new_slowmode_stat = ('off' if duration == 0 else f'{duration.seconds}s')
            except AttributeError:
                pass
            if duration == None:
                embed = discord.Embed(title='Slowmode', description=f'> Slowmode status for {ctx.channel.mention}: `{old_slowmode_stat}`', color=discord.Color.yellow())
                await ctx.channel.send(embed=embed)
                return
            
            else:
                await channel.edit(slowmode_delay=duration.seconds)
                embed = discord.Embed(title="Slowmode", description=f'> Updated slowmode for {channel.mention}: `{old_slowmode_stat}` → `{new_slowmode_stat}`', color=discord.Color.green())
                await ctx.channel.send(embed=embed)
                return
        except Exception:
            traceback.print_exc()

    @slowmode.error
    async def slowmode_error(self, ctx: commands.Context, error):
        interaction = ctx.interaction if ctx.interaction else mh.MessageInteractionAdapter(ctx.message)
        await mh.userPermsError(interaction)
        return 
    
    @commands.hybrid_command(name='purge', description = 'Delete the last \'x\' messages in bulk.')
    @app_commands.guilds(*guilds)
    @commands.has_permissions(moderate_members = True)
    @app_commands.describe(n='Number of messages to be deleted/purged.')
    async def purge(self, ctx: commands.Context, n: int = 1):
        await asyncio.gather(
        await ctx.message.delete(),
        await ctx.channel.purge(limit = n))

        msg = await ctx.channel.send(embed=gh.success(' Messages purged', description=f'> {n} message(s) purged'))
        await asyncio.sleep(5)
        await msg.delete()
async def setup(bot):
    try:
        await bot.add_cog(Moderation(bot))
    except Exception:
        print("=========== MODERATION COG SETUP ERROR ===========")
        traceback.print_exc()

    