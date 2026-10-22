# back

discord server backup bot. stores full server snapshots (roles, channels, categories, permissions, members, emojis, stickers, icon, banner) in supabase storage.

per-backup ids, monochrome ui, components v2 only, lowercase, no emojis.

## commands

| command | permission | description |
|---|---|---|
| `/avatar [image] [url]` | manage server | set this bot's per-server avatar |
| `/banner [image] [url]` | manage server | set this bot's per-server banner |
| `/onlinestatus <status>` | manage server | set presence (global - discord does not support per-server presence) |
| `/backup` | administrator | snapshot this server to supabase and return a backup id |
| `/restore` | administrator | pick from this server's backups and restore |
| `/load` | administrator | pick from any server you administer and load into this one |

## how backups are identified

every `/backup` call generates a fresh 12-char hex **backup id** and uploads `{id}.json`.
an `_index.json` maps each id to its source guild, creator, timestamp and size.
this means a single guild can hold unlimited backups.

## setup

### 1. discord developer portal
1. create an application -> bot -> copy the token
2. enable **server members intent**
3. invite with scopes `bot applications.commands` and permissions **administrator**

### 2. supabase
1. create a project -> copy **project url** and **service role key**
2. create a private storage bucket named `discord-backups`
3. (no other config needed)

### 3. local
```bash
cp .env.example .env
# edit .env
pip install -r requirements.txt
python bot.py
```

### 4. deploy on bot-hosting.net
1. push this repo to github
2. create a new server -> discord.py -> connect your repo
3. add these secrets in their panel (do **not** commit them):
   - `DISCORD_TOKEN`
   - `SUPABASE_URL`
   - `SUPABASE_KEY`
   - `SUPABASE_BUCKET` (optional, defaults to `discord-backups`)
4. start command: `python bot.py`

slash commands sync on first boot.

## notes

- **`/onlinestatus` is global** - discord has no per-server presence. preference is stored in `_config.json` and reapplied on restart.
- **`/avatar` and `/banner` are per-server** - handled natively by discord; nothing is stored.
- **restore is merge-style** - missing items are created, nothing is deleted. safe to run repeatedly and safe for `/load`.
- **backup ids are independent of guild ids** - a server can hold unlimited backups; `/restore` filters by the current guild, `/load` filters by admin access on the source guild.
- **binary assets** (emoji/sticker/icon images) are stored as cdn urls only, not raw bytes.
- **select menus show up to 25 entries** - the 25 newest per filter.
- **rate limits** - restores include small sleeps between creations; large servers take a minute or two.

## license
mit
