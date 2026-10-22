from supabase import create_client, Client

from config import SUPABASE_URL, SUPABASE_KEY, SUPABASE_BUCKET

supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)


# ---------------------------------------------------------------------------
# backup json blobs (storage)
# ---------------------------------------------------------------------------
def upload_backup(backup_id: str, data: bytes) -> None:
    supabase.storage.from_(SUPABASE_BUCKET).upload(
        path=f"{backup_id}.json",
        file=data,
        file_options={"content-type": "application/json", "upsert": "true"},
    )


def download_backup(backup_id: str) -> bytes:
    return supabase.storage.from_(SUPABASE_BUCKET).download(f"{backup_id}.json")


# ---------------------------------------------------------------------------
# backup metadata (table)
# ---------------------------------------------------------------------------
def register_backup(
    backup_id: str,
    guild_id: int,
    guild_name: str,
    user_id: int,
    size: int,
) -> None:
    supabase.table("backups").insert({
        "id": backup_id,
        "guild_id": guild_id,
        "guild_name": guild_name,
        "user_id": user_id,
        "size": size,
    }).execute()


# alias created_at -> timestamp so cogs/backup.py needs no changes
_SELECT = "id, guild_id, guild_name, user_id, size, timestamp:created_at"


def list_guild_backups(guild_id: int) -> list[tuple[str, dict]]:
    rows = (
        supabase.table("backups")
        .select(_SELECT)
        .eq("guild_id", guild_id)
        .order("created_at", desc=True)
        .execute()
        .data
    )
    return [(r["id"], r) for r in rows]


def list_all_backups() -> list[tuple[str, dict]]:
    rows = (
        supabase.table("backups")
        .select(_SELECT)
        .order("created_at", desc=True)
        .execute()
        .data
    )
    return [(r["id"], r) for r in rows]


# ---------------------------------------------------------------------------
# settings (table)
# ---------------------------------------------------------------------------
def load_settings() -> dict:
    try:
        rows = supabase.table("bot_config").select("key, value").execute().data
        return {r["key"]: r["value"] for r in rows}
    except Exception:
        return {}


def save_settings(updates: dict) -> None:
    for key, value in updates.items():
        supabase.rpc("set_config", {"p_key": key, "p_value": value}).execute()
