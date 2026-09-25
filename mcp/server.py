import asyncio
import json
import os

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
async def semantic_search(query: str, limit: int = 5) -> list[dict]:
    """Search captured thoughts by meaning, not keyword."""
    query_embedding = await embed(query)
    rows = await db.semantic_search(query_embedding, limit)
    return [_format_row(r) for r in rows]


@server.tool()
async def list_recent(limit: int = 10) -> list[dict]:
    """List the most recently captured thoughts."""
    rows = await db.list_recent(limit)
    return [_format_row(r) for r in rows]


@server.tool()
async def stats() -> dict:
    """Summary stats: counts by type, top people/topics, captures per day this week."""
    return await db.stats()


@server.tool()
async def capture(text: str, source: str = "mcp") -> dict:
    """Capture a thought with automatic metadata extraction and embedding."""
    if mcp_access_level.get() != "write":
        raise ToolError("This token is read-only; capture requires the write token.")
    embedding, metadata = await asyncio.gather(
        embed(text),
        extract_metadata(text),
    )
    thought = await db.insert_thought(text, embedding, metadata, source)
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
