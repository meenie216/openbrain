import asyncio
import json
import os
import uuid

from mcp.server.mcpserver import MCPServer
from mcp.server.mcpserver.exceptions import ToolError

import db
from auth_middleware import BearerAuthMiddleware
from common.auth import mcp_access_level
from common.embeddings import embed
from capture.app.metadata import extract_metadata

server = MCPServer("openbrain")


def _format_row(row: dict) -> dict:
    out = dict(row)
    out["id"] = str(out["id"])
    out["created_at"] = out["created_at"].isoformat()
    out["metadata"] = json.loads(out["metadata"])
    return out


@server.tool()
async def semantic_search(
    query: str, limit: int = 5, scopes: list[str] | None = None, include_global: bool = True
) -> list[dict]:
    """Search captured thoughts by meaning, not keyword.

    scopes: restrict to these scopes (a group like "cm", a project key, or
    both), plus global thoughts unless include_global=False. Omit to search
    everything, the default.
    """
    query_embedding = await embed(query)
    rows = await db.semantic_search(query_embedding, limit, scopes, include_global)
    return [_format_row(r) for r in rows]


@server.tool()
async def list_recent(limit: int = 10, scopes: list[str] | None = None, include_global: bool = True) -> list[dict]:
    """List the most recently captured thoughts. Same scopes/include_global as semantic_search."""
    rows = await db.list_recent(limit, scopes, include_global)
    return [_format_row(r) for r in rows]


@server.tool()
async def get_rules(scopes: list[str] | None = None) -> list[dict]:
    """Standing rules to load at session start: global rules, plus those of
    each given scope (general to specific, e.g. ["cm", "owner/repo"]).
    Unlike thoughts, rules aren't meant to be found by search — they're
    meant to already be in context."""
    rows = await db.get_rules(scopes)
    return [_format_row(r) for r in rows]


@server.tool()
async def capture(text: str, source: str = "mcp", scope: str | None = None, kind: str = "thought") -> dict:
    """Capture a thought, or a standing 'rule' (kind='rule') to be loaded
    into every future session instead of found by search.

    scope: None for global (applies everywhere); otherwise a group ("cm",
    "personal") or a project key (e.g. an owner/repo). The caller decides
    both — never inferred.
    """
    if mcp_access_level.get() != "write":
        raise ToolError("This token is read-only; capture requires the write token.")
    if kind not in ("rule", "thought"):
        raise ToolError(f"kind must be 'rule' or 'thought', got {kind!r}")
    embedding, metadata = await asyncio.gather(
        embed(text),
        extract_metadata(text),
    )
    thought = await db.insert_thought(text, embedding, metadata, source, scope, kind)
    return _format_row(thought)


def _require_write() -> None:
    if mcp_access_level.get() != "write":
        raise ToolError("This token is read-only; this requires the write token.")


def _check_id(thought_id: str) -> None:
    try:
        uuid.UUID(thought_id)
    except ValueError:
        raise ToolError(f"{thought_id!r} is not a valid thought id")


@server.tool()
async def forget(id: str) -> dict:
    """Permanently delete a thought or rule by id (as returned by search,
    list_recent or get_rules). Use when a stored memory is wrong or obsolete.
    Not reversible."""
    _require_write()
    _check_id(id)
    if not await db.delete_thought(id):
        raise ToolError(f"No thought with id {id}")
    return {"deleted": id}


@server.tool()
async def update_thought(
    id: str, text: str | None = None, scope: str | None = None, kind: str | None = None
) -> dict:
    """Edit an existing thought or rule in place, keeping its id and created_at.
    Only the fields you pass change.

    text: replacement text (re-embedded and re-classified).
    scope: new project key; pass "" to make it global. Omit to leave unchanged.
    kind: 'rule' or 'thought'. Omit to leave unchanged.
    """
    _require_write()
    _check_id(id)
    if text is None and scope is None and kind is None:
        raise ToolError("Nothing to update: pass text, scope and/or kind")
    if kind is not None and kind not in ("rule", "thought"):
        raise ToolError(f"kind must be 'rule' or 'thought', got {kind!r}")
    embedding = metadata = None
    if text is not None:
        embedding, metadata = await asyncio.gather(embed(text), extract_metadata(text))
    thought = await db.update_thought(
        id,
        raw_text=text,
        embedding=embedding,
        metadata=metadata,
        scope=scope or None,
        set_scope=scope is not None,
        kind=kind,
    )
    if thought is None:
        raise ToolError(f"No thought with id {id}")
    return _format_row(thought)


if __name__ == "__main__":
    import uvicorn

    host = "0.0.0.0"
    port = int(os.environ.get("MCP_SERVER_PORT", 8765))

    # Built and run by hand (rather than server.run(transport="streamable-http",
    # ...)) so BearerAuthMiddleware sits in front of every request, including
    # the ones .run() would otherwise send straight to the MCP session layer.
    app = BearerAuthMiddleware(server.streamable_http_app(host=host))
    uvicorn.run(app, host=host, port=port)
