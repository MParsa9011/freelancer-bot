import aiosqlite
from pathlib import Path

DB_PATH = Path(__file__).parent / "bot_data.db"


async def init_db() -> None:
    async with aiosqlite.connect(DB_PATH) as db:
        await db.executescript("""
            CREATE TABLE IF NOT EXISTS users (
                chat_id INTEGER PRIMARY KEY,
                interval INTEGER NOT NULL DEFAULT 5
            );

            CREATE TABLE IF NOT EXISTS skills (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                chat_id INTEGER NOT NULL,
                name TEXT NOT NULL,
                slug TEXT NOT NULL,
                UNIQUE(chat_id, slug)
            );

            CREATE TABLE IF NOT EXISTS seen_projects (
                chat_id INTEGER NOT NULL,
                project_id TEXT NOT NULL,
                PRIMARY KEY (chat_id, project_id)
            );
        """)
        await db.commit()


async def upsert_user(chat_id: int, interval: int | None = None) -> None:
    async with aiosqlite.connect(DB_PATH) as db:
        if interval is None:
            await db.execute(
                "INSERT OR IGNORE INTO users (chat_id) VALUES (?)", (chat_id,)
            )
        else:
            await db.execute(
                "INSERT INTO users (chat_id, interval) VALUES (?, ?)"
                " ON CONFLICT(chat_id) DO UPDATE SET interval = excluded.interval",
                (chat_id, interval),
            )
        await db.commit()


async def get_interval(chat_id: int) -> int:
    async with aiosqlite.connect(DB_PATH) as db:
        async with db.execute(
            "SELECT interval FROM users WHERE chat_id = ?", (chat_id,)
        ) as cur:
            row = await cur.fetchone()
            return row[0] if row else 5


async def add_skill(chat_id: int, name: str, slug: str) -> bool:
    """Returns True if inserted, False if already exists."""
    async with aiosqlite.connect(DB_PATH) as db:
        try:
            await db.execute(
                "INSERT INTO skills (chat_id, name, slug) VALUES (?, ?, ?)",
                (chat_id, name, slug),
            )
            await db.commit()
            return True
        except aiosqlite.IntegrityError:
            return False


async def remove_skill(chat_id: int, name: str) -> bool:
    """Returns True if deleted."""
    async with aiosqlite.connect(DB_PATH) as db:
        cur = await db.execute(
            "DELETE FROM skills WHERE chat_id = ? AND (name = ? OR slug = ?)",
            (chat_id, name.lower(), name.lower()),
        )
        await db.commit()
        return cur.rowcount > 0


async def get_skills(chat_id: int) -> list[tuple[str, str]]:
    """Returns list of (name, slug)."""
    async with aiosqlite.connect(DB_PATH) as db:
        async with db.execute(
            "SELECT name, slug FROM skills WHERE chat_id = ? ORDER BY name",
            (chat_id,),
        ) as cur:
            return await cur.fetchall()


async def get_all_users() -> list[int]:
    async with aiosqlite.connect(DB_PATH) as db:
        async with db.execute("SELECT chat_id FROM users") as cur:
            return [row[0] for row in await cur.fetchall()]


async def is_seen(chat_id: int, project_id: str) -> bool:
    async with aiosqlite.connect(DB_PATH) as db:
        async with db.execute(
            "SELECT 1 FROM seen_projects WHERE chat_id = ? AND project_id = ?",
            (chat_id, project_id),
        ) as cur:
            return await cur.fetchone() is not None


async def mark_seen(chat_id: int, project_id: str) -> None:
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute(
            "INSERT OR IGNORE INTO seen_projects (chat_id, project_id) VALUES (?, ?)",
            (chat_id, project_id),
        )
        await db.commit()


async def cleanup_old_seen(days: int = 30) -> None:
    """Not used yet — placeholder for future cleanup."""
    pass
