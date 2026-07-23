import discord
from discord.ext import commands
import copy
import json
import io
import html
import uuid
import datetime
from datetime import timedelta
import GenHelp as gh
from Cogs.Logs import LogsHelp as lh

TICKETS_FILE = "Data/Tickets/tickets.json"
PANEL_COLOR = 0x4EBEA2

DEFAULT_PANEL_MESSAGE = {
    "content": "",
    "embeds": [{
        "title": "Open A Ticket",
        "description": "> Click the button below to create a ticket.",
        "color": PANEL_COLOR
    }],
    "buttons": [{
        "id": "default_btn",
        "label": "Create",
        "emoji": "📩",
        "style": "primary",
        "type_id": "default_type"
    }]
}

DEFAULT_OPEN_MESSAGE = {
    "content": "",
    "embeds": [{
        "title": "Ticket Opened",
        "description": (
            "> Welcome {user}!\n"
            "> Ticket type: **{ticket_type}**\n"
            "> A staff member will be with you shortly."
        ),
        "color": PANEL_COLOR
    }]
}

DEFAULT_GUILD_DATA = {
    "max_tickets_per_user": 2,
    "panels": {},
    "opening_templates": {},
    "active_tickets": {},
    "user_open_tickets": {}
}

DEFAULT_PANEL = {
    "message_data": None,
    "transcript_channel": None,
    "category_id": None,
    "ping_roles": [],
    "ticket_types": {},
    "counter": 0,
    "panel_message_id": None,
    "panel_channel_id": None
}

BUTTON_STYLES = {
    "primary": discord.ButtonStyle.primary,
    "blue": discord.ButtonStyle.primary,
    "secondary": discord.ButtonStyle.secondary,
    "black": discord.ButtonStyle.secondary,
    "success": discord.ButtonStyle.success,
    "green": discord.ButtonStyle.success,
    "danger": discord.ButtonStyle.danger,
    "red": discord.ButtonStyle.danger,
}

STYLE_LABELS = {
    "primary": "Blue (primary)",
    "secondary": "Black (secondary)",
    "success": "Green (success)",
    "danger": "Red (danger)",
}

DISCOHOOK_TUTORIAL = (
    "## To import from Discohook:\n"
    "> 1. Go to https://discohook.app/\n"
    "> 2. Customize your message.\n"
    "> 3. Scroll down -> `Options`\n"
    "> 4. Open JSON Editor\n"
    "> 5. Click Copy\n"
    "> 6. Paste the JSON in the modal.\n\n"
    "**Note:** Only one raw content message is supported.\n"
    "Multiple embeds are allowed.\n"
    "Buttons will be imported as ticket type buttons.\n\n"
    "### Ticket Variables:\n"
    "{user} {username} {user_id} {user_avatar} {user_created} {user_joined}\n"
    "{server_name} {server_membercount} {server_owner} {server_icon}\n"
    "{ticket_type} {ticket_name} {ticket_role_mentions}\n"
    "{opened_at} {claimed_by} {closed_by}\n"
    "{guild_boosts} {guild_boost_level}"
)

TICKET_VARIABLES_HELP = (
    "### Variables:\n"
    "User mention: ```{user}```\n"
    "Username: ```{username}```\n"
    "User ID: ```{user_id}```\n"
    "User avatar URL: ```{user_avatar}```\n"
    "Account created: ```{user_created}```\n"
    "Joined server: ```{user_joined}```\n"
    "Server name: ```{server_name}```\n"
    "Member count: ```{server_membercount}```\n"
    "Server owner: ```{server_owner}```\n"
    "Server icon: ```{server_icon}```\n"
    "Ticket type: ```{ticket_type}```\n"
    "Ticket name: ```{ticket_name}```\n"
    "Ticket role mentions: ```{ticket_role_mentions}```\n"
    "Opened at: ```{opened_at}```\n"
    "Claimed by: ```{claimed_by}```\n"
    "Closed by: ```{closed_by}```\n"
    "Guild boosts: ```{guild_boosts}```\n"
    "Boost level: ```{guild_boost_level}```"
)


# ------------------------------------------
# Data helpers
# ------------------------------------------

def get_tickets_guilds():
    return gh.get_whitelisted_guilds("tickets")


def load_tickets():
    return gh.load_data(TICKETS_FILE, {"guilds": {}})


def save_tickets(data):
    gh.save_data(TICKETS_FILE, data)


def get_guild_ticket_data(guild_id: int, create=False):
    data = load_tickets()
    gid = str(guild_id)
    if gid not in data["guilds"]:
        if not create:
            return data, None
        data["guilds"][gid] = copy.deepcopy(DEFAULT_GUILD_DATA)
        save_tickets(data)
    return data, data["guilds"][gid]


def get_panel(guild_id: int, panel_name: str, create=False):
    data, gdata = get_guild_ticket_data(guild_id, create=create)
    if gdata is None:
        return data, None, None
    key = panel_name.lower()
    if key not in gdata["panels"]:
        if not create:
            return data, gdata, None
        panel = copy.deepcopy(DEFAULT_PANEL)
        panel["message_data"] = copy.deepcopy(DEFAULT_PANEL_MESSAGE)
        panel["ticket_types"]["default_type"] = {
            "id": "default_type",
            "name": "Support",
            "emoji": "💬",
            "style": "primary",
            "category_id": None,
            "ticket_roles": [],
            "opening_template_id": None,
            "modal_questions": []
        }
        gdata["panels"][key] = panel
        save_tickets(data)
    return data, gdata, gdata["panels"][key]


def save_panel(guild_id: int, panel_name: str, panel: dict):
    data, gdata = get_guild_ticket_data(guild_id, create=True)
    gdata["panels"][panel_name.lower()] = panel
    print("(DEBUG) Updated GUILD data: \n" + f"{json.dumps(gdata, indent=4)}")
    print("(DEBUG) Updated(?) data: \n" + f"{json.dumps(data, indent=4)}")
    save_tickets(data)


def new_id():
    return uuid.uuid4().hex[:8]


def style_from_str(style: str):
    return BUTTON_STYLES.get(style.lower(), discord.ButtonStyle.primary)


def style_to_str(style) -> str:
    if isinstance(style, str):
        return style.lower()
    mapping = {
        discord.ButtonStyle.primary: "primary",
        discord.ButtonStyle.secondary: "secondary",
        discord.ButtonStyle.success: "success",
        discord.ButtonStyle.danger: "danger",
    }
    return mapping.get(style, "primary")


def sanitize_channel_name(name: str) -> str:
    name = name.lower().replace(" ", "-")
    allowed = "abcdefghijklmnopqrstuvwxyz0123456789-_"
    return "".join(c for c in name if c in allowed)[:90] or "ticket"


# ------------------------------------------
# Message parsing (reuses LogsHelp)
# ------------------------------------------

def parse_message_data(message_data: dict):
    return lh.parse_message_data(message_data=message_data, join=True)


