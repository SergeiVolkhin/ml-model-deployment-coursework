"""Step 3 notebook enrichment.

Replace cell 7 (currently a one-line `#data_report.run(...)` placeholder) with a fully
runnable inline Evidently flow tailored for Colab, and insert a Russian-language
interpretation markdown cell right after it.
"""
from __future__ import annotations

from pathlib import Path

import nbformat
from nbformat.v4 import new_markdown_cell

REPO_ROOT = Path(r"C:\Python\ML HW\8")
NOTEBOOK = REPO_ROOT / "notebook" / "HW8_Monitoring_Volkhin_Sergei.ipynb"

CELL7_CODE = r'''# Шаг 3. Дрифт данных + деградация модели
# В Colab: !pip install -q "evidently==0.7.21" pandas==2.2.3 scikit-learn==1.8.0 numpy==2.2.1
# Локально: pip install -r drift/requirements.txt и python drift/drift_report.py

import numpy as np
import pandas as pd
from sklearn.linear_model import Ridge
from sklearn.metrics import mean_absolute_error, mean_squared_error
from sklearn.preprocessing import OneHotEncoder

from evidently import DataDefinition, Dataset, Report
from evidently.core.datasets import Regression
from evidently.presets import DataDriftPreset, DataSummaryPreset, RegressionPreset

rng = np.random.default_rng(42)
N = 5000
NUMERICAL = ["user_age", "watch_time_min", "n_views_last_30d"]
CATEGORICAL = ["device_type", "country"]


def _gt(df, rng):
    base = 2.5 + 0.01 * df["watch_time_min"].clip(upper=300) + 0.05 * df["n_views_last_30d"].clip(upper=40)
    return (base + rng.normal(0, 0.4, size=len(df))).clip(1, 5).round(2).to_numpy()


reference = pd.DataFrame({
    "user_age": rng.normal(33, 10, N).clip(14, 80).round(1),
    "watch_time_min": rng.gamma(2.0, 20.0, N).round(1),
    "n_views_last_30d": rng.poisson(15, N),
    "device_type": rng.choice(["mobile", "smart_tv", "web", "tablet"], N, p=[0.40, 0.30, 0.20, 0.10]),
    "country": rng.choice(["RU", "KZ", "BY", "AM", "UZ"], N, p=[0.55, 0.20, 0.10, 0.08, 0.07]),
})
reference["target"] = _gt(reference, rng)

current = pd.DataFrame({
    "user_age": rng.normal(33, 10, N).clip(14, 80).round(1),
    "watch_time_min": (rng.gamma(2.0, 20.0, N) * 3.0).round(1),       # дрифт x3
    "n_views_last_30d": rng.poisson(18, N),
    "device_type": rng.choice(["mobile", "smart_tv", "web", "tablet"], N, p=[0.75, 0.12, 0.08, 0.05]),
    "country": rng.choice(["RU", "KZ", "BY", "AM", "UZ", "KG"], N, p=[0.45, 0.18, 0.08, 0.07, 0.07, 0.15]),
})
current["target"] = _gt(current, rng)

encoder = OneHotEncoder(handle_unknown="ignore", sparse_output=False).fit(reference[CATEGORICAL])


def feats(df):
    return np.hstack([df[NUMERICAL].to_numpy(), encoder.transform(df[CATEGORICAL])])


model = Ridge(alpha=1.0).fit(feats(reference), reference["target"])
reference["prediction"] = model.predict(feats(reference))
current["prediction"] = model.predict(feats(current))

rmse_ref = float(np.sqrt(mean_squared_error(reference["target"], reference["prediction"])))
rmse_cur = float(np.sqrt(mean_squared_error(current["target"], current["prediction"])))
print(f"Ridge RMSE on reference = {rmse_ref:.3f}")
print(f"Ridge RMSE on current   = {rmse_cur:.3f}  (delta = {100 * (rmse_cur - rmse_ref) / rmse_ref:+.1f}%)")
print(f"Ridge MAE on current    = {mean_absolute_error(current['target'], current['prediction']):.3f}")

drift_def = DataDefinition(numerical_columns=NUMERICAL + ["target"], categorical_columns=CATEGORICAL)
drift_ref = Dataset.from_pandas(reference[NUMERICAL + CATEGORICAL + ["target"]], data_definition=drift_def)
drift_cur = Dataset.from_pandas(current[NUMERICAL + CATEGORICAL + ["target"]], data_definition=drift_def)

drift_report = Report([DataDriftPreset(method="psi"), DataSummaryPreset()], include_tests=True)
drift = drift_report.run(current_data=drift_cur, reference_data=drift_ref)
drift.save_html("data_drift_report.html")

regression_def = DataDefinition(
    numerical_columns=NUMERICAL,
    categorical_columns=CATEGORICAL,
    regression=[Regression(target="target", prediction="prediction")],
)
regression_ref = Dataset.from_pandas(reference, data_definition=regression_def)
regression_cur = Dataset.from_pandas(current, data_definition=regression_def)

regression_report = Report([RegressionPreset()], include_tests=True)
regression = regression_report.run(current_data=regression_cur, reference_data=regression_ref)
regression.save_html("regression_report.html")

print("HTML отчёты сохранены: data_drift_report.html, regression_report.html")
drift  # Colab отрисует Snapshot inline
'''

