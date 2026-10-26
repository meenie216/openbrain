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


async def get_rules(scopes: list[str] | None = None) -> list[dict]:
    """Standing rules: global (scope IS NULL) plus those of each given scope.

    Global first, then the scopes in the order given (general to specific),
    each newest-last so a later rule (added to override an earlier one)
    reads as the final word.
    """
    pool = await get_pool()
    rows = await pool.fetch(
        """
        SELECT id, raw_text, metadata, source, scope, kind, created_at
        FROM thoughts
        WHERE kind = 'rule' AND (scope IS NULL OR scope = ANY($1::text[]))
        ORDER BY (scope IS NOT NULL), array_position($1::text[], scope), created_at ASC
        """,
        scopes or [],
    )
    return [dict(r) for r in rows]