def build_embeds_from_data(embeds_data: list) -> list[discord.Embed]:
    embeds = []
    for e in embeds_data:
        embed = discord.Embed(
            title=e.get("title"),
            description=e.get("description"),
            color=e.get("color")
        )
        if "author" in e:
            embed.set_author(
                name=e["author"].get("name", ""),
                icon_url=e["author"].get("icon_url")
            )
        if "footer" in e:
            embed.set_footer(
                text=e["footer"].get("text", ""),
                icon_url=e["footer"].get("icon_url")
            )
        if "thumbnail" in e and e["thumbnail"].get("url"):
            embed.set_thumbnail(url=e["thumbnail"]["url"])
        if "image" in e and e["image"].get("url"):
            embed.set_image(url=e["image"]["url"])
        if "fields" in e:
            for f in e["fields"]:
                embed.add_field(
                    name=f["name"],
                    value=f["value"],
                    inline=f.get("inline", False)
                )
        embeds.append(embed)
    return embeds


def button_preview_text(buttons: list) -> str:
    if not buttons:
        return "None"
    parts = []
    for btn in buttons:
        emoji = btn.get("emoji") or ""
        label = btn.get("label") or "Button"
        parts.append(f"[{emoji} {label}]".strip())
    return " ".join(parts)


def apply_button_author(embeds: list[discord.Embed], buttons: list) -> list[discord.Embed]:
    if not embeds:
        embeds = [discord.Embed(description=" ")]
    preview = embeds[0]
    preview.set_author(name=f"Buttons: {button_preview_text(buttons)}")
    return embeds


def parse_ticket_placeholders(obj, member: discord.Member, ticket_info: dict = None, guild: discord.Guild = None):
    ticket_info = ticket_info or {}
    guild = guild or member.guild

    role_mentions = ""
    if ticket_info.get("ticket_roles"):
        mentions = []
        for rid in ticket_info["ticket_roles"]:
            role = guild.get_role(rid)
            if role:
                mentions.append(role.mention)
        role_mentions = " ".join(mentions)

    owner = guild.owner
    if owner is None and guild.owner_id:
        owner = guild.get_member(guild.owner_id)

    placeholders = {
        "{user}": member.mention,
        "{username}": member.name,
        "{user_id}": str(member.id),
        "{user_avatar}": str(member.display_avatar.url),
        "{user_created}": gh.format_dt(member.created_at),
        "{user_joined}": gh.format_dt(member.joined_at) if member.joined_at else "Unknown",
        "{server_name}": guild.name,
        "{servername}": guild.name,
        "{server_membercount}": str(guild.member_count),
        "{server_owner}": owner.mention if owner else "Unknown",
        "{server_icon}": str(guild.icon.url) if guild.icon else "",
        "{ticket_type}": ticket_info.get("ticket_type", "Ticket"),
        "{ticket_name}": ticket_info.get("ticket_name", "ticket"),
        "{ticket_role_mentions}": role_mentions,
        "{opened_at}": ticket_info.get("opened_at", gh.format_dt(discord.utils.utcnow())),
        "{claimed_by}": ticket_info.get("claimed_by", "Unclaimed"),
        "{closed_by}": ticket_info.get("closed_by", "Not closed"),
        "{guild_boosts}": str(guild.premium_subscription_count or 0),
        "{guild_boost_level}": str(guild.premium_tier),
    }

    if isinstance(obj, str):
        for key, value in placeholders.items():
            obj = obj.replace(key, value)
        return obj
    if isinstance(obj, list):
        return [parse_ticket_placeholders(item, member, ticket_info, guild) for item in obj]
    if isinstance(obj, dict):
        return {k: parse_ticket_placeholders(v, member, ticket_info, guild) for k, v in obj.items()}
    return obj


def parse_discohook_json(raw: str) -> dict:
    parsed = json.loads(raw)
    if not isinstance(parsed, dict):
        raise ValueError("JSON must be an object.")

    result = {
        "content": parsed.get("content", "") or "",
        "embeds": parsed.get("embeds", []) or [],
        "buttons": []
    }

    components = parsed.get("components", [])
    for row in components:
        if not isinstance(row, dict):
            continue
        for comp in row.get("components", []):
            if comp.get("type") != 2:
                continue
            type_id = new_id()
            result["buttons"].append({
                "id": new_id(),
                "label": comp.get("label", "Ticket"),
                "emoji": comp.get("emoji", {}).get("name") if isinstance(comp.get("emoji"), dict) else comp.get("emoji"),
                "style": style_to_str(comp.get("style", 1)),
                "type_id": type_id
            })
    return result


def embed_dict_from_modal(
    author="", author_icon="", title="", description="",
    footer="", footer_icon="", thumbnail="", image="", color=""
):
    if not any([author, author_icon, title, description, footer, footer_icon, thumbnail, image, color]):
        return None

    embed = {}
    if title:
        embed["title"] = title
    if description:
        embed["description"] = description
    if color:
        try:
            embed["color"] = int(color.replace("#", ""), 16)
        except ValueError:
            embed["color"] = PANEL_COLOR
    if author:
        embed["author"] = {"name": author}
        if author_icon:
            embed["author"]["icon_url"] = author_icon
    if footer:
        embed["footer"] = {"text": footer}
        if footer_icon:
            embed["footer"]["icon_url"] = footer_icon
    if thumbnail:
        embed["thumbnail"] = {"url": thumbnail}
    if image:
        embed["image"] = {"url": image}
    return embed


def get_ticket_staff_roles(panel: dict, ticket_type: dict) -> list[int]:
    roles = ticket_type.get("ticket_roles") or panel.get("ping_roles") or []
    return roles


def is_ticket_staff(member: discord.Member, panel: dict, ticket_type: dict) -> bool:
    if member.guild_permissions.administrator:
        return True
    staff_roles = get_ticket_staff_roles(panel, ticket_type)
    member_role_ids = {r.id for r in member.roles}
    return any(rid in member_role_ids for rid in staff_roles)


def get_active_ticket(channel_id: int):
    data = load_tickets()
    for gid, gdata in data["guilds"].items():
        ticket = gdata.get("active_tickets", {}).get(str(channel_id))
        if ticket:
            ticket["guild_id"] = int(gid)
            return data, gdata, ticket
    return data, None, None


def count_user_open_tickets(guild_id: int, user_id: int) -> int:
    data, gdata = get_guild_ticket_data(guild_id)
    if not gdata:
        return 0
    return len(gdata.get("user_open_tickets", {}).get(str(user_id), []))


# ------------------------------------------
# Transcript
# ------------------------------------------

async def generate_transcript_html(channel: discord.TextChannel) -> str:
    lines = [
        "<!DOCTYPE html><html><head><meta charset='utf-8'>",
        f"<title>Transcript - {html.escape(channel.name)}</title>",
        "<style>body{font-family:sans-serif;background:#36393f;color:#dcddde;padding:20px}",
        ".msg{margin:8px 0;padding:8px;border-radius:4px;background:#2f3136}",
        ".author{font-weight:bold;color:#fff}.time{color:#72767d;font-size:0.85em}",
        ".content{margin-top:4px;white-space:pre-wrap}</style></head><body>",
        f"<h1>Transcript: {html.escape(channel.name)}</h1><hr>"
    ]

    async for msg in channel.history(limit=None, oldest_first=True):
        ts = msg.created_at.strftime("%Y-%m-%d %H:%M:%S UTC")
        author = html.escape(str(msg.author))
        content = html.escape(msg.content or "")
        lines.append(
            f"<div class='msg'><span class='author'>{author}</span> "
            f"<span class='time'>{ts}</span><div class='content'>{content}</div></div>"
        )
        for att in msg.attachments:
            lines.append(f"<div class='msg'><a href='{html.escape(att.url)}'>{html.escape(att.filename)}</a></div>")

    lines.append("</body></html>")
    return "\n".join(lines)


