DROP TABLE IF EXISTS interactions CASCADE;
DROP TABLE IF EXISTS items       CASCADE;
DROP TABLE IF EXISTS users       CASCADE;


-- users
CREATE TABLE users (
    user_id    INTEGER     PRIMARY KEY,
    gender     CHAR(1)     NOT NULL,          -- 'M' | 'F'
    age        SMALLINT    NOT NULL,           -- age-group code
    occupation SMALLINT    NOT NULL,           -- occupation code 0-20
    zip_code   VARCHAR(10)
);


-- items  (movies)
CREATE TABLE items (
    item_id          INTEGER      PRIMARY KEY,
    title            VARCHAR(300) NOT NULL,
    genres           VARCHAR(300),             -- pipe-separated genre list
    first_seen_month SMALLINT,                 -- synthetic month 1-12
    last_seen_month  SMALLINT                  -- synthetic month 1-12
);

-- interactions
CREATE TABLE interactions (
    interaction_id BIGSERIAL    PRIMARY KEY,
    user_id        INTEGER      NOT NULL REFERENCES users(user_id),
    item_id        INTEGER      NOT NULL REFERENCES items(item_id),
    rating         NUMERIC(3,1) NOT NULL,
    timestamp      BIGINT       NOT NULL,      -- Unix timestamp (original)
    month          SMALLINT     NOT NULL       -- synthetic month 1-12
);

-- Indexes on interactions  (critical for temporal query performance)

-- Single-column timestamp index  (Q1, Q2 – trending / recent popularity)
CREATE INDEX idx_interactions_timestamp
    ON interactions (timestamp);

-- user + timestamp  (Q3 – user recent history)
CREATE INDEX idx_interactions_user_timestamp
    ON interactions (user_id, timestamp);

-- item + timestamp  (Q1, Q2, Q5, Q7 – item popularity over time)
CREATE INDEX idx_interactions_item_timestamp
    ON interactions (item_id, timestamp);

-- Month index  (for incremental loading queries)
CREATE INDEX idx_interactions_month
    ON interactions (month);

-- user + month  (Q4, Q6 – new items / user activity trend)
CREATE INDEX idx_interactions_user_month
    ON interactions (user_id, month);
