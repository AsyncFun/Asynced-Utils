from discord.ext import commands
import discord
import GenHelp as gh
import json
from discord import app_commands
import asyncio
import Cogs.Util.UtilHelp as uh

member_converter = commands.MemberConverter()
user_converter = commands.UserConverter()
guild_converter = commands.GuildConverter()
guilds = gh.get_whitelisted_guilds("get")
class Getter(commands.Cog):
    async def cog_check(self, ctx: commands.Context):
        allowed_guilds = gh.get_whitelisted_guilds("get")

        return ctx.guild is not None and ctx.guild.id in allowed_guilds
    def __init__(self, bot: discord.Client):
        self.bot = bot

    @commands.hybrid_group(name='get', aliases=['getter', 'rec', 'recieve', 'fetch'])
    @app_commands.guilds(*guilds)
    async def get_group(self, ctx: commands.Context):
        pass

    @get_group.command(
        name="user-info", aliases=['ui', 'user i', 'info user', 'iu', 'info-user'],
        description="View information about a user."
    )
    @app_commands.describe(
        user="The user whose information you want to view."
    )
    async def user_info(
        self,
        ctx: commands.Context,
        user: str = None
    ):

        is_member = False
        #user = user or ctx.author
        if user != None:
            print("User not none confirm")
            user = await user_converter.convert(ctx=ctx, argument=user)
            uid = str(user.id)
            if user in ctx.guild.members:
                print("User in guild confirm")
                user = await member_converter.convert(ctx=ctx, argument=uid)
                is_member = True
                print(f"Is member check inside if nest: {is_member}")
        
        else:
            user = ctx.author
            is_member = True
            
        print(f"Is member check outside if nest: {is_member}")
        
        try:

            embed = discord.Embed(
                title=f"User Information",
                colour=user.colour if user.colour.value else discord.Colour.blurple()
            )

            embed.set_thumbnail(
                url=user.display_avatar.url
            )

            embed.add_field(
                name="User",
                value=f"{user.mention}\n`{user}`",
                inline=True
            )

            embed.add_field(
                name="User ID",
                value=f"`{user.id}`",
                inline=True
            )

            embed.add_field(
                name="Created",
                value=(
                    f"{gh.format_dt(user.created_at)}\n"
                    f"{gh.format_relative(user.created_at)}"
                ),
                inline=True
            )

            if is_member:
                embed.add_field(
                    name="Joined Server",
                    value=(
                        f"{gh.format_dt(user.joined_at)}\n"
                        f"{gh.format_relative(user.joined_at)}"
                    ),
                    inline=False
                )

                embed.add_field(
                    name="Nickname",
                    value=user.nick or "None",
                    inline=True
                )

                embed.add_field(
                    name="Badges",
                    value=gh.user_badges(user),
                    inline=True
                )

                embed.add_field(
                    name="Highest Role",
                    value=user.top_role.mention,
                    inline=False
                )

                embed.add_field(
                    name="Roles",
                    value=str(len(user.roles) - 1),
                    inline=True
                )

            embed.set_footer(
                text=f"Username: {user.name}"
            )

            await ctx.send(embed=embed)

        except Exception:
            raise Exception

    @get_group.command(
        name="guild-info", aliases=['guild', 'info-guild'],
        description="View information about this server."
    )
    async def guild_info(
        self,
        ctx: commands.Context,
        guild: str = None
    ):
        if guild == None: guild = str(ctx.guild.id)
        guild = await guild_converter.convert(ctx=ctx, argument=guild)
        guild = guild or ctx.guild

        try:

            owner = guild.owner

            bots = len(
                [member for member in guild.members if member.bot]
            )

            humans = guild.member_count - bots

            embed = discord.Embed(
                title="Server Information",
                colour=discord.Colour.blurple()
            )

            if guild.icon:
                embed.set_thumbnail(
                    url=guild.icon.url
                )

            embed.add_field(
                name="Name",
                value=guild.name,
                inline=True
            )

            embed.add_field(
                name="Server ID",
                value=f"`{guild.id}`",
                inline=True
            )

            embed.add_field(
                name="Owner",
                value=owner.mention if owner else "Unknown",
                inline=True
            )

            embed.add_field(
                name="Created",
                value=(
                    f"{gh.format_dt(guild.created_at)}\n"
                    f"{gh.format_relative(guild.created_at)}"
                ),
                inline=False
            )

            embed.add_field(
                name="Members",
                value=f"{guild.member_count:,}",
                inline=True
            )

            embed.add_field(
                name="Humans",
                value=f"{humans:,}",
                inline=True
            )

            embed.add_field(
                name="Bots",
                value=f"{bots:,}",
                inline=True
            )

            embed.add_field(
                name="Roles",
                value=f"{len(guild.roles):,}",
                inline=True
            )

            embed.add_field(
                name="Channels",
                value=f"{len(guild.channels):,}",
                inline=True
            )

            embed.add_field(
                name="Emojis",
                value=f"{len(guild.emojis):,}",
                inline=True
            )

            embed.add_field(
                name="Boost Tier",
                value=str(guild.premium_tier),
                inline=True
            )

            embed.add_field(
                name="Boost Count",
                value=str(guild.premium_subscription_count),
                inline=True
            )

            embed.add_field(
                name="Verification Level",
                value=str(guild.verification_level).title(),
                inline=True
            )

            if guild.banner:
                embed.set_image(
                    url=guild.banner.url
                )

            embed.set_footer(
                text=f"Requested by {ctx.author}"
            )

            await ctx.send(embed=embed)

        except Exception:
            raise Exception
            # await ctx.send(
            #     embed=gh.fail(
            #         title="Cannot get server information",
            #         description="> Server is out of my reach."
            #     )
            # )
        
    @get_group.command(
        name="role-info", aliases=['role'],
        description="View information about a role."
    )
    @app_commands.describe(
        role="The role to inspect."
    )
    async def role_info(
        self,
        ctx: commands.Context,
        role: discord.Role
    ):

        try:

            permissions = [
                perm.replace("_", " ").title()
                for perm, value in role.permissions
                if value
            ]

            embed = discord.Embed(
                title="Role Information",
                colour=role.colour if role.colour.value else discord.Colour.blurple()
            )

            embed.add_field(
                name="Name",
                value=role.mention,
                inline=True
            )

            embed.add_field(
                name="Role ID",
                value=f"`{role.id}`",
                inline=True
            )

            embed.add_field(
                name="Colour",
                value=f"`{str(role.colour)}`",
                inline=True
            )

            embed.add_field(
                name="Created",
                value=(
                    f"{gh.format_dt(role.created_at)}\n"
                    f"{gh.format_relative(role.created_at)}"
                ),
                inline=False
            )

            embed.add_field(
                name="Position",
                value=str(role.position),
                inline=True
            )

            embed.add_field(
                name="Members",
                value=str(len(role.members)),
                inline=True
            )

            embed.add_field(
                name="Mentionable",
                value="Yes" if role.mentionable else "No",
                inline=True
            )

            embed.add_field(
                name="Displayed Separately",
                value="Yes" if role.hoist else "No",
                inline=True
            )

            embed.add_field(
                name="Managed",
                value="Yes" if role.managed else "No",
                inline=True
            )

            embed.add_field(
                name="Permissions",
                value=(
                    ", ".join(permissions[:20])
                    if permissions else "None"
                ),
                inline=False
            )

            embed.set_footer(
                text=f"Requested by {ctx.author}"
            )

            await ctx.send(embed=embed)

        except Exception:

            await ctx.send(
                embed=gh.fail(
                    title="Cannot get role information",
                    description="> Role is out of my reach."
                )
            )


    @get_group.command(
        name="channel-info", aliases=['channel'],
        description="View information about a channel."
    )
    @app_commands.describe(
        channel="The channel to inspect."
    )
    async def channel_info(
        self,
        ctx: commands.Context,
        channel: discord.abc.GuildChannel | None = None
    ):

        channel = channel or ctx.channel

        try:

            embed = discord.Embed(
                title="Channel Information",
                colour=discord.Colour.blurple()
            )

            embed.add_field(
                name="Name",
                value=channel.mention,
                inline=True
            )

            embed.add_field(
                name="Channel ID",
                value=f"`{channel.id}`",
                inline=True
            )

            embed.add_field(
                name="Type",
                value=channel.type.name.replace("_", " ").title(),
                inline=True
            )

            embed.add_field(
                name="Created",
                value=(
                    f"{gh.format_dt(channel.created_at)}\n"
                    f"{gh.format_relative(channel.created_at)}"
                ),
                inline=False
            )

            embed.add_field(
                name="Position",
                value=str(channel.position),
                inline=True
            )

            embed.add_field(
                name="Category",
                value=channel.category.mention
                if channel.category
                else "None",
                inline=True
            )

            if hasattr(channel, "slowmode_delay"):
                embed.add_field(
                    name="Slowmode",
                    value=f"{channel.slowmode_delay}s",
                    inline=True
                )

            if hasattr(channel, "nsfw"):
                embed.add_field(
                    name="NSFW",
                    value="Yes" if channel.nsfw else "No",
                    inline=True
                )

            embed.set_footer(
                text=f"Requested by {ctx.author}"
            )

            await ctx.send(embed=embed)

        except Exception:

            await ctx.send(
                embed=gh.fail(
                    title="Cannot get channel information",
                    description="> Channel is out of my reach."
                )
            )


    @get_group.command(
        name="permissions", aliases=['perms', 'perm', 'permission'],
        description="View permissions of a member or role."
    )
    @app_commands.describe(
        target="The member or role to inspect."
    )
    async def permissions(
        self,
        ctx: commands.Context,
        target: discord.Member | discord.Role
    ):

        try:

            if isinstance(target, discord.Member):

                perms = gh.format_permissions(
                    target.guild_permissions
                )

                title = f"Permissions • {target}"

                colour = (
                    target.colour
                    if target.colour.value
                    else discord.Colour.blurple()
                )

            else:

                perms = gh.format_permissions(
                    target.permissions
                )

                title = f"Permissions • {target.name}"

                colour = (
                    target.colour
                    if target.colour.value
                    else discord.Colour.blurple()
                )

            embed = discord.Embed(
                title=title,
                colour=colour
            )

            chunks = []

            current = []

            for perm in perms:

                current.append(f"• {perm}")

                if len(current) >= 15:

                    chunks.append("\n".join(current))
                    current = []

            if current:
                chunks.append("\n".join(current))

            for i, chunk in enumerate(chunks, start=1):

                embed.add_field(
                    name=f"Permissions {i}",
                    value=chunk,
                    inline=False
                )

            embed.set_footer(
                text=f"{len(perms)} permissions"
            )

            await ctx.send(embed=embed)

        except Exception as e:
            await ctx.send(
                embed=gh.fail(
                    title="Cannot get permissions",
                    description="> Target is out of my reach."
                )
            )


    @get_group.command(
        name="avatar", aliases=['av'],
        description="View a user's avatar."
    )
    @app_commands.describe(
        user="The user whose avatar you want to view."
    )
    async def avatar(
        self,
        ctx: commands.Context,
        user: discord.Member | None = None
    ):

        user = user or ctx.author

        try:

            embed = discord.Embed(
                title=f"{user.display_name}'s Avatar",
                colour=user.colour if user.colour.value else discord.Colour.blurple()
            )

            embed.set_image(
                url=user.display_avatar.url
            )

            embed.add_field(
                name="Download",
                value=f"[Avatar]({user.display_avatar.url})",
                inline=False
            )

            embed.set_footer(
                text=f"Requested by {ctx.author}"
            )

            await ctx.send(embed=embed)

        except Exception:

            await ctx.send(
                embed=gh.fail(
                    title="Cannot get avatar",
                    description="> User is out of my reach."
                )
            )


    @get_group.command(
        name="emoji-info",
        description="View information about an emoji."
    )
    @app_commands.describe(
        emoji="The emoji to inspect."
    )
    async def emoji_info(
        self,
        ctx: commands.Context,
        emoji: discord.Emoji
    ):

        try:

            embed = discord.Embed(
                title="Emoji Information",
                colour=discord.Colour.blurple()
            )

            embed.set_thumbnail(
                url=emoji.url
            )

            embed.add_field(
                name="Name",
                value=emoji.name,
                inline=True
            )

            embed.add_field(
                name="Emoji ID",
                value=f"`{emoji.id}`",
                inline=True
            )

            embed.add_field(
                name="Animated",
                value="Yes" if emoji.animated else "No",
                inline=True
            )

            embed.add_field(
                name="Created",
                value=(
                    f"{gh.format_dt(emoji.created_at)}\n"
                    f"{gh.format_relative(emoji.created_at)}"
                ),
                inline=False
            )

            embed.set_image(
                url=emoji.url
            )

            embed.set_footer(
                text=f"Requested by {ctx.author}"
            )

            await ctx.send(embed=embed)

        except Exception:

            await ctx.send(
                embed=gh.fail(
                    title="Cannot get emoji information",
                    description="> Emoji is out of my reach."
                )
            )
async def setup(bot):
    await bot.add_cog(Getter(bot))