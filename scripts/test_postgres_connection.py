"""
test_postgres_connection.py – Verify that Python can connect to PostgreSQL.

Run:
    python scripts/test_postgres_connection.py
"""

import sys
from pathlib import Path

# Allow importing config from project root
sys.path.insert(0, str(Path(__file__).parent.parent))

import psycopg2
from config import PG_CONN_DICT, POSTGRES_HOST, POSTGRES_PORT, POSTGRES_DB


def test_connection() -> None:
    print(f"Connecting to PostgreSQL at {POSTGRES_HOST}:{POSTGRES_PORT}/{POSTGRES_DB} ...")
    try:
        conn = psycopg2.connect(**PG_CONN_DICT)
        cur = conn.cursor()
        cur.execute("SELECT version();")
        version = cur.fetchone()[0]
        cur.close()
        conn.close()
        print(f"  Connection OK")
        print(f"  Server version: {version}")
    except Exception as exc:
        print(f"  Connection FAILED: {exc}")
        sys.exit(1)


if __name__ == "__main__":
    test_connection()