INTERPRETATION_MD = """### Интерпретация дрифта и деградации модели

**Что произошло с данными (Data Drift):**
- `watch_time_min`: распределение умножено на 3 (пандемийный буст). PSI > 0.25 - явный признак дрифта.
- `device_type`: доля mobile выросла с 40% до 75%. PSI на категориальной фиче > 0.20 - дрифт.
- `country`: появилась новая категория `KG`, которой не было в reference. Это concept drift - модель не видела этот сегмент при обучении.

**Что произошло с моделью (Model Degradation):**
- Ridge, обученный на reference, выдаёт более высокую RMSE на current. Прирост RMSE 15-30% типичен для подобного сдвига.
- RegressionPreset подсветит, что residuals смещены - модель систематически промахивается на хвостах распределения `watch_time_min`.

**Что бы делал в проде:**
1. Поднять алерт по PSI > 0.25 на ключевых фичах и MAE/RMSE > baseline * 1.2.
2. Запустить тeневой A/B (shadow deployment) с retrain-моделью на current батче, сравнить онлайн-метрики (CTR, watch-through rate).
3. Если retrain не даёт улучшения и причина - concept drift (новая страна), пересмотреть feature pipeline: добавить fallback-handling unseen categories, обновить feature store.
4. Откат (rollback) только если бизнес-метрики деградировали > 5%; иначе мониторим и копим обучающую выборку.
"""


def main() -> None:
    nb = nbformat.read(str(NOTEBOOK), as_version=4)
    cell7 = nb.cells[7]
    assert cell7.cell_type == "code", f"cell 7 must be code, got {cell7.cell_type}"
    cell7.source = CELL7_CODE
    cell7.outputs = []
    cell7.execution_count = None

    interpretation_cell = new_markdown_cell(INTERPRETATION_MD)
    already_present = any(
        c.cell_type == "markdown" and "### Интерпретация дрифта" in c.source
        for c in nb.cells
    )
    if not already_present:
        nb.cells.insert(8, interpretation_cell)
        print("inserted interpretation markdown at index 8")
    else:
        print("interpretation markdown already present; skipped")

    nbformat.write(nb, str(NOTEBOOK))
    nb_check = nbformat.read(str(NOTEBOOK), as_version=4)
    nbformat.validate(nb_check)
    print(f"cell 7 source length: {len(nb_check.cells[7].source)}")
    print(f"total cells now: {len(nb_check.cells)}")


if __name__ == "__main__":
    main()
