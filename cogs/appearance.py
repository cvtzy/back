import discord
from discord import app_commands
from discord.ext import commands

from utils.images import fetch_image_bytes
from utils.supabase_client import save_settings

BLACK = discord.Colour(0x000000)


def _layout(text: str) -> discord.ui.LayoutView:
    view = discord.ui.LayoutView(timeout=60)
    container = discord.ui.Container(accent_colour=BLACK)
    container.add_item(discord.ui.TextDisplay(text))
    view.add_item(container)
    return view


class Appearance(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot

    @app_commands.command(name="avatar", description="set this bot's avatar for this server")
    @app_commands.describe(image="upload an image", url="or paste an image url")
    @app_commands.checks.has_permissions(manage_guild=True)
    async def avatar(
        self,
        interaction: discord.Interaction,
        image: discord.Attachment | None = None,
        url: str | None = None,
    ):
        await interaction.response.defer(ephemeral=True)
        try:
            data = await fetch_image_bytes(image, url)
            me = interaction.guild.me or await interaction.guild.fetch_member(self.bot.user.id)
            await me.edit(avatar=data, reason=f"per-server avatar by {interaction.user}")
            await interaction.followup.send(
                view=_layout("server avatar updated"), ephemeral=True
            )
        except Exception as e:
            await interaction.followup.send(
                view=_layout(f"failed: {e}"), ephemeral=True
            )

    @app_commands.command(name="banner", description="set this bot's banner for this server")
    @app_commands.describe(image="upload an image", url="or paste an image url")
    @app_commands.checks.has_permissions(manage_guild=True)
    async def banner(
        self,
        interaction: discord.Interaction,
        image: discord.Attachment | None = None,
        url: str | None = None,
    ):
        await interaction.response.defer(ephemeral=True)
        try:
            data = await fetch_image_bytes(image, url)
            me = interaction.guild.me or await interaction.guild.fetch_member(self.bot.user.id)
            await me.edit(banner=data, reason=f"per-server banner by {interaction.user}")
            await interaction.followup.send(
                view=_layout("server banner updated"), ephemeral=True
            )
        except Exception as e:
            await interaction.followup.send(
                view=_layout(f"failed: {e}"), ephemeral=True
            )

    @app_commands.command(name="onlinestatus", description="set the bot's presence (global)")
    @app_commands.describe(status="new presence")
    @app_commands.choices(status=[
        app_commands.Choice(name="online", value="online"),
        app_commands.Choice(name="idle", value="idle"),
        app_commands.Choice(name="do not disturb", value="dnd"),
        app_commands.Choice(name="invisible", value="invisible"),
    ])
    @app_commands.checks.has_permissions(manage_guild=True)
    async def onlinestatus(
        self, interaction: discord.Interaction, status: app_commands.Choice[str]
    ):
        await interaction.response.defer(ephemeral=True)
        await self.bot.change_presence(status=discord.Status(status.value))
        try:
            save_settings({"status": status.value})
        except Exception:
            pass
        await interaction.followup.send(
            view=_layout(
                f"status set to {status.name} (global - applies to all servers, "
                f"not per-server; discord does not support per-server presence)"
            ),
            ephemeral=True,
        )

    async def cog_app_command_error(self, interaction: discord.Interaction, error):
        msg = (
            "you need manage server permission for this command."
            if isinstance(error, app_commands.MissingPermissions)
            else f"an error occurred: {error}"
        )
        if interaction.response.is_done():
            await interaction.followup.send(view=_layout(msg), ephemeral=True)
        else:
            await interaction.response.send_message(view=_layout(msg), ephemeral=True)


async def setup(bot: commands.Bot):
    await bot.add_cog(Appearance(bot))
