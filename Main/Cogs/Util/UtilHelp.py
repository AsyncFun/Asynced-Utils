from discord.ext import commands
import discord
import GenHelp as gh
import json
from discord import app_commands
import asyncio
import Cogs.Moderation.ModHelp as mh
import re

#------------------------------------------
# Decorators
#------------------------------------------


def can_manage_roles():
    async def predicate(ctx: commands.Context):
        perms = ctx.author.guild_permissions
        if perms.administrator or perms.manage_roles or perms.manage_guild:
            return True
        
        raise commands.MissingPermissions()
    return commands.check(predicate)

async def send_membercount(interaction: discord.Interaction):
    guild = interaction.guild
    bots = 0
    humans = 0
    total = 0

    for m in guild.members:
        if m.bot:
            bots+=1
        else:
            humans+=1

        total+=1

    embed = discord.Embed(description=f"### {interaction.guild.name} Member Count:", color=discord.Color.blue())
    embed.add_field(name="Total", value=total, inline=True)
    embed.add_field(name="Humans", value=humans, inline=True)
    embed.add_field(name="Bots", value=bots, inline=True)
    embed.set_thumbnail(url=interaction.guild.icon.url)

    await interaction.response.send_message(embed=embed)


#------------------------------------------
# ROLE HELPERS
#------------------------------------------
async def send_role_response(ctx: commands.Context, embed: discord.Embed):
    interaction = ctx.interaction if ctx.interaction else mh.MessageInteractionAdapter(ctx.message)
    await interaction.response.send_message(embed=embed)

async def can_edit_role(ctx: commands.Context, role: discord.Role):
    member = ctx.author
    bot_member = ctx.guild.me

    if role >= member.top_role and ctx.guild.owner_id != member.id:
        await send_role_response(
            ctx,
            gh.fail(
                " Cannot edit role",
                "> You cannot edit a role that is higher than or equal to your highest role."
            )
        )
        return False

    if role >= bot_member.top_role:
        await send_role_response(
            ctx,
            gh.fail(
                " Cannot edit role",
                "> I cannot edit a role that is higher than or equal to my highest role."
            )
        )
        return False

    if role.managed:
        await send_role_response(
            ctx,
            gh.fail(
                " Cannot edit role",
                "> This role is managed by an integration and cannot be edited."
            )
        )
        return False

    return True

def parse_bool_value(value: str):
    value = value.lower().strip()

    if value in ["true", "t", "yes", "y", "1", "on"]:
        return True

    if value in ["false", "f", "no", "n", "0", "off"]:
        return False

    return None

def clean_emoji_name(name: str):
    cleaned = re.sub(r"[^A-Za-z0-9_]", "x", name)
    cleaned = re.sub(r"_+", "_", cleaned)
    cleaned = cleaned.strip("_")

    if not cleaned:
        cleaned = "role_icon"

    return cleaned

def get_custom_emoji_from_input(guild: discord.Guild, value: str):
    match = re.fullmatch(r"<a?:([A-Za-z0-9_]+):(\d+)>", value)

    if match:
        emoji_id = int(match.group(2))
        emoji = discord.utils.get(guild.emojis, id=emoji_id)

        if emoji is None:
            return None, "not_in_server"

        return emoji, None

    cleaned_name = clean_emoji_name(value)
    emoji = discord.utils.get(guild.emojis, name=cleaned_name)

    if emoji is None:
        return None, "not_found"

    return emoji, None


