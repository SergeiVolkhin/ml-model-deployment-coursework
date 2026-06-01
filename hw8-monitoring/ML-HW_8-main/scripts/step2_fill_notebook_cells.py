"""Step 2 notebook enrichment: fill cells 4 (%%writefile prometheus.yaml) and 5 (%%writefile grafana.yaml).

Cell 4 receives the content of prometheus/prometheus.yml with a short Russian comment header.
Cell 5 concatenates three Grafana provisioning YAMLs (datasource, contact points, alert rules)
separated by `# --- <relative-path> ---` markers.
"""
from __future__ import annotations

from pathlib import Path

import nbformat

REPO_ROOT = Path(r"C:\Python\ML HW\8")
NOTEBOOK = REPO_ROOT / "notebook" / "HW8_Monitoring_Volkhin_Sergei.ipynb"

PROM_HEADER = """%%writefile prometheus.yaml
# Конфиг Prometheus для стенда ДЗ-8.
# Ключевые блоки:
#  - global.scrape_interval / evaluation_interval = 15s (баланс между точностью и нагрузкой).
#  - rule_files: alerts.yml - PromQL правило HighLatencyP95 дублирует Grafana alert (надёжность).
#  - scrape_configs: job 'ml_service' дёргает /metrics на FastAPI сервисе раз в 15s.
#  - external_labels помечают серию меткой cluster=hw8-local для отделения от прод-инсталляций.

"""

GRAFANA_HEADER = """%%writefile grafana.yaml
# Объединённый provisioning bundle Grafana для ДЗ-8.
# Файл разделён на три YAML-документа, как они монтируются в /etc/grafana/provisioning/<...>:
#  1. datasources/prometheus.yml - указатель на Prometheus как default datasource.
#  2. alerting/contact-points.yml - Telegram contact point с подстановкой TG_BOT_TOKEN/TG_CHAT_ID из env.
#  3. alerting/alert-rules.yml - правило HighLatencyP95 (p95 > 1s) с маршрутом по severity=warning.
# В реальном compose каждый блок лежит в отдельном файле; здесь склейка для удобства просмотра.

"""


def _read(path: Path) -> str:
    return path.read_text(encoding="utf-8").rstrip() + "\n"


def main() -> None:
    nb = nbformat.read(str(NOTEBOOK), as_version=4)

    cell4 = nb.cells[4]
    assert cell4.cell_type == "code", f"cell 4 must be code, got {cell4.cell_type}"
    assert cell4.source.lstrip().startswith("%%writefile prometheus.yaml"), "cell 4 must start with %%writefile prometheus.yaml"
    cell4.source = PROM_HEADER + _read(REPO_ROOT / "prometheus" / "prometheus.yml")

    cell5 = nb.cells[5]
    assert cell5.cell_type == "code", f"cell 5 must be code, got {cell5.cell_type}"
    assert cell5.source.lstrip().startswith("%%writefile grafana.yaml"), "cell 5 must start with %%writefile grafana.yaml"

    parts = [
        ("grafana/provisioning/datasources/prometheus.yml", REPO_ROOT / "grafana" / "provisioning" / "datasources" / "prometheus.yml"),
        ("grafana/provisioning/alerting/contact-points.yml", REPO_ROOT / "grafana" / "provisioning" / "alerting" / "contact-points.yml"),
        ("grafana/provisioning/alerting/alert-rules.yml", REPO_ROOT / "grafana" / "provisioning" / "alerting" / "alert-rules.yml"),
    ]
    body = []
    for label, path in parts:
        body.append(f"# --- {label} ---")
        body.append(_read(path).rstrip())
        body.append("")
    cell5.source = GRAFANA_HEADER + "\n".join(body).rstrip() + "\n"

    nbformat.write(nb, str(NOTEBOOK))
    nb_check = nbformat.read(str(NOTEBOOK), as_version=4)
    nbformat.validate(nb_check)
    print(f"cell 4 updated: {len(nb_check.cells[4].source)} chars")
    print(f"cell 5 updated: {len(nb_check.cells[5].source)} chars")
    print("notebook validated OK")


if __name__ == "__main__":
    main()
