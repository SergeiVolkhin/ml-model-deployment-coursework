"""Synthetic ML service for HW8 monitoring.

Exposes:
    GET  /healthz   - liveness probe (always 200 unless app crashed)
    GET  /metrics   - Prometheus exposition
    POST /predict   - imitates an inference call with controlled latency

Environment:
    LATENCY_MODE         normal | degraded  (controls injected sleep window)
    ML_SERVICE_VERSION   string label for app_info gauge
    MLFLOW_TRACKING_URI  if reachable on startup, a dummy classifier is logged
"""
from __future__ import annotations

import asyncio
import logging
import os
import random
import time
from contextlib import asynccontextmanager
from typing import Any

import numpy as np
from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse, Response
from prometheus_client import (
    CONTENT_TYPE_LATEST,
    CollectorRegistry,
    Counter,
    Gauge,
    Histogram,
    generate_latest,
)
from pydantic import BaseModel, Field

logger = logging.getLogger("ml_service")
logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(name)s: %(message)s")

LATENCY_MODE = os.getenv("LATENCY_MODE", "normal").lower()
VERSION = os.getenv("ML_SERVICE_VERSION", "0.1.0")
MLFLOW_TRACKING_URI = os.getenv("MLFLOW_TRACKING_URI", "")

# Histogram buckets tuned for an SLO of p95 < 1s (covers sub-millisecond fast path up to the 5s tail).
LATENCY_BUCKETS = (0.005, 0.01, 0.025, 0.05, 0.1, 0.25, 0.5, 1.0, 2.5, 5.0)

registry = CollectorRegistry()
REQUEST_LATENCY = Histogram(
    "request_latency_seconds",
    "End-to-end HTTP request latency in seconds.",
    labelnames=("endpoint", "method"),
    buckets=LATENCY_BUCKETS,
    registry=registry,
)
REQUESTS_TOTAL = Counter(
    "requests_total",
    "Total HTTP requests served, partitioned by endpoint and status.",
    labelnames=("endpoint", "method", "status"),
    registry=registry,
)
MODEL_PREDICTIONS_TOTAL = Counter(
    "model_predictions_total",
    "Total model predictions emitted, partitioned by predicted class label.",
    labelnames=("class_label",),
    registry=registry,
)
MODEL_PREDICTION_CONFIDENCE = Histogram(
    "model_prediction_confidence",
    "Distribution of softmax-style model prediction confidence in [0, 1].",
    buckets=(0.1, 0.2, 0.3, 0.4, 0.5, 0.6, 0.7, 0.8, 0.9, 0.95, 0.99),
    registry=registry,
)
APP_INFO = Gauge(
    "app_info",
    "Static app metadata exposed as a labeled gauge (always set to 1).",
    labelnames=("version",),
    registry=registry,
)
APP_INFO.labels(version=VERSION).set(1)


def _bootstrap_mlflow_experiment() -> None:
    """Log a dummy sklearn classifier so a fresh MLflow server has tangible content.

    Failures are non-fatal: we keep the app healthy even if MLflow is unreachable.
    """
    if not MLFLOW_TRACKING_URI:
        logger.info("MLFLOW_TRACKING_URI is empty, skipping bootstrap experiment")
        return

    try:
        import mlflow
        import mlflow.sklearn
        from sklearn.datasets import make_classification
        from sklearn.linear_model import LogisticRegression
        from sklearn.metrics import accuracy_score
        from sklearn.model_selection import train_test_split

        mlflow.set_tracking_uri(MLFLOW_TRACKING_URI)
        mlflow.set_experiment("ml_service_bootstrap")

        X, y = make_classification(n_samples=500, n_features=8, random_state=42)
        X_tr, X_te, y_tr, y_te = train_test_split(X, y, test_size=0.2, random_state=42)
        clf = LogisticRegression(max_iter=200).fit(X_tr, y_tr)
        acc = accuracy_score(y_te, clf.predict(X_te))

        with mlflow.start_run(run_name=f"bootstrap-{VERSION}"):
            mlflow.log_param("model_family", "LogisticRegression")
            mlflow.log_param("service_version", VERSION)
            mlflow.log_metric("bootstrap_accuracy", float(acc))
            mlflow.sklearn.log_model(clf, artifact_path="model")

        logger.info("MLflow bootstrap run logged with accuracy=%.4f", acc)
    except Exception as exc:
        logger.warning("MLflow bootstrap failed (continuing without it): %s", exc)


@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("ml_service starting; LATENCY_MODE=%s, version=%s", LATENCY_MODE, VERSION)
    _bootstrap_mlflow_experiment()
    yield
    logger.info("ml_service shutting down")


app = FastAPI(title="HW8 ML Service", version=VERSION, lifespan=lifespan)


@app.middleware("http")
async def prometheus_middleware(request: Request, call_next):
    """Wrap every request with latency Histogram + status Counter."""
    endpoint = request.url.path
    method = request.method
    start = time.perf_counter()
    status = "500"
    try:
        response = await call_next(request)
        status = str(response.status_code)
        return response
    finally:
        elapsed = time.perf_counter() - start
        REQUEST_LATENCY.labels(endpoint=endpoint, method=method).observe(elapsed)
        REQUESTS_TOTAL.labels(endpoint=endpoint, method=method, status=status).inc()


class PredictRequest(BaseModel):
    user_id: int = Field(..., ge=0, description="Stable user identifier")
    features: list[float] = Field(default_factory=list, description="Feature vector (any length)")


class PredictResponse(BaseModel):
    user_id: int
    class_label: str
    confidence: float
    latency_mode: str


@app.get("/healthz")
async def healthz() -> dict[str, Any]:
    return {"status": "ok", "version": VERSION, "latency_mode": LATENCY_MODE}


@app.get("/metrics")
async def metrics() -> Response:
    return Response(generate_latest(registry), media_type=CONTENT_TYPE_LATEST)


def _injected_sleep_seconds() -> float:
    """Return synthetic processing time controlled by LATENCY_MODE env."""
    if LATENCY_MODE == "degraded":
        return random.uniform(2.0, 3.0)
    return random.uniform(0.05, 0.2)


@app.post("/predict", response_model=PredictResponse)
async def predict(payload: PredictRequest) -> PredictResponse:
    await asyncio.sleep(_injected_sleep_seconds())

    rng = np.random.default_rng(payload.user_id)
    confidence = float(rng.beta(5, 2))  # skewed toward high confidence
    class_label = rng.choice(["drama", "comedy", "thriller", "documentary", "scifi"])

    MODEL_PREDICTIONS_TOTAL.labels(class_label=class_label).inc()
    MODEL_PREDICTION_CONFIDENCE.observe(confidence)

    return PredictResponse(
        user_id=payload.user_id,
        class_label=class_label,
        confidence=round(confidence, 4),
        latency_mode=LATENCY_MODE,
    )


@app.exception_handler(Exception)
async def unhandled_exception_handler(request: Request, exc: Exception) -> JSONResponse:
    logger.exception("Unhandled exception on %s", request.url.path)
    return JSONResponse(status_code=500, content={"error": "internal_error"})
