import discord
from discord.ext import commands
import asyncio
import GenHelp as gh
import copy
LOGS_FILE = "Data/Logs/log_channels.json"
INVITES_FILE = "Data/Logs/invites.json"
JOIN_LEAVE_FILE = "Data/Logs/joinleave.json"
DEFAULT_JOIN_MESSAGE = {
    "content": "Hello **{user}**! The community welcomes you to **{servername}**.\nMember count: **{server_membercount}**",
    "embeds": []
}
DEFAULT_LEAVE_MESSAGE = {
    "content": "{user} left the server at {server_membercount} members. Sadge.",
    "embeds": []
}
pending_message_edits = {}

#------------------------------------------
# Guild resolvers
#------------------------------------------
def get_log_guilds():
    data = gh.load_data(gh.GUILDS_FILE, {"guilds": {}})
    guilds = []
    for x in data["guilds"]:
        if data["guilds"][x]["logs"]:
            
            guilds.append(int(x))
        else:
            continue
    print(f"Guilds IDs allowed to log server events: {guilds}")
    return guilds


def get_joinleave_guilds():
    data = gh.load_data(gh.GUILDS_FILE, {"guilds": {}})
    guilds = []

    for x in data["guilds"]:
        if data["guilds"][x]["joinleave"]:
            guilds.append(int(x))
        
        else:
            continue

    return guilds

def is_guild_logs_whitelisted():
        async def predicate(ctx: commands.Context):
            guilds = get_log_guilds()
            return ctx.guild.id in guilds
        
        return commands.check(predicate)
    

def is_guild_joinleave_whitelisted():
        async def predicate(ctx: commands.Context):
            guilds = get_joinleave_guilds()
            return ctx.guild.id in guilds
        
        return commands.check(predicate)
    

#------------------------------------------
# JOIN LEAVE HELPER FUNCTIONS AND CLASSES
#------------------------------------------
def parse_message_data(message_data: dict, join=False, leave=False):
    if join:
        content = message_data["content"]
        embeds_data = message_data["embeds"]

    if leave:
        content = message_data["content"]
        embeds_data = message_data["embeds"]

    embeds = []

    for e in embeds_data:
        title = e["title"] if "title" in e else None
        description = e["description"] if "description" in e else None
        color = e["color"] if "color" in e else None

        thumbnail_url = e["thumbnail"]["url"] if "thumbnail" in e else None

        embed = discord.Embed(
            title=title,
            description=description,
            color=color
        )

        if thumbnail_url:
            embed.set_thumbnail(url=thumbnail_url)

        if "author" in e:
            embed.set_author(
                name=e["author"]["name"],
                icon_url=e["author"]["icon_url"] if "icon_url" in e["author"] else None
            )

        if "footer" in e:
            embed.set_footer(
                text=e["footer"]["text"],
                icon_url=e["footer"]["icon_url"] if "icon_url" in e["footer"] else None
            )

        if "fields" in e:
            for f in e["fields"]:
                embed.add_field(
                    name=f["name"],
                    value=f["value"],
                    inline=f["inline"] if "inline" in f else False
                )

        embeds.append(embed)

    return content, embeds


def parse_placeholders(obj, member: discord.Member):
    placeholders = {
        "{user}": member.mention,
        "{username}": member.name,
        "{servername}": member.guild.name,
        "{server_membercount}": str(member.guild.member_count)
    }

    if isinstance(obj, str):
        for key, value in placeholders.items():
            obj = obj.replace(key, value)
        return obj

    if isinstance(obj, list):
        return [parse_placeholders(item, member) for item in obj]

    if isinstance(obj, dict):
        return {
            key: parse_placeholders(value, member)
            for key, value in obj.items()
        }

    return obj


