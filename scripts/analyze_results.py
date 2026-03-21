import sys
from pathlib import Path

import numpy as np
import pandas as pd
import matplotlib
matplotlib.use("Agg")  # non-interactive backend (no display required)
import matplotlib.pyplot as plt
import matplotlib.ticker as mticker
import seaborn as sns

sys.path.insert(0, str(Path(__file__).parent.parent))
from config import BENCHMARK_CSV, RESULTS_DIR, PLOTS_DIR

#  Visual identity for the three databases, and query labels/descriptions
DB_ORDER   = ["postgres", "mongo", "neo4j"]
DB_LABELS  = {"postgres": "PostgreSQL", "mongo": "MongoDB", "neo4j": "Neo4j"}
DB_COLORS  = {"postgres": "#4472C4",    "mongo": "#70AD47", "neo4j": "#ED7D31"}

QUERY_LABELS = {i: f"Q{i}" for i in range(1, 9)}
QUERY_DESCRIPTIONS = {
    1: "Q1 Trending-30d",
    2: "Q2 Trending-7d",
    3: "Q3 User History",
    4: "Q4 New Items",
    5: "Q5 Cold→Hot",
    6: "Q6 Activity Trend",
    7: "Q7 Rank Change",
    8: "Q8 Unique Users",
}

sns.set_theme(style="whitegrid", font_scale=1.1)
plt.rcParams.update({
    "axes.spines.top":    False,
    "axes.spines.right":  False,
    "figure.dpi":         100,
})
DPI_SAVE = 300


# Data loading  
def load_data(csv_path: Path) -> pd.DataFrame:
    df = pd.read_csv(csv_path)
    # Normalise is_warmup (Python csv writes True/False as strings)
    df["is_warmup"] = df["is_warmup"].astype(str).str.upper() == "TRUE"
    df = df[~df["is_warmup"]].copy()                # drop warm-up rep
    df = df[df["elapsed_ms"] > 0].copy()            # drop error rows (-1)
    df["db_label"]    = df["db"].map(DB_LABELS)
    df["query_label"] = df["query_id"].map(QUERY_LABELS)
    return df


#  Statistics
def compute_stats(df: pd.DataFrame) -> pd.DataFrame:
    """Median / mean / std / p95 per (db, query_id)."""
    return (
        df.groupby(["db", "query_id"])["elapsed_ms"]
        .agg(
            median=lambda x: x.median(),
            mean=lambda x:   x.mean(),
            std=lambda x:    x.std(),
            p95=lambda x:    x.quantile(0.95),
            min=lambda x:    x.min(),
            max=lambda x:    x.max(),
            n="count",
        )
        .reset_index()
    )


#  Helper: pivot for median latency 
def pivot_median(df: pd.DataFrame) -> pd.DataFrame:
    """rows=query_id, cols=db  – median elapsed_ms."""
    piv = (
        df.groupby(["query_id", "db"])["elapsed_ms"]
        .median()
        .unstack("db")
        .reindex(columns=DB_ORDER)
    )
    piv.index = [f"Q{i}" for i in piv.index]
    return piv


# Figure 1: Grouped bar – median latency per query
def fig1_median_bar(df: pd.DataFrame, out_dir: Path):
    piv = pivot_median(df)
    x   = np.arange(len(piv))
    w   = 0.25
    offsets = [-w, 0, w]

    fig, ax = plt.subplots(figsize=(13, 6))
    for i, db in enumerate(DB_ORDER):
        ax.bar(
            x + offsets[i], piv[db], w,
            label=DB_LABELS[db],
            color=DB_COLORS[db],
            edgecolor="white", linewidth=0.5,
        )

    # log scale
    ax.set_yscale("log")
    ax.set_ylabel("Median Latency (ms) — log scale", fontsize=12)

    # Clean tick labels: show actual ms values instead of 10^n notation
    ax.yaxis.set_major_formatter(
        mticker.FuncFormatter(lambda v, _: f"{v:g}")
    )

    ax.set_xticks(x)
    ax.set_xticklabels(piv.index, fontsize=11)
    ax.set_xlabel("Query", fontsize=12)
    ax.legend(title="Database", fontsize=10)
    plt.tight_layout()
    path = out_dir / "fig1_median_latency_by_query.png"
    fig.savefig(path, dpi=DPI_SAVE, bbox_inches="tight")
    plt.close(fig)
    print(f"  Saved: {path}")


# Figure 2: Temporal evolution – 2×4 subplots
def fig2_temporal_evolution(df: pd.DataFrame, out_dir: Path):
    fig, axes = plt.subplots(2, 4, figsize=(18, 8), sharex=True)
    axes_flat = axes.flatten()

    for idx, qid in enumerate(range(1, 9)):
        ax = axes_flat[idx]
        for db in DB_ORDER:
            sub = df[(df["query_id"] == qid) & (df["db"] == db)]
            ts_med = sub.groupby("time_step")["elapsed_ms"].median()
            ax.plot(
                ts_med.index, ts_med.values,
                label=DB_LABELS[db],
                color=DB_COLORS[db],
                marker="o", markersize=4, linewidth=1.8,
            )
        ax.set_title(f"{QUERY_DESCRIPTIONS[qid]}", fontsize=10, fontweight="bold")
        ax.set_xlabel("Time Step", fontsize=9)
        ax.set_ylabel("Median (ms)", fontsize=9)
        ax.tick_params(labelsize=8)
        if idx == 0:
            ax.legend(fontsize=8, loc="upper left")

    plt.tight_layout()
    path = out_dir / "fig2_temporal_evolution.png"
    fig.savefig(path, dpi=DPI_SAVE, bbox_inches="tight")
    plt.close(fig)
    print(f"  Saved: {path}")


