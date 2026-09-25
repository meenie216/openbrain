CREATE TABLE thoughts (
    id          UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    raw_text    TEXT NOT NULL,
    embedding   VECTOR(768) NOT NULL,
    metadata    JSONB NOT NULL DEFAULT '{}',
    source      TEXT NOT NULL DEFAULT 'http',
    -- NULL = global (applies everywhere); otherwise a project key
    -- (owner/repo, or a ~-relative path for non-git directories).
    scope       TEXT NULL,
    -- 'rule': loaded into every session at start, not searched for.
    -- 'thought': found via semantic_search when relevant.
    kind        TEXT NOT NULL DEFAULT 'thought'
                CHECK (kind IN ('rule', 'thought')),
    created_at  TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX thoughts_embedding_idx ON thoughts
    USING hnsw (embedding vector_cosine_ops);
CREATE INDEX thoughts_metadata_idx ON thoughts USING gin (metadata);
CREATE INDEX thoughts_created_at_idx ON thoughts (created_at DESC);
CREATE INDEX thoughts_kind_scope_idx ON thoughts (kind, scope);

-- Tracks which db/migrations/*.sql files have been applied to a database
-- that started life before scope/kind existed. A fresh install (this file)
-- already has the final schema, so it's seeded as if those migrations had
-- already run — nothing in db/migrations/ needs to be applied here.
CREATE TABLE schema_migrations (
    version    TEXT PRIMARY KEY,
    applied_at TIMESTAMPTZ NOT NULL DEFAULT now()
);
INSERT INTO schema_migrations (version) VALUES
    ('001_schema_migrations'),
    ('002_scope_kind');
