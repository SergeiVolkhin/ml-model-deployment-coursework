-- HW8 Step 4: SQL для воспроизведения инцидента качества данных.
-- Применяется ПОСЛЕ первичного профайлинга в DQOps. Каждый ALTER/UPDATE заметно меняет profiling stats
-- и должен поднять алерт во вкладке Incidents.

USE ml_data_quality;

-- 1) Семантический сдвиг: переименование колонки с сохранением типа.
--    Downstream-код, который читал monthly_watch_minutes, теперь либо упадёт по имени, либо начнёт
--    интерпретировать ту же величину как секунды (значения станут в 60 раз меньше ожидаемого).
ALTER TABLE cinema_users
    RENAME COLUMN monthly_watch_minutes TO monthly_watch_seconds;

-- 2) Расширение ENUM: новая категория `enterprise`, которой не было в reference distribution.
--    Ломает downstream дашборды и retention-модель, которая обучалась на 3 категориях.
ALTER TABLE cinema_users
    MODIFY COLUMN subscription_tier ENUM('free', 'premium', 'family', 'enterprise') NOT NULL DEFAULT 'free';

-- 3) Ослабление NOT NULL constraint на email.
--    Это качественный дефект сам по себе - снимать ограничение на ключевой контактный канал
--    нельзя без согласования; DQOps зафиксирует изменение в schema/profiling stats.
ALTER TABLE cinema_users
    MODIFY COLUMN email VARCHAR(255) NULL;

-- 4) Удаление DEFAULT 0 у переименованной колонки.
--    Новые вставки без явного значения будут падать или давать NULL в зависимости от движка/режима.
ALTER TABLE cinema_users
    ALTER COLUMN monthly_watch_seconds DROP DEFAULT;

-- 5) Инжект ~5% NULL в email после ослабления constraint.
--    После шага (3) это формально разрешено, но DQOps зафиксирует резкий рост null rate
--    с 0% до 5% и поднимет инцидент по правилу row_count_null_rate.
UPDATE cinema_users
SET email = NULL
WHERE user_id % 20 = 0;

-- Ожидаемые правила DQOps, которые сработают:
--   * column_schema (email): nullable изменился false -> true
--   * column_schema (subscription_tier): allowed values list расширен
--   * column_schema (monthly_watch_*): имя колонки изменилось
--   * column_nulls_count (email): null_count = 0 -> ~50
--   * column_nulls_percent (email): 0% -> ~5%
