import asyncio

from fastapi import Depends, FastAPI, Header, HTTPException
from pydantic import BaseModel

from app.db import insert_thought
from app.metadata import extract_metadata
from common.auth import check_token, parse_bearer
from common.embeddings import embed

app = FastAPI()


class CaptureRequest(BaseModel):
    text: str
    source: str = "http"


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


@app.post("/capture", dependencies=[Depends(require_write)])
async def capture(req: CaptureRequest):
    embedding, metadata = await asyncio.gather(
        embed(req.text),
        extract_metadata(req.text),
    )
    thought = await insert_thought(req.text, embedding, metadata, req.source)
    return thought
