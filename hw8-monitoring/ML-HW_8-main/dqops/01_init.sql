-- HW8 Step 4: эталонная схема таблицы cinema_users для DQOps профайлинга.
-- Применяется автоматически через монтирование в /docker-entrypoint-initdb.d/ MySQL контейнера.

CREATE DATABASE IF NOT EXISTS ml_data_quality
    CHARACTER SET utf8mb4
    COLLATE utf8mb4_unicode_ci;

USE ml_data_quality;

DROP TABLE IF EXISTS cinema_users;

CREATE TABLE cinema_users (
    user_id BIGINT NOT NULL PRIMARY KEY,
    email VARCHAR(255) NOT NULL,
    subscription_tier ENUM('free', 'premium', 'family') NOT NULL DEFAULT 'free',
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    country_code CHAR(2) NOT NULL,
    monthly_watch_minutes INT NOT NULL DEFAULT 0,
    INDEX idx_country (country_code),
    INDEX idx_tier (subscription_tier)
) ENGINE=InnoDB;

-- DQOps будет профайлить именно эту таблицу. Базовые ожидания:
--   * email IS NOT NULL для всех строк
--   * subscription_tier in (free, premium, family)
--   * monthly_watch_minutes >= 0
--   * country_code: 2-буквенный ISO код
