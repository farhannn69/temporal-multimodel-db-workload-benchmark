// Switch to (or create) the benchmark database
use("temporal_bench");

// Collection: users
db.users.createIndex({ user_id: 1 }, { unique: true, name: "uq_users_user_id" });


// Collection: items
db.items.createIndex({ item_id: 1 }, { unique: true, name: "uq_items_item_id" });
db.items.createIndex({ first_seen_month: 1, last_seen_month: 1 }, { name: "idx_items_month_range" });


// Collection: interactions
// Single-field indexes
// Q1, Q2 – trending / recent popularity  (range scan on timestamp)
db.interactions.createIndex({ timestamp: 1 }, { name: "idx_interactions_timestamp" });

// synthetic month  (incremental loading filter)
db.interactions.createIndex({ month: 1 }, { name: "idx_interactions_month" });

// Q3 – user recent history  (user_id equality + timestamp range)
db.interactions.createIndex(
    { user_id: 1, timestamp: 1 },
    { name: "idx_interactions_user_timestamp" }
);

// Q1, Q5, Q7 – item popularity / lifecycle  (item_id equality + timestamp range)
db.interactions.createIndex(
    { item_id: 1, timestamp: 1 },
    { name: "idx_interactions_item_timestamp" }
);

// Q4, Q6 – new items / user activity per month
db.interactions.createIndex(
    { user_id: 1, month: 1 },
    { name: "idx_interactions_user_month" }
);