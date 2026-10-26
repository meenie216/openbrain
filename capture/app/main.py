import asyncio
from typing import Literal

from fastapi import Depends, FastAPI, Header, HTTPException, Query
from fastapi.responses import PlainTextResponse
from pydantic import BaseModel

from app.db import get_rules as db_get_rules
from app.db import insert_thought
from app.metadata import extract_metadata
from common.auth import check_token, parse_bearer
from common.embeddings import embed

app = FastAPI()


class CaptureRequest(BaseModel):
    text: str
    source: str = "http"
    # None = global (applies everywhere); otherwise a group or project key. The
    # caller decides both explicitly — never inferred from the text.
    scope: str | None = None
    kind: Literal["rule", "thought"] = "thought"


async def require_write(authorization: str | None = Header(default=None)) -> None:
    level = check_token(parse_bearer(authorization))
    if level is None:
        raise HTTPException(status_code=401, detail="Missing or invalid bearer token")
    if level != "write":
        raise HTTPException(status_code=403, detail="Write token required")


async def require_read(authorization: str | None = Header(default=None)) -> None:
    level = check_token(parse_bearer(authorization))
    if level is None:
        raise HTTPException(status_code=401, detail="Missing or invalid bearer token")


@app.get("/health")
async def health():
    return {"status": "ok"}


def _rules_markdown(rows: list[dict]) -> str:
    """Plain markdown, ready to paste into a session's context — used by
    the (not yet built) SessionStart hook, which can't call an MCP tool."""
    if not rows:
        return "(no standing rules)\n"
    # Rows arrive global first, then each scope in the order requested;
    # group them under one heading per scope, keeping that order.
    by_scope: dict[str | None, list[str]] = {}
    for r in rows:
        by_scope.setdefault(r["scope"], []).append(r["raw_text"])
    lines = ["# Standing rules", ""]
    for scope, texts in by_scope.items():
        lines.append(f"## {scope or 'Global'}")
        lines += [f"- {t}" for t in texts]
        lines.append("")
    return "\n".join(lines) + "\n"


@app.get("/rules", dependencies=[Depends(require_read)], response_class=PlainTextResponse)
async def rules(scope: list[str] = Query(default=[])):
    """scope may repeat, general to specific: /rules?scope=cm&scope=owner/repo"""
    rows = await db_get_rules(scope)
    return _rules_markdown(rows)


@app.post("/capture", dependencies=[Depends(require_write)])
async def capture(req: CaptureRequest):
    embedding, metadata = await asyncio.gather(
        embed(req.text),
        extract_metadata(req.text),
    )
    thought = await insert_thought(req.text, embedding, metadata, req.source, req.scope, req.kind)
    return thought
