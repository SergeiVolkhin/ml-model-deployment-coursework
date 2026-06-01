"""Consumer: читает texts.incoming, батчит, пишет в embeddings.ready.

При старте делает model.warmup(). Все тексты складываются в BatchProcessor,
который флашит либо по 64 элементам либо по 30 секундам от первого элемента.
После флаша результаты публикуются по одному сообщению на каждый request_id.
"""
from __future__ import annotations

import logging
import os
import time
from typing import Optional

from faststream import FastStream
from pydantic import BaseModel

from src.batching import BatchProcessor
from src.broker import get_broker
from src.model_loader import get_model

log = logging.getLogger(__name__)

BATCH_SIZE = int(os.getenv("BATCH_SIZE", "64"))
BATCH_TIMEOUT = float(os.getenv("BATCH_TIMEOUT", "30.0"))  # сек

broker = get_broker()
app = FastStream(broker)

_model = get_model()
_batcher: Optional[BatchProcessor] = None


class IncomingText(BaseModel):
    request_id: str
    text: str
    ts: float


class EmbeddingReady(BaseModel):
    request_id: str
    embedding: list[float]
    ts: float


def _encode_batch(items: list[str]):
    return _model.encode(items)


@app.on_startup
async def _on_start() -> None:
    global _batcher
    log.info("прогрев модели...")
    _model.warmup()
    _batcher = BatchProcessor(_encode_batch, batch_size=BATCH_SIZE, timeout=BATCH_TIMEOUT)
    await _batcher.start()
    log.info("consumer готов")


@app.on_shutdown
async def _on_stop() -> None:
    if _batcher is not None:
        await _batcher.stop()


# max_workers - чтобы FastStream обрабатывал сообщения конкурентно. иначе сабскрайбер
# берет по одному, ждет батчер, и батч никогда не наполняется
@broker.subscriber(stream="texts.incoming", max_workers=128)
async def handle_text(msg: IncomingText) -> None:
    assert _batcher is not None, "batcher не инициализирован"
    fut = await _batcher.submit(msg.text)
    vec = await fut
    out = EmbeddingReady(
        request_id=msg.request_id,
        embedding=[float(x) for x in vec.tolist()],
        ts=time.time(),
    )
    await broker.publish(out.model_dump(), stream="embeddings.ready")
