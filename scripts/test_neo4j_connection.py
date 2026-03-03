"""
test_neo4j_connection.py – Verify that Python can connect to Neo4j.

Run:
    python scripts/test_neo4j_connection.py
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from neo4j import GraphDatabase
from neo4j.exceptions import ServiceUnavailable, AuthError
from config import NEO4J_URI, NEO4J_AUTH, NEO4J_USER


def test_connection() -> None:
    print(f"Connecting to Neo4j at {NEO4J_URI} (user: {NEO4J_USER}) ...")
    driver = None
    try:
        driver = GraphDatabase.driver(NEO4J_URI, auth=NEO4J_AUTH)
        driver.verify_connectivity()

        with driver.session() as session:
            result = session.run("CALL dbms.components() YIELD name, versions")
            row = result.single()
            name     = row["name"]     if row else "unknown"
            versions = row["versions"] if row else []

        print(f"  Connection OK")
        print(f"  Server: {name} {versions}")
    except AuthError as exc:
        print(f"  Authentication FAILED: {exc}")
        sys.exit(1)
    except ServiceUnavailable as exc:
        print(f"  Connection FAILED (service unavailable): {exc}")
        sys.exit(1)
    except Exception as exc:
        print(f"  Connection FAILED: {exc}")
        sys.exit(1)
    finally:
        if driver:
            driver.close()


if __name__ == "__main__":
    test_connection()
