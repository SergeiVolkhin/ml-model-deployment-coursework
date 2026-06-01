"""Seed ~1000 synthetic cinema_users rows into the running MySQL container.

Run after `docker compose -f dqops/docker-compose.dqops.yml up -d mysql` has finished initialising
(it processes 01_init.sql automatically on first start) and the service is healthy.

    python dqops/seed_data.py

Reads MySQL connection settings from .env (or defaults from .env.example).
"""
from __future__ import annotations

import os
import random
import sys
from datetime import datetime, timedelta

try:
    import pymysql
except ImportError:
    print("install pymysql first: pip install pymysql", file=sys.stderr)
    raise

HOST = os.getenv("MYSQL_HOST", "127.0.0.1")
PORT = int(os.getenv("MYSQL_PORT", "3306"))
USER = os.getenv("MYSQL_USER", "dqops_user")
PASSWORD = os.getenv("MYSQL_PASSWORD", "dqops_password_change_me")
DATABASE = os.getenv("MYSQL_DATABASE", "ml_data_quality")

COUNTRIES = ["RU", "KZ", "BY", "AM", "UZ", "GE", "KG", "AZ", "TJ"]
TIERS = ["free", "premium", "family"]
TIER_WEIGHTS = [0.55, 0.30, 0.15]


def _gen_email(uid: int) -> str:
    return f"user_{uid}_{random.randint(1000, 9999)}@example.com"


def main() -> int:
    random.seed(2026)
    conn = pymysql.connect(
        host=HOST, port=PORT, user=USER, password=PASSWORD, database=DATABASE,
        charset="utf8mb4", autocommit=False,
    )
    inserted = 0
    try:
        with conn.cursor() as cur:
            cur.execute("DELETE FROM cinema_users")
            now = datetime.now()
            rows = []
            for uid in range(1, 1001):
                tier = random.choices(TIERS, weights=TIER_WEIGHTS, k=1)[0]
                created_at = now - timedelta(days=random.randint(0, 720))
                rows.append((
                    uid,
                    _gen_email(uid),
                    tier,
                    created_at.strftime("%Y-%m-%d %H:%M:%S"),
                    random.choice(COUNTRIES),
                    random.randint(0, 30000),
                ))
            cur.executemany(
                """INSERT INTO cinema_users (user_id, email, subscription_tier, created_at, country_code, monthly_watch_minutes)
                   VALUES (%s, %s, %s, %s, %s, %s)""",
                rows,
            )
            inserted = cur.rowcount
        conn.commit()
        print(f"inserted {inserted} rows into {DATABASE}.cinema_users")
    finally:
        conn.close()
    return 0


if __name__ == "__main__":
    sys.exit(main())
