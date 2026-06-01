import marimo

__generated_with = "0.23.3"
app = marimo.App(width="medium")


@app.cell
def _():
    import duckdb
    import pandas as pd
    from sklearn.datasets import load_wine
    return duckdb, load_wine, pd


@app.cell
def _(load_wine, pd):
    # тут грузим Wine в DataFrame
    ds = load_wine(as_frame=True)
    df: pd.DataFrame = ds.frame.rename(columns={"target": "wine_class"})
    df.shape, list(df.columns)[:5]
    return df, ds


@app.cell
def _(df):
    # базовая статистика по числовым фичам
    df.describe().T[["mean", "std", "min", "max"]]
    return


@app.cell
def _(df):
    # распределение по классу
    df["wine_class"].value_counts().sort_index()
    return


@app.cell
def _(df, duckdb):
    # SQL прямо по DataFrame через duckdb - средний alcohol по классу
    duckdb.query(
        "SELECT wine_class, ROUND(AVG(alcohol), 2) AS mean_alcohol, "
        "COUNT(*) AS n FROM df GROUP BY wine_class ORDER BY wine_class"
    ).to_df()
    return


@app.cell
def _(df, duckdb):
    # топ-5 по proline среди класса 0
    duckdb.query(
        "SELECT alcohol, proline FROM df WHERE wine_class = 0 "
        "ORDER BY proline DESC LIMIT 5"
    ).to_df()
    return


if __name__ == "__main__":
    app.run()
