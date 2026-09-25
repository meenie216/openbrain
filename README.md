# Open Brain

A self-hosted memory for AI tools. Postgres + pgvector is the single store, an
MCP server handles retrieval, and a capture path embeds and classifies every
thought as it is saved. Any MCP-capable client (Claude Code, Claude Desktop,
Cursor, ...) reads and writes the same store, so there are no per-tool memory
silos.

Inspired by ["You Don't Need SaaS. The $0.10 System That Replaced My AI
Workflow"](https://www.youtube.com/watch?v=2JiMmye2ezg) (Nate B Jones).

## Architecture

```
                    ┌─────────────┐
  HTTP POST  ──────▶│             │
  CLI script ──────▶│ capture-api │──▶ Ollama (embed) ───────┐
                    │  (FastAPI)  │──▶ Claude API (metadata) │──▶ Postgres+pgvector
                    └─────────────┘                          │      (thoughts)
                                                             │
                    ┌─────────────┐                          │
  MCP clients  ────▶│ mcp-server  │──▶ Ollama (embed) ───────┘
                    │ (HTTP)      │──▶ Postgres (read)
                    └─────────────┘
```

| Service       | Base                     | Purpose                                  |
|---------------|--------------------------|------------------------------------------|
| `postgres`    | `pgvector/pgvector:pg16` | `thoughts` table + vector index          |
| `capture-api` | `python:3.12-slim`       | `/capture` HTTP endpoint, the write path |
| `mcp-server`  | `python:3.12-slim`       | MCP tools, the read path                 |

The CLI is not a service: it is a script that talks to `capture-api`.

Design decisions:

- **Embeddings are local**, via Ollama (`nomic-embed-text`, 768 dimensions).
  Capture and query must use the same model or semantic search silently
  breaks. Ollama runs natively on the host and the containers reach it at
  `host.docker.internal:11434`; the compose file has an optional `ollama`
  profile for hosts without one.
- **Metadata** (people, topics, type, action items) comes from a single
  Claude call per captured thought, using tool-use for structured output.
- **Retrieval makes no LLM call**, only the local embedding for the query plus
  SQL.
- **Capture is HTTP plus a thin CLI wrapper**, so there is one code path.
- **The MCP server speaks HTTP**, not stdio, so it can stay up in Docker and
  serve several clients.

## Running it

```
cp .env.example .env     # fill in the API key and passwords
docker compose up -d
cli/brain-capture "a thought worth keeping"
```

## Schema and migrations

A fresh install gets the full schema from `db/init/` (and `schema_migrations`
pre-seeded), so nothing in `db/migrations/` needs applying. An existing
database is brought up to date by applying `db/migrations/*.sql` in order.
Each migration is wrapped in a transaction, is safe to re-run, and records
itself in `schema_migrations`.

## Authentication

Two static bearer tokens, `OPENBRAIN_READ_TOKEN` and `OPENBRAIN_WRITE_TOKEN`
(generate with `openssl rand -hex 32`). Write also grants read. Both servers
refuse to start if either is unset, and `/health` stays open. Tokens are
never logged.

Deliberately not OAuth: this is a single-user system, so two long-lived
tokens are enough. Services bind to `127.0.0.1` by default; reach them from
other machines over a private network or VPN rather than exposing them
publicly.

To rotate, generate a new token, update `.env` and the clients, then run
`docker compose up -d`.

## Deploying

`DEPLOY_TARGET=user@host:path/ cli/deploy.sh` rsyncs the code to another
machine. It deliberately never syncs `.env`: that file mixes host-specific
values (`OLLAMA_BASE_URL`, `COMPOSE_PROFILES`) with values that should be
shared (API keys, tokens), and a wholesale copy overwrites the former. Edit
`.env` on the target by hand when a new variable is added.

## Scopes and rules

Every thought has a `scope` (a project key, `NULL` = global) and a `kind`:

- `thought`: found via `semantic_search` when relevant.
- `rule`: a durable "always/never do X" preference, loaded into every session
  at start rather than searched for.

The caller chooses both explicitly on capture (`POST /capture` takes `scope`
and `kind`); they are never inferred from the text. `semantic_search` and
`list_recent` take an optional `scope` plus `include_global`; omitting `scope`
searches everything. `get_rules(scope)` (MCP) and `GET /rules?scope=` (HTTP,
read token, plain markdown) return every rule that is global or matches the
scope, global first.
