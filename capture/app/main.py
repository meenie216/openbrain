import asyncio

from fastapi import FastAPI
from pydantic import BaseModel

from app.db import insert_thought
from app.metadata import extract_metadata
from common.embeddings import embed

app = FastAPI()


class CaptureRequest(BaseModel):
    text: str
    source: str = "http"


@app.get("/health")
async def health():
    return {"status": "ok"}


@app.post("/capture")
async def capture(req: CaptureRequest):
    embedding, metadata = await asyncio.gather(
        embed(req.text),
        extract_metadata(req.text),
    )
    thought = await insert_thought(req.text, embedding, metadata, req.source)
    return thought
