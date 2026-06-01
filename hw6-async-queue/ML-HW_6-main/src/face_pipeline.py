"""3 стадии face-blur пайплайна на FastStream + Redis Streams.

Реализация цепочки из async.yaml. Каждая стадия читает из своего стрима, делает
работу, публикует в следующий. Вид cv2-логики - 1в1 как в ноутбуке ДЗ5.

Запуск отдельной стадии:
    faststream run src.face_pipeline:app
"""
from __future__ import annotations

import base64
import logging
import os
from typing import Any

import cv2
import numpy as np
from faststream import FastStream
from faststream.redis import RedisBroker
from pydantic import BaseModel, Field

log = logging.getLogger(__name__)

REDIS_URL = os.getenv("REDIS_URL", "redis://localhost:6379")
CASCADE_PATH = os.getenv(
    "CASCADE_PATH",
    cv2.data.haarcascades + "haarcascade_frontalface_default.xml",
)
SCALE_FACTOR = 1.1
MIN_NEIGHBORS = 4
PIXEL_SIZE = 100  # как в ДЗ5

broker = RedisBroker(REDIS_URL)
app = FastStream(broker)


class FrameMessage(BaseModel):
    frame_id: str
    ts: float
    width: int
    height: int
    image_bgr_b64: str


class GrayFrameMessage(BaseModel):
    frame_id: str
    ts: float
    width: int
    height: int
    image_gray_b64: str
    image_bgr_b64: str  # тащим оригинал по цепочке - на финале он нужен для мозаики


class FaceBox(BaseModel):
    x: int
    y: int
    w: int
    h: int


class FaceDetections(BaseModel):
    frame_id: str
    ts: float
    width: int
    height: int
    image_bgr_b64: str
    faces: list[FaceBox] = Field(default_factory=list)


class BlurredFrame(BaseModel):
    frame_id: str
    ts: float
    image_bgr_b64: str


# каскад грузим один раз - при импорте модуля
_face_cascade = cv2.CascadeClassifier(CASCADE_PATH)
if _face_cascade.empty():
    log.warning("каскад %s не загрузился, detectFaces будет пустым", CASCADE_PATH)


def _decode_bgr(b64: str, h: int, w: int) -> np.ndarray:
    raw = base64.b64decode(b64)
    return np.frombuffer(raw, dtype=np.uint8).reshape(h, w, 3)


def _encode_bgr(arr: np.ndarray) -> str:
    return base64.b64encode(arr.tobytes()).decode("ascii")


def _decode_gray(b64: str, h: int, w: int) -> np.ndarray:
    raw = base64.b64decode(b64)
    return np.frombuffer(raw, dtype=np.uint8).reshape(h, w)


def _encode_gray(arr: np.ndarray) -> str:
    return base64.b64encode(arr.tobytes()).decode("ascii")


def apply_mosaic_effect(face_roi: np.ndarray, pixel_size: int = PIXEL_SIZE) -> np.ndarray:
    h, w = face_roi.shape[:2]
    new_w = max(1, w // pixel_size)
    new_h = max(1, h // pixel_size)
    downscaled = cv2.resize(face_roi, (new_w, new_h), interpolation=cv2.INTER_LINEAR)
    return cv2.resize(downscaled, (w, h), interpolation=cv2.INTER_NEAREST)


@broker.subscriber(stream="frames.raw")
@broker.publisher(stream="frames.gray")
async def stage_grayscale(msg: FrameMessage) -> GrayFrameMessage:
    bgr = _decode_bgr(msg.image_bgr_b64, msg.height, msg.width)
    gray = cv2.cvtColor(bgr, cv2.COLOR_BGR2GRAY)
    return GrayFrameMessage(
        frame_id=msg.frame_id,
        ts=msg.ts,
        width=msg.width,
        height=msg.height,
        image_gray_b64=_encode_gray(gray),
        image_bgr_b64=msg.image_bgr_b64,
    )


@broker.subscriber(stream="frames.gray")
@broker.publisher(stream="frames.faces")
async def stage_detect_faces(msg: GrayFrameMessage) -> FaceDetections:
    gray = _decode_gray(msg.image_gray_b64, msg.height, msg.width)
    detected: Any = _face_cascade.detectMultiScale(gray, SCALE_FACTOR, MIN_NEIGHBORS)
    boxes: list[FaceBox] = []
    # detectMultiScale возвращает либо ndarray (N,4), либо пустой tuple
    if len(detected) > 0:
        for (x, y, w, h) in detected:
            boxes.append(FaceBox(x=int(x), y=int(y), w=int(w), h=int(h)))
    return FaceDetections(
        frame_id=msg.frame_id,
        ts=msg.ts,
        width=msg.width,
        height=msg.height,
        image_bgr_b64=msg.image_bgr_b64,
        faces=boxes,
    )


@broker.subscriber(stream="frames.faces")
@broker.publisher(stream="frames.output")
async def stage_blur(msg: FaceDetections) -> BlurredFrame:
    bgr = _decode_bgr(msg.image_bgr_b64, msg.height, msg.width).copy()
    for box in msg.faces:
        x, y, fw, fh = box.x, box.y, box.w, box.h
        roi = bgr[y:y + fh, x:x + fw]
        if roi.size == 0:
            continue
        bgr[y:y + fh, x:x + fw] = apply_mosaic_effect(roi)

    return BlurredFrame(
        frame_id=msg.frame_id,
        ts=msg.ts,
        image_bgr_b64=_encode_bgr(bgr),
    )
