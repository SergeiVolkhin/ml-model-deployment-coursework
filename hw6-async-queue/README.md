# HW6 - Async inference with a message queue

Asynchronous embedding service over Redis Streams with request batching.

## Stack

Python 3.11, `asyncio`, FastAPI, Uvicorn, Redis Streams, FastStream, transformers + torch (rubert-tiny2), Pydantic, `opencv-python-headless`, pytest-asyncio.

## Assignment

Build an asynchronous inference pipeline: a FastAPI producer publishes text to Redis, a FastStream consumer batches requests and runs the model, and results go back on an `embeddings.ready` stream. I added a lazy-loaded model with warmup and a batch processor that flushes on size or timeout, plus an AsyncAPI spec for the face-blur event flow from HW5.

## Files

| File | Description |
|------|-------------|
| `ML-HW_6-main/` | Main project: `src/` (broker/consumer/producer/batching), tests, docker-compose |
| `ML-HW_6-main/HW6_Async_Volkhin_Sergei.ipynb` | Solution notebook |
| `Развертывание ML моделей_ Домашнее задание 6. Подключение очереди и асинхронной обработки.pdf` | Assignment specification |

Full project writeup: [`ML-HW_6-main/README.md`](ML-HW_6-main/README.md).

## Notes

The batch processor flushes on whichever comes first, 8 items or 0.5s, and getting that race right under pytest-asyncio took a couple of tries. The first version deadlocked when the timeout and the size trigger fired at the same time.
