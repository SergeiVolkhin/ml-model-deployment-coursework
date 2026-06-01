import logging
import os
from contextlib import asynccontextmanager
from pathlib import Path

import joblib
import numpy as np
from fastapi import FastAPI, HTTPException, Request

from app.schemas import HealthResponse, PredictRequest, PredictResponse

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(name)s %(message)s",
)
logger = logging.getLogger("ml-service")

CLASS_NAMES = ["setosa", "versicolor", "virginica"]
MODEL_PATH = Path(os.getenv("MODEL_PATH", "app/models/model.pkl"))
MODEL_VERSION = os.getenv("MODEL_VERSION", "v1.0.0")

state: dict = {"model": None}


@asynccontextmanager
async def lifespan(app: FastAPI):
    if MODEL_PATH.exists():
        state["model"] = joblib.load(MODEL_PATH)
        logger.info("model loaded from %s, version=%s", MODEL_PATH, MODEL_VERSION)
    else:
        logger.warning("model file not found at %s, /predict will return 503", MODEL_PATH)
    yield
    state["model"] = None


app = FastAPI(title="iris ml-service", version=MODEL_VERSION, lifespan=lifespan)


@app.middleware("http")
async def add_version_header(request: Request, call_next):
    forwarded = request.headers.get("x-forwarded-version")
    response = await call_next(request)
    response.headers["X-Service-Version"] = forwarded or MODEL_VERSION
    return response


@app.get("/health", response_model=HealthResponse)
async def health() -> HealthResponse:
    return HealthResponse(
        status="ok",
        version=MODEL_VERSION,
        model_loaded=state["model"] is not None,
    )


@app.post("/predict", response_model=PredictResponse)
async def predict(payload: PredictRequest) -> PredictResponse:
    model = state["model"]
    if model is None:
        raise HTTPException(status_code=503, detail="model is not loaded")
    try:
        features = np.asarray(payload.x, dtype=float).reshape(1, -1)
        prediction = int(model.predict(features)[0])
    except Exception as exc:
        logger.exception("prediction failed")
        raise HTTPException(status_code=500, detail="prediction error") from exc

    return PredictResponse(
        prediction=prediction,
        class_name=CLASS_NAMES[prediction],
        version=MODEL_VERSION,
    )
