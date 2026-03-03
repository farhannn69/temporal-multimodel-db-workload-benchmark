"""
test_mongo_connection.py – Verify that Python can connect to MongoDB.

Run:
    python scripts/test_mongo_connection.py
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from pymongo import MongoClient
from pymongo.errors import ConnectionFailure
from config import MONGO_URI, MONGO_HOST, MONGO_PORT, MONGO_DB


def test_connection() -> None:
    print(f"Connecting to MongoDB at {MONGO_HOST}:{MONGO_PORT}/{MONGO_DB} ...")
    try:
        client = MongoClient(MONGO_URI, serverSelectionTimeoutMS=5000)
        # Force the connection by executing a command
        info = client.admin.command("ping")
        server_info = client.server_info()
        client.close()
        print(f"  Connection OK")
        print(f"  Server version: {server_info.get('version', 'unknown')}")
    except ConnectionFailure as exc:
        print(f"  Connection FAILED: {exc}")
        sys.exit(1)
    except Exception as exc:
        print(f"  Connection FAILED: {exc}")
        sys.exit(1)


if __name__ == "__main__":
    test_connection()
