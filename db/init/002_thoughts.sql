CREATE TABLE thoughts (
    id          UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    raw_text    TEXT NOT NULL,
    embedding   VECTOR(768) NOT NULL,
    metadata    JSONB NOT NULL DEFAULT '{}',
    source      TEXT NOT NULL DEFAULT 'http',
    created_at  TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX thoughts_embedding_idx ON thoughts
    USING hnsw (embedding vector_cosine_ops);
CREATE INDEX thoughts_metadata_idx ON thoughts USING gin (metadata);
CREATE INDEX thoughts_created_at_idx ON thoughts (created_at DESC);