# Figure 3: Heatmap – Q × DB median latency
def fig3_heatmap(df: pd.DataFrame, out_dir: Path):
    piv = pivot_median(df)
    piv.columns = [DB_LABELS[c] for c in piv.columns]

    fig, ax = plt.subplots(figsize=(8, 6))
    sns.heatmap(
        piv,
        annot=True,
        fmt=".1f",
        cmap="YlOrRd",
        linewidths=0.5,
        linecolor="white",
        cbar_kws={"label": "Median Latency (ms)", "shrink": 0.8},
        ax=ax,
    )
    ax.set_xlabel("Database", fontsize=11)
    ax.set_ylabel("Query", fontsize=11)
    ax.tick_params(axis="x", labelsize=10)
    ax.tick_params(axis="y", labelsize=10, rotation=0)
    plt.tight_layout()
    path = out_dir / "fig3_heatmap.png"
    fig.savefig(path, dpi=DPI_SAVE, bbox_inches="tight")
    plt.close(fig)
    print(f"  Saved: {path}")


# Figure 4: Speedup ratio vs PostgreSQL baseline
def fig4_speedup(df: pd.DataFrame, out_dir: Path):
    piv    = pivot_median(df)
    pg_med = piv["postgres"]

    speedup = pd.DataFrame({
        "MongoDB": pg_med / piv["mongo"],
        "Neo4j":   pg_med / piv["neo4j"],
    })

    x = np.arange(len(speedup))
    w = 0.35

    fig, ax = plt.subplots(figsize=(12, 5))
    bars_mg = ax.bar(
        x - w / 2, speedup["MongoDB"], w,
        label="MongoDB", color=DB_COLORS["mongo"],
        edgecolor="white", linewidth=0.5,
    )
    bars_n4 = ax.bar(
        x + w / 2, speedup["Neo4j"], w,
        label="Neo4j", color=DB_COLORS["neo4j"],
        edgecolor="white", linewidth=0.5,
    )

    ax.axhline(1.0, linestyle="--", color="#4472C4", linewidth=1.5,
               label="PostgreSQL baseline (1.0×)")

    # Annotate bars with their value
    for bar in list(bars_mg) + list(bars_n4):
        h = bar.get_height()
        ax.text(
            bar.get_x() + bar.get_width() / 2, h + 0.02,
            f"{h:.2f}×", ha="center", va="bottom", fontsize=8,
        )

    ax.set_xticks(x)
    ax.set_xticklabels(speedup.index, fontsize=11)
    ax.set_xlabel("Query", fontsize=12)
    ax.set_ylabel("Speedup Ratio  (PostgreSQL time / DB time)", fontsize=12)
    ax.legend(fontsize=10)
    ax.yaxis.set_major_formatter(mticker.FormatStrFormatter("%.1f"))
    plt.tight_layout()
    path = out_dir / "fig4_speedup_ratio.png"
    fig.savefig(path, dpi=DPI_SAVE, bbox_inches="tight")
    plt.close(fig)
    print(f"  Saved: {path}")


# Console summary
def print_summary(stats: pd.DataFrame):
    print("\n" + "=" * 76)
    print("  Benchmark Summary  (warm-up rep excluded)")
    print("=" * 76)
    print(f"  {'DB':<12} {'Query':<8} {'Median ms':>10} {'Mean ms':>10} "
          f"{'Std ms':>9} {'P95 ms':>9} {'Min ms':>9} {'Max ms':>9}")
    print(f"  {'-'*12} {'-'*8} {'-'*10} {'-'*10} {'-'*9} {'-'*9} {'-'*9} {'-'*9}")

    for db in DB_ORDER:
        sub = stats[stats["db"] == db].sort_values("query_id")
        for _, row in sub.iterrows():
            print(
                f"  {DB_LABELS[db]:<12} Q{int(row['query_id']):<7} "
                f"{row['median']:>10.2f} {row['mean']:>10.2f} "
                f"{row['std']:>9.2f} {row['p95']:>9.2f} "
                f"{row['min']:>9.2f} {row['max']:>9.2f}"
            )
        print()

    print("=" * 76)
    print("\n  Median latency OVERALL (all queries, all time steps):\n")
    for db in DB_ORDER:
        med = stats[stats["db"] == db]["median"].mean()
        print(f"    {DB_LABELS[db]:<12}  {med:>8.2f} ms (mean of per-query medians)")
    print()


# Entry point
def main():
    print("\n" + "=" * 60)
    print("  Analyzing benchmark results …")
    print("=" * 60 + "\n")

    if not BENCHMARK_CSV.exists():
        print(f"  ERROR: {BENCHMARK_CSV} not found.")
        print("  Run scripts/benchmark_temporal.py first.\n")
        sys.exit(1)

    PLOTS_DIR.mkdir(parents=True, exist_ok=True)

    df    = load_data(BENCHMARK_CSV)
    stats = compute_stats(df)

    # Save full stats table
    stats_path = RESULTS_DIR / "summary_stats.csv"
    stats.to_csv(stats_path, index=False)
    print(f"  Stats table  → {stats_path}")

    # Generate all four figures
    print("  Generating figures …\n")
    fig1_median_bar(df, PLOTS_DIR)
    fig2_temporal_evolution(df, PLOTS_DIR)
    fig3_heatmap(df, PLOTS_DIR)
    fig4_speedup(df, PLOTS_DIR)

    print_summary(stats)

    print(f"  All plots saved to  {PLOTS_DIR}/")
    print(f"  Stats CSV saved to  {stats_path}\n")
    print(
        "  All done. See docs/results_summary.md for the full research\n"
        "  paper description with results already filled in.\n"
    )


if __name__ == "__main__":
    main()
