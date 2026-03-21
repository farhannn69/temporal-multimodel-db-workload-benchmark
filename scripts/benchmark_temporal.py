import csv
import sys
import time
from pathlib import Path

import pandas as pd
import psycopg2
from pymongo import MongoClient
from neo4j import GraphDatabase

sys.path.insert(0, str(Path(__file__).parent.parent))

from config import (
    PG_CONN_DICT,
    MONGO_URI, MONGO_DB,
    NEO4J_URI, NEO4J_AUTH,
    INTERACTIONS_CSV,
    BENCHMARK_CSV, RESULTS_DIR,
    BENCHMARK_REPETITIONS, NUM_TIME_STEPS,
)

# Import all 8 query functions for each database
from db.postgres.queries import (
    q1 as pg_q1, q2 as pg_q2, q3 as pg_q3, q4 as pg_q4,
    q5 as pg_q5, q6 as pg_q6, q7 as pg_q7, q8 as pg_q8,
)
from db.mongo.queries import (
    q1 as mg_q1, q2 as mg_q2, q3 as mg_q3, q4 as mg_q4,
    q5 as mg_q5, q6 as mg_q6, q7 as mg_q7, q8 as mg_q8,
)
from db.neo4j.queries import (
    q1 as n4_q1, q2 as n4_q2, q3 as n4_q3, q4 as n4_q4,
    q5 as n4_q5, q6 as n4_q6, q7 as n4_q7, q8 as n4_q8,
)

PG_QUERIES = [pg_q1, pg_q2, pg_q3, pg_q4, pg_q5, pg_q6, pg_q7, pg_q8]
MG_QUERIES = [mg_q1, mg_q2, mg_q3, mg_q4, mg_q5, mg_q6, mg_q7, mg_q8]
N4_QUERIES = [n4_q1, n4_q2, n4_q3, n4_q4, n4_q5, n4_q6, n4_q7, n4_q8]

DAY = 86_400  # seconds in one day

CSV_HEADER = ["rep", "is_warmup", "time_step", "query_id", "db",
              "elapsed_ms", "row_count"]


# Pre-computation helpers
def compute_max_ts(csv_path: Path) -> dict:
    """max_ts[t] = maximum UNIX timestamp where month <= t, for t = 1..12.

    This anchors each time step to a realistic calendar maximum so that
    time-window parameters (cutoff_ts = max_ts[t] - N days) fall inside the
    actual data distribution.
    """
    print("  Loading interaction timestamps …", flush=True)
    df = pd.read_csv(csv_path, usecols=["timestamp", "month"])
    max_ts = {}
    for t in range(1, 13):
        subset = df.loc[df["month"] <= t, "timestamp"]
        max_ts[t] = int(subset.max()) if len(subset) else 0
    return max_ts


def get_sample_user(csv_path: Path) -> int:
    """Return the user_id with the highest total interaction count.

    Using the most-active user ensures Q3/Q4/Q6 return non-empty result sets
    across all 12 time steps, producing meaningful latency measurements.
    """
    df = pd.read_csv(csv_path, usecols=["user_id"])
    return int(df["user_id"].value_counts().idxmax())