def format_duration(opened_at: str) -> str:
    try:
        opened = datetime.datetime.fromisoformat(opened_at)
        delta = discord.utils.utcnow() - opened.replace(tzinfo=datetime.timezone.utc)
        hours, rem = divmod(int(delta.total_seconds()), 3600)
        minutes, seconds = divmod(rem, 60)
        return f"{hours}h {minutes}m {seconds}s"
    except Exception:
        return "Unknown"


# ------------------------------------------
# Modals
# ------------------------------------------

class RawContentModal(discord.ui.Modal, title="Edit Raw Content"):
    content_input = discord.ui.TextInput(
        label="Message Content",
        style=discord.TextStyle.paragraph,
        required=False,
        max_length=2000
    )

    def __init__(self, parent_view, current=""):
        super().__init__()
        self.parent_view = parent_view
        self.content_input.default = current

    async def on_submit(self, interaction: discord.Interaction):
        self.parent_view.message_data["content"] = self.content_input.value
        await self.parent_view.refresh_preview(interaction)


class EmbedCreateModal(discord.ui.Modal, title="Add Embed"):
    title_field = discord.ui.TextInput(label="Title", required=False, max_length=256)
    description = discord.ui.TextInput(label="Description", style=discord.TextStyle.paragraph, required=False, max_length=4000)
    author = discord.ui.TextInput(label="Author (Name|Icon URL)", required=False, max_length=512)
    footer = discord.ui.TextInput(label="Footer (Text|Icon URL)", required=False, max_length=512)
    color = discord.ui.TextInput(label="Color (hex)", required=False, placeholder="#4EBEA2")

    def __init__(self, parent_view):
        super().__init__()
        self.parent_view = parent_view

    async def on_submit(self, interaction: discord.Interaction):
        author_name, author_icon = "", ""
        if self.author.value and "|" in self.author.value:
            author_name, author_icon = self.author.value.split("|", 1)
        elif self.author.value:
            author_name = self.author.value
        footer_text, footer_icon = "", ""
        if self.footer.value and "|" in self.footer.value:
            footer_text, footer_icon = self.footer.value.split("|", 1)
        elif self.footer.value:
            footer_text = self.footer.value
        embed = embed_dict_from_modal(
            author_name.strip(), author_icon.strip(),
            self.title_field.value, self.description.value,
            footer_text.strip(), footer_icon.strip(),
            "", "", self.color.value
        )
        if not embed:
            return await interaction.response.send_message(
                f"{gh.FAIL} Enter at least one embed value.",
                ephemeral=True
            )
        view = EmbedDraftView(self.parent_view, embed)
        embeds = build_embeds_from_data([embed])
        await interaction.response.send_message(
            embed=embeds[0],
            view=view,
            ephemeral=True
        )


class EmbedFieldModal(discord.ui.Modal, title="Add Field"):
    name = discord.ui.TextInput(label="Field Name", max_length=256)
    value = discord.ui.TextInput(label="Field Value", style=discord.TextStyle.paragraph, max_length=1024)
    inline = discord.ui.TextInput(label="Inline (true/false)", required=False, default="false")

    def __init__(self, draft_view):
        super().__init__()
        self.draft_view = draft_view

    async def on_submit(self, interaction: discord.Interaction):
        self.draft_view.embed.setdefault("fields", []).append({
            "name": self.name.value,
            "value": self.value.value,
            "inline": self.inline.value.lower() == "true"
        })
        await self.draft_view.refresh(interaction)


class EmbedEditModal(discord.ui.Modal):
    def __init__(self, draft_view, field: str, label: str, current="", paragraph=False):
        super().__init__(title=f"Edit {label}")
        self.draft_view = draft_view
        self.field = field
        self.input = discord.ui.TextInput(
            label=label,
            default=current,
            style=discord.TextStyle.paragraph if paragraph else discord.TextStyle.short,
            required=False,
            max_length=4000 if paragraph else 256
        )
        self.add_item(self.input)

    async def on_submit(self, interaction: discord.Interaction):
        if self.field in ("title", "description"):
            self.draft_view.embed[self.field] = self.input.value or None
            if self.field in self.draft_view.embed and self.draft_view.embed[self.field] is None:
                del self.draft_view.embed[self.field]
        elif self.field == "color":
            if self.input.value:
                try:
                    self.draft_view.embed["color"] = int(self.input.value.replace("#", ""), 16)
                except ValueError:
                    pass
            elif "color" in self.draft_view.embed:
                del self.draft_view.embed["color"]
        elif self.field == "author":
            if self.input.value:
                parts = self.input.value.split("|", 1)
                self.draft_view.embed["author"] = {"name": parts[0].strip()}
                if len(parts) > 1 and parts[1].strip():
                    self.draft_view.embed["author"]["icon_url"] = parts[1].strip()
            elif "author" in self.draft_view.embed:
                del self.draft_view.embed["author"]
        elif self.field == "footer":
            if self.input.value:
                parts = self.input.value.split("|", 1)
                self.draft_view.embed["footer"] = {"text": parts[0].strip()}
                if len(parts) > 1 and parts[1].strip():
                    self.draft_view.embed["footer"]["icon_url"] = parts[1].strip()
            elif "footer" in self.draft_view.embed:
                del self.draft_view.embed["footer"]
        elif self.field == "thumbnail":
            if self.input.value:
                self.draft_view.embed["thumbnail"] = {"url": self.input.value}
            elif "thumbnail" in self.draft_view.embed:
                del self.draft_view.embed["thumbnail"]
        elif self.field == "image":
            if self.input.value:
                self.draft_view.embed["image"] = {"url": self.input.value}
            elif "image" in self.draft_view.embed:
                del self.draft_view.embed["image"]
        await self.draft_view.refresh(interaction)


class AddTicketButtonModal(discord.ui.Modal, title="Add Ticket Button"):
    name = discord.ui.TextInput(label="Button Name", max_length=80)
    emoji = discord.ui.TextInput(label="Emoji (empty for none)", required=False, max_length=50)
    style = discord.ui.TextInput(
        label="Style",
        placeholder="primary / secondary / success / danger",
        default="primary",
        max_length=20
    )

    def __init__(self, parent_view, panel_name: str, guild_id: int):
        super().__init__()
        self.parent_view = parent_view
        self.panel_name = panel_name
        self.guild_id = guild_id

    async def on_submit(self, interaction: discord.Interaction):
        style = self.style.value.lower().strip()
        if style not in BUTTON_STYLES:
            style = "primary"

        type_id = new_id()
        btn_id = new_id()
        btn = {
            "id": btn_id,
            "label": self.name.value,
            "emoji": self.emoji.value or None,
            "style": style,
            "type_id": type_id
        }
        self.parent_view.message_data.setdefault("buttons", []).append(btn)

        data, gdata, panel = get_panel(self.guild_id, self.panel_name, create=True)
        panel["ticket_types"][type_id] = {
            "id": type_id,
            "name": self.name.value,
            "emoji": self.emoji.value or None,
            "style": style,
            "category_id": None,
            "ticket_roles": [],
            "opening_template_id": None,
            "modal_questions": []
        }
        print("(DEBUG) Updated panel:" f"{panel}")
        save_panel(self.guild_id, self.panel_name, panel)

        await self.parent_view.refresh_preview(interaction)


