from discord.ext import commands
import discord
import GenHelp as gh
import json
from discord import app_commands
import asyncio
import Cogs.Util.UtilHelp as uh
import re
import Cogs.Moderation.ModHelp as mh


class AboveUserGrade(commands.CheckFailure):
    pass
#------------------------------------------
# Role commands
#------------------------------------------
guilds = gh.get_whitelisted_guilds("role")
class Roles(commands.Cog):
    async def cog_check(self, ctx: commands.Context):
        allowed_guilds = gh.get_whitelisted_guilds("role")
        return ctx.guild is not None and ctx.guild.id in allowed_guilds
    
    def __init__(self, bot: discord.Client):
        self.bot = bot

    role_conv = commands.RoleConverter()
    mem_conv = commands.MemberConverter()

    @commands.hybrid_group(
        name="role",
        description="Role commands",
        invoke_without_command=True
    )
    @app_commands.guilds(*guilds)
    async def role(self, ctx: commands.Context):
        embed = discord.Embed(
            title="Role Commands",
            description=(
                "> `role edit color <role> <hex>`\n"
                "> `role edit name <role> <name>`\n"
                "> `role edit hoist <role> <true/false>`\n"
                "> `role edit mentionable <role> <true/false>`\n"
                "> `role edit icon <role> <emoji>`"
            ),
            color=discord.Color.blue()
        )
        await uh.send_role_response(ctx, embed)

    @role.command(name='info', description='Get information on a specific role.', aliases = ['i'], )
    async def role_info(self, ctx: commands.Context, role: discord.Role):
        if ctx.interaction == None:
            await ctx.channel.send(embed=discord.Embed(
                gh.fail(title=' Could not execute command', description='> Please use slash `/` for this command.')
            ))
            return
        
        name = role.name
        creator = "Not Found/Unknown"
        async for entry in ctx.guild.audit_logs(action=discord.AuditLogAction.role_create):
            if entry.target.id == role.id:
                creator = f"{entry.user.mention} ({entry.user.name})"
        hoist = role.hoist
        mentionable = role.mentionable
        color = role.color
        administrator = role.permissions.administrator

        embed = discord.Embed(title='Role info', description=f'Role id: ```{role.id}```', color=role.color)
        embed.add_field(name='Name', value=name, inline= True)       
        embed.add_field(name='Color', value=color, inline= True)       
        embed.add_field(name='Creator', value=creator, inline= True)       
        embed.add_field(name='Hoist', value=hoist, inline= True)       
        embed.add_field(name='Mentionable', value=mentionable, inline= True)       
        embed.add_field(name='Is admin?', value=administrator, inline= True)
        
        await ctx.interaction.response.send_message(embed=embed)


    @role.command(name='create', description='Create a new server role.')
    @commands.has_guild_permissions(manage_roles=True)
    @app_commands.describe(
    name="The name of the role.",
    hoist="Display the role separately from online members.",
    mentionable="Whether everyone can mention the role.")
    @app_commands.choices(
        hoist=[
            app_commands.Choice(name="True", value=1),
            app_commands.Choice(name="False", value=0),],
        mentionable=[
            app_commands.Choice(name="True", value=1),
            app_commands.Choice(name="False", value=0),])
    async def role_create(self, ctx: commands.Context, name: str = 'new role', hoist = 0, mentionable = 1):
        if ctx.interaction == None:
            await ctx.channel.send(
                embed=gh.fail(title=' Could not execute command', description='> Please use slash `/` for this command.'))
            
            return
        
        hoist = True if hoist == 1 else False
        mentionable = True if mentionable == 1 else False
        
        role = await ctx.guild.create_role(
            reason=f'Made by {ctx.interaction.user.name}',
            name=name,
            hoist=hoist,
            mentionable=mentionable,
            )
        await self.role_info(ctx, role)
        await ctx.channel.send(embed=gh.success(title=f" Success", description=f'Role has been created'))

    @role_create.error
    async def role_create_error(self, ctx: commands.Context, error: commands.CommandError):
        interaction = ctx.interaction if ctx.interaction != None else mh.MessageInteractionAdapter(ctx.message)
        if isinstance(error, commands.MissingPermissions):
            await gh.userPermsError(interaction=interaction)

        elif isinstance(error, commands.BotMissingPermissions):
            await mh.botPermsError(interaction=interaction)

        elif isinstance(error, commands.MissingRequiredArgument):
            await ctx.send(embed=gh.fail(title=f"Missing arguments", description=f"> Usage: role create <name> [hoist: True/False] [mentionable: True/False]"))

        else:
            raise error

    @role.command(name='delete', description='Delete a server role.')
    @commands.has_guild_permissions(manage_roles=True)
    async def role_delete(self, ctx: commands.Context, role: discord.Role):
        embed = discord.Embed(
            title="⚠️ Confirm Role Deletion",
            description=(
                f"Are you sure you want to delete {role.mention}?\n\n"
                "> React with <:Success:1481222312345862215> to confirm.\n"
                "> React with <:Fail:1481222299381272696> to cancel.\n\n"
                "> **You have 30 seconds to react.**"
            ),
            color=discord.Color.orange())

        if ctx.interaction:
            await ctx.interaction.response.send_message(embed=embed)
            message = await ctx.interaction.original_response()
        else:
            message = await ctx.send(embed=embed)
        # Bot reacts first
        await message.add_reaction(f"<:Success:{gh.SUCCESS_ID}>")
        await message.add_reaction(f"<:Fail:{gh.FAIL_ID}>")

        def check(reaction, user):
            return (
                user.id == ctx.author.id
                and reaction.message.id == message.id
                and reaction.emoji.id in (gh.SUCCESS_ID, gh.FAIL_ID)
            )

        try:
            reaction, user = await self.bot.wait_for(
                "reaction_add",
                timeout=30,
                check=check
            )

        except asyncio.TimeoutError:
            await message.edit(
                embed=gh.fail(
                    " Confirmation Timed Out",
                    "> You did not respond within **30 seconds**."
                )
            )

            try:
                await message.clear_reactions()
            except discord.Forbidden:
                pass

            return

        # User cancelled
        if reaction.emoji.id == gh.FAIL_ID:
            await message.edit(
                embed=gh.fail(
                    " Deletion Cancelled",
                    "> The role was **not** deleted."
                )
            )

            try:
                await message.clear_reactions()
            except discord.Forbidden:
                pass

            return

        # User confirmed
        await role.delete(reason=f"Deleted by {ctx.author}")

        await message.edit(
            embed=gh.success(
                " Role Deleted",
                f"> Successfully deleted **{role.name}**."
            )
        )

        try:
            await message.clear_reactions()
        except discord.Forbidden:
            pass

    @role_create.error
    async def role_create_error(self, ctx: commands.Context, error: commands.CommandError):
        interaction = ctx.interaction if ctx.interaction != None else mh.MessageInteractionAdapter(ctx.message)
        if isinstance(error, commands.MissingPermissions):
            await gh.userPermsError(interaction=interaction)

        elif isinstance(error, commands.BotMissingPermissions):
            await mh.botPermsError(interaction=interaction)

        elif isinstance(error, commands.MissingRequiredArgument):
            await interaction.response.send_message(embed=gh.fail(title=f" Missing argument", description=f"> Usage: /role delete <role>"))

        else:
            raise error


    @role.command(name="add", description="Add a specific role to a member.")
    @uh.can_manage_roles()
    async def add(self, ctx: commands.Context, member: str, role: str):
        try:
            target: discord.Member = await self.mem_conv.convert(ctx, member)
            role: discord.Role = await self.role_conv.convert(ctx, role)

            if target == None:
                embed = gh.fail(title=f" Could not resolve username", description= f'> Please mention a valid server member.')
                return await ctx.channel.send(embed=embed)

            if ctx.author.id is not ctx.guild.owner.id and ctx.author.top_role <= role:
                raise AboveUserGrade("User does not have permission to edit that role")

            if role in target.roles:
                return await ctx.send(embed=gh.fail(
                    title=" Member already has role",
                    description=f"> {target.mention} already has {role.mention}."
                ))

            await target.add_roles(role)

            await ctx.send(embed=gh.success(
                title=" Role added",
                description=f"Added {role.mention} to {target.mention}."
            ))
        except Exception as e:
            await self.role_add_error(ctx, e)
    @add.error
    async def role_add_error(self, ctx: commands.Context, error: commands.CommandError):
        interaction = ctx.interaction if ctx.interaction != None else mh.MessageInteractionAdapter(ctx.message)
        if isinstance(error, commands.MissingPermissions):
            await gh.userPermsError(interaction=interaction)

        elif isinstance(error, commands.BotMissingPermissions):
            await mh.botPermsError(interaction=interaction)

        elif isinstance(error, commands.MissingRequiredArgument):
            await interaction.response.send_message(embed=gh.fail(title=f" Missing argument", description=f"> Usage: /role delete <role>"))

        elif isinstance(error, commands.MemberNotFound):
            return await interaction.response.send_message(embed=gh.fail(title="Could not resolve member", description="> The first argument must be a valid member."))

        elif isinstance(error, commands.RoleNotFound):
            return await interaction.response.send_message(embed=gh.fail(title="Could not resolve role", description="> The second argument must be a valid role."))
       
        elif isinstance(error, discord.NotFound):
            return await interaction.response.send_message(embed=gh.fail(title="Could not resolve or member", description="> Please enter valid arguments."))

        elif isinstance(error, AboveUserGrade):
            return await interaction.response.send_message(embed=gh.fail(title=" Failed to add role", description="> The role must be above your top role."))

        else:
            raise error
            # await ctx.send(embed=gh.fail(title=' Unnexpected error!', description=f'More info:\n> {error}'))

    @role.command(name="remove", description="Remove a role from a member")
    @uh.can_manage_roles()
    async def remove(self, ctx: commands.Context, member: str, role: str):
        target: discord.Member = await self.mem_conv.convert(ctx, member)
        role: discord.Role = await self.role_conv.convert(ctx, role)
        
        if target == None:
            embed = gh.fail(title=f" Could not resolve username", description= f'> Please mention a valid server member.')
            return await ctx.channel.send(embed=embed)
        
            if ctx.author.id is not ctx.guild.owner.id and ctx.author.top_role <= role:
                raise AboveUserGrade("User does not have permission to edit that role")

        if role not in target.roles:
            return await ctx.send(embed=gh.fail(
                title=" Member doesn't have role",
                description=f"> {target.mention} doesn't have {role.mention}."
            ))

        await target.remove_roles(role)

        await ctx.send(embed=gh.success(
            title=" Role removed",
            description=f"> Removed {role.mention} from {target.mention}."
        ))


    @remove.error
    async def role_remove_error(self, ctx: commands.Context, error: commands.CommandError):
        interaction = ctx.interaction if ctx.interaction != None else mh.MessageInteractionAdapter(ctx.message)
        if isinstance(error, commands.MissingPermissions):
            await gh.userPermsError(interaction=interaction)

        elif isinstance(error, commands.BotMissingPermissions):
            await mh.botPermsError(interaction=interaction)

        elif isinstance(error, commands.MissingRequiredArgument):
            await interaction.response.send_message(embed=gh.fail(title=f" Missing argument", description=f"> Usage: /role delete <role>"))

        elif isinstance(error, commands.MemberNotFound):
            return await interaction.response.send_message(embed=gh.fail(title="Could not resolve member", description="> The first argument must be a valid member."))

        elif isinstance(error, commands.RoleNotFound):
            return await interaction.response.send_message(embed=gh.fail(title="Could not resolve role", description="> The second argument must be a valid role."))

        elif isinstance(error, discord.NotFound):
            return await interaction.response.send_message(embed=gh.fail(title="Could not resolve or member", description="> Please enter valid arguments."))

        elif isinstance(error, AboveUserGrade):
            return await interaction.response.send_message(embed=gh.fail(title=" Failed to add role", description="> The role must be above your top role."))

        else:
            raise error
            # await ctx.send(embed=gh.fail(title=' Unnexpected error!', description=f'More info:\n> {error}'))


    @role.command(name="add-all", description="Add a role to all the members of the server.")
    @commands.has_permissions(administrator=True)
    async def add_all(self, ctx: commands.Context, *, role: str):
        role = await self.role_conv.convert(ctx, role)
        if ctx.interaction != None:
            await ctx.defer()

        interaction = ctx.interaction if ctx.interaction != None else mh.MessageInteractionAdapter(ctx.message)
        count = 0
        await ctx.send(embed=gh.success(title=f" Starting to add the role to all the members", description='> This may take a while.'))
        for member in ctx.guild.members:
            if member.bot:
                continue

            if role in member.roles:
                continue

            try:
                await member.add_roles(role)
                count += 1
            except discord.Forbidden:
                pass

        await ctx.send(embed=gh.success(
            title=" Completed",
            description=f"> Added {role.mention} to **{count}** members."
        ), content= interaction.user.mention)


    @add_all.error
    async def role_add_all_error(self, ctx: commands.Context, error: commands.CommandError):
        interaction = ctx.interaction if ctx.interaction != None else mh.MessageInteractionAdapter(ctx.message)
        if isinstance(error, commands.MissingPermissions):
            await gh.userPermsError(interaction=interaction)

        elif isinstance(error, commands.BotMissingPermissions):
            await mh.botPermsError(interaction=interaction)

        elif isinstance(error, commands.MissingRequiredArgument):
            await interaction.response.send_message(embed=gh.fail(title=f" Missing argument", description=f"> Usage: /role delete <role>"))

        elif isinstance(error, commands.RoleNotFound):
            return await interaction.response.send_message(embed=gh.fail(title="Could not resolve role", description="> The second argument must be a valid role."))
        else:
            raise error
            # await ctx.send(embed=gh.fail(title=' Unnexpected error!', description=f'More info:\n> {error}'))


    @role.command(name="remove-all", description="Remove a role from all the members of the server.")
    @commands.has_permissions(administrator=True)
    async def remove_all(self, ctx: commands.Context, *, role: str):
        if ctx.interaction != None:
            await ctx.defer()
        role = await self.role_conv.convert(ctx, role)
        interaction = ctx.interaction if ctx.interaction != None else mh.MessageInteractionAdapter(ctx.message)
        count = 0

        await ctx.send(embed=gh.success(title=f" Starting to remove the role from all the members", description='> This may take a while.'))
        for member in ctx.guild.members:
            if role not in member.roles:
                continue

            try:
                await member.remove_roles(role)
                count += 1
            except discord.Forbidden:
                pass

        await ctx.send(embed=gh.success(
            title=" Completed",
            description=f"Removed {role.mention} from **{count}** members."
        ), content=interaction.user.mention)


    @remove_all.error
    async def role_remove_all_error(self, ctx: commands.Context, error: commands.CommandError):
        interaction = ctx.interaction if ctx.interaction != None else mh.MessageInteractionAdapter(ctx.message)
        if isinstance(error, commands.MissingPermissions):
            await gh.userPermsError(interaction=interaction)

        elif isinstance(error, commands.BotMissingPermissions):
            await mh.botPermsError(interaction=interaction)

        elif isinstance(error, commands.MissingRequiredArgument):
            await interaction.response.send_message(embed=gh.fail(title=f" Missing argument", description=f"> Usage: /role delete <role>"))
            
        elif isinstance(error, commands.RoleNotFound):
            return await interaction.response.send_message(embed=gh.fail(title="Could not resolve role", description="> The second argument must be a valid role."))
        else:
            raise error
            # await ctx.send(embed=gh.fail(title=' Unnexpected error!', description=f'More info:\n> {error}'))


    @role.group(
        name="edit",
        description="Edit role settings",
        invoke_without_command=True
    )
    async def edit_role(self, ctx: commands.Context):
        embed = gh.fail(
            " Missing subcommand",
            "> Use `color`, `name`, `hoist`, `mentionable`, or `icon`."
        )
        await uh.send_role_response(ctx, embed)
  
  
    @edit_role.command(name="color", description="Edit a role color")
    @commands.has_guild_permissions(manage_roles=True)
    @app_commands.checks.has_permissions(manage_roles=True)
    async def edit_role_color(self, ctx: commands.Context, role: discord.Role, color: str):
        if not await uh.can_edit_role(ctx, role):
            return

        color = color.strip()

        if color.startswith("#"):
            color = color[1:]

        if not re.fullmatch(r"[0-9a-fA-F]{6}", color):
            await uh.send_role_response(
                ctx,
                gh.fail(
                    " Invalid color",
                    "> Please provide a valid hex color like `#ff0000` or `ff0000`."
                )
            )
            return

        await role.edit(color=discord.Color(int(color, 16)))

        await uh.send_role_response(
            ctx,
            gh.success(
                " Role color updated",
                f"> {role.mention}'s color has been updated to `#{color.upper()}`."
            )
        )

    @edit_role.command(name="name", description="Edit a role name")
    @commands.has_guild_permissions(manage_roles=True)
    @app_commands.checks.has_permissions(manage_roles=True)
    async def edit_role_name(self, ctx: commands.Context, role: discord.Role, *, name: str):
        if not name or not name.strip():
            await uh.send_role_response(
                ctx,
                gh.fail(
                    " Invalid name",
                    "> Please provide a valid role name."
                )
            )
            return

        if len(name) > 100:
            await uh.send_role_response(
                ctx,
                gh.fail(
                    " Invalid name",
                    "> Role names cannot be longer than 100 characters."
                )
            )
            return

        if not await uh.can_edit_role(ctx, role):
            return

        old_name = role.name
        await role.edit(name=name.strip())

        await uh.send_role_response(
            ctx,
            gh.success(
                " Role name updated",
                f"> `{old_name}` has been renamed to `{name.strip()}`."
            )
        )

    @edit_role.command(name="hoist", description="Edit whether a role is displayed separately")
    @commands.has_guild_permissions(manage_roles=True)
    @app_commands.checks.has_permissions(manage_roles=True)
    @app_commands.describe(value="Choose whether this role should be hoisted")
    @app_commands.choices(value=[
        app_commands.Choice(name="True", value="true"),
        app_commands.Choice(name="False", value="false")
    ])
    async def edit_role_hoist(
        self,
        ctx: commands.Context,
        role: discord.Role,
        value: str
    ):
        parsed = uh.parse_bool_value(value)

        if parsed is None:
            await uh.send_role_response(
                ctx,
                gh.fail(
                    " Invalid value",
                    "> Please use `true` or `false`. You can also use `t` or `f`."
                )
            )
            return

        if not await uh.can_edit_role(ctx, role):
            return

        await role.edit(hoist=parsed)

        await uh.send_role_response(
            ctx,
            gh.success(
                " Role hoist updated",
                f"> {role.mention} hoist has been set to `{parsed}`."
            )
        )

    @edit_role.command(name="mentionable", description="Edit whether a role is mentionable")
    @commands.has_guild_permissions(manage_roles=True)
    @app_commands.checks.has_permissions(manage_roles=True)
    @app_commands.describe(value="Choose whether this role should be mentionable")
    @app_commands.choices(value=[
        app_commands.Choice(name="True", value="true"),
        app_commands.Choice(name="False", value="false")
    ])
    async def edit_role_mentionable(
        self,
        ctx: commands.Context,
        role: discord.Role,
        value: str
    ):
        parsed = uh.parse_bool_value(value)

        if parsed is None:
            await uh.send_role_response(
                ctx,
                gh.fail(
                    " Invalid value",
                    "> Please use `true` or `false`. You can also use `t` or `f`."
                )
            )
            return

        if not await uh.can_edit_role(ctx, role):
            return

        await role.edit(mentionable=parsed)

        await uh.send_role_response(
            ctx,
            gh.success(
                " Role mentionable updated",
                f"> {role.mention} mentionable has been set to `{parsed}`."
            )
        )

    @edit_role.command(name="icon", description="Edit a role icon")
    @commands.has_guild_permissions(manage_roles=True)
    @app_commands.checks.has_permissions(manage_roles=True)
    async def edit_role_icon(self, ctx: commands.Context, role: discord.Role, icon: str):
        if ctx.guild.premium_tier < 2:
            await uh.send_role_response(
                ctx,
                gh.fail(
                    " Role icons unavailable",
                    "> This server does not have enough boosts to use role icons."
                )
            )
            return

        if not await uh.can_edit_role(ctx, role):
            return

        emoji, error = uh.get_custom_emoji_from_input(ctx.guild, icon)

        if error == "not_in_server":
            await uh.send_role_response(
                ctx,
                gh.fail(
                    " Invalid emoji",
                    "> That custom emoji is not from this server."
                )
            )
            return

        if emoji is None:
            cleaned_name = uh.clean_emoji_name(icon)

            if cleaned_name != icon:
                emoji = discord.utils.get(ctx.guild.emojis, name=cleaned_name)

            if emoji is None:
                await uh.send_role_response(
                    ctx,
                    gh.fail(
                        " Invalid emoji",
                        f"> I could not find `{cleaned_name}` in this server's emoji list."
                    )
                )
                return

        try:
            emoji_bytes = await emoji.read()
            await role.edit(display_icon=emoji_bytes)

        except discord.Forbidden:
            await uh.send_role_response(
                ctx,
                gh.fail(
                    " Missing permissions",
                    "> I do not have permission to edit that role."
                )
            )
            return

        except discord.HTTPException as e:
            await uh.send_role_response(
                ctx,
                gh.fail(
                    " Could not update icon",
                    f"> Discord rejected the icon update.\n> `{e}`"
                )
            )
            return

        await uh.send_role_response(
            ctx,
            gh.success(
                " Role icon updated",
                f"> {role.mention}'s icon has been updated to {emoji}."
            )
        )

async def setup(bot):
    await bot.add_cog(Roles(bot))
