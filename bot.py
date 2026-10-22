import asyncio
import discord
from discord.ext import commands

from config import DISCORD_TOKEN, BOT_NAME
from utils.supabase_client import load_settings

intents = discord.Intents.default()
intents.members = True
intents.message_content = True

bot = commands.Bot(command_prefix="!", intents=intents)


@bot.event
async def on_ready():
    settings = load_settings()
    if "status" in settings:
        try:
            await bot.change_presence(status=discord.Status(settings["status"]))
        except Exception:
            pass

    for cog in ("cogs.appearance", "cogs.backup"):
        try:
            await bot.load_extension(cog)
            print(f"loaded {cog}")
        except Exception as e:
            print(f"failed to load {cog}: {e}")

    try:
        synced = await bot.tree.sync()
        print(f"synced {len(synced)} slash commands")
    except Exception as e:
        print(f"command sync failed: {e}")

    print(f"{BOT_NAME} logged in as {bot.user}")


async def main():
    async with bot:
        await bot.start(DISCORD_TOKEN)


if __name__ == "__main__":
    asyncio.run(main())
