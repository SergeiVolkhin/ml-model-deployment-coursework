FROM python:3.11-slim

ARG MODEL_VERSION=v1.0.0
ENV MODEL_VERSION=${MODEL_VERSION} \
    PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    MODEL_PATH=/app/models/model.pkl

LABEL org.opencontainers.image.title="iris-ml-service" \
      org.opencontainers.image.version="${MODEL_VERSION}" \
      org.opencontainers.image.source="https://github.com/SergeiVolkhin/ML-HW_7"

RUN groupadd -r app && useradd -r -g app -u 1000 -m -d /home/app app

WORKDIR /app

COPY --chown=app:app requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt

COPY --chown=app:app app/ ./app/

RUN mkdir -p /app/models && \
    python -m app.ml_pipeline --output-path /app/models/model.pkl --random-state 42 && \
    chown -R app:app /app/models

USER app

EXPOSE 8000

HEALTHCHECK --interval=10s --timeout=3s --retries=3 --start-period=15s \
    CMD python -c "import urllib.request, sys; \
sys.exit(0 if urllib.request.urlopen('http://127.0.0.1:8000/health', timeout=2).status == 200 else 1)"

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
