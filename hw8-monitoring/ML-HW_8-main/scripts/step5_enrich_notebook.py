"""Step 5 notebook enrichment.

Append three cells AFTER the existing YOLO/Redis demo (originally cells 14-19 of the
template). The original last cell of the template is an empty code cell - we keep the
YOLO chain intact and add a new sub-section "### Архитектурная диаграмма" at the very end:

    1) markdown explaining the Kappa choice (5-7 sentences, RU)
    2) code: full body of architecture/vpp_architecture.py
    3) code: display(Image('vpp_architecture.png')) so Colab renders the PNG inline

If run repeatedly, it is idempotent: looks for an anchor sentinel "ARCH_DIAGRAM_MARKER".
"""
from __future__ import annotations

from pathlib import Path

import nbformat
from nbformat.v4 import new_code_cell, new_markdown_cell

REPO_ROOT = Path(r"C:\Python\ML HW\8")
NOTEBOOK = REPO_ROOT / "notebook" / "HW8_Monitoring_Volkhin_Sergei.ipynb"
SCRIPT = REPO_ROOT / "architecture" / "vpp_architecture.py"
ANCHOR = "ARCH_DIAGRAM_MARKER_HW8_STEP5"

KAPPA_MD = f"""<!-- {ANCHOR} -->
### Архитектурная диаграмма

Архитектура выбрана **Kappa**: единый потоковый пайплайн без отдельного батч-слоя.

- Видеокадры приходят непрерывно (живой поток), искусственно дробить их на батчи нет смысла - время и так в неявных микро-окнах Spark Structured Streaming / Flink.
- Подменять логотипы постфактум в Lambda-style батче бесполезно: пользователь уже посмотрел эпизод.
- Retrain происходит переигрыванием Kafka-топика `video_frames_raw` (retention 21 день) тем же кодом, что и стрим - один пайплайн вместо двух.
- Discriminative-модели (YOLO + segmentation) и Generative-модель (inpainting) подключены как независимые consumer-группы, масштабируются по нагрузке раздельно.
- Observability (Prometheus + Grafana + MLflow) собирает метрики со всех сервисов, feedback loop через A/B и MLflow Registry замыкает контур.

Полное обоснование - в `docs/adr/0001-stream-architecture-for-vpp.md` (ADR по шаблону Nygard, рассмотрены Lambda, Kappa и микро-сервисы без шины).
"""

DISPLAY_CELL = (
    "# Отрисовываем сгенерированную PNG-диаграмму прямо в Colab\n"
    "from IPython.display import Image\n"
    "Image('vpp_architecture.png')\n"
)


def main() -> None:
    nb = nbformat.read(str(NOTEBOOK), as_version=4)

    if any(c.cell_type == "markdown" and ANCHOR in c.source for c in nb.cells):
        print("architecture diagram section already present; nothing to do")
        return

    md_cell = new_markdown_cell(KAPPA_MD)
    code_cell = new_code_cell(SCRIPT.read_text(encoding="utf-8"))
    display_cell = new_code_cell(DISPLAY_CELL)

    nb.cells.extend([md_cell, code_cell, display_cell])
    nbformat.write(nb, str(NOTEBOOK))

    nb_check = nbformat.read(str(NOTEBOOK), as_version=4)
    nbformat.validate(nb_check)
    print(f"appended 3 cells; total cells now: {len(nb_check.cells)}")


if __name__ == "__main__":
    main()
