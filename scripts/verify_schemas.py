import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

import psycopg2
from pymongo import MongoClient, ASCENDING
from neo4j import GraphDatabase

from config import (
    PG_CONN_DICT,
    MONGO_URI, MONGO_DB,
    NEO4J_URI, NEO4J_AUTH,
)

SCHEMA_SQL = Path(__file__).parent.parent / "db" / "postgres" / "schema.sql"


# PostgreSQL
def apply_postgres_schema():
    print("\n── PostgreSQL ──────────────────────────────────────────────")
    sql = SCHEMA_SQL.read_text(encoding="utf-8")
    conn = psycopg2.connect(**PG_CONN_DICT)
    conn.autocommit = True
    cur = conn.cursor()
    try:
        cur.execute(sql)
        print("  Schema applied (tables + indexes created).")

        # Verify tables exist
        cur.execute("""
            SELECT table_name
            FROM information_schema.tables
            WHERE table_schema = 'public'
            ORDER BY table_name;
        """)
        tables = [r[0] for r in cur.fetchall()]
        print(f"  Tables found : {tables}")

        # Verify indexes
        cur.execute("""
            SELECT indexname
            FROM pg_indexes
            WHERE schemaname = 'public'
            ORDER BY indexname;
        """)
        indexes = [r[0] for r in cur.fetchall()]
        print(f"  Indexes found: {indexes}")
    finally:
        cur.close()
        conn.close()


# MongoDB
def apply_mongo_indexes():
    print("\n── MongoDB ─────────────────────────────────────────────────")
    client = MongoClient(MONGO_URI, serverSelectionTimeoutMS=5000)
    db = client[MONGO_DB]

    index_specs = {
        "users": [
            ([("user_id", ASCENDING)], {"unique": True,  "name": "uq_users_user_id"}),
        ],
        "items": [
            ([("item_id", ASCENDING)], {"unique": True,  "name": "uq_items_item_id"}),
            ([("first_seen_month", ASCENDING), ("last_seen_month", ASCENDING)],
             {"name": "idx_items_month_range"}),
        ],
        "interactions": [
            ([("timestamp",  ASCENDING)], {"name": "idx_interactions_timestamp"}),
            ([("month",      ASCENDING)], {"name": "idx_interactions_month"}),
            ([("user_id",    ASCENDING), ("timestamp", ASCENDING)],
             {"name": "idx_interactions_user_timestamp"}),
            ([("item_id",    ASCENDING), ("timestamp", ASCENDING)],
             {"name": "idx_interactions_item_timestamp"}),
            ([("user_id",    ASCENDING), ("month", ASCENDING)],
             {"name": "idx_interactions_user_month"}),
        ],
    }

    for coll_name, specs in index_specs.items():
        coll = db[coll_name]
        for keys, opts in specs:
            coll.create_index(keys, **opts)
        idxs = [i["name"] for i in coll.list_indexes()]
        print(f"  {coll_name:15s} indexes: {idxs}")

    client.close()
    print("  Indexes applied.")


# Neo4j
def apply_neo4j_schema():
    print("\n── Neo4j ───────────────────────────────────────────────────")
    driver = GraphDatabase.driver(NEO4J_URI, auth=NEO4J_AUTH)

    statements = [
        "CREATE CONSTRAINT uq_user_id IF NOT EXISTS FOR (u:User) REQUIRE u.user_id IS UNIQUE",
        "CREATE CONSTRAINT uq_item_id IF NOT EXISTS FOR (i:Item) REQUIRE i.item_id IS UNIQUE",
        "CREATE INDEX idx_interacted_timestamp IF NOT EXISTS FOR ()-[r:INTERACTED]-() ON (r.timestamp)",
        "CREATE INDEX idx_interacted_month     IF NOT EXISTS FOR ()-[r:INTERACTED]-() ON (r.month)",
        "CREATE INDEX idx_user_gender          IF NOT EXISTS FOR (u:User) ON (u.gender)",
        "CREATE INDEX idx_item_first_seen      IF NOT EXISTS FOR (i:Item) ON (i.first_seen_month)",
    ]

    with driver.session() as session:
        for stmt in statements:
            session.run(stmt)
        print("  Constraints and indexes applied.")

        # Verify constraints
        result = session.run("SHOW CONSTRAINTS")
        constraints = [r["name"] for r in result]
        print(f"  Constraints : {constraints}")

        # Verify indexes
        result = session.run("SHOW INDEXES YIELD name, type, state WHERE state = 'ONLINE'")
        indexes = [r["name"] for r in result]
        print(f"  Indexes     : {indexes}")

    driver.close()

# Main
def main():
    print("=" * 60)
    print("Step 4 – Schema Verification")
    print("=" * 60)

    errors = []

    try:
        apply_postgres_schema()
    except Exception as e:
        print(f"  ERROR: {e}")
        errors.append(("PostgreSQL", e))

    try:
        apply_mongo_indexes()
    except Exception as e:
        print(f"  ERROR: {e}")
        errors.append(("MongoDB", e))

    try:
        apply_neo4j_schema()
    except Exception as e:
        print(f"  ERROR: {e}")
        errors.append(("Neo4j", e))

    print("\n" + "=" * 60)
    if errors:
        print("RESULT: FAILED")
        for db, err in errors:
            print(f"  {db}: {err}")
        sys.exit(1)
    else:
        print("RESULT: All schemas applied successfully.")
    print("=" * 60)


if __name__ == "__main__":
    main()
