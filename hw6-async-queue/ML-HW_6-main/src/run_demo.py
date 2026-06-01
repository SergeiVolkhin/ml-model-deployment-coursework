"""End-to-end демо.

Поднимает FastStream-приложение consumer'а в том же процессе (включая прогрев
модели и батчер), регистрирует подписчик на embeddings.ready, шлет 100
текстов в texts.incoming, ждет 100 ответов, печатает суммарное время и
распределение задержек.

Перед запуском: docker compose up -d redis

Чтобы демо завершилось быстрее, для последнего неполного батча таймаут флаша
снижен через env BATCH_TIMEOUT=2.0. В проде дефолт 30 сек.
"""
from __future__ import annotations

import asyncio
import logging
import os
import time
import uuid

# демо-таймаут флаша - чтобы хвостовой батч (36 элементов) не ждал 30 секунд
os.environ.setdefault("BATCH_TIMEOUT", "2.0")

# импорты идут после env, чтобы consumer подцепил BATCH_TIMEOUT при инициализации
from src.broker import get_broker  # noqa: E402
from src.consumer import app as consumer_app  # noqa: E402

DEMO_TEXTS = [
    f"текст номер {i}: про асинхронную обработку и батчинг."
    for i in range(100)
]

broker = get_broker()
sent_at: dict[str, float] = {}
got_at: dict[str, float] = {}


@broker.subscriber(stream="embeddings.ready")
async def _collect(payload: dict) -> None:
    rid = payload.get("request_id")
    if rid in sent_at and rid not in got_at:
        got_at[rid] = time.monotonic()


async def main() -> None:
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s: %(message)s")
    log = logging.getLogger("demo")

    log.info("стартую consumer-приложение (warmup модели может занять ~40s в первый раз)")
    await consumer_app.start()

    log.info("шлю %d текстов", len(DEMO_TEXTS))
    t0 = time.monotonic()
    for text in DEMO_TEXTS:
        rid = str(uuid.uuid4())
        sent_at[rid] = time.monotonic()
        await broker.publish({"request_id": rid, "text": text, "ts": time.time()}, stream="texts.incoming")
    log.info("отправил все за %.2fs", time.monotonic() - t0)

    log.info("жду ответы...")
    deadline = time.monotonic() + 120.0
    while len(got_at) < len(DEMO_TEXTS) and time.monotonic() < deadline:
        await asyncio.sleep(0.2)

    total = time.monotonic() - t0
    latencies = sorted(got_at[r] - sent_at[r] for r in got_at)

    print("=" * 60)
    print(f"всего получено: {len(got_at)}/{len(DEMO_TEXTS)}")
    print(f"общее время: {total:.2f}s")
    if latencies:
        print(f"средняя задержка: {sum(latencies) / len(latencies):.3f}s")
        print(f"медиана: {latencies[len(latencies) // 2]:.3f}s")
        print(f"p95: {latencies[int(len(latencies) * 0.95)]:.3f}s")
        print(f"min: {latencies[0]:.3f}s, max: {latencies[-1]:.3f}s")
    print("=" * 60)

    await consumer_app.stop()


if __name__ == "__main__":
    asyncio.run(main())
