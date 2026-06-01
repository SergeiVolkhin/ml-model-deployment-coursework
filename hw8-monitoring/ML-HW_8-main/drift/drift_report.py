"""Generate Evidently data-drift report and model-regression report for HW8 Step 3.

We simulate an online cinema recommender:
  - reference batch is sampled from a stable historical distribution;
  - current batch contains an injected drift (watch_time x3, mobile share 40% -> 75%,
    a brand new country category absent from the reference).
A Ridge regressor is trained on the reference batch; predictions are scored on both
batches to surface model degradation in addition to feature drift.

Run:
    python drift/drift_report.py
Outputs:
    drift/reports/data_drift_report.html
    drift/reports/data_drift_summary.json
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd
from sklearn.linear_model import Ridge
from sklearn.metrics import mean_absolute_error, mean_squared_error
from sklearn.preprocessing import OneHotEncoder

from evidently import DataDefinition, Dataset, Report
from evidently.core.datasets import Regression
from evidently.presets import DataDriftPreset, DataSummaryPreset, RegressionPreset

REPORTS_DIR = Path(__file__).parent / "reports"
REPORTS_DIR.mkdir(parents=True, exist_ok=True)
HTML_OUT = REPORTS_DIR / "data_drift_report.html"
JSON_OUT = REPORTS_DIR / "data_drift_summary.json"

N_REF = 5000
N_CUR = 5000
NUMERICAL = ["user_age", "watch_time_min", "n_views_last_30d"]
CATEGORICAL = ["device_type", "country"]


def _build_reference(rng: np.random.Generator) -> pd.DataFrame:
    df = pd.DataFrame({
        "user_age": rng.normal(loc=33, scale=10, size=N_REF).clip(14, 80).round(1),
        "watch_time_min": rng.gamma(shape=2.0, scale=20.0, size=N_REF).round(1),
        "n_views_last_30d": rng.poisson(lam=15, size=N_REF),
        "device_type": rng.choice(
            ["mobile", "smart_tv", "web", "tablet"], size=N_REF, p=[0.40, 0.30, 0.20, 0.10]
        ),
        "country": rng.choice(
            ["RU", "KZ", "BY", "AM", "UZ"], size=N_REF, p=[0.55, 0.20, 0.10, 0.08, 0.07]
        ),
    })
    df["target"] = _ground_truth_rating(df, rng)
    return df


def _build_current_with_drift(rng: np.random.Generator) -> pd.DataFrame:
    """Inject three explicit drifts versus the reference distribution."""
    df = pd.DataFrame({
        "user_age": rng.normal(loc=33, scale=10, size=N_CUR).clip(14, 80).round(1),
        # Drift #1: watch_time x3 (pandemic-style binge)
        "watch_time_min": (rng.gamma(shape=2.0, scale=20.0, size=N_CUR) * 3.0).round(1),
        "n_views_last_30d": rng.poisson(lam=18, size=N_CUR),
        # Drift #2: device_type mobile share jumps 40% -> 75%
        "device_type": rng.choice(
            ["mobile", "smart_tv", "web", "tablet"], size=N_CUR, p=[0.75, 0.12, 0.08, 0.05]
        ),
        # Drift #3: new country category KG that did not exist in reference (concept drift)
        "country": rng.choice(
            ["RU", "KZ", "BY", "AM", "UZ", "KG"], size=N_CUR, p=[0.45, 0.18, 0.08, 0.07, 0.07, 0.15]
        ),
    })
    df["target"] = _ground_truth_rating(df, rng)
    return df


def _ground_truth_rating(df: pd.DataFrame, rng: np.random.Generator) -> np.ndarray:
    """Synthetic target generator: rating in [1, 5] modestly correlated with watch_time and views."""
    base = 2.5 + 0.01 * df["watch_time_min"].clip(upper=300) + 0.05 * df["n_views_last_30d"].clip(upper=40)
    noise = rng.normal(0, 0.4, size=len(df))
    return (base + noise).clip(1, 5).round(2).to_numpy()


def _fit_predict(reference: pd.DataFrame, current: pd.DataFrame) -> tuple[pd.DataFrame, pd.DataFrame, dict[str, float]]:
    """Train Ridge on reference, attach predictions to both frames, report RMSE/MAE on both."""
    encoder = OneHotEncoder(handle_unknown="ignore", sparse_output=False)
    encoder.fit(reference[CATEGORICAL])

    def _features(df: pd.DataFrame) -> np.ndarray:
        cat = encoder.transform(df[CATEGORICAL])
        num = df[NUMERICAL].to_numpy()
        return np.hstack([num, cat])

    model = Ridge(alpha=1.0).fit(_features(reference), reference["target"].to_numpy())

    ref_pred = model.predict(_features(reference))
    cur_pred = model.predict(_features(current))

    ref_out = reference.copy()
    cur_out = current.copy()
    ref_out["prediction"] = ref_pred
    cur_out["prediction"] = cur_pred

    rmse_ref = float(np.sqrt(mean_squared_error(reference["target"], ref_pred)))
    rmse_cur = float(np.sqrt(mean_squared_error(current["target"], cur_pred)))
    mae_ref = float(mean_absolute_error(reference["target"], ref_pred))
    mae_cur = float(mean_absolute_error(current["target"], cur_pred))

    return ref_out, cur_out, {
        "rmse_reference": round(rmse_ref, 4),
        "rmse_current": round(rmse_cur, 4),
        "mae_reference": round(mae_ref, 4),
        "mae_current": round(mae_cur, 4),
        "rmse_delta_pct": round(100.0 * (rmse_cur - rmse_ref) / rmse_ref, 2),
    }


def _snapshot_payload(snapshot) -> dict:
    """Best-effort serializable payload across evidently 0.7.x point releases."""
    for attr in ("dict", "as_dict"):
        method = getattr(snapshot, attr, None)
        if callable(method):
            try:
                return method()
            except Exception:
                continue
    json_method = getattr(snapshot, "json", None)
    if callable(json_method):
        try:
            return json.loads(json_method())
        except Exception:
            pass
    return {"warning": "snapshot does not expose dict/json; HTML report is the canonical artefact"}


def main() -> int:
    rng = np.random.default_rng(seed=42)
    reference = _build_reference(rng)
    current = _build_current_with_drift(rng)

    print("reference batch:", reference.shape)
    print("current batch  :", current.shape)
    print("reference country categories:", sorted(reference['country'].unique()))
    print("current country categories  :", sorted(current['country'].unique()))

    reference_pred, current_pred, regression_summary = _fit_predict(reference, current)
    print("regression summary:")
    for k, v in regression_summary.items():
        print(f"  {k}: {v}")

    drift_definition = DataDefinition(
        numerical_columns=NUMERICAL + ["target"],
        categorical_columns=CATEGORICAL,
    )
    drift_ref_ds = Dataset.from_pandas(reference, data_definition=drift_definition)
    drift_cur_ds = Dataset.from_pandas(current, data_definition=drift_definition)

    drift_report = Report([
        DataDriftPreset(method="psi"),
        DataSummaryPreset(),
    ], include_tests=True)
    drift_snapshot = drift_report.run(current_data=drift_cur_ds, reference_data=drift_ref_ds)
    drift_snapshot.save_html(str(HTML_OUT))
    print(f"data-drift HTML report -> {HTML_OUT}")

    regression_definition = DataDefinition(
        numerical_columns=NUMERICAL,
        categorical_columns=CATEGORICAL,
        regression=[Regression(target="target", prediction="prediction")],
    )
    regression_ref_ds = Dataset.from_pandas(reference_pred, data_definition=regression_definition)
    regression_cur_ds = Dataset.from_pandas(current_pred, data_definition=regression_definition)
    regression_report = Report([RegressionPreset()], include_tests=True)
    regression_snapshot = regression_report.run(current_data=regression_cur_ds, reference_data=regression_ref_ds)

    payload = {
        "regression_summary": regression_summary,
        "drift_snapshot": _snapshot_payload(drift_snapshot),
        "regression_snapshot": _snapshot_payload(regression_snapshot),
    }
    JSON_OUT.write_text(json.dumps(payload, ensure_ascii=False, indent=2, default=str), encoding="utf-8")
    print(f"summary JSON -> {JSON_OUT}")
    print("OK")
    return 0


if __name__ == "__main__":
    sys.exit(main())
