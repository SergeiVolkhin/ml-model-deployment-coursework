# DQOps инцидент качества данных - сценарий воспроизведения

Демонстрирует обнаружение инцидента DQ на синтетической таблице `cinema_users`:
эталонная схема -> профайлинг -> применение `02_break_schema.sql` -> повторный профайлинг -> инцидент в DQOps.

## Стек

- MySQL 8.4 (`mysql:8.4.9`) - хранит таблицу `cinema_users` с эталонной структурой и ~1000 синтетических строк.
- DQOps (`dqops/dqo:1.10.1`) - data quality observability платформа, web-UI на `:8888`.

> Почему 1.10.1, а не последний `1.13.x`. Начиная с `1.11` команда DQOps убрала FREE edition: контейнер логирует
> `DQOps no longer supports a FREE edition. Please contact DQOps sales...` и завершается, даже если передать
> Cloud API key с тарифом FREE. Релиз `1.10.1` (ноябрь 2024) - последний полностью offline community-вариант,
> по функционалу профайлинга и инцидентов достаточен для ДЗ.

Альтернатива контейнеру: `pip install --user dqops` и запуск как локальный python-процесс (см. секцию "Fallback" ниже).

## Шаги

### 1. Запуск стека

```powershell
cd "C:\Python\ML HW\8"
Copy-Item .env.example .env -ErrorAction SilentlyContinue   # если ещё не делал
# --env-file обязателен: compose ищет .env рядом с compose-файлом, у нас он в корне
docker compose --env-file .env -f dqops\docker-compose.dqops.yml up -d
docker compose --env-file .env -f dqops\docker-compose.dqops.yml ps
```

Дождись `mysql` -> `healthy` (HEALTHCHECK через `mysqladmin ping`).

`DQO_CLOUD_API_KEY` можно оставить плейсхолдером - 1.10.1 community работает offline. Если у тебя есть аккаунт
на cloud.dqops.com и хочется синхронизировать профайлы - впиши key в `.env`, compose автоматически прокинет его в контейнер.

### 2. Засев данных

```powershell
.venv\Scripts\python.exe -m pip install pymysql
.venv\Scripts\python.exe dqops\seed_data.py
```

Ожидаемо: `inserted 1000 rows into ml_data_quality.cinema_users`.

Проверить:

```powershell
docker exec dqops_mysql mysql -udqops_user -p"$env:MYSQL_PASSWORD" ml_data_quality -e "SELECT COUNT(*) FROM cinema_users;"
```

### 3. Импорт таблицы в DQOps

1. Открыть `http://localhost:8888` (первый запуск - DQOps Cloud ключ пропускаем, режим local file storage).
2. **Data Sources -> Add data source** -> тип `MySQL`. Параметры:
   - Host: `dqops_mysql` (если DQOps в той же docker-сети) или `host.docker.internal:3306`.
   - User: `dqops_user`, Password: из `.env`.
   - Database: `ml_data_quality`.
3. **Import metadata** -> выбрать `cinema_users`.

### 4. Эталонный профайлинг

1. Открыть таблицу `cinema_users` в DQOps.
2. Запустить **Basic data statistics** (Profiling -> Run profiling checks).
3. Запустить расширенные проверки: `row_count`, `column_nulls_count`, `column_schema`, `column_distinct_count`, `column_string_min_length`. Зафиксировать baseline.

### 5. Применение инцидента

В новой PowerShell:

```powershell
Get-Content dqops\02_break_schema.sql -Raw | docker exec -i dqops_mysql mysql -uroot -p"$env:MYSQL_ROOT_PASSWORD" ml_data_quality
```

Что произойдёт в БД:
- `monthly_watch_minutes` -> `monthly_watch_seconds` (semantic break).
- `subscription_tier` ENUM расширен значением `enterprise`.
- `email` теряет NOT NULL constraint.
- DEFAULT 0 удалён у переименованной колонки.
- 5% строк получают `email = NULL`.

### 6. Повторный профайлинг

1. В DQOps снова запустить Profiling.
2. Открыть вкладку **Incidents** - должен появиться инцидент с группой `column_schema` (drift в metadata) и `column_nulls_percent` для `email`.

### 7. Снять скриншот

Прикладывается к сдаче ДЗ как `08_dqops_incident.png` (в репозиторий не коммитится).

## Fallback: DQOps без Docker

Если образ `dqops/dqo:1.13.1` недоступен (network/registry) - запуск напрямую:

```powershell
.venv\Scripts\python.exe -m pip install --upgrade dqops
.venv\Scripts\python.exe -m dqops
```

При первом запуске DQOps попросит ключ DQOps Cloud - можно пропустить (ответ "n"), он создаст локальный `userhome` в текущей директории. Дальше WEB UI на `http://localhost:8888`. Остальные шаги (3-6) идентичны.

## Откат инцидента (для повторного прогона)

```powershell
docker compose --env-file .env -f dqops\docker-compose.dqops.yml down -v   # удаляет оба volume
docker compose --env-file .env -f dqops\docker-compose.dqops.yml up -d
```

Это пересоздаст таблицу с эталонной схемой через `01_init.sql`. Дальше повторить шаги 2-6.

## Headless quirks

- DQOps на старте интерактивно спрашивает `Log in to DQOps Cloud? [Y,n]`. В compose stdin не TTY, поэтому
  Scanner.nextLine() кидает `NoSuchElementException` и контейнер падает в restart-loop. Compose-команда
  заворачивает entrypoint в `(echo n; exec sleep infinity) | dqo_docker_entrypoint.sh run`: один "n"
  отвечает на prompt, `sleep infinity` держит pipe открытым (Scanner блокируется, без log-spam).
- DQOps требует, чтобы User Home volume был bind-mounted. Named volume `dqops_userhome` он считает unmounted,
  поэтому передаём `DQO_DOCKER_USER_HOME_ALLOW_UNMOUNTED=true`.
- MySQL 8.4 убрал переменную `default-authentication-plugin` (в 8.4 это уже дефолт), поэтому `command:` MySQL
  её не содержит. Healthcheck сделан в форме `CMD-SHELL`, чтобы `$MYSQL_ROOT_PASSWORD` подставлялся шеллом.
