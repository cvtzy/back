import json
import uuid
from datetime import datetime

import discord
from discord import app_commands
from discord.ext import commands

from utils.backup_builder import build_guild_backup
from utils.restore import restore_guild
from utils.supabase_client import (
    download_backup,
    list_all_backups,
    list_guild_backups,
    register_backup,
    upload_backup,
)

BLACK = discord.Colour(0x000000)


# ---------------------------------------------------------------------------
# helpers
# ---------------------------------------------------------------------------
def _new_backup_id() -> str:
    return uuid.uuid4().hex[:12]


def _friendly(ts: str) -> str:
    try:
        dt = datetime.fromisoformat(ts)
        return dt.strftime("%Y-%m-%d %H:%M utc").lower()
    except Exception:
        return ts


def _short(text: str, limit: int = 60) -> str:
    return text if len(text) <= limit else text[: limit - 1] + "…"


# ---------------------------------------------------------------------------
# confirm view (components v2)
# ---------------------------------------------------------------------------
class _ConfirmButton(discord.ui.Button):
    def __init__(self, *, label: str, value: bool):
        super().__init__(label=label, style=discord.ButtonStyle.secondary)
        self.value = value

    async def callback(self, interaction: discord.Interaction):
        self.view.value = self.value
        await interaction.response.defer()
        self.view.stop()


class ConfirmView(discord.ui.LayoutView):
    def __init__(self, text: str):
        super().__init__(timeout=60)
        self.value: bool | None = None

        container = discord.ui.Container(accent_colour=BLACK)
        container.add_item(discord.ui.TextDisplay(text))
        container.add_item(discord.ui.Separator())

        row = discord.ui.ActionRow()
        row.add_item(_ConfirmButton(label="confirm", value=True))
        row.add_item(_ConfirmButton(label="cancel", value=False))
        container.add_item(row)

        self.add_item(container)


# ---------------------------------------------------------------------------
# backup picker (components v2)
# ---------------------------------------------------------------------------
class _BackupSelect(discord.ui.Select):
    def __init__(self, *, options: list[discord.SelectOption], mode: str):
        super().__init__(placeholder="choose a backup", options=options)
        self.mode = mode

    async def callback(self, interaction: discord.Interaction):
        backup_id = self.values[0]
        guild = interaction.guild
        mode = self.mode

        confirm = ConfirmView(
            f"{mode} backup {backup_id} into {guild.name.lower()}.\n"
            f"this will add any missing roles, categories, channels, "
            f"emojis and reapply member roles. existing items are never deleted."
        )
        await interaction.response.send_message(view=confirm, ephemeral=True)
        await confirm.wait()

        if not confirm.value:
            await interaction.edit_original_response(
                view=_flat_layout("cancelled"), content=None
            )
            return

        await interaction.edit_original_response(
            view=_flat_layout(f"{mode} in progress..."), content=None
        )

        try:
            raw = download_backup(backup_id)
            data = json.loads(raw)
        except Exception as e:
            await interaction.edit_original_response(
                view=_flat_layout(f"could not download backup: {e}"), content=None
            )
            return

        try:
            log = await restore_guild(guild, data)
        except Exception as e:
            await interaction.edit_original_response(
                view=_flat_layout(f"{mode} crashed: {e}"), content=None
            )
            return

        lines = "\n".join(f"- {line}" for line in log[:20])
        if len(log) > 20:
            lines += f"\n- ...and {len(log) - 20} more"

        body = (
            f"{mode} finished in {guild.name.lower()}\n\n"
            f"{lines if lines else 'nothing to do'}"
        )
        await interaction.edit_original_response(
            view=_flat_layout(body), content=None
        )


class BackupPicker(discord.ui.LayoutView):
    def __init__(self, *, options: list[discord.SelectOption], mode: str, text: str):
        super().__init__(timeout=180)

        container = discord.ui.Container(accent_colour=BLACK)
        container.add_item(discord.ui.TextDisplay(text))
        container.add_item(discord.ui.Separator())

        row = discord.ui.ActionRow()
        row.add_item(_BackupSelect(options=options, mode=mode))
        container.add_item(row)

        self.add_item(container)


def _flat_layout(text: str) -> discord.ui.LayoutView:
    view = discord.ui.LayoutView(timeout=60)
    container = discord.ui.Container(accent_colour=BLACK)
    container.add_item(discord.ui.TextDisplay(text))
    view.add_item(container)
    return view


