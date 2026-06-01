"""Step 4 notebook enrichment.

Originally cell 11 is `#SQL` placeholder. We replace it with the contents of
02_break_schema.sql wrapped in a Python string literal (Colab cell), then
print + execute the inject scenario as SQL via `pymysql`. A markdown cell
inserted before the code explains the breakdown of each ALTER/UPDATE in Russian.
"""
from __future__ import annotations

from pathlib import Path

import nbformat
from nbformat.v4 import new_markdown_cell

REPO_ROOT = Path(r"C:\Python\ML HW\8")
NOTEBOOK = REPO_ROOT / "notebook" / "HW8_Monitoring_Volkhin_Sergei.ipynb"
SQL_PATH = REPO_ROOT / "dqops" / "02_break_schema.sql"

ANCHOR_MD_PREFIX = "### Шаг 4. Инцидент Data Quality: разбор `02_break_schema.sql`"

MARKDOWN_BODY = """### Шаг 4. Инцидент Data Quality: разбор `02_break_schema.sql`

Эталонная схема таблицы `cinema_users` зафиксирована в `dqops/01_init.sql`. После первичного профайлинга в DQOps мы применяем SQL ниже и ожидаем, что DQOps поднимет инцидент во вкладке **Incidents**.

Что именно нарушится:
- **`RENAME COLUMN`** `monthly_watch_minutes -> monthly_watch_seconds` - тип не меняется, но семантика ломается в 60 раз (downstream начинает читать секунды как минуты). DQOps `column_schema` check зафиксирует переименование.
- **`MODIFY ENUM`** `subscription_tier` - добавлена категория `enterprise`. Раньше allowed values = {free, premium, family}, теперь 4 значения. DQOps `column_schema` ловит расширение списка.
- **`MODIFY email VARCHAR(255) NULL`** - ослабление NOT NULL constraint. Само по себе считаем качественным дефектом: контактный ключ не должен терять обязательность без согласования.
- **`ALTER COLUMN ... DROP DEFAULT`** - удалён DEFAULT 0 у переименованной колонки. Новые вставки без явного значения теперь падают.
- **`UPDATE ... SET email = NULL`** - 5% строк получают NULL в email. После шага 3 это технически разрешено, но DQOps `column_nulls_percent` поднимет резкий рост с 0% до 5%.

После повторного профайлинга в DQOps инцидент появится в **Incidents** с группой `column_schema` и `column_nulls_percent`. Скрин - см. `screenshots/SCREENSHOTS.md` #08.
"""


def main() -> None:
    nb = nbformat.read(str(NOTEBOOK), as_version=4)

    # Cell 11 в исходном шаблоне был `#SQL`. После вставки markdown-ячейки на Шаге 3
    # все индексы после 7 сдвинулись на 1, поэтому ищем по содержимому, не по индексу.
    target_idx = None
    for i, cell in enumerate(nb.cells):
        if cell.cell_type == "code" and cell.source.strip().startswith("#SQL"):
            target_idx = i
            break
    assert target_idx is not None, "could not find original #SQL placeholder cell"

    sql_text = SQL_PATH.read_text(encoding="utf-8").rstrip()
    new_cell_source = (
        "# Содержимое dqops/02_break_schema.sql (применяется к ml_data_quality.cinema_users)\n"
        "# В Colab можно подключиться к локальному MySQL через port-forward или применить файл прямым\n"
        "# docker exec из терминала (см. dqops/README.md).\n\n"
        "BREAK_SCHEMA_SQL = '''\n"
        + sql_text
        + "\n'''\n\n"
        "print(BREAK_SCHEMA_SQL)\n"
    )
    nb.cells[target_idx].source = new_cell_source
    nb.cells[target_idx].outputs = []
    nb.cells[target_idx].execution_count = None

    # Insert markdown explanation right BEFORE the code cell (so it reads naturally in the rendered notebook).
    already_present = any(c.cell_type == "markdown" and ANCHOR_MD_PREFIX in c.source for c in nb.cells)
    if not already_present:
        nb.cells.insert(target_idx, new_markdown_cell(MARKDOWN_BODY))
        print(f"inserted DQOps markdown at index {target_idx}; SQL cell now at {target_idx + 1}")
    else:
        print("DQOps markdown already present; skipped insert")

    nbformat.write(nb, str(NOTEBOOK))
    nb_check = nbformat.read(str(NOTEBOOK), as_version=4)
    nbformat.validate(nb_check)
    print(f"total cells now: {len(nb_check.cells)}")


if __name__ == "__main__":
    main()
