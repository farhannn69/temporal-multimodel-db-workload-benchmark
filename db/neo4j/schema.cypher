// db/neo4j/schema.cypher
// Neo4j constraints and indexes for the temporal benchmark.
// Reference only – applied programmatically from load_neo4j.py.

CREATE CONSTRAINT uq_user_id IF NOT EXISTS
    FOR (u:User) REQUIRE u.user_id IS UNIQUE;

CREATE CONSTRAINT uq_item_id IF NOT EXISTS
    FOR (i:Item) REQUIRE i.item_id IS UNIQUE;

// Range indexes on relationship properties
// Neo4j 5 supports range indexes on relationship properties natively.

// Q1, Q2 – trending items: range scan on INTERACTED.timestamp
CREATE INDEX idx_interacted_timestamp IF NOT EXISTS
    FOR ()-[r:INTERACTED]-() ON (r.timestamp);

// Q3 – user recent history, Q5 – item lifecycle
CREATE INDEX idx_interacted_month IF NOT EXISTS
    FOR ()-[r:INTERACTED]-() ON (r.month);


// Node property indexes (for lookup by attribute in Q5/Q6/Q7)
CREATE INDEX idx_user_gender IF NOT EXISTS
    FOR (u:User) ON (u.gender);

CREATE INDEX idx_item_first_seen IF NOT EXISTS
    FOR (i:Item) ON (i.first_seen_month);

// Nodes:
//   (:User  { user_id, gender, age, occupation, zip_code })
//   (:Item  { item_id, title, genres, first_seen_month, last_seen_month })
// Relationships:
//   (:User)-[:INTERACTED { rating, timestamp, month }]->(:Item)

