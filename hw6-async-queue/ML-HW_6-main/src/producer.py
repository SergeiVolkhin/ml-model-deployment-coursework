"""FastAPI producer.

POST /embed принимает текст, генерит request_id, публикует в Redis Stream
texts.incoming, отдает 202 + request_id. Юзер потом забирает результат
из embeddings.ready по request_id (см. consumer.py).
"""
from __future__ import annotations

import logging
import time
import uuid
from contextlib import asynccontextmanager

from fastapi import FastAPI, status
from pydantic import BaseModel, Field

from src.broker import get_broker

log = logging.getLogger(__name__)


class EmbedRequest(BaseModel):
    text: str = Field(min_length=1, max_length=2000)


class EmbedAccepted(BaseModel):
    request_id: str
    accepted_at: float


@asynccontextmanager
async def lifespan(app: FastAPI):
    broker = get_broker()
    await broker.connect()
    yield
    await broker.close()


app = FastAPI(title="HW6 producer", lifespan=lifespan)


@app.post("/embed", status_code=status.HTTP_202_ACCEPTED, response_model=EmbedAccepted)
async def embed(req: EmbedRequest) -> EmbedAccepted:
    broker = get_broker()
    request_id = str(uuid.uuid4())
    ts = time.time()
    payload = {"request_id": request_id, "text": req.text, "ts": ts}
    await broker.publish(payload, stream="texts.incoming")
    return EmbedAccepted(request_id=request_id, accepted_at=ts)


@app.get("/healthz")
async def healthz() -> dict:
    return {"status": "ok"}
