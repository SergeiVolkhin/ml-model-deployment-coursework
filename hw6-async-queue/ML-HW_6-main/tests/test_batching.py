import asyncio
import time

import numpy as np
import pytest

from src.batching import BatchProcessor


def fake_encoder(items: list) -> np.ndarray:
    # детерминированный энкодер - возвращает length каждого элемента в виде вектора длины 1
    return np.asarray([[float(len(str(x)))] for x in items], dtype=np.float32)


@pytest.mark.asyncio
async def test_flush_by_size():
    bp = BatchProcessor(fake_encoder, batch_size=8, timeout=10.0)
    await bp.start()
    try:
        # шлем ровно batch_size - должен флашнуться сразу, не дожидаясь таймаута
        t0 = time.monotonic()
        futs = [await bp.submit(f"item-{i}") for i in range(8)]
        results = await asyncio.gather(*futs)
        elapsed = time.monotonic() - t0
        assert elapsed < 1.0, f"флаш по размеру должен быть мгновенным, прошло {elapsed:.2f}s"
        assert len(results) == 8
        assert all(r.shape == (1,) for r in results)
    finally:
        await bp.stop()


@pytest.mark.asyncio
async def test_flush_by_timeout():
    bp = BatchProcessor(fake_encoder, batch_size=64, timeout=0.5)
    await bp.start()
    try:
        # шлем меньше batch_size - должен флашнуться по таймауту
        t0 = time.monotonic()
        futs = [await bp.submit(f"x-{i}") for i in range(5)]
        results = await asyncio.gather(*futs)
        elapsed = time.monotonic() - t0
        assert 0.4 < elapsed < 1.5, f"должен флашнуться около timeout=0.5, прошло {elapsed:.2f}s"
        assert len(results) == 5
    finally:
        await bp.stop()


@pytest.mark.asyncio
async def test_results_routed_to_correct_futures():
    # критичная проверка: после флаша каждый submit получает СВОЙ результат,
    # а не чужой. Энкодер возвращает длину строки - можно сверить
    bp = BatchProcessor(fake_encoder, batch_size=4, timeout=5.0)
    await bp.start()
    try:
        items = ["a", "bb", "ccc", "dddd"]
        futs = [await bp.submit(s) for s in items]
        results = await asyncio.gather(*futs)
        for s, vec in zip(items, results):
            assert vec[0] == float(len(s)), f"для '{s}' ожидали {len(s)}, получили {vec[0]}"
    finally:
        await bp.stop()


@pytest.mark.asyncio
async def test_size_threshold_wins_over_timeout():
    # отдельный кейс: если до таймаута набрали batch_size - флаш должен быть мгновенный
    # даже если таймаут большой
    bp = BatchProcessor(fake_encoder, batch_size=3, timeout=10.0)
    await bp.start()
    try:
        t0 = time.monotonic()
        futs = []
        for i in range(3):
            futs.append(await bp.submit(f"q-{i}"))
            await asyncio.sleep(0.05)
        await asyncio.gather(*futs)
        elapsed = time.monotonic() - t0
        # 3 submit'а с паузой 0.05 = ~0.15s, плюс минимум на флаш
        assert elapsed < 1.0, f"должен флашнуться по размеру, прошло {elapsed:.2f}s"
    finally:
        await bp.stop()
