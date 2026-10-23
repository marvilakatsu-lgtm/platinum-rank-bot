import os
import aiosqlite
from levels import nivel_por_xp

SCHEMA = """
CREATE TABLE IF NOT EXISTS users (
    user_id   INTEGER PRIMARY KEY,
    xp        INTEGER NOT NULL DEFAULT 0,
    denarios  INTEGER NOT NULL DEFAULT 0
);
CREATE TABLE IF NOT EXISTS platinas (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id     INTEGER NOT NULL,
    game        TEXT NOT NULL,
    platform    TEXT NOT NULL,
    earned_at   TEXT NOT NULL,
    proof_url   TEXT NOT NULL,
    status      TEXT NOT NULL DEFAULT 'pending',   -- pending | approved | rejected
    reviewer_id INTEGER,
    created_at  TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
);
CREATE INDEX IF NOT EXISTS idx_plat_user ON platinas(user_id, status);
CREATE TABLE IF NOT EXISTS logs (
    id         INTEGER PRIMARY KEY AUTOINCREMENT,
    actor_id   INTEGER NOT NULL,
    action     TEXT NOT NULL,
    details    TEXT,
    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
);
"""


class Database:
    def __init__(self, path: str):
        self.path = path
        self.conn: aiosqlite.Connection | None = None

    async def connect(self):
        os.makedirs(os.path.dirname(self.path) or ".", exist_ok=True)
        self.conn = await aiosqlite.connect(self.path)
        self.conn.row_factory = aiosqlite.Row
        await self.conn.executescript(SCHEMA)
        await self.conn.commit()

    async def _one(self, sql, args=()):
        async with self.conn.execute(sql, args) as cur:
            return await cur.fetchone()

    async def _all(self, sql, args=()):
        async with self.conn.execute(sql, args) as cur:
            return await cur.fetchall()

    async def log(self, actor_id: int, action: str, details: str = ""):
        await self.conn.execute(
            "INSERT INTO logs(actor_id, action, details) VALUES (?,?,?)",
            (actor_id, action, details),
        )
        await self.conn.commit()

    # ---------- usuários ----------
    async def get_user(self, user_id: int):
        await self.conn.execute("INSERT OR IGNORE INTO users(user_id) VALUES (?)", (user_id,))
        await self.conn.commit()
        return await self._one("SELECT * FROM users WHERE user_id=?", (user_id,))

    async def add_reward(self, user_id: int, xp: int, denarios: int):
        """Soma XP/Denários e devolve (nível_antigo, nível_novo, xp_total)."""
        user = await self.get_user(user_id)
        antigo = nivel_por_xp(user["xp"])
        await self.conn.execute(
            "UPDATE users SET xp = xp + ?, denarios = denarios + ? WHERE user_id=?",
            (xp, denarios, user_id),
        )
        await self.conn.commit()
        novo_xp = user["xp"] + xp
        return antigo, nivel_por_xp(novo_xp), novo_xp

    async def posicao_xp(self, xp: int) -> int:
        row = await self._one("SELECT COUNT(*)+1 AS p FROM users WHERE xp > ?", (xp,))
        return row["p"]

    # ---------- platinas ----------
    async def platina_duplicada(self, user_id: int, game: str, platform: str) -> bool:
        row = await self._one(
            """SELECT 1 FROM platinas WHERE user_id=? AND lower(game)=lower(?)
               AND lower(platform)=lower(?) AND status IN ('pending','approved')""",
            (user_id, game, platform),
        )
        return row is not None

    async def criar_platina(self, user_id, game, platform, earned_at, proof_url) -> int:
        cur = await self.conn.execute(
            "INSERT INTO platinas(user_id, game, platform, earned_at, proof_url) VALUES (?,?,?,?,?)",
            (user_id, game, platform, earned_at, proof_url),
        )
        await self.conn.commit()
        return cur.lastrowid

    async def get_platina(self, platina_id: int):
        return await self._one("SELECT * FROM platinas WHERE id=?", (platina_id,))

    async def set_status(self, platina_id: int, status: str, reviewer_id: int):
        await self.conn.execute(
            "UPDATE platinas SET status=?, reviewer_id=? WHERE id=?",
            (status, reviewer_id, platina_id),
        )
        await self.conn.commit()

    async def platinas_do_usuario(self, user_id: int):
        return await self._all(
            "SELECT * FROM platinas WHERE user_id=? AND status='approved' ORDER BY earned_at DESC",
            (user_id,),
        )

    async def contar_platinas(self, user_id: int) -> int:
        row = await self._one(
            "SELECT COUNT(*) AS c FROM platinas WHERE user_id=? AND status='approved'", (user_id,)
        )
        return row["c"]

    async def posicao_platinas(self, quantidade: int) -> int:
        row = await self._one(
            """SELECT COUNT(*)+1 AS p FROM (
                 SELECT user_id, COUNT(*) AS c FROM platinas WHERE status='approved'
                 GROUP BY user_id HAVING c > ?)""",
            (quantidade,),
        )
        return row["p"]

    # ---------- rankings ----------
    async def ranking_platinas(self, limite=10):
        return await self._all(
            """SELECT user_id, COUNT(*) AS valor FROM platinas WHERE status='approved'
               GROUP BY user_id ORDER BY valor DESC LIMIT ?""",
            (limite,),
        )

    async def ranking_xp(self, limite=10):
        return await self._all(
            "SELECT user_id, xp AS valor FROM users WHERE xp > 0 ORDER BY xp DESC LIMIT ?",
            (limite,),
        )

    async def ranking_mensal(self, mes: str, limite=10):
        """mes no formato AAAA-MM, baseado na data da conquista."""
        return await self._all(
            """SELECT user_id, COUNT(*) AS valor FROM platinas
               WHERE status='approved' AND substr(earned_at,1,7)=?
               GROUP BY user_id ORDER BY valor DESC LIMIT ?""",
            (mes, limite),
        )
