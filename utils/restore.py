import asyncio
import aiohttp
import discord


def _overwrites_from_data(guild: discord.Guild, data: list[dict]) -> dict:
    result = {}
    for ow in data:
        if ow["type"] == "role":
            target = guild.get_role(ow["id"])
        else:
            target = guild.get_member(ow["id"])
        if target is None:
            continue
        result[target] = discord.PermissionOverwrite.from_pair(
            discord.Permissions(ow["allow"]),
            discord.Permissions(ow["deny"]),
        )
    return result


async def restore_guild(guild: discord.Guild, backup: dict) -> list[str]:
    log: list[str] = []
    role_map: dict[int, discord.Role] = {}

    for role_data in backup["roles"]:
        if role_data["name"] == "@everyone":
            everyone = guild.default_role
            try:
                await everyone.edit(permissions=discord.Permissions(role_data["permissions"]))
                log.append("updated @everyone permissions")
            except Exception as e:
                log.append(f"@everyone update failed: {e}")
            role_map[role_data["id"]] = everyone

    for role_data in sorted(backup["roles"], key=lambda r: r["position"]):
        if role_data["name"] == "@everyone" or role_data["managed"]:
            continue
        existing = discord.utils.get(guild.roles, name=role_data["name"])
        if existing:
            role_map[role_data["id"]] = existing
            continue
        try:
            new_role = await guild.create_role(
                name=role_data["name"],
                colour=discord.Colour(role_data["color"]),
                permissions=discord.Permissions(role_data["permissions"]),
                hoist=role_data["hoist"],
                mentionable=role_data["mentionable"],
                reason="backup restore",
            )
            role_map[role_data["id"]] = new_role
            log.append(f"created role {new_role.name}")
            await asyncio.sleep(0.2)
        except Exception as e:
            log.append(f"role {role_data['name']} failed: {e}")

    category_map: dict[int, discord.CategoryChannel] = {}
    for cat_data in sorted(backup["categories"], key=lambda c: c["position"]):
        existing = discord.utils.get(guild.categories, name=cat_data["name"])
        if existing:
            category_map[cat_data["id"]] = existing
            continue
        try:
            new_cat = await guild.create_category(
                name=cat_data["name"],
                overwrites=_overwrites_from_data(guild, cat_data["permission_overwrites"]),
                reason="backup restore",
            )
            category_map[cat_data["id"]] = new_cat
            log.append(f"created category {new_cat.name}")
            await asyncio.sleep(0.2)
        except Exception as e:
            log.append(f"category {cat_data['name']} failed: {e}")

    for ch_data in sorted(backup["channels"], key=lambda c: c["position"]):
        category = category_map.get(ch_data.get("category_id"))
        ctype = ch_data["type"].lower()
        try:
            if "text" in ctype:
                if discord.utils.get(guild.text_channels, name=ch_data["name"]):
                    continue
                await guild.create_text_channel(
                    name=ch_data["name"],
                    category=category,
                    topic=ch_data.get("topic"),
                    nsfw=ch_data.get("nsfw", False),
                    slowmode_delay=ch_data.get("slowmode_delay", 0),
                    overwrites=_overwrites_from_data(guild, ch_data["permission_overwrites"]),
                    reason="backup restore",
                )
            elif "voice" in ctype:
                if discord.utils.get(guild.voice_channels, name=ch_data["name"]):
                    continue
                await guild.create_voice_channel(
                    name=ch_data["name"],
                    category=category,
                    bitrate=ch_data.get("bitrate", 64000),
                    user_limit=ch_data.get("user_limit", 0),
                    overwrites=_overwrites_from_data(guild, ch_data["permission_overwrites"]),
                    reason="backup restore",
                )
            log.append(f"created channel {ch_data['name']}")
            await asyncio.sleep(0.2)
        except Exception as e:
            log.append(f"channel {ch_data['name']} failed: {e}")

    for emoji_data in backup["emojis"]:
        if discord.utils.get(guild.emojis, name=emoji_data["name"]):
            continue
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(emoji_data["url"]) as resp:
                    image = await resp.read()
            await guild.create_custom_emoji(
                name=emoji_data["name"], image=image, reason="backup restore"
            )
            log.append(f"restored emoji {emoji_data['name']}")
            await asyncio.sleep(0.3)
        except Exception as e:
            log.append(f"emoji {emoji_data['name']} failed: {e}")

    for mdata in backup["members"]:
        member = guild.get_member(mdata["id"])
        if member is None:
            continue
        roles_to_add = [
            role_map[rid]
            for rid in mdata["roles"]
            if rid in role_map and not role_map[rid].managed
        ]
        missing = [r for r in roles_to_add if r not in member.roles]
        if not missing:
            continue
        try:
            await member.add_roles(*missing, reason="backup restore")
            await asyncio.sleep(0.2)
        except Exception:
            pass

    return log
