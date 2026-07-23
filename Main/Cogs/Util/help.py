import discord
from discord.ext import commands
from discord import app_commands
import GenHelp as gh


ICONS = {
    "Moderation": "<:Moderation:1518284435248648243>",
    "Util": "<:Util:1518284437388005457>",
    "Configuration": "<:Config:1518284428470652989>",
    "Roles": "<:Role:1518284431197081620>",
    "Fun": "🎮",
    "Music": "🎵",
    "Information": "📚",
}

guilds = gh.get_whitelisted_guilds("help")
class Help(commands.Cog):
    async def cog_check(self, ctx: commands.Context):
        allowed_guilds = gh.get_whitelisted_guilds("help")
        
        return ctx.guild is not None and ctx.guild.id in allowed_guilds
    def __init__(self, bot: commands.Bot):
        self.bot = bot
        self.command_cache = {}
        self.category_cache = {}

    # ---------------- Cache ---------------- #

    def build_cache(self):
        self.command_cache.clear()
        self.category_cache.clear()

        for command in self.bot.walk_commands():
            if command.hidden:
                continue

            self.command_cache[command.qualified_name.lower()] = command

            category = command.cog_name or "No Category"
            self.category_cache.setdefault(category, []).append(command)

        for commands_list in self.category_cache.values():
            commands_list.sort(key=lambda c: c.qualified_name)

    @commands.Cog.listener()
    async def on_ready(self):
        self.build_cache()

    @commands.Cog.listener()
    async def on_cog_load(self):
        self.build_cache()

    @commands.Cog.listener()
    async def on_cog_remove(self, _):
        self.build_cache()

    # ---------------- Autocomplete ---------------- #

    async def command_autocomplete(
        self,
        interaction: discord.Interaction,
        current: str
    ):
        return [
            app_commands.Choice(
                name=name,
                value=name
            )
            for name in self.command_cache
            if current.lower() in name
        ][:25]

    # ---------------- Help Command ---------------- #

    @commands.hybrid_group(
        name="help",
        description="View the bot's commands.",
        invoke_without_command=True,
        with_app_command=True
    )
    @app_commands.autocomplete(command=command_autocomplete)
    @app_commands.guilds(*guilds)
    async def help(
        self,
        ctx: commands.Context,
        *,
        command: str | None = None
    ):

        # Build cache if necessary
        if not self.command_cache:
            self.build_cache()

        # ---------------- Main Help ---------------- #

        if command is None:

            prefixes = sorted(set(await self.bot.get_prefix(ctx.message)))
            prefixes = [p for p in prefixes if isinstance(p, str)]

            prefix_text = (
                "### Active Prefixes\n"
                + " ".join(f"`{p}`" for p in prefixes)
            )

            embed = discord.Embed(
                colour=discord.Colour.blurple()
            )

            embed.set_author(
                name=f"{self.bot.user.name} Help",
                icon_url=self.bot.user.display_avatar.url
            )

            embed.description = (
                "Browse all available commands below.\n"
                f"Use **`{ctx.clean_prefix}help <command>`** "
                "for detailed information."
            )

            total = 0

            for category in sorted(self.category_cache):

                cmds = [
                    c for c in self.category_cache[category]
                    if c.parent is None and not c.hidden
                ]

                if not cmds:
                    continue

                total += len(cmds)

                icon = ICONS.get(category, "<:folder:1518287606876733655>")
                embed.add_field(
                    name=f"{icon} {category}",
                    value=" ".join(f"`{c.name}`" for c in cmds),
                    inline=False
                )

            embed.set_footer(
                text=f"{total} commands"
            )

            return await ctx.send(
                content=prefix_text,
                embed=embed
            )
        # ---------------- Command Help ---------------- #

        cmd = self.command_cache.get(command.lower())

        if cmd is None:
            return await ctx.send(embed=gh.fail(title=' Failed to execute command.', description=f"❌ No command named `{command}` found."))
        
        
        embed = discord.Embed(
            colour=discord.Colour.blurple()
        )

        embed.set_author(
            name=cmd.qualified_name,
            icon_url=self.bot.user.display_avatar.url
        )

        embed.description = cmd.description or "No description provided."

        embed.add_field(
            name="Category",
            value=f"`{cmd.cog_name or 'None'}`",
            inline=True
        )

        usage = f"{ctx.clean_prefix}{cmd.qualified_name}"

        if cmd.signature:
            usage += f" {cmd.signature}"

        embed.add_field(
            name="Usage",
            value=f"```{usage}```",
            inline=False
        )

        aliases = (
            ", ".join(f"`{a}`" for a in cmd.aliases)
            if cmd.aliases
            else "`None`"
        )

        embed.add_field(
            name="Aliases",
            value=aliases,
            inline=False
        )

        if isinstance(cmd, commands.Group) and cmd.commands:

            subs = "\n".join(
                f"• `{c.name}` — {c.description or 'No description'}"
                for c in sorted(cmd.commands, key=lambda x: x.name)
            )

            embed.add_field(
                name="Subcommands",
                value=subs,
                inline=False
            )
        await ctx.send(embed=embed)


async def setup(bot: commands.Bot):
    await bot.add_cog(Help(bot))