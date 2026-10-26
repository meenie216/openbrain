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


async def semantic_search(
    embedding: list[float], limit: int, scope: str | None = None, include_global: bool = True
) -> list[dict]:
    """scope=None searches everything (the pre-scope behaviour). scope=X
    restricts to that project plus global (scope IS NULL) rows, unless
    include_global is False."""
    pool = await get_pool()
    embedding_literal = "[" + ",".join(str(x) for x in embedding) + "]"
    rows = await pool.fetch(
        """
        SELECT id, raw_text, metadata, source, scope, kind, created_at,
               1 - (embedding <=> $1::vector) AS similarity
        FROM thoughts
        WHERE $3::text IS NULL OR scope = $3 OR ($4 AND scope IS NULL)
        ORDER BY embedding <=> $1::vector
        LIMIT $2
        """,
        embedding_literal,
        limit,
        scope,
        include_global,
    )
    return [dict(r) for r in rows]


async def list_recent(limit: int, scope: str | None = None, include_global: bool = True) -> list[dict]:
    pool = await get_pool()
    rows = await pool.fetch(
        """
        SELECT id, raw_text, metadata, source, scope, kind, created_at
        FROM thoughts
        WHERE $2::text IS NULL OR scope = $2 OR ($3 AND scope IS NULL)
        ORDER BY created_at DESC
        LIMIT $1
        """,
        limit,
        scope,
        include_global,
    )
    return [dict(r) for r in rows]


async def get_rules(scope: str | None = None) -> list[dict]:
    """Standing rules: global (scope IS NULL) plus this scope's, if given.

    Global rules first, then project rules, each group newest-last so a
    later rule (added to override an earlier one) reads as the final word.
    """
    pool = await get_pool()
    rows = await pool.fetch(
        """
        SELECT id, raw_text, metadata, source, scope, kind, created_at
        FROM thoughts
        WHERE kind = 'rule' AND (scope IS NULL OR scope = $1::text)
        ORDER BY (scope IS NOT NULL), created_at ASC
        """,
        scope,
    )
    return [dict(r) for r in rows]


async def insert_thought(
    raw_text: str,
    embedding: list[float],
    metadata: dict,
    source: str,
    scope: str | None = None,
    kind: str = "thought",
) -> dict:
    pool = await get_pool()
    embedding_literal = "[" + ",".join(str(x) for x in embedding) + "]"
    row = await pool.fetchrow(
        """
        INSERT INTO thoughts (raw_text, embedding, metadata, source, scope, kind)
        VALUES ($1, $2::vector, $3::jsonb, $4, $5, $6)
        RETURNING id, raw_text, metadata, source, scope, kind, created_at
        """,
        raw_text,
        embedding_literal,
        json.dumps(metadata),
        source,
        scope,
        kind,
    )
    return dict(row)


async def delete_thought(thought_id: str) -> bool:
    pool = await get_pool()
    result = await pool.execute("DELETE FROM thoughts WHERE id = $1::uuid", thought_id)
    return result == "DELETE 1"


async def update_thought(
    thought_id: str,
    *,
    raw_text: str | None = None,
    embedding: list[float] | None = None,
    metadata: dict | None = None,
    scope: str | None = None,
    set_scope: bool = False,
    kind: str | None = None,
) -> dict | None:
    """Update only the fields given. scope needs set_scope because None is a
    real value (global). Text, embedding and metadata change together — the
    caller re-derives the latter two when the text changes."""
    pool = await get_pool()
    embedding_literal = None if embedding is None else "[" + ",".join(str(x) for x in embedding) + "]"
    row = await pool.fetchrow(
        """
        UPDATE thoughts SET
            raw_text  = COALESCE($2, raw_text),
            embedding = COALESCE($3::vector, embedding),
            metadata  = COALESCE($4::jsonb, metadata),
            scope     = CASE WHEN $5 THEN $6 ELSE scope END,
            kind      = COALESCE($7, kind)
        WHERE id = $1::uuid
        RETURNING id, raw_text, metadata, source, scope, kind, created_at
        """,
        thought_id,
        raw_text,
        embedding_literal,
        None if metadata is None else json.dumps(metadata),
        set_scope,
        scope,
        kind,
    )
    return None if row is None else dict(row)


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
