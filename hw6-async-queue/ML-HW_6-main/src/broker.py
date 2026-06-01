"""Один общий RedisBroker для producer/consumer/face_pipeline.

Брокер ленивый - не открывает соединение пока не позвали connect/start.
"""
from __future__ import annotations

import os

from faststream.redis import RedisBroker

REDIS_URL = os.getenv("REDIS_URL", "redis://localhost:6379")

# единый инстанс - чтобы FastStream не плодил коннекшены
broker = RedisBroker(REDIS_URL)


def get_broker() -> RedisBroker:
    return broker
