import sys
from pathlib import Path

# allow importing config from project root
sys.path.insert(0, str(Path(__file__).parent.parent))

import pandas as pd
import numpy as np
from config import DATA_RAW_DIR, DATA_PROCESSED_DIR

# paths
ML_DIR       = DATA_RAW_DIR / "ml-1m"
RATINGS_FILE = ML_DIR / "ratings.dat"
MOVIES_FILE  = ML_DIR / "movies.dat"
USERS_FILE   = ML_DIR / "users.dat"

OUT_INTERACTIONS = DATA_PROCESSED_DIR / "interactions_12m.csv"
OUT_ITEMS        = DATA_PROCESSED_DIR / "items.csv"
OUT_USERS        = DATA_PROCESSED_DIR / "users.csv"


def load_ratings(path: Path) -> pd.DataFrame:
    """Load ratings.dat (UserID::MovieID::Rating::Timestamp)."""
    print(f"  Loading {path.name} ...")
    df = pd.read_csv(
        path,
        sep="::",
        engine="python",
        header=None,
        names=["user_id", "item_id", "rating", "timestamp"],
        dtype={"user_id": int, "item_id": int, "rating": float, "timestamp": int},
    )
    print(f"    Rows loaded: {len(df):,}")
    return df


def load_movies(path: Path) -> pd.DataFrame:
    """Load movies.dat (MovieID::Title::Genres)."""
    print(f"  Loading {path.name} ...")
    df = pd.read_csv(
        path,
        sep="::",
        engine="python",
        header=None,
        names=["item_id", "title", "genres"],
        dtype={"item_id": int, "title": str, "genres": str},
        encoding="latin-1",   # MovieLens 1M uses latin-1
    )
    print(f"    Rows loaded: {len(df):,}")
    return df


def load_users(path: Path) -> pd.DataFrame:
    """Load users.dat (UserID::Gender::Age::Occupation::Zip-code)."""
    print(f"  Loading {path.name} ...")
    df = pd.read_csv(
        path,
        sep="::",
        engine="python",
        header=None,
        names=["user_id", "gender", "age", "occupation", "zip_code"],
        dtype={"user_id": int, "gender": str, "age": int,
               "occupation": int, "zip_code": str},
    )
    print(f"    Rows loaded: {len(df):,}")
    return df


def assign_synthetic_months(ratings: pd.DataFrame, n_months: int = 12) -> pd.DataFrame:
    """
    Bin the full timestamp range of the ratings into n_months equal-width
    intervals, assigning each interaction a synthetic month 1..n_months.

    This compresses the real multi-year timeline into a 12-step benchmark
    timeline while preserving temporal ordering.
    """
    ts_min = ratings["timestamp"].min()
    ts_max = ratings["timestamp"].max()
    print(f"\n  Timestamp range:")
    print(f"    Min  : {ts_min}  ({pd.Timestamp(ts_min, unit='s')})")
    print(f"    Max  : {ts_max}  ({pd.Timestamp(ts_max, unit='s')})")
    print(f"    Span : {(ts_max - ts_min) / 86400:.0f} days total")

    # np.digitize returns bins 1..n_months
    bins = np.linspace(ts_min, ts_max + 1, n_months + 1)
    ratings = ratings.copy()
    ratings["month"] = np.digitize(ratings["timestamp"].values, bins)
    # Clamp to [1, n_months] for safety (edge timestamps)
    ratings["month"] = ratings["month"].clip(1, n_months)

    dist = ratings["month"].value_counts().sort_index()
    print(f"\n  Interactions per synthetic month:")
    for m, cnt in dist.items():
        bar = "█" * (cnt // 5000)
        print(f"    Month {m:>2}: {cnt:>7,}  {bar}")

    return ratings



# Main
def main() -> None:
    DATA_PROCESSED_DIR.mkdir(parents=True, exist_ok=True)

    # ── Verify raw files exist ─────────────────────────────────────────────────
    for f in [RATINGS_FILE, MOVIES_FILE, USERS_FILE]:
        if not f.exists():
            print(f"ERROR: {f} not found.")
            print("  Please download MovieLens 1M from:")
            print("  https://grouplens.org/datasets/movielens/1m/")
            print("  and unzip to data/raw/ml-1m/")
            sys.exit(1)

    print("=" * 60)
    print("Step 1 – Loading raw files")
    print("=" * 60)
    ratings = load_ratings(RATINGS_FILE)
    movies  = load_movies(MOVIES_FILE)
    users   = load_users(USERS_FILE)

    # ── Assign synthetic months ────────────────────────────────────────────────
    print("\n" + "=" * 60)
    print("Step 2 – Assigning synthetic months (1-12)")
    print("=" * 60)
    ratings = assign_synthetic_months(ratings, n_months=12)

    # Sort by timestamp so loaders can read in temporal order
    ratings = ratings.sort_values("timestamp").reset_index(drop=True)

    # ── Enrich movies with first/last month info ───────────────────────────────
    item_stats = (
        ratings.groupby("item_id")["month"]
        .agg(first_seen_month="min", last_seen_month="max")
        .reset_index()
    )
    movies = movies.merge(item_stats, on="item_id", how="left")

    # ── Save outputs ───────────────────────────────────────────────────────────
    print("\n" + "=" * 60)
    print("Step 3 – Saving processed CSVs")
    print("=" * 60)

    # interactions_12m.csv – the main benchmark feed
    cols_out = ["user_id", "item_id", "rating", "timestamp", "month"]
    ratings[cols_out].to_csv(OUT_INTERACTIONS, index=False)
    print(f"  Saved: {OUT_INTERACTIONS}")
    print(f"    Rows: {len(ratings):,}")

    # items.csv
    movies.to_csv(OUT_ITEMS, index=False)
    print(f"  Saved: {OUT_ITEMS}")
    print(f"    Rows: {len(movies):,}")

    # users.csv
    users.to_csv(OUT_USERS, index=False)
    print(f"  Saved: {OUT_USERS}")
    print(f"    Rows: {len(users):,}")

    # ── Final summary ──────────────────────────────────────────────────────────
    print("\n" + "=" * 60)
    print("Summary")
    print("=" * 60)
    print(f"  Unique users        : {ratings['user_id'].nunique():>7,}")
    print(f"  Unique items        : {ratings['item_id'].nunique():>7,}")
    print(f"  Total interactions  : {len(ratings):>7,}")
    print(f"  Rating range        : {ratings['rating'].min()} – {ratings['rating'].max()}")
    print(f"  Months covered      : 1 – {ratings['month'].max()}")
    print("\nData preparation complete.")


if __name__ == "__main__":
    main()
