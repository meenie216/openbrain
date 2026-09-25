-- Adds scope (project key, NULL = global) and kind (rule vs thought) to
-- thoughts. See README.md. Safe to re-run.
--
-- Requires 001_schema_migrations.sql to have been applied first.
BEGIN;

ALTER TABLE thoughts ADD COLUMN IF NOT EXISTS scope TEXT NULL;
ALTER TABLE thoughts ADD COLUMN IF NOT EXISTS kind  TEXT NOT NULL DEFAULT 'thought';

-- ADD CONSTRAINT has no IF NOT EXISTS, so guard it manually.
DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM pg_constraint WHERE conname = 'thoughts_kind_check'
    ) THEN
        ALTER TABLE thoughts ADD CONSTRAINT thoughts_kind_check
            CHECK (kind IN ('rule', 'thought'));
    END IF;
END $$;

CREATE INDEX IF NOT EXISTS thoughts_kind_scope_idx ON thoughts (kind, scope);

INSERT INTO schema_migrations (version) VALUES ('002_scope_kind')
    ON CONFLICT (version) DO NOTHING;

COMMIT;
