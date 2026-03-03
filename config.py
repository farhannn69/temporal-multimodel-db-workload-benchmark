"""
config.py – Central configuration loader.

Reads connection settings from a .env file (or environment variables)
and exposes ready-to-use connection factories for PostgreSQL, MongoDB,
and Neo4j.

Usage:
    from config import PG_CONN_STR, MONGO_URI, NEO4J_URI, NEO4J_AUTH
    import psycopg2
    conn = psycopg2.connect(PG_CONN_STR)
"""

import os
from pathlib import Path
from dotenv import load_dotenv

# ── Load .env file from project root ──────────────────────────────────────────
_project_root = Path(__file__).parent
load_dotenv(_project_root / ".env")


# ── PostgreSQL ─────────────────────────────────────────────────────────────────
POSTGRES_HOST     = os.getenv("POSTGRES_HOST", "localhost")
POSTGRES_PORT     = int(os.getenv("POSTGRES_PORT", 5432))
POSTGRES_DB       = os.getenv("POSTGRES_DB", "temporal_bench")
POSTGRES_USER     = os.getenv("POSTGRES_USER", "bench_user")
POSTGRES_PASSWORD = os.getenv("POSTGRES_PASSWORD", "bench_pass")

PG_CONN_STR = (
    f"host={POSTGRES_HOST} "
    f"port={POSTGRES_PORT} "
    f"dbname={POSTGRES_DB} "
    f"user={POSTGRES_USER} "
    f"password={POSTGRES_PASSWORD}"
)

PG_CONN_DICT = {
    "host":     POSTGRES_HOST,
    "port":     POSTGRES_PORT,
    "dbname":   POSTGRES_DB,
    "user":     POSTGRES_USER,
    "password": POSTGRES_PASSWORD,
}


# ── MongoDB ────────────────────────────────────────────────────────────────────
MONGO_HOST     = os.getenv("MONGO_HOST", "localhost")
MONGO_PORT     = int(os.getenv("MONGO_PORT", 27017))
MONGO_DB       = os.getenv("MONGO_DB", "temporal_bench")
MONGO_USER     = os.getenv("MONGO_USER", "bench_user")
MONGO_PASSWORD = os.getenv("MONGO_PASSWORD", "bench_pass")

MONGO_URI = (
    f"mongodb://{MONGO_USER}:{MONGO_PASSWORD}"
    f"@{MONGO_HOST}:{MONGO_PORT}/{MONGO_DB}?authSource=admin"
)


# ── Neo4j ──────────────────────────────────────────────────────────────────────
NEO4J_URI      = os.getenv("NEO4J_URI", "bolt://localhost:7687")
NEO4J_USER     = os.getenv("NEO4J_USER", "neo4j")
NEO4J_PASSWORD = os.getenv("NEO4J_PASSWORD", "bench_pass")
NEO4J_AUTH     = (NEO4J_USER, NEO4J_PASSWORD)


# ── Benchmark settings ─────────────────────────────────────────────────────────
BENCHMARK_REPETITIONS = int(os.getenv("BENCHMARK_REPETITIONS", 5))
NUM_TIME_STEPS        = int(os.getenv("NUM_TIME_STEPS", 12))


# ── Paths ──────────────────────────────────────────────────────────────────────
DATA_RAW_DIR       = _project_root / "data" / "raw"
DATA_PROCESSED_DIR = _project_root / "data" / "processed"
RESULTS_DIR        = _project_root / "results"
PLOTS_DIR          = _project_root / "plots"
DOCS_DIR           = _project_root / "docs"

INTERACTIONS_CSV = DATA_PROCESSED_DIR / "interactions_12m.csv"
USERS_CSV        = DATA_PROCESSED_DIR / "users.csv"
ITEMS_CSV        = DATA_PROCESSED_DIR / "items.csv"
BENCHMARK_CSV    = RESULTS_DIR / "benchmark_results.csv"


if __name__ == "__main__":
    print("=== Config Check ===")
    print(f"PostgreSQL : {POSTGRES_HOST}:{POSTGRES_PORT}/{POSTGRES_DB}")
    print(f"MongoDB    : {MONGO_HOST}:{MONGO_PORT}/{MONGO_DB}")
    print(f"Neo4j      : {NEO4J_URI}")
    print(f"Time steps : {NUM_TIME_STEPS}")
    print(f"Repetitions: {BENCHMARK_REPETITIONS}")