class DiscohookImportPromptView(discord.ui.View):
    def __init__(self, parent_view, panel_name: str, guild_id: int):
        super().__init__(timeout=120)
        self.parent_view = parent_view
        self.panel_name = panel_name
        self.guild_id = guild_id

    @discord.ui.button(label="Paste JSON", style=discord.ButtonStyle.green, emoji="📥")
    async def open_modal(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.send_modal(
            DiscohookImportModal(self.parent_view, self.panel_name, self.guild_id)
        )


class DiscohookImportModal(discord.ui.Modal, title="Import Discohook JSON"):
    json_input = discord.ui.TextInput(
        label="Discohook JSON",
        style=discord.TextStyle.paragraph,
        max_length=4000
    )

    def __init__(self, parent_view, panel_name: str, guild_id: int):
        super().__init__()
        self.parent_view = parent_view
        self.panel_name = panel_name
        self.guild_id = guild_id

    async def on_submit(self, interaction: discord.Interaction):
        try:
            parsed = parse_discohook_json(self.json_input.value)
        except Exception as e:
            return await interaction.response.send_message(
                f"{gh.FAIL} Invalid JSON: {e}",
                ephemeral=True
            )

        self.parent_view.message_data["content"] = parsed["content"]
        self.parent_view.message_data["embeds"] = parsed["embeds"]

        if parsed["buttons"]:
            self.parent_view.message_data["buttons"] = parsed["buttons"]
            data, gdata, panel = get_panel(self.guild_id, self.panel_name, create=True)
            for btn in parsed["buttons"]:
                panel["ticket_types"][btn["type_id"]] = {
                    "id": btn["type_id"],
                    "name": btn["label"],
                    "emoji": btn.get("emoji"),
                    "style": btn.get("style", "primary"),
                    "category_id": None,
                    "ticket_roles": [],
                    "opening_template_id": None,
                    "modal_questions": []
                }
            save_panel(self.guild_id, self.panel_name, panel)

        await self.parent_view.refresh_preview(interaction)


class PanelNameModal(discord.ui.Modal, title="Panel Name"):
    name = discord.ui.TextInput(label="Panel Name", max_length=50)

    def __init__(self, callback_fn):
        super().__init__()
        self.callback_fn = callback_fn

    async def on_submit(self, interaction: discord.Interaction):
        await self.callback_fn(interaction, self.name.value)


# ------------------------------------------
# Embed draft / edit views
# ------------------------------------------

class EmbedDraftView(discord.ui.View):
    def __init__(self, parent_view, embed: dict):
        super().__init__(timeout=300)
        self.parent_view = parent_view
        self.embed = embed

    async def refresh(self, interaction: discord.Interaction):
        embeds = build_embeds_from_data([self.embed])
        await interaction.response.edit_message(embed=embeds[0], view=self)

    @discord.ui.button(label="Add Embed", style=discord.ButtonStyle.green, emoji="✅")
    async def add_embed(self, interaction: discord.Interaction, button: discord.ui.Button):
        self.parent_view.message_data.setdefault("embeds", []).append(copy.deepcopy(self.embed))
        await interaction.response.send_message(f"{gh.SUCCESS} Embed added.", ephemeral=True)
        self.stop()

    @discord.ui.button(label="Edit Title", style=discord.ButtonStyle.blurple, emoji="✏")
    async def edit_title(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.send_modal(
            EmbedEditModal(self, "title", "Title", self.embed.get("title", ""))
        )

    @discord.ui.button(label="Edit Description", style=discord.ButtonStyle.blurple, emoji="✏")
    async def edit_desc(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.send_modal(
            EmbedEditModal(self, "description", "Description", self.embed.get("description", ""), paragraph=True)
        )

    @discord.ui.button(label="Edit Author", style=discord.ButtonStyle.blurple, emoji="✏")
    async def edit_author(self, interaction: discord.Interaction, button: discord.ui.Button):
        author = self.embed.get("author", {})
        current = author.get("name", "")
        if author.get("icon_url"):
            current += f"|{author['icon_url']}"
        await interaction.response.send_modal(EmbedEditModal(self, "author", "Author (Name|Icon URL)", current))

    @discord.ui.button(label="Edit Footer", style=discord.ButtonStyle.blurple, emoji="✏")
    async def edit_footer(self, interaction: discord.Interaction, button: discord.ui.Button):
        footer = self.embed.get("footer", {})
        current = footer.get("text", "")
        if footer.get("icon_url"):
            current += f"|{footer['icon_url']}"
        await interaction.response.send_modal(EmbedEditModal(self, "footer", "Footer (Text|Icon URL)", current))

    @discord.ui.button(label="Edit Thumbnail", style=discord.ButtonStyle.blurple, emoji="✏")
    async def edit_thumb(self, interaction: discord.Interaction, button: discord.ui.Button):
        url = self.embed.get("thumbnail", {}).get("url", "")
        await interaction.response.send_modal(EmbedEditModal(self, "thumbnail", "Thumbnail URL", url))

    @discord.ui.button(label="Edit Image", style=discord.ButtonStyle.blurple, emoji="✏")
    async def edit_image(self, interaction: discord.Interaction, button: discord.ui.Button):
        url = self.embed.get("image", {}).get("url", "")
        await interaction.response.send_modal(EmbedEditModal(self, "image", "Image URL", url))

    @discord.ui.button(label="Edit Color", style=discord.ButtonStyle.blurple, emoji="🎨")
    async def edit_color(self, interaction: discord.Interaction, button: discord.ui.Button):
        color = ""
        if "color" in self.embed:
            color = f"#{self.embed['color']:06x}"
        await interaction.response.send_modal(EmbedEditModal(self, "color", "Color (hex)", color))

    @discord.ui.button(label="Add Field", style=discord.ButtonStyle.green, emoji="➕")
    async def add_field(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.send_modal(EmbedFieldModal(self))

    @discord.ui.button(label="Remove Field", style=discord.ButtonStyle.red, emoji="🗑")
    async def remove_field(self, interaction: discord.Interaction, button: discord.ui.Button):
        fields = self.embed.get("fields", [])
        if fields:
            fields.pop()
            if not fields:
                self.embed.pop("fields", None)
            await self.refresh(interaction)
        else:
            await interaction.response.send_message("No fields to remove.", ephemeral=True)

    @discord.ui.button(label="Cancel", style=discord.ButtonStyle.red, emoji="❌")
    async def cancel(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.edit_message(content=f"{gh.FAIL} Cancelled.", embed=None, view=None)


class EmbedSelect(discord.ui.Select):
    def __init__(self, parent_view):
        embeds = parent_view.message_data.get("embeds", [])
        options = [
            discord.SelectOption(label=f"Embed {i + 1}", value=str(i), description=(e.get("title") or "No title")[:100])
            for i, e in enumerate(embeds[:25])
        ]
        super().__init__(placeholder="Select embed to edit", options=options)
        self.parent_view = parent_view

    async def callback(self, interaction: discord.Interaction):
        idx = int(self.values[0])
        embed = self.parent_view.message_data["embeds"][idx]
        view = EmbedEditView(self.parent_view, idx, embed)
        embeds = build_embeds_from_data([embed])
        await interaction.response.send_message(embed=embeds[0], view=view, ephemeral=True)


class EmbedEditView(discord.ui.View):
    def __init__(self, parent_view, index: int, embed: dict):
        super().__init__(timeout=300)
        self.parent_view = parent_view
        self.index = index
        self.embed = embed

    async def refresh(self, interaction: discord.Interaction):
        embeds = build_embeds_from_data([self.embed])
        self.parent_view.message_data["embeds"][self.index] = self.embed
        await interaction.response.edit_message(embed=embeds[0], view=self)

    @discord.ui.button(label="Edit Title", style=discord.ButtonStyle.blurple, emoji="✏")
    async def edit_title(self, interaction: discord.Interaction, button: discord.ui.Button):
        draft = EmbedDraftView(self.parent_view, self.embed)
        await interaction.response.send_modal(EmbedEditModal(draft, "title", "Title", self.embed.get("title", "")))

    @discord.ui.button(label="Edit Description", style=discord.ButtonStyle.blurple, emoji="✏")
    async def edit_desc(self, interaction: discord.Interaction, button: discord.ui.Button):
        draft = EmbedDraftView(self.parent_view, self.embed)
        await interaction.response.send_modal(
            EmbedEditModal(draft, "description", "Description", self.embed.get("description", ""), paragraph=True)
        )

    @discord.ui.button(label="Delete Embed", style=discord.ButtonStyle.red, emoji="🗑")
    async def delete(self, interaction: discord.Interaction, button: discord.ui.Button):
        self.parent_view.message_data["embeds"].pop(self.index)
        await self.parent_view.refresh_preview(interaction)


class ButtonSelect(discord.ui.Select):
    def __init__(self, parent_view):
        buttons = parent_view.message_data.get("buttons", [])
        options = [
            discord.SelectOption(label=btn.get("label", "Button"), value=str(i))
            for i, btn in enumerate(buttons[:25])
        ]
        super().__init__(placeholder="Select button", options=options)
        self.parent_view = parent_view

    async def callback(self, interaction: discord.Interaction):
        await interaction.response.send_message(
            f"{gh.SUCCESS} Selected button {int(self.values[0]) + 1}.",
            ephemeral=True
        )


# ------------------------------------------
# Message edit view (shared panel + open message)
# ------------------------------------------

class MessageEditView(discord.ui.View):
    def __init__(
        self,
        author_id: int,
        message_data: dict,
        panel_name: str = None,
        guild_id: int = None,
        allow_buttons: bool = True,
        on_confirm=None
    ):
        super().__init__(timeout=300)
        self.author_id = author_id
        self.message_data = copy.deepcopy(message_data)
        self.panel_name = panel_name
        self.guild_id = guild_id
        self.allow_buttons = allow_buttons
        self.on_confirm = on_confirm
        self.preview_message = None

    async def interaction_check(self, interaction: discord.Interaction) -> bool:
        if interaction.user.id != self.author_id:
            await interaction.response.send_message("You cannot use this interaction.", ephemeral=True)
            return False
        return True

    async def build_preview(self, member: discord.Member):
        parsed = parse_ticket_placeholders(copy.deepcopy(self.message_data), member)
        content = parsed.get("content") or None
        embeds = build_embeds_from_data(parsed.get("embeds", []))
        buttons = parsed.get("buttons", []) if self.allow_buttons else []
        if buttons:
            embeds = apply_button_author(embeds, buttons)
        elif not embeds:
            embeds = [discord.Embed(description=" ")]
        return content, embeds

    async def refresh_preview(self, interaction: discord.Interaction):
        content, embeds = await self.build_preview(interaction.user)
        if interaction.response.is_done():
            await interaction.followup.edit_message(interaction.message.id, content=content, embeds=embeds, view=self)
        else:
            await interaction.response.edit_message(content=content, embeds=embeds, view=self)

    @discord.ui.button(label="Edit Raw Content", style=discord.ButtonStyle.blurple, emoji="💬", row=0)
    async def edit_raw(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.send_modal(
            RawContentModal(self, self.message_data.get("content", ""))
        )

    @discord.ui.button(label="Add Embed", style=discord.ButtonStyle.green, emoji="➕", row=0)
    async def add_embed(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.send_modal(EmbedCreateModal(self))

    @discord.ui.button(label="Edit Existing Embed", style=discord.ButtonStyle.blurple, emoji="✏", row=0)
    async def edit_embed(self, interaction: discord.Interaction, button: discord.ui.Button):
        if not self.message_data.get("embeds"):
            return await interaction.response.send_message("No embeds to edit.", ephemeral=True)
        view = discord.ui.View(timeout=120)
        view.add_item(EmbedSelect(self))
        await interaction.response.send_message("Select an embed:", view=view, ephemeral=True)

    @discord.ui.button(label="Delete Embed", style=discord.ButtonStyle.red, emoji="🗑", row=0)
    async def delete_embed(self, interaction: discord.Interaction, button: discord.ui.Button):
        if not self.message_data.get("embeds"):
            return await interaction.response.send_message("No embeds to delete.", ephemeral=True)
        view = discord.ui.View(timeout=120)
        view.add_item(EmbedDeleteSelect(self))
        await interaction.response.send_message("Select embed to delete:", view=view, ephemeral=True)

    @discord.ui.button(label="Move Embed Up", style=discord.ButtonStyle.gray, emoji="⬆", row=1)
    async def move_up(self, interaction: discord.Interaction, button: discord.ui.Button):
        embeds = self.message_data.get("embeds", [])
        if len(embeds) < 2:
            return await interaction.response.send_message("Need at least 2 embeds.", ephemeral=True)
        view = discord.ui.View(timeout=120)
        view.add_item(EmbedMoveSelect(self, direction=-1))
        await interaction.response.send_message("Select embed to move up:", view=view, ephemeral=True)

    @discord.ui.button(label="Move Embed Down", style=discord.ButtonStyle.gray, emoji="⬇", row=1)
    async def move_down(self, interaction: discord.Interaction, button: discord.ui.Button):
        embeds = self.message_data.get("embeds", [])
        if len(embeds) < 2:
            return await interaction.response.send_message("Need at least 2 embeds.", ephemeral=True)
        view = discord.ui.View(timeout=120)
        view.add_item(EmbedMoveSelect(self, direction=1))
        await interaction.response.send_message("Select embed to move down:", view=view, ephemeral=True)

    @discord.ui.button(label="Clear Embeds", style=discord.ButtonStyle.red, emoji="⛔", row=1)
    async def clear_embeds(self, interaction: discord.Interaction, button: discord.ui.Button):
        self.message_data["embeds"] = []
        await self.refresh_preview(interaction)

    @discord.ui.button(label="Add Button", style=discord.ButtonStyle.green, emoji="🔘", row=1)
    async def add_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        if not self.allow_buttons:
            return await interaction.response.send_message("Buttons are fixed for this message.", ephemeral=True)
        await interaction.response.send_modal(
            AddTicketButtonModal(self, self.panel_name, self.guild_id)
        )

    @discord.ui.button(label="Delete Button", style=discord.ButtonStyle.red, emoji="🗑", row=2)
    async def delete_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        if not self.message_data.get("buttons"):
            return await interaction.response.send_message("No buttons to delete.", ephemeral=True)
        view = discord.ui.View(timeout=120)
        view.add_item(ButtonDeleteSelect(self))
        await interaction.response.send_message("Select button to delete:", view=view, ephemeral=True)

    @discord.ui.button(label="Move Button Left", style=discord.ButtonStyle.gray, emoji="⬅", row=2)
    async def move_btn_left(self, interaction: discord.Interaction, button: discord.ui.Button):
        view = discord.ui.View(timeout=120)
        view.add_item(ButtonMoveSelect(self, direction=-1))
        await interaction.response.send_message("Select button to move left:", view=view, ephemeral=True)

    @discord.ui.button(label="Move Button Right", style=discord.ButtonStyle.gray, emoji="➡", row=2)
    async def move_btn_right(self, interaction: discord.Interaction, button: discord.ui.Button):
        view = discord.ui.View(timeout=120)
        view.add_item(ButtonMoveSelect(self, direction=1))
        await interaction.response.send_message("Select button to move right:", view=view, ephemeral=True)

    @discord.ui.button(label="Import Discohook", style=discord.ButtonStyle.blurple, emoji="📥", row=3)
    async def import_discohook(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.send_message(
            DISCOHOOK_TUTORIAL,
            view=DiscohookImportPromptView(self, self.panel_name, self.guild_id),
            ephemeral=True
        )

    @discord.ui.button(label="Confirm", style=discord.ButtonStyle.green, emoji="✅", row=3)
    async def confirm(self, interaction: discord.Interaction, button: discord.ui.Button):
        if self.on_confirm:
            await self.on_confirm(interaction, self.message_data)
        else:
            await interaction.response.send_message(f"{gh.SUCCESS} Message saved.", ephemeral=True)

    @discord.ui.button(label="Cancel", style=discord.ButtonStyle.red, emoji="❌", row=3)
    async def cancel(self, interaction: discord.Interaction, button: discord.ui.Button):
        for item in self.children:
            item.disabled = True
        await interaction.response.edit_message(content=f"{gh.FAIL} Cancelled.", view=self)


class EmbedDeleteSelect(discord.ui.Select):
    def __init__(self, parent_view):
        embeds = parent_view.message_data.get("embeds", [])
        options = [discord.SelectOption(label=f"Embed {i + 1}", value=str(i)) for i in range(len(embeds[:25]))]
        super().__init__(placeholder="Select embed to delete", options=options)
        self.parent_view = parent_view

    async def callback(self, interaction: discord.Interaction):
        idx = int(self.values[0])
        self.parent_view.message_data["embeds"].pop(idx)
        await self.parent_view.refresh_preview(interaction)


class EmbedMoveSelect(discord.ui.Select):
    def __init__(self, parent_view, direction: int):
        embeds = parent_view.message_data.get("embeds", [])
        options = [discord.SelectOption(label=f"Embed {i + 1}", value=str(i)) for i in range(len(embeds[:25]))]
        super().__init__(placeholder="Select embed", options=options)
        self.parent_view = parent_view
        self.direction = direction

    async def callback(self, interaction: discord.Interaction):
        idx = int(self.values[0])
        new_idx = idx + self.direction
        embeds = self.parent_view.message_data["embeds"]
        if 0 <= new_idx < len(embeds):
            embeds[idx], embeds[new_idx] = embeds[new_idx], embeds[idx]
        await self.parent_view.refresh_preview(interaction)


class ButtonDeleteSelect(discord.ui.Select):
    def __init__(self, parent_view):
        buttons = parent_view.message_data.get("buttons", [])
        options = [discord.SelectOption(label=btn.get("label", "Button"), value=str(i)) for i, btn in enumerate(buttons[:25])]
        super().__init__(placeholder="Select button to delete", options=options)
        self.parent_view = parent_view

    async def callback(self, interaction: discord.Interaction):
        idx = int(self.values[0])
        self.parent_view.message_data["buttons"].pop(idx)
        await self.parent_view.refresh_preview(interaction)


class ButtonMoveSelect(discord.ui.Select):
    def __init__(self, parent_view, direction: int):
        buttons = parent_view.message_data.get("buttons", [])
        options = [discord.SelectOption(label=btn.get("label", "Button"), value=str(i)) for i, btn in enumerate(buttons[:25])]
        super().__init__(placeholder="Select button", options=options)
        self.parent_view = parent_view
        self.direction = direction

    async def callback(self, interaction: discord.Interaction):
        idx = int(self.values[0])
        new_idx = idx + self.direction
        buttons = self.parent_view.message_data["buttons"]
        if 0 <= new_idx < len(buttons):
            buttons[idx], buttons[new_idx] = buttons[new_idx], buttons[idx]
        await self.parent_view.refresh_preview(interaction)


# ------------------------------------------
# Panel setup views
# ------------------------------------------

class TranscriptChannelSelect(discord.ui.ChannelSelect):
    def __init__(self, parent_view):
        super().__init__(
            placeholder="Select transcript channel",
            channel_types=[discord.ChannelType.text, discord.ChannelType.news],
            min_values=1, max_values=1
        )
        self.parent_view = parent_view

    async def callback(self, interaction: discord.Interaction):
        self.parent_view.panel["transcript_channel"] = self.values[0].id
        await interaction.response.send_message(
            f"{gh.SUCCESS} Transcript channel set to {self.values[0].mention}",
            ephemeral=True
        )


class TicketCategorySelect(discord.ui.ChannelSelect):
    def __init__(self, parent_view):
        super().__init__(
            placeholder="Select ticket category",
            channel_types=[discord.ChannelType.category],
            min_values=1, max_values=1
        )
        self.parent_view = parent_view

    async def callback(self, interaction: discord.Interaction):
        self.parent_view.panel["category_id"] = self.values[0].id
        await interaction.response.send_message(
            f"{gh.SUCCESS} Ticket category set to **{self.values[0].name}**",
            ephemeral=True
        )


class PingRolesSelect(discord.ui.RoleSelect):
    def __init__(self, parent_view):
        super().__init__(
            placeholder="Select ping roles (moderator roles only)",
            min_values=0, max_values=25
        )
        self.parent_view = parent_view

    async def callback(self, interaction: discord.Interaction):
        self.parent_view.panel["ping_roles"] = [r.id for r in self.values]
        await interaction.response.send_message(
            f"{gh.SUCCESS} Ping roles updated ({len(self.values)} selected).\n"
            "> **Tip:** Only add moderator/staff roles.",
            ephemeral=True
        )


class PanelMessageSetupView(discord.ui.View):
    def __init__(self, author_id: int, guild_id: int, panel_name: str, panel: dict):
        super().__init__(timeout=300)
        self.author_id = author_id
        self.guild_id = guild_id
        self.panel_name = panel_name
        self.panel = panel
        self.message_data = copy.deepcopy(
            panel["message_data"] if panel.get("message_data") else DEFAULT_PANEL_MESSAGE
        )

    async def interaction_check(self, interaction: discord.Interaction) -> bool:
        if interaction.user.id != self.author_id:
            await interaction.response.send_message("You cannot use this interaction.", ephemeral=True)
            return False
        return True

    async def save(self):
        data, gdata, latest_panel = get_panel(self.guild_id, self.panel_name, create=True)

        self.panel["ticket_types"] = latest_panel.get("ticket_types", {})
        self.panel["message_data"] = self.message_data

        save_panel(self.guild_id, self.panel_name, self.panel)

    @discord.ui.button(label="Confirm", style=discord.ButtonStyle.green, emoji="✅")
    async def confirm(self, interaction: discord.Interaction, button: discord.ui.Button):
        await self.save()
        for item in self.children:
            item.disabled = True
        await interaction.response.edit_message(
            content=f"{gh.SUCCESS} Panel **{self.panel_name}** message saved.",
            view=self
        )

    @discord.ui.button(label="Edit Message", style=discord.ButtonStyle.blurple, emoji="✏")
    async def edit_message(self, interaction: discord.Interaction, button: discord.ui.Button):
        async def on_confirm(inter, data):
            self.message_data = data
            await self.save()
            content, embeds = await MessageEditView(
                self.author_id, data, self.panel_name, self.guild_id
            ).build_preview(inter.user)
            await inter.response.edit_message(content=content, embeds=embeds, view=self)

        edit_view = MessageEditView(
            self.author_id, self.message_data,
            panel_name=self.panel_name, guild_id=self.guild_id,
            on_confirm=on_confirm
        )
        content, embeds = await edit_view.build_preview(interaction.user)
        await interaction.response.send_message(content=content, embeds=embeds, view=edit_view, ephemeral=True)

    @discord.ui.button(label="Edit Transcript Channel", style=discord.ButtonStyle.blurple, emoji="✏")
    async def edit_transcript(self, interaction: discord.Interaction, button: discord.ui.Button):
        view = discord.ui.View(timeout=120)
        view.add_item(TranscriptChannelSelect(self))
        await interaction.response.send_message("Select transcript logging channel:", view=view, ephemeral=True)

    @discord.ui.button(label="Edit Ticket Category", style=discord.ButtonStyle.blurple, emoji="✏")
    async def edit_category(self, interaction: discord.Interaction, button: discord.ui.Button):
        view = discord.ui.View(timeout=120)
        view.add_item(TicketCategorySelect(self))
        await interaction.response.send_message("Select category for ticket channels:", view=view, ephemeral=True)

    @discord.ui.button(label="Edit Ping Roles", style=discord.ButtonStyle.blurple, emoji="✏")
    async def edit_ping(self, interaction: discord.Interaction, button: discord.ui.Button):
        view = discord.ui.View(timeout=120)
        view.add_item(PingRolesSelect(self))
        await interaction.response.send_message(
            "Select roles to ping when a ticket opens.\n> **Tip:** Only add moderator/staff roles.",
            view=view, ephemeral=True
        )

    @discord.ui.button(label="Cancel", style=discord.ButtonStyle.red, emoji="❌")
    async def cancel(self, interaction: discord.Interaction, button: discord.ui.Button):
        for item in self.children:
            item.disabled = True
        await interaction.response.edit_message(content=f"{gh.FAIL} Setup cancelled.", view=self)


# ------------------------------------------
# Persistent panel view
# ------------------------------------------

class PanelTicketButton(discord.ui.Button):
    def __init__(self, guild_id: int, panel_name: str, btn_data: dict):
        super().__init__(
            label=btn_data.get("label", "Ticket"),
            emoji=btn_data.get("emoji"),
            style=style_from_str(btn_data.get("style", "primary")),
            custom_id=f"tkt:panel:{guild_id}:{panel_name}:{btn_data['type_id']}"
        )
        self.guild_id = guild_id
        self.panel_name = panel_name
        self.type_id = btn_data["type_id"]


class PanelPersistentView(discord.ui.View):
    def __init__(self, guild_id: int, panel_name: str, buttons: list):
        super().__init__(timeout=None)
        for btn in buttons[:25]:
            self.add_item(PanelTicketButton(guild_id, panel_name, btn))


# ------------------------------------------
# Ticket control persistent view
# ------------------------------------------

class TicketClaimButton(discord.ui.Button):
    def __init__(self, channel_id: int):
        super().__init__(
            label="Claim", emoji="🙋", style=discord.ButtonStyle.primary,
            custom_id=f"tkt:claim:{channel_id}"
        )
        self.channel_id = channel_id


class TicketCloseButton(discord.ui.Button):
    def __init__(self, channel_id: int):
        super().__init__(
            label="Close", emoji="🔒", style=discord.ButtonStyle.danger,
            custom_id=f"tkt:close:{channel_id}"
        )
        self.channel_id = channel_id


class TicketControlView(discord.ui.View):
    def __init__(self, channel_id: int, claimed: bool = False):
        super().__init__(timeout=None)
        claim_btn = TicketClaimButton(channel_id)
        if claimed:
            claim_btn.disabled = True
        self.add_item(claim_btn)
        self.add_item(TicketCloseButton(channel_id))


class CloseRequestView(discord.ui.View):
    def __init__(self, channel_id: int, opener_id: int):
        super().__init__(timeout=300)
        self.channel_id = channel_id
        self.opener_id = opener_id
        self.result = None

    @discord.ui.button(label="Close", style=discord.ButtonStyle.green, emoji="✅")
    async def accept(self, interaction: discord.Interaction, button: discord.ui.Button):
        if interaction.user.id != self.opener_id:
            return await interaction.response.send_message("Only the ticket opener can respond.", ephemeral=True)
        self.result = True 
        
        timestamp = discord.utils.utcnow() + timedelta(seconds=5)
        formatted = discord.utils.format_dt(timestamp, style="R")

        await interaction.response.edit_message(content=f"{gh.SUCCESS} Closing ticket {formatted}", embeds=[], view=None)
        self.stop()

    @discord.ui.button(label="Keep Open", style=discord.ButtonStyle.red, emoji="❌")
    async def deny(self, interaction: discord.Interaction, button: discord.ui.Button):
        if interaction.user.id != self.opener_id:
            return await interaction.response.send_message("Only the ticket opener can respond.", ephemeral=True)
        self.result = False
        await interaction.response.edit_message(content=f"{gh.FAIL} Close request cancelled.", embeds=[], view=None)
        self.stop()


# ------------------------------------------
# Open message setup
# ------------------------------------------

class OpeningTemplatePanelSelect(discord.ui.Select):
    def __init__(self, guild_id: int, template_id: str, panels: list):
        options = [
            discord.SelectOption(label=name, value=name.lower())
            for name in panels[:25]
        ]
        super().__init__(
            placeholder="Assign to panels",
            min_values=0, max_values=min(len(options), 25),
            options=options
        )
        self.guild_id = guild_id
        self.template_id = template_id

    async def callback(self, interaction: discord.Interaction):
        data, gdata = get_guild_ticket_data(self.guild_id, create=True)
        template = gdata["opening_templates"][self.template_id]
        template["panels"] = self.values
        for panel_name in gdata["panels"]:
            if panel_name in self.values:
                for tid, ttype in gdata["panels"][panel_name]["ticket_types"].items():
                    ttype["opening_template_id"] = self.template_id
        save_tickets(data)
        await interaction.response.send_message(
            f"{gh.SUCCESS} Template assigned to {len(self.values)} panel(s).",
            ephemeral=True
        )


class OpenMessageSetupView(discord.ui.View):
    def __init__(self, author_id: int, guild_id: int, template_id: str, template: dict):
        super().__init__(timeout=300)
        self.author_id = author_id
        self.guild_id = guild_id
        self.template_id = template_id
        self.template = template
        self.message_data = copy.deepcopy(template.get("message_data", DEFAULT_OPEN_MESSAGE))

    async def interaction_check(self, interaction: discord.Interaction) -> bool:
        if interaction.user.id != self.author_id:
            await interaction.response.send_message("You cannot use this interaction.", ephemeral=True)
            return False
        return True

    async def save(self):
        data, gdata = get_guild_ticket_data(self.guild_id, create=True)
        gdata["opening_templates"][self.template_id] = self.template
        gdata["opening_templates"][self.template_id]["message_data"] = self.message_data
        save_tickets(data)

    @discord.ui.button(label="Confirm", style=discord.ButtonStyle.green, emoji="✅")
    async def confirm(self, interaction: discord.Interaction, button: discord.ui.Button):
        await self.save()
        for item in self.children:
            item.disabled = True
        await interaction.response.edit_message(
            content=f"{gh.SUCCESS} Opening message template saved.",
            view=self
        )

    @discord.ui.button(label="Edit Message", style=discord.ButtonStyle.blurple, emoji="✏")
    async def edit_message(self, interaction: discord.Interaction, button: discord.ui.Button):
        async def on_confirm(inter, data):
            self.message_data = data
            await self.save()
            await inter.response.send_message(f"{gh.SUCCESS} Opening message updated.", ephemeral=True)

        edit_view = MessageEditView(
            self.author_id, self.message_data,
            allow_buttons=False, on_confirm=on_confirm
        )
        content, embeds = await edit_view.build_preview(interaction.user)
        fixed = apply_button_author(embeds, [
            {"emoji": "🙋", "label": "Claim"},
            {"emoji": "🔒", "label": "Close"}
        ])
        await interaction.response.send_message(
            content=content, embeds=fixed, view=edit_view, ephemeral=True
        )

    @discord.ui.button(label="Assign Panels", style=discord.ButtonStyle.gray, emoji="📋")
    async def assign_panels(self, interaction: discord.Interaction, button: discord.ui.Button):
        data, gdata = get_guild_ticket_data(self.guild_id)
        panels = list(gdata.get("panels", {}).keys())
        if not panels:
            return await interaction.response.send_message("No panels exist yet.", ephemeral=True)
        view = discord.ui.View(timeout=120)
        view.add_item(OpeningTemplatePanelSelect(self.guild_id, self.template_id, panels))
        await interaction.response.send_message("Select panels for this template:", view=view, ephemeral=True)

    @discord.ui.button(label="Cancel", style=discord.ButtonStyle.red, emoji="❌")
    async def cancel(self, interaction: discord.Interaction, button: discord.ui.Button):
        for item in self.children:
            item.disabled = True
        await interaction.response.edit_message(content=f"{gh.FAIL} Cancelled.", view=self)


# ------------------------------------------
# Ticket type edit view
# ------------------------------------------

class TicketTypeRoleSelect(discord.ui.RoleSelect):
    def __init__(self, panel_name: str, guild_id: int, type_id: str):
        super().__init__(placeholder="Select ticket staff roles", min_values=0, max_values=25)
        self.panel_name = panel_name
        self.guild_id = guild_id
        self.type_id = type_id

    async def callback(self, interaction: discord.Interaction):
        data, gdata, panel = get_panel(self.guild_id, self.panel_name)
        panel["ticket_types"][self.type_id]["ticket_roles"] = [r.id for r in self.values]
        save_panel(self.guild_id, self.panel_name, panel)
        await interaction.response.send_message(
            f"{gh.SUCCESS} Ticket roles updated.\n> **Tip:** Only add moderator/staff roles.",
            ephemeral=True
        )


class TicketTypeCategorySelect(discord.ui.ChannelSelect):
    def __init__(self, panel_name: str, guild_id: int, type_id: str):
        super().__init__(
            placeholder="Select category override",
            channel_types=[discord.ChannelType.category],
            min_values=1, max_values=1
        )
        self.panel_name = panel_name
        self.guild_id = guild_id
        self.type_id = type_id

    async def callback(self, interaction: discord.Interaction):
        data, gdata, panel = get_panel(self.guild_id, self.panel_name)
        panel["ticket_types"][self.type_id]["category_id"] = self.values[0].id
        save_panel(self.guild_id, self.panel_name, panel)
        await interaction.response.send_message(
            f"{gh.SUCCESS} Category override set to **{self.values[0].name}**",
            ephemeral=True
        )


class TicketTypeSelect(discord.ui.Select):
    def __init__(self, panel_name: str, guild_id: int, panel: dict):
        options = []
        for tid, ttype in panel.get("ticket_types", {}).items():
            emoji = ttype.get("emoji") or "🎫"
            options.append(discord.SelectOption(
                label=ttype.get("name", "Type"),
                value=tid,
                emoji=emoji
            ))
        super().__init__(placeholder="Select ticket type to edit", options=options[:25])
        self.panel_name = panel_name
        self.guild_id = guild_id
        self.panel = panel

    async def callback(self, interaction: discord.Interaction):
        type_id = self.values[0]
        ttype = self.panel["ticket_types"][type_id]
        embed = discord.Embed(
            title=f"Ticket Type: {ttype.get('name')}",
            description=(
                f"**Emoji:** {ttype.get('emoji') or 'None'}\n"
                f"**Style:** {ttype.get('style')}\n"
                f"**Staff Roles:** {len(ttype.get('ticket_roles', []))}\n"
                f"**Modal Questions:** {len(ttype.get('modal_questions', []))}"
            ),
            color=discord.Color.blurple()
        )
        view = TicketTypeEditView(self.panel_name, self.guild_id, type_id, ttype)
        await interaction.response.send_message(embed=embed, view=view, ephemeral=True)


class TicketTypeEditView(discord.ui.View):
    def __init__(self, panel_name: str, guild_id: int, type_id: str, ticket_type: dict):
        super().__init__(timeout=300)
        self.panel_name = panel_name
        self.guild_id = guild_id
        self.type_id = type_id
        self.ticket_type = ticket_type

    @discord.ui.button(label="Edit Staff Roles", style=discord.ButtonStyle.blurple, emoji="👥")
    async def edit_roles(self, interaction: discord.Interaction, button: discord.ui.Button):
        view = discord.ui.View(timeout=120)
        view.add_item(TicketTypeRoleSelect(self.panel_name, self.guild_id, self.type_id))
        await interaction.response.send_message(
            "Select staff roles for this ticket type.\n> **Tip:** Only add moderator roles.",
            view=view, ephemeral=True
        )

    @discord.ui.button(label="Edit Category", style=discord.ButtonStyle.blurple, emoji="📁")
    async def edit_category(self, interaction: discord.Interaction, button: discord.ui.Button):
        view = discord.ui.View(timeout=120)
        view.add_item(TicketTypeCategorySelect(self.panel_name, self.guild_id, self.type_id))
        await interaction.response.send_message("Select category override:", view=view, ephemeral=True)


def build_panel_preview(member: discord.Member, message_data: dict):
    parsed = parse_ticket_placeholders(copy.deepcopy(message_data), member)
    content = parsed.get("content") or None
    embeds = build_embeds_from_data(parsed.get("embeds", []))
    embeds = apply_button_author(embeds, parsed.get("buttons", []))
    return content, embeds


def register_persistent_views(bot: discord.Client):
    data = load_tickets()
    for gid, gdata in data.get("guilds", {}).items():
        for panel_name, panel in gdata.get("panels", {}).items():
            msg = panel.get("message_data") or DEFAULT_PANEL_MESSAGE
            buttons = msg.get("buttons", [])
            if buttons:
                bot.add_view(PanelPersistentView(int(gid), panel_name, buttons))
        for ch_id, ticket in gdata.get("active_tickets", {}).items():
            claimed = ticket.get("claimed_by") is not None
            bot.add_view(TicketControlView(int(ch_id), claimed=claimed))
