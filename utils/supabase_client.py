import json
from datetime import datetime, timezone
from supabase import create_client, Client

from config import SUPABASE_URL, SUPABASE_KEY, SUPABASE_BUCKET

supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)

_INDEX_FILE = "_index.json"
_SETTINGS_FILE = "_config.json"


# ---------------------------------------------------------------------------
# storage primitives
# ---------------------------------------------------------------------------
def _upload(file_name: str, data: bytes, content_type: str = "application/json"):
    supabase.storage.from_(SUPABASE_BUCKET).upload(
        path=file_name,
        file=data,
        file_options={"content-type": content_type, "upsert": "true"},
    )


def _download(file_name: str) -> bytes:
    return supabase.storage.from_(SUPABASE_BUCKET).download(file_name)


def _list_raw() -> list[str]:
    try:
        files = supabase.storage.from_(SUPABASE_BUCKET).list()
    except Exception:
        return []
    return [
        f["name"] for f in files
        if isinstance(f, dict)
        and f.get("name", "").endswith(".json")
        and not f["name"].startswith("_")
    ]


# ---------------------------------------------------------------------------
# public api
# ---------------------------------------------------------------------------
def upload_backup(backup_id: str, data: bytes) -> None:
    _upload(f"{backup_id}.json", data)


def download_backup(backup_id: str) -> bytes:
    return _download(f"{backup_id}.json")


def load_index() -> dict:
    try:
        return json.loads(_download(_INDEX_FILE))
    except Exception:
        return {"backups": {}}


def save_index(index: dict) -> None:
    _upload(_INDEX_FILE, json.dumps(index).encode("utf-8"))


def register_backup(backup_id: str, guild_id: int, guild_name: str, user_id: int, size: int) -> None:
    idx = load_index()
    idx.setdefault("backups", {})[backup_id] = {
        "guild_id": guild_id,
        "guild_name": guild_name,
        "user_id": user_id,
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "size": size,
    }
    save_index(idx)


def list_guild_backups(guild_id: int) -> list[tuple[str, dict]]:
    idx = load_index().get("backups", {})
    items = [(bid, meta) for bid, meta in idx.items() if meta.get("guild_id") == guild_id]
    items.sort(key=lambda x: x[1].get("timestamp", ""), reverse=True)
    return items


def list_all_backups() -> list[tuple[str, dict]]:
    idx = load_index().get("backups", {})
    items = list(idx.items())
    items.sort(key=lambda x: x[1].get("timestamp", ""), reverse=True)
    return items


def load_settings() -> dict:
    try:
        return json.loads(_download(_SETTINGS_FILE))
    except Exception:
        return {}


def save_settings(updates: dict) -> None:
    current = load_settings()
    current.update(updates)
    _upload(_SETTINGS_FILE, json.dumps(current).encode("utf-8"))
