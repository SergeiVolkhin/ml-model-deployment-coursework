"""Определения фичей Wine для Feast (postgres backend)."""
from datetime import timedelta

from feast import Entity, FeatureService, FeatureView, Field, ValueType
from feast.infra.offline_stores.contrib.postgres_offline_store.postgres_source import (
    PostgreSQLSource,
)
from feast.types import Float32, Int64

# одна сущность - бутылка вина
wine = Entity(
    name="wine",
    join_keys=["wine_id"],
    value_type=ValueType.INT64,
    description="ID бутылки вина в исходном датасете",
)

# источник - таблица в Postgres (создается отдельным скриптом load_to_postgres.py)
wine_source = PostgreSQLSource(
    name="wine_features_source",
    query="SELECT * FROM wine_features",
    timestamp_field="event_timestamp",
    created_timestamp_column="created_timestamp",
)

# 13 числовых фичей Wine + 1 целевая - но target в FeatureView не кладем
wine_features_fv = FeatureView(
    name="wine_features",
    entities=[wine],
    ttl=timedelta(days=365),
    schema=[
        Field(name="alcohol", dtype=Float32),
        Field(name="malic_acid", dtype=Float32),
        Field(name="ash", dtype=Float32),
        Field(name="alcalinity_of_ash", dtype=Float32),
        Field(name="magnesium", dtype=Float32),
        Field(name="total_phenols", dtype=Float32),
        Field(name="flavanoids", dtype=Float32),
        Field(name="nonflavanoid_phenols", dtype=Float32),
        Field(name="proanthocyanins", dtype=Float32),
        Field(name="color_intensity", dtype=Float32),
        Field(name="hue", dtype=Float32),
        Field(name="od280_od315_diluted", dtype=Float32),
        Field(name="proline", dtype=Float32),
        Field(name="wine_class", dtype=Int64),
    ],
    source=wine_source,
    online=True,
    tags={"team": "ml-platform", "domain": "wine"},
)

# отдельный сервис фичей - под обучение классификатора
wine_training_service = FeatureService(
    name="wine_training_v1",
    features=[wine_features_fv],
)
