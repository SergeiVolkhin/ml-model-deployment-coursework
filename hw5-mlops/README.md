# HW5 - Reproducible ML pipeline (DVC + MLflow + Feast)

End-to-end reproducible wine-classification pipeline with data versioning, experiment tracking, and a feature store.

## Stack

Python, scikit-learn 1.8.0, pandas 2.3.3, numpy 2.3.5, DVC 3.67.1, MLflow 3.11.1, Feast 0.62.0 + PostgreSQL (`psycopg`), marimo, matplotlib/seaborn, duckdb.

## Assignment

Build a reproducible ML contour: dataset under DVC, experiments logged to MLflow, features served from Feast on Postgres. I wired a `dvc.yaml` pipeline (`prepare` then `train`) for a RandomForest on the Wine dataset (3 classes, 13 features), logged params/metrics/artifacts to MLflow, and materialized features into the online and offline stores.

## Files

| File | Description |
|------|-------------|
| `ML-HW-hw5/` | Main project: DVC pipeline, `src/`, Feast feature store, docker-compose, report notebook |
| `ML-HW-hw5/HW5_MLOps_Вольхин_Сергей.ipynb` | Solution report notebook (6 sections) |
| `материалы семинара/` | Seminar materials (Feature Stores) |

Full project writeup: [`ML-HW-hw5/README.md`](ML-HW-hw5/README.md).

## Notes

The notebook has no cell outputs on purpose. The pipeline runs through `dvc repro`, not inside Jupyter, so the notebook is the report and the real execution lives in `src/`. Getting Feast to talk to Postgres on Windows was the fiddly part.
