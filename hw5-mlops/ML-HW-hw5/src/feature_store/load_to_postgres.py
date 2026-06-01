"""Грузим Wine dataset в Postgres под Feast."""
from datetime import datetime, timezone
from pathlib import Path

import pandas as pd
from sqlalchemy import create_engine, text

ROOT = Path(__file__).resolve().parents[2]
RAW = ROOT / "data" / "raw" / "wine.csv"
DSN = "postgresql+psycopg://feast:feast@localhost:5433/feast"
TABLE = "wine_features"


def main() -> None:
    df = pd.read_csv(RAW).reset_index().rename(columns={"index": "wine_id"})

    # Feast требует event_timestamp; created_timestamp - служебная колонка
    now = datetime.now(timezone.utc)
    df["event_timestamp"] = now
    df["created_timestamp"] = now

    engine = create_engine(DSN)
    with engine.begin() as conn:
        conn.execute(text(f"DROP TABLE IF EXISTS {TABLE}"))
    df.to_sql(TABLE, engine, index=False, if_exists="replace")

    with engine.begin() as conn:
        rows = conn.execute(text(f"SELECT count(*) FROM {TABLE}")).scalar_one()
        print(f"loaded {rows} rows into {TABLE}")


if __name__ == "__main__":
    main()
