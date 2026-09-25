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
    # None = global (applies everywhere); otherwise a project key. The
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
    global_rules = [r for r in rows if r["scope"] is None]
    project_rules = [r for r in rows if r["scope"] is not None]
    lines = ["# Standing rules", ""]
    if global_rules:
        lines.append("## Global")
        lines += [f"- {r['raw_text']}" for r in global_rules]
        lines.append("")
    if project_rules:
        lines.append(f"## {project_rules[0]['scope']}")
        lines += [f"- {r['raw_text']}" for r in project_rules]
        lines.append("")
    return "\n".join(lines) + "\n"


@app.get("/rules", dependencies=[Depends(require_read)], response_class=PlainTextResponse)
async def rules(scope: str | None = Query(default=None)):
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