# ---------------------------------------------------------------------------
# cog
# ---------------------------------------------------------------------------
class Backup(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot

    # ---------------------------------------------------------------- /backup
    @app_commands.command(name="backup", description="back up this server to supabase")
    @app_commands.checks.has_permissions(administrator=True)
    async def backup(self, interaction: discord.Interaction):
        await interaction.response.defer(ephemeral=True)
        guild = interaction.guild

        try:
            data = await build_guild_backup(guild)
            payload = json.dumps(data, indent=2, ensure_ascii=False).encode("utf-8")
            backup_id = _new_backup_id()

            upload_backup(backup_id, payload)
            register_backup(
                backup_id=backup_id,
                guild_id=guild.id,
                guild_name=guild.name,
                user_id=interaction.user.id,
                size=len(payload),
            )

            body = (
                f"backup complete\n"
                f"id: {backup_id}\n"
                f"size: {len(payload):,} bytes\n"
                f"restore later with /restore or /load"
            )
            await interaction.followup.send(
                view=_flat_layout(body), ephemeral=True
            )
        except Exception as e:
            await interaction.followup.send(
                view=_flat_layout(f"backup failed: {e}"), ephemeral=True
            )

    # --------------------------------------------------------------- /restore
    @app_commands.command(name="restore", description="restore one of this server's backups")
    @app_commands.checks.has_permissions(administrator=True)
    async def restore(self, interaction: discord.Interaction):
        await interaction.response.defer(ephemeral=True)

        items = list_guild_backups(interaction.guild.id)
        if not items:
            await interaction.followup.send(
                view=_flat_layout("no backups found for this server. run /backup first."),
                ephemeral=True,
            )
            return

        options = [
            discord.SelectOption(
                label=_friendly(meta.get("timestamp", ""))[:100],
                value=bid,
                description=f"id {bid} | {meta.get('size', 0):,} bytes"[:100],
            )
            for bid, meta in items[:25]
        ]

        picker = BackupPicker(
            options=options,
            mode="restore",
            text=(
                f"select a backup to restore into {interaction.guild.name.lower()}\n"
                f"{len(items)} backup(s) found"
            ),
        )
        await interaction.followup.send(view=picker, ephemeral=True)

    # ------------------------------------------------------------------ /load
    @app_commands.command(
        name="load",
        description="load a backup from any server you administer into this server",
    )
    @app_commands.checks.has_permissions(administrator=True)
    async def load(self, interaction: discord.Interaction):
        await interaction.response.defer(ephemeral=True)

        all_items = list_all_backups()
        if not all_items:
            await interaction.followup.send(
                view=_flat_layout("no backups exist in supabase yet."), ephemeral=True
            )
            return

        accessible: list[tuple[str, dict]] = []
        seen_guilds: dict[int, discord.Guild | None] = {}

        for bid, meta in all_items:
            gid = meta.get("guild_id")
            if gid is None:
                continue

            if gid not in seen_guilds:
                seen_guilds[gid] = self.bot.get_guild(gid)
            source = seen_guilds[gid]

            if gid == interaction.guild.id:
                accessible.append((bid, meta))
                continue

            if source is None:
                continue
            member = source.get_member(interaction.user.id)
            if member is None or not member.guild_permissions.administrator:
                continue

            accessible.append((bid, meta))

        if not accessible:
            await interaction.followup.send(
                view=_flat_layout(
                    "no accessible backups. you must be an administrator in the "
                    "source server and the bot must still be in it."
                ),
                ephemeral=True,
            )
            return

        accessible.sort(key=lambda x: x[1].get("timestamp", ""), reverse=True)

        options = []
        for bid, meta in accessible[:25]:
            gname = meta.get("guild_name", "unknown")
            label = _short(f"{bid} | {gname}", 100)
            description = _short(
                f"{_friendly(meta.get('timestamp', ''))} | "
                f"{meta.get('size', 0):,} bytes",
                100,
            )
            options.append(
                discord.SelectOption(label=label, value=bid, description=description)
            )

        picker = BackupPicker(
            options=options,
            mode="load",
            text=(
                f"select a backup to load into {interaction.guild.name.lower()}\n"
                f"{len(accessible)} accessible backup(s)"
            ),
        )
        await interaction.followup.send(view=picker, ephemeral=True)

    # ---------------------------------------------------------- error handler
    async def cog_app_command_error(self, interaction: discord.Interaction, error):
        msg = (
            "you need administrator permission for this command."
            if isinstance(error, app_commands.MissingPermissions)
            else f"an error occurred: {error}"
        )
        if interaction.response.is_done():
            await interaction.followup.send(view=_flat_layout(msg), ephemeral=True)
        else:
            await interaction.response.send_message(
                view=_flat_layout(msg), ephemeral=True
            )


async def setup(bot: commands.Bot):
    await bot.add_cog(Backup(bot))
