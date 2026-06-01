# HW6 - Async Inference Pipeline

Асинхронный инференс `cointegrated/rubert-tiny2` через Redis Streams и FastStream. Lazy-загрузка модели с прогревом, батчинг по размеру/таймауту, event-driven цепочка face-blur из ДЗ5 в формате AsyncAPI 3.0.

## Стек

- Python 3.11
- transformers + torch (rubert-tiny2)
- Redis 7 (Streams) - один контейнер
- FastStream 0.5+ (async-обёртка над Redis Streams)
- FastAPI (producer)
- pytest + pytest-asyncio

## Структура

```
.
├── HW6_Async_Volkhin_Sergei.ipynb  # ноутбук с заполненными ячейками
├── async.yaml                       # AsyncAPI 3.0 спецификация face-blur цепочки
├── docker-compose.yml               # Redis 7-alpine + healthcheck
├── requirements.txt
├── pytest.ini
├── .gitignore
├── src/
│   ├── model_loader.py              # LazyModel с warmup
│   ├── batching.py                  # BatchProcessor (size/timeout flush)
│   ├── face_pipeline.py             # 3 FastStream stage-функции под async.yaml
│   ├── broker.py                    # один RedisBroker на все приложения
│   ├── producer.py                  # FastAPI POST /embed
│   ├── consumer.py                  # subscriber + батчинг + публикация в embeddings.ready
│   └── run_demo.py                  # e2e демо на 100 текстов
└── tests/
    └── test_batching.py             # тесты флаша по размеру и по таймауту
```

## Быстрый старт

```bash
git clone git@github.com:SergeiVolkhin/ML-HW_6.git
cd ML-HW_6
python -m venv .venv && .venv\Scripts\activate    # Windows
pip install -r requirements.txt

# 1. поднимаем Redis
docker compose up -d redis

# 2. тесты батчера
pytest -v

# 3. e2e демо
python -m src.run_demo
```

После `run_demo` в консоль печатается общее время, средняя задержка, медиана и p95 по 100 запросам.

## Producer как HTTP-сервис (опционально)

```bash
uvicorn src.producer:app --host 0.0.0.0 --port 8000
curl -X POST http://localhost:8000/embed -H "Content-Type: application/json" -d "{\"text\":\"привет\"}"
```

Ответ: `{"request_id":"...","accepted_at":...}`. Эмбеддинг придет в Redis Stream `embeddings.ready` тем же `request_id`.

## AsyncAPI

`async.yaml` описывает цепочку face-blur из ДЗ5: 4 канала (`frames.raw`, `frames.gray`, `frames.faces`, `frames.output`), 3 операции-перехода (`toGrayscale`, `detectFaces`, `applyBlur`). Спецификацию можно валидировать:

```bash
npx @asyncapi/cli validate async.yaml
```

или открыть в AsyncAPI Studio (см. ноутбук, ячейка с git clone studio).

## Что зачем (по критериям ДЗ)

| Критерий | Где |
|---|---|
| 1. Обоснование async (HDD-расчет) | ноутбук, ячейка `1JM7AcPIaERg` |
| 2. Брокер + AsyncAPI 3 события | `async.yaml`, `src/face_pipeline.py`, ноутбук ячейка `aBYphRLZ3x4H` |
| 3. Стратегия загрузки (Lazy + warmup) | `src/model_loader.py`, ноутбук ячейка `X5IFDgIr35O5` |
| 4. Батчинг с таймаутом | `src/batching.py`, тесты в `tests/test_batching.py`, ноутбук `U1qbvPfICwEi` |
| 5. Онлайн-загрузка | `src/producer.py` + `src/consumer.py` + `src/broker.py` + `src/run_demo.py`, ноутбук `FZiukZtfaCAY` |

## Почему Redis Streams, а не Kafka/RabbitMQ

- цепочка плоская (3 стадии, без сложной маршрутизации) - RabbitMQ-фичи с exchange/binding не нужны
- одна модель на одном хосте - инфраструктура Kafka (zookeeper/kraft, topics, partitions) избыточна
- нужны гарантия порядка и consumer groups - Redis Streams дает оба нативно
- задержка sub-ms на localhost, FastStream скрывает API-разницу
- один контейнер в docker-compose, поднимается за пару секунд

## Тесты

```bash
pytest -v
```

4 теста:
- `test_flush_by_size` - буфер из 8 элементов флашится мгновенно
- `test_flush_by_timeout` - 5 элементов уезжают через 0.5s (timeout в тесте опущен)
- `test_results_routed_to_correct_futures` - каждый submit получает свой результат
- `test_size_threshold_wins_over_timeout` - размер бьет таймаут даже при 10s timeout

## Ограничения

- face-blur stage'ы написаны под FastStream + Redis Streams, но в текущем демо runs только embedding-цепочка (rubert-tiny2). Запустить face_pipeline целиком можно командой `faststream run src.face_pipeline:app` если есть кадры в `frames.raw`.
- batch flush для float-чисел может тащить ~5-10мс на CPU из-за `loop.run_in_executor` - в проде имеет смысл вынести encoder в отдельный процесс/сервис.
