from discord.ext import commands
import discord
import GenHelp as gh
import json
from discord import app_commands
import asyncio

#------------------------------------------
# Errors
#------------------------------------------
class NotInGuild(Exception):
    pass


guild_converter = commands.GuildConverter()
class ModuleSelect(discord.ui.Select):

    def __init__(self, bot: discord.Client, owner: discord.User, gid: int, modules: list[str]):
        self.bot = bot
        self.owner = owner
        self.gid = gid
        self.modules = modules
    
        options = [
            discord.SelectOption(
                label=module,
                value=module
            )
            for module in modules
        ]

        super().__init__(
            placeholder="Select the modules to be enabled...",
            min_values=0,
            max_values=len(options),
            options=options
        )

    async def callback(self, interaction: discord.Interaction):

        if interaction.user.id != self.owner.id:
            return await interaction.response.send_message(
                "❌ This menu isn't for you.",
                ephemeral=True
            )

        data = gh.load_data(
            gh.GUILDS_FILE,
            {"guilds": {}}
        )

        gid = str(self.gid)

        if gid not in data["guilds"]:
            data["guilds"][gid] = {}

        for module in self.modules:
            data["guilds"][gid][module] = module in self.values

        gh.save_data(
            gh.GUILDS_FILE,
            data
        )
        bot = self.bot
        for ext in list(bot.extensions.keys()):
            print(f"Reloading {ext} extension")
            await bot.reload_extension(ext)
            print("Successful")

        await gh.sync_guild(bot=bot, guild_id=int(gid))
        await interaction.response.edit_message(
            embed=gh.success(title= " Guild modules updated.", description=" "),
            view=None
        )

class ModuleView(discord.ui.View):

    def __init__(self, bot: discord.Client, owner, gid, modules):

        super().__init__(timeout=300)

        self.add_item(
            ModuleSelect(bot, owner, gid, modules)
        ) 

class Config(commands.Cog):
    def __init__(self, bot: discord.Client):
        self.bot = bot
    
    @gh.is_creator()
    @app_commands.command(name="whitelist-guild")
    @app_commands.allowed_contexts(
        guilds=True,
        dms=True,
        private_channels=True
    )
    @app_commands.allowed_installs(
        guilds=True,
        users=True
    )
    async def whitelist_guild(self, interaction: discord.Interaction, guild_id: str):
        guild_id = int(guild_id)
        guild = self.bot.get_guild(guild_id)

        if guild == None:
            await interaction.response.send_message(
                embed=gh.fail(
                    title=" Whitelist error",
                    description= "> The bot is not in the specified guild, or the guild doesnt exist"
                ))
            return
        print(f"(DEBUG) Guild: {guild}")
        print("(DEBUG) Guild members:\n" + f"{guild.members}")
        if guild.me is None:
            print([member.name for member in guild.members])
            raise NotInGuild("The bot must be in the guild specified.")
        
        if guild.id not in gh.GUILD_IDS:
            gh.GUILD_IDS.append(guild.id)
            gh.to_guild_object_list(gh.GUILD_IDS)

        print("(Debug) Extensions:")
        print(cog.split(".")[-1] for cog in self.bot.extensions)
        modules = sorted({
            cog.split(".")[-1]
            for cog in self.bot.extensions
        })

        modules.remove("config")
        print(modules)
        #modules.remove("")
        await interaction.response.send_message(
            "Select the modules that should be enabled.",
            view=ModuleView(
                self.bot,
                interaction.user,
                guild.id,
                modules
            ),
            ephemeral=True
        )

async def setup(bot):
    await bot.add_cog(Config(bot))