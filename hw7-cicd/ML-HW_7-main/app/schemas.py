from pydantic import BaseModel, ConfigDict, Field


class PredictRequest(BaseModel):
    x: list[float] = Field(
        ...,
        min_length=4,
        max_length=4,
        description="Признаки iris: sepal length, sepal width, petal length, petal width (см)",
    )


class PredictResponse(BaseModel):
    prediction: int
    class_name: str
    version: str


class HealthResponse(BaseModel):
    model_config = ConfigDict(protected_namespaces=())

    status: str
    version: str
    model_loaded: bool
