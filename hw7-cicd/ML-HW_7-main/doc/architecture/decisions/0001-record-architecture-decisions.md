# 1. Record architecture decisions

Date: 2026-05-11

## Status

Accepted

## Context

Нужен механизм фиксации архитектурных решений по проекту ml-сервиса iris, чтобы:
- сохранять контекст принятия решений (а не только сам выбор);
- видеть какие альтернативы рассматривались;
- понимать последствия и риски;
- ревьюить решения в pull-request'ах вместе с кодом.

## Decision

Используем формат Architecture Decision Records (ADR) по шаблону Michael Nygard,
утилита adr-tools (https://github.com/npryce/adr-tools).

Файлы хранятся в `doc/architecture/decisions/` с нумерацией `NNNN-kebab-case.md`.

Каждый ADR содержит секции: Status, Context, Decision, Consequences.

## Consequences

Положительные:
- единый формат для всех архитектурных записей;
- ADR версионируются вместе с кодом и попадают в diff пул-реквестов;
- легко найти причины старых решений через `adr list` и `adr search`.

Отрицательные:
- требуется дисциплина команды на ведение ADR при каждом значимом решении;
- утилита adr-tools не имеет нативной поддержки в Windows, нужно ставить через
  WSL или использовать ручное создание файлов по шаблону.
