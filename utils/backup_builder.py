import discord
from datetime import datetime, timezone


def _serialize_overwrites(overwrites: dict) -> list:
    out = []
    for target, ow in overwrites.items():
        out.append({
            "id": target.id,
            "type": "role" if isinstance(target, discord.Role) else "member",
            "allow": ow.allow.value,
            "deny": ow.deny.value,
        })
    return out


async def build_guild_backup(guild: discord.Guild) -> dict:
    members = [m async for m in guild.fetch_members(limit=None)]

    roles = [{
        "id": r.id,
        "name": r.name,
        "color": r.color.value,
        "permissions": r.permissions.value,
        "hoist": r.hoist,
        "mentionable": r.mentionable,
        "position": r.position,
        "managed": r.managed,
        "icon": r.icon.url if r.icon else None,
    } for r in sorted(guild.roles, key=lambda x: x.position)]

    categories = [{
        "id": c.id,
        "name": c.name,
        "position": c.position,
        "permission_overwrites": _serialize_overwrites(c.overwrites),
    } for c in guild.categories]

    channels = []
    for ch in guild.channels:
        if isinstance(ch, discord.CategoryChannel):
            continue
        data = {
            "id": ch.id,
            "name": ch.name,
            "type": str(ch.type),
            "position": ch.position,
            "category_id": ch.category_id,
            "permission_overwrites": _serialize_overwrites(ch.overwrites),
        }
        if isinstance(ch, discord.TextChannel):
            data.update({
                "topic": ch.topic,
                "nsfw": ch.nsfw,
                "slowmode_delay": ch.slowmode_delay,
            })
        elif isinstance(ch, discord.VoiceChannel):
            data.update({
                "bitrate": ch.bitrate,
                "user_limit": ch.user_limit,
            })
        channels.append(data)

    emojis = [{
        "id": e.id, "name": e.name, "animated": e.animated, "url": str(e.url),
    } for e in guild.emojis]

    stickers = [{
        "id": s.id, "name": s.name, "description": s.description,
        "url": str(s.url), "tags": s.tags,
    } for s in guild.stickers]

    members_data = [{
        "id": m.id,
        "name": str(m),
        "display_name": m.display_name,
        "roles": [r.id for r in m.roles if r.name != "@everyone"],
        "joined_at": m.joined_at.isoformat() if m.joined_at else None,
        "nick": m.nick,
        "bot": m.bot,
    } for m in members]

    return {
        "backup_timestamp": datetime.now(timezone.utc).isoformat(),
        "guild": {
            "id": guild.id,
            "name": guild.name,
            "description": guild.description,
            "icon_url": guild.icon.url if guild.icon else None,
            "banner_url": guild.banner.url if guild.banner else None,
            "splash_url": guild.splash.url if guild.splash else None,
            "verification_level": str(guild.verification_level),
            "default_notifications": str(guild.default_notifications),
            "explicit_content_filter": str(guild.explicit_content_filter),
            "owner_id": guild.owner_id,
        },
        "roles": roles,
        "categories": categories,
        "channels": channels,
        "emojis": emojis,
        "stickers": stickers,
        "members": members_data,
    }
