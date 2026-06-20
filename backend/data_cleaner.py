"""Data preparation script for ASTraM traffic event records."""

from pathlib import Path

import pandas as pd

DATA_DIR = Path(__file__).parent / "data"
INPUT_PATH = DATA_DIR / "astram_data.csv"
OUTPUT_PATH = DATA_DIR / "cleaned_astram_data.csv"


def load_raw_data(path: Path = INPUT_PATH) -> pd.DataFrame:
    return pd.read_csv(path)


def clean_astram_data(df: pd.DataFrame) -> pd.DataFrame:
    cleaned = df.copy()

    cleaned = cleaned.dropna(subset=["latitude", "longitude"])
    cleaned = cleaned[
        (cleaned["latitude"] != 0) & (cleaned["longitude"] != 0)
    ]

    cleaned["created_date"] = pd.to_datetime(
        cleaned["created_date"], errors="coerce"
    )

    resolved_col = "resolved_date" if "resolved_date" in cleaned.columns else "resolved_datetime"
    cleaned[resolved_col] = pd.to_datetime(cleaned[resolved_col], errors="coerce")

    cleaned = cleaned.dropna(subset=["created_date", resolved_col])

    cleaned["resolution_time_mins"] = (
        cleaned[resolved_col] - cleaned["created_date"]
    ).dt.total_seconds() / 60

    cleaned["event_cause"] = cleaned["event_cause"].fillna("unknown")

    return cleaned


def save_cleaned_data(df: pd.DataFrame, path: Path = OUTPUT_PATH) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    df.to_csv(path, index=False)


if __name__ == "__main__":
    raw_df = load_raw_data()
    rows_before = len(raw_df)

    cleaned_df = clean_astram_data(raw_df)
    rows_after = len(cleaned_df)

    save_cleaned_data(cleaned_df)

    print(f"Rows before cleaning: {rows_before}")
    print(f"Rows after cleaning:  {rows_after}")
    print(f"Cleaned data saved to: {OUTPUT_PATH}")
