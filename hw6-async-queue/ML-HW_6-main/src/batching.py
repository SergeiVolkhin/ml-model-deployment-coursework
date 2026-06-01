"""Батчинг с таймаутом.

Флаш по len >= batch_size либо по таймауту от первого элемента в буфере.
Каждый submit() возвращает future, в который ляжет результат для конкретного элемента.
"""
from __future__ import annotations

import asyncio
import logging
import time
from typing import Any, Callable, Optional

import numpy as np

log = logging.getLogger(__name__)

Encoder = Callable[[list[Any]], np.ndarray]


class BatchProcessor:
    def __init__(
        self,
        encoder: Encoder,
        batch_size: int = 64,
        timeout: float = 30.0,
    ):
        if batch_size <= 0:
            raise ValueError("batch_size > 0")
        if timeout <= 0:
            raise ValueError("timeout > 0")
        self._encoder = encoder
        self._batch_size = batch_size
        self._timeout = timeout
        self._buf: list[tuple[Any, asyncio.Future]] = []
        self._first_at: Optional[float] = None
        self._lock = asyncio.Lock()
        self._wake = asyncio.Event()
        self._task: Optional[asyncio.Task] = None
        self._stopping = False

    async def start(self) -> None:
        if self._task is not None:
            return
        self._stopping = False
        self._task = asyncio.create_task(self._loop(), name="batcher-loop")

    async def stop(self) -> None:
        self._stopping = True
        self._wake.set()
        if self._task is not None:
            try:
                await asyncio.wait_for(self._task, timeout=5.0)
            except asyncio.TimeoutError:
                self._task.cancel()
            self._task = None
        await self._flush_now()

    async def submit(self, item: Any) -> asyncio.Future:
        loop = asyncio.get_running_loop()
        fut: asyncio.Future = loop.create_future()
        async with self._lock:
            was_empty = not self._buf
            if was_empty:
                self._first_at = time.monotonic()
            self._buf.append((item, fut))
            new_len = len(self._buf)
        # будим _loop в двух случаях:
        # 1) появился первый элемент - чтобы _loop запустил отсчет таймаута
        # 2) набрали batch_size - чтобы флашнуть не дожидаясь таймаута
        if was_empty or new_len >= self._batch_size:
            self._wake.set()
        return fut

    async def _loop(self) -> None:
        while not self._stopping:
            async with self._lock:
                buf_len = len(self._buf)
                first_at = self._first_at

            if buf_len == 0:
                # пусто - ждем сигнал о появлении работы
                await self._wake.wait()
                self._wake.clear()
                continue

            if buf_len >= self._batch_size:
                await self._flush_now()
                # после флаша wake может быть в любом состоянии - сбрасываем
                self._wake.clear()
                continue

            # есть элементы, до батча не дотянули - ждем event либо timeout
            deadline = (first_at or time.monotonic()) + self._timeout
            remaining = max(0.0, deadline - time.monotonic())
            try:
                await asyncio.wait_for(self._wake.wait(), timeout=remaining)
                # event сработал - просыпаемся, на следующей итерации перечитаем
                # состояние и решим что делать (вариантов два: набрали батч либо stop)
                self._wake.clear()
            except asyncio.TimeoutError:
                await self._flush_now()

    async def _flush_now(self) -> None:
        async with self._lock:
            if not self._buf:
                return
            pending = self._buf
            self._buf = []
            self._first_at = None

        items = [x[0] for x in pending]
        futs = [x[1] for x in pending]
        log.debug("flush size=%d", len(items))

        try:
            # encoder обычно синхронный (torch на cpu блокирует event loop) -
            # уносим в пул потоков
            loop = asyncio.get_running_loop()
            result = await loop.run_in_executor(None, self._encoder, items)
        except Exception as exc:
            log.exception("encode failed")
            for fut in futs:
                if not fut.done():
                    fut.set_exception(exc)
            return

        if len(result) != len(futs):
            err = RuntimeError(f"encoder вернул {len(result)} результатов на {len(futs)} запросов")
            for fut in futs:
                if not fut.done():
                    fut.set_exception(err)
            return

        for fut, row in zip(futs, result):
            if not fut.done():
                fut.set_result(row)
