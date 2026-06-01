"""Сплит Wine dataset на train/test."""
from pathlib import Path

import pandas as pd
import yaml
from sklearn.model_selection import train_test_split

ROOT = Path(__file__).resolve().parents[1]
RAW = ROOT / "data" / "raw" / "wine.csv"
OUT = ROOT / "data" / "processed"
TARGET = "wine_class"


def main() -> None:
    # читаем гиперпараметры сплита
    params = yaml.safe_load((ROOT / "params.yaml").read_text(encoding="utf-8"))["prepare"]

    # тут грузим сырой датасет
    df = pd.read_csv(RAW)

    # сплит со стратификацией по классу - чтобы пропорции совпадали в train/test
    train_df, test_df = train_test_split(
        df,
        test_size=params["test_size"],
        random_state=params["random_state"],
        stratify=df[TARGET],
    )

    OUT.mkdir(parents=True, exist_ok=True)
    train_df.to_csv(OUT / "train.csv", index=False)
    test_df.to_csv(OUT / "test.csv", index=False)

    print(f"train: {train_df.shape}, test: {test_df.shape}")


if __name__ == "__main__":
    main()