class JoinMessageSetupView(discord.ui.View):
    def __init__(
        self,
        author_id: int,
        channel: discord.TextChannel | None,
        create_channel: bool,
        message_data: dict | None = None
    ):
        super().__init__(timeout=300)

        self.author_id = author_id
        self.channel = channel
        self.create_channel = create_channel
        self.message_data = copy.deepcopy(
            message_data if message_data is not None else DEFAULT_JOIN_MESSAGE
        )

    async def interaction_check(self, interaction: discord.Interaction):
        if interaction.user.id != self.author_id:
            await interaction.response.send_message(
                "You cannot use this interaction.",
                ephemeral=True
            )
            return False

        return True

    @discord.ui.button(label="Confirm", style=discord.ButtonStyle.green)
    async def confirm(self, interaction: discord.Interaction, button: discord.ui.Button):
        guild = interaction.guild

        if self.create_channel:
            existing = discord.utils.get(guild.text_channels, name="joins")

            if existing:
                channel = existing
            else:
                channel = await guild.create_text_channel("joins")
        else:
            channel = self.channel

        data = gh.load_data(JOIN_LEAVE_FILE, {"guilds": {}})
        gid = str(guild.id)

        if gid not in data["guilds"]:
            data["guilds"][gid] = {}

        data["guilds"][gid]["join"] = {
            "enabled": True,
            "channel": channel.id,
            "message_data": self.message_data
        }

        gh.save_data(JOIN_LEAVE_FILE, data)

        for item in self.children:
            item.disabled = True

        await interaction.response.edit_message(
            content=f"{gh.SUCCESS} Join messages setup in {channel.mention}",
            view=self
        )

    @discord.ui.button(label="Edit Channel", style=discord.ButtonStyle.gray)
    async def edit_channel(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.send_message(
            "Select the join message channel:",
            view=JoinMessageChannelView(self),
            ephemeral=True
        )

    @discord.ui.button(label="Edit Message", style=discord.ButtonStyle.blurple)
    async def edit_message(self, interaction: discord.Interaction, button: discord.ui.Button):
        pending_message_edits[interaction.user.id] = {
            "guild_id": interaction.guild.id,
            "channel_id": interaction.channel.id,
            "type": "join",
            "view": self
        }

        await interaction.response.send_message(
            (
                "## To edit your message:\n"
                "> 1. Go to https://discohook.app/\n"
                "> 2. Customize your message.\n"
                "> 3. Scroll down -> `Options`\n"
                "> 4. Open JSON Editor\n"
                "> 5. Click Copy\n"
                "> 6. Paste the JSON here.\n\n"
                "**Note:** Only one raw content message is supported.\n"
                "Multiple embeds are allowed.\n\n"
                "### Variables:\n"
                "Joined Member mention: ```{user}```\n"
                "Joined Member username: ```{username}```\n"
                "Server name: ```{servername}```\n"
                "Server Member count: ```{server_membercount}``` "
            ),
            ephemeral=True
        )

    @discord.ui.button(label="Cancel", style=discord.ButtonStyle.red)
    async def cancel(self, interaction: discord.Interaction, button: discord.ui.Button):
        for item in self.children:
            item.disabled = True

        await interaction.response.edit_message(
            content=f"{gh.FAIL} Setup cancelled.",
            view=self
        )


class JoinMessageChannelSelect(discord.ui.ChannelSelect):
    def __init__(self, parent_view):
        super().__init__(
            placeholder="Select a channel",
            min_values=1,
            max_values=1,
            channel_types=[discord.ChannelType.text]
        )

        self.parent_view = parent_view

    async def callback(self, interaction: discord.Interaction):
        channel = self.values[0]

        self.parent_view.channel = channel
        self.parent_view.create_channel = False

        await interaction.response.send_message(
            f"{gh.SUCCESS} Join channel updated to {channel.mention}",
            ephemeral=True
        )


class JoinMessageChannelView(discord.ui.View):
    def __init__(self, parent_view):
        super().__init__(timeout=120)
        self.add_item(JoinMessageChannelSelect(parent_view))


class LeaveMessageSetupView(discord.ui.View):
    def __init__(
        self,
        author_id: int,
        channel: discord.TextChannel | None,
        create_channel: bool,
        message_data: dict | None = None
    ):
        super().__init__(timeout=300)

        self.author_id = author_id
        self.channel = channel
        self.create_channel = create_channel
        self.message_data = copy.deepcopy(
            message_data if message_data is not None else DEFAULT_LEAVE_MESSAGE
        )
    async def interaction_check(self, interaction: discord.Interaction):
        if interaction.user.id != self.author_id:
            await interaction.response.send_message(
                "You cannot use this interaction.",
                ephemeral=True
            )
            return False

        return True

    @discord.ui.button(label="Confirm", style=discord.ButtonStyle.green)
    async def confirm(self, interaction: discord.Interaction, button: discord.ui.Button):
        guild = interaction.guild

        if self.create_channel:
            existing = discord.utils.get(guild.text_channels, name="leaves")

            if existing:
                channel = existing
            else:
                channel = await guild.create_text_channel("leaves")
        else:
            channel = self.channel

        data = gh.load_data(JOIN_LEAVE_FILE, {"guilds": {}})
        gid = str(guild.id)

        if gid not in data["guilds"]:
            data["guilds"][gid] = {}

        data["guilds"][gid]["leave"] = {
            "enabled": True,
            "channel": channel.id,
            "message_data": self.message_data
        }

        gh.save_data(JOIN_LEAVE_FILE, data)

        for item in self.children:
            item.disabled = True

        await interaction.response.edit_message(
            content=f"{gh.SUCCESS} Leave messages setup in {channel.mention}",
            view=self
        )

    @discord.ui.button(label="Edit Channel", style=discord.ButtonStyle.gray)
    async def edit_channel(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.send_message(
            "Select the leave message channel:",
            view=LeaveMessageChannelView(self),
            ephemeral=True
        )

    @discord.ui.button(label="Edit Message", style=discord.ButtonStyle.blurple)
    async def edit_message(self, interaction: discord.Interaction, button: discord.ui.Button):
        pending_message_edits[interaction.user.id] = {
            "guild_id": interaction.guild.id,
            "channel_id": interaction.channel.id,
            "type": "leave",
            "view": self
        }

        await interaction.response.send_message(
            (
                "## To edit your message:\n"
                "> 1. Go to https://discohook.app/\n"
                "> 2. Customize your message.\n"
                "> 3. Scroll down -> `Options`\n"
                "> 4. Open JSON Editor\n"
                "> 5. Click Copy\n"
                "> 6. Paste the JSON here.\n\n"
                "**Note:** Only one raw content message is supported.\n"
                "Multiple embeds are allowed.\n\n"
                "### Variables:\n"
                "Left Member mention: ```{user}```\n"
                "Left Member username: ```{username}```\n"
                "Server name: ```{servername}```\n"
                "Server Member count: ```{server_membercount}``` "
            ),
            ephemeral=True
        )

    @discord.ui.button(label="Cancel", style=discord.ButtonStyle.red)
    async def cancel(self, interaction: discord.Interaction, button: discord.ui.Button):
        for item in self.children:
            item.disabled = True

        await interaction.response.edit_message(
            content=f"{gh.FAIL} Setup cancelled.",
            view=self
        )


class LeaveMessageChannelSelect(discord.ui.ChannelSelect):
    def __init__(self, parent_view):
        super().__init__(
            placeholder="Select a channel",
            min_values=1,
            max_values=1,
            channel_types=[discord.ChannelType.text]
        )

        self.parent_view = parent_view

    async def callback(self, interaction: discord.Interaction):
        channel = self.values[0]

        self.parent_view.channel = channel
        self.parent_view.create_channel = False

        await interaction.response.send_message(
            f"{gh.SUCCESS} Leave channel updated to {channel.mention}",
            ephemeral=True
        )


class LeaveMessageChannelView(discord.ui.View):
    def __init__(self, parent_view):
        super().__init__(timeout=120)
        self.add_item(LeaveMessageChannelSelect(parent_view))   

#------------------------------------------
# LOGS HELPERS 
#------------------------------------------

class ChannelSelect(discord.ui.ChannelSelect):
    def __init__(self, category):
        super().__init__(
            placeholder="Select a channel",
            min_values=1,
            max_values=1,
            channel_types=[
                discord.ChannelType.text,
                discord.ChannelType.news,
                discord.ChannelType.category,
                discord.ChannelType.public_thread,
                discord.ChannelType.private_thread,
]
        )
        self.category = category

    async def callback(self, interaction: discord.Interaction):
        channel = self.values[0]

        data = gh.load_data(LOGS_FILE, {"guilds": {}})
        gid = str(interaction.guild.id)

        if gid not in data["guilds"]:
            data["guilds"][gid] = {}

        data["guilds"][gid][self.category] = channel.id

        gh.save_data(LOGS_FILE, data)

        await interaction.response.send_message(
            f"{gh.SUCCESS} {self.category} logs set to {channel.mention}",
            ephemeral=True
        )

class ChannelView(discord.ui.View):
    def __init__(self, category):
        super().__init__()
        self.add_item(ChannelSelect(category))

class CategorySelect(discord.ui.Select):
    def __init__(self):
        options = [
            discord.SelectOption(label="Message Logs", value="message"),
            discord.SelectOption(label="Member Logs", value="member"),
            discord.SelectOption(label="Role Logs", value="roles"),
            discord.SelectOption(label="Channel Logs", value="channels"),
        ]

        super().__init__(
            placeholder="Select log type",
            options=options
        )

    async def callback(self, interaction: discord.Interaction):
        category = self.values[0]

        view = ChannelView(category)

        await interaction.response.send_message(
            f"Select a channel for {category} logs:",
            view=view,
            ephemeral=True
        )

class CategoryView(discord.ui.View):
    def __init__(self):
        super().__init__()
        self.add_item(CategorySelect())


