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


async def semantic_search(embedding: list[float], limit: int) -> list[dict]:
    pool = await get_pool()
    embedding_literal = "[" + ",".join(str(x) for x in embedding) + "]"
    rows = await pool.fetch(
        """
        SELECT id, raw_text, metadata, source, created_at,
               1 - (embedding <=> $1::vector) AS similarity
        FROM thoughts
        ORDER BY embedding <=> $1::vector
        LIMIT $2
        """,
        embedding_literal,
        limit,
    )
    return [dict(r) for r in rows]


async def list_recent(limit: int) -> list[dict]:
    pool = await get_pool()
    rows = await pool.fetch(
        """
        SELECT id, raw_text, metadata, source, created_at
        FROM thoughts
        ORDER BY created_at DESC
        LIMIT $1
        """,
        limit,
    )
    return [dict(r) for r in rows]


async def stats() -> dict:
    pool = await get_pool()
    total = await pool.fetchval("SELECT count(*) FROM thoughts")
    by_type = await pool.fetch(
        """
        SELECT metadata->>'type' AS type, count(*) AS count
        FROM thoughts
        GROUP BY metadata->>'type'
        ORDER BY count DESC
        """
    )
    by_day = await pool.fetch(
        """
        SELECT date_trunc('day', created_at) AS day, count(*) AS count
        FROM thoughts
        WHERE created_at > now() - interval '7 days'
        GROUP BY day
        ORDER BY day
        """
    )
    top_topics = await pool.fetch(
        """
        SELECT topic, count(*) AS count
        FROM thoughts, jsonb_array_elements_text(metadata->'topics') AS topic
        GROUP BY topic
        ORDER BY count DESC
        LIMIT 10
        """
    )
    top_people = await pool.fetch(
        """
        SELECT person, count(*) AS count
        FROM thoughts, jsonb_array_elements_text(metadata->'people') AS person
        GROUP BY person
        ORDER BY count DESC
        LIMIT 10
        """
    )
    return {
        "total_thoughts": total,
        "by_type": {r["type"]: r["count"] for r in by_type},
        "captures_last_7_days": {str(r["day"].date()): r["count"] for r in by_day},
        "top_topics": {r["topic"]: r["count"] for r in top_topics},
        "top_people": {r["person"]: r["count"] for r in top_people},
    }
