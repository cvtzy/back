import os
from dotenv import load_dotenv

load_dotenv()

BOT_NAME = "back"

DISCORD_TOKEN = os.getenv("DISCORD_TOKEN")
SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_KEY")
SUPABASE_BUCKET = os.getenv("SUPABASE_BUCKET", "discord-backups")

_missing = [k for k, v in {
    "DISCORD_TOKEN": DISCORD_TOKEN,
    "SUPABASE_URL": SUPABASE_URL,
    "SUPABASE_KEY": SUPABASE_KEY,
}.items() if not v]

if _missing:
    raise RuntimeError(f"missing required environment variables: {', '.join(_missing)}")
