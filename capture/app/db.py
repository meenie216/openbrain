import json
import os

import asyncpg

_pool: asyncpg.Pool | None = None


async def get_pool() -> asyncpg.Pool:
    global _pool
    if _pool is None:
        _pool = await asyncpg.create_pool(
            user=os.environ["POSTGRES_USER"],
            password=os.environ["POSTGRES_PASSWORD"],
            database=os.environ["POSTGRES_DB"],
            host=os.environ.get("POSTGRES_HOST", "postgres"),
            port=5432,
        )
    return _pool


async def insert_thought(raw_text: str, embedding: list[float], metadata: dict, source: str) -> dict:
    pool = await get_pool()
    embedding_literal = "[" + ",".join(str(x) for x in embedding) + "]"
    row = await pool.fetchrow(
        """
        INSERT INTO thoughts (raw_text, embedding, metadata, source)
        VALUES ($1, $2::vector, $3::jsonb, $4)
        RETURNING id, raw_text, metadata, source, created_at
        """,
        raw_text,
        embedding_literal,
        json.dumps(metadata),
        source,
    )
    return dict(row)