# Query parameter factory
def build_params(t: int, max_ts: dict, sample_user: int) -> dict:
    """Return a dict mapping query_id (1-8) -> kwargs for time step t.

    Window design:
        Q1  – 30-day trailing window anchored at max_ts[t]
        Q2  –  7-day trailing window (weekly trending)
        Q3  – 90-day trailing window (recent history)
        Q4  – 30-day window for first-time items
        Q5  – month-based split: early=[1, mid_month], late=[mid_month+1, 12]
        Q6  – full user history (no time filter; measures per-month aggregation)
        Q7  – early=[1, mid_month], late=[mid_month+1, t]  (adaptive halves)
        Q8  – 90-day trailing window for unique-user count
    """
    ts  = max_ts[t]
    mid = max(1, t // 2) # split point: months 1..mid vs mid+1..t

    # For very early steps (t=1) late_start > late_end → degenerate window;
    # clamp so late_start <= t (Q7 still runs, returns 0 rows – valid data point).
    late_start = min(t, mid + 1)

    return {
        1: {"cutoff_ts":    ts - 30 * DAY},
        2: {"cutoff_ts":    ts -  7 * DAY},
        3: {"user_id": sample_user, "cutoff_ts":    ts - 90 * DAY},
        4: {"user_id": sample_user, "window_start": ts - 30 * DAY},
        5: {"mid_month": mid, "early_thr": 100, "late_thr": 1},
        6: {"user_id": sample_user},
        7: {"early_start": 1, "early_end": mid,
            "late_start": late_start, "late_end": t},
        8: {"cutoff_ts": ts - 90 * DAY},
    }


# Timing helper
def timed_call(fn, handle, **kwargs):
    """Call fn(handle, **kwargs); return (result_list, elapsed_ms)."""
    t0     = time.perf_counter()
    result = fn(handle, **kwargs)
    elapsed_ms = (time.perf_counter() - t0) * 1_000
    return result, elapsed_ms


# Main benchmark loop
def run_benchmark():
    RESULTS_DIR.mkdir(parents=True, exist_ok=True)

    # Pre-compute (not timed)
    print("\n" + "=" * 60)
    print("  Benchmark pre-computation")
    print("=" * 60)
    max_ts      = compute_max_ts(INTERACTIONS_CSV)
    sample_user = get_sample_user(INTERACTIONS_CSV)
    print(f"  Sample user : {sample_user}")
    print(f"  max_ts[ 1]  : {max_ts[1]}")
    print(f"  max_ts[12]  : {max_ts[12]}")
    print(f"  Reps        : {BENCHMARK_REPETITIONS}  (rep 1 = warm-up)")
    print(f"  Time steps  : {NUM_TIME_STEPS}")
    print(f"  Output      : {BENCHMARK_CSV}\n")

    # Open connections once (reused across all reps)
    print("  Connecting to databases …", flush=True)
    pg_conn = psycopg2.connect(**PG_CONN_DICT)
    pg_conn.autocommit = True          # avoid idle transaction overhead
    mg_client = MongoClient(MONGO_URI)
    mg_db     = mg_client[MONGO_DB]
    neo4j_driver = GraphDatabase.driver(NEO4J_URI, auth=NEO4J_AUTH)
    print("  All connections OK.\n")

    total_measurements = BENCHMARK_REPETITIONS * NUM_TIME_STEPS * 8 * 3
    done = 0

    try:
        with open(BENCHMARK_CSV, "w", newline="") as fout:
            writer = csv.DictWriter(fout, fieldnames=CSV_HEADER)
            writer.writeheader()
            fout.flush()

            for rep in range(1, BENCHMARK_REPETITIONS + 1):
                is_warmup = (rep == 1)
                label = "WARM-UP — results excluded from analysis" if is_warmup \
                        else f"rep {rep}/{BENCHMARK_REPETITIONS}"
                print(f"\n{'='*60}")
                print(f"  Rep {rep}  |  {label}")
                print(f"{'='*60}")

                for t in range(1, NUM_TIME_STEPS + 1):
                    params = build_params(t, max_ts, sample_user)

                    # One Neo4j session per time step (lightweight, clean)
                    with neo4j_driver.session() as neo4j_session:
                        for qid in range(1, 9):
                            p = params[qid]

                            for db_name, fn, handle in [
                                ("postgres", PG_QUERIES[qid - 1], pg_conn),
                                ("mongo",    MG_QUERIES[qid - 1], mg_db),
                                ("neo4j",    N4_QUERIES[qid - 1], neo4j_session),
                            ]:
                                try:
                                    result, ms = timed_call(fn, handle, **p)
                                    row_count  = len(result)
                                except Exception as exc:
                                    print(
                                        f"  [ERROR {db_name.upper()}] "
                                        f"step={t} Q{qid}: {exc}"
                                    )
                                    ms, row_count = 0.0, -1

                                writer.writerow({
                                    "rep":        rep,
                                    "is_warmup":  is_warmup,
                                    "time_step":  t,
                                    "query_id":   qid,
                                    "db":         db_name,
                                    "elapsed_ms": round(ms, 4),
                                    "row_count":  row_count,
                                })
                                fout.flush()

                                done += 1
                                pct = done / total_measurements * 100
                                tag = "WU" if is_warmup else f"R{rep}"
                                print(
                                    f"  [{tag}] step={t:>2}/12  Q{qid}  "
                                    f"{db_name:<8}  {ms:>9.2f} ms  "
                                    f"({row_count:>4} rows)  "
                                    f"[{pct:4.1f}%]",
                                    flush=True,
                                )

    finally:
        pg_conn.close()
        mg_client.close()
        neo4j_driver.close()

    print(f"\n{'='*60}")
    print(f"  Benchmark complete!")
    print(f"  {done} measurements recorded → {BENCHMARK_CSV}")
    print(f"{'='*60}\n")

    # Quick console summary
    df = pd.read_csv(BENCHMARK_CSV)
    df = df[df["is_warmup"].astype(str) == "False"]  # exclude warm-up

    print("  Median latency (ms) per DB — averaged across all queries & steps:\n")
    summary = df.groupby("db")["elapsed_ms"].median().sort_values()
    for db, med in summary.items():
        print(f"    {db:<10} {med:>8.2f} ms")
    print()


if __name__ == "__main__":
    run_benchmark()
