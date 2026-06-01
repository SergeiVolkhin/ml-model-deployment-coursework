# Итоговый проект. Сквозная MLOps-платформа

## Цели задания

- Построить production-платформу MLOps, покрывающую полный жизненный цикл модели.
- Автоматизировать путь от данных до вывода старой модели из эксплуатации.

## Условия

Итоговый проект - законченная MLOps-платформа (uneemi): фича-, обучающий и мониторинговый
пайплайны как DAG Airflow; промоут champion/challenger за гейтом качества; горячая
подмена модели в сервинге без рестарта; continuous training по дрифту (Evidently, PSI);
guardrail-откат при срыве latency или доли ошибок. SigLIP 2 (ONNX) работает слоем
извлечения признаков (768d board-эмбеддинги).

## Что внутри

- [`uneemi-mlops-main/`](uneemi-mlops-main/) - полный проект: `dags/`, `serving/`, `feature_repo/`, `monitoring/`, `infra/`, `training/`, `docs/`, `tests/`.
- [`uneemi-mlops-main/README.md`](uneemi-mlops-main/README.md) - подробное описание (также опубликовано как [github.com/SergeiVolkhin/uneemi-mlops](https://github.com/SergeiVolkhin/uneemi-mlops)).
- [`Задание.pdf`](Задание.pdf) - условие итогового задания.
- [`компоненты из перечня.pdf`](компоненты%20из%20перечня.pdf) - перечень компонентов (C1-C9).
- [`MLOps Continuous delivery.pdf`](MLOps%20Continuous%20delivery.pdf) - справочный материал.

---

[← К списку модулей](../README.ru.md)
