-- Bootstraps migration tracking on a database that predates this framework.
-- Safe to re-run. Not needed on a fresh install: db/init/002_thoughts.sql
-- creates and seeds this table directly.
BEGIN;

CREATE TABLE IF NOT EXISTS schema_migrations (
    version    TEXT PRIMARY KEY,
    applied_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

INSERT INTO schema_migrations (version) VALUES ('001_schema_migrations')
    ON CONFLICT (version) DO NOTHING;

COMMIT;
