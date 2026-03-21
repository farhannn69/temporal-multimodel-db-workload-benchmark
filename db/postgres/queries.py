import psycopg2.extras


def _execute(conn, sql, params=None):
    """Run sql with params; return all rows as list[dict]."""
    with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
        cur.execute(sql, params or ())
        return [dict(r) for r in cur.fetchall()]


# Q1: Trending items – top 10 by interaction count in the last ~30 days
def q1(conn, cutoff_ts):
    """Top 10 items by interaction count since cutoff_ts (≈ last 30 days)."""
    return _execute(conn, """
        SELECT i.item_id, i.title, COUNT(*) AS interaction_count
        FROM   interactions ia
        JOIN   items i ON ia.item_id = i.item_id
        WHERE  ia.timestamp >= %s
        GROUP  BY i.item_id, i.title
        ORDER  BY interaction_count DESC
        LIMIT  10
    """, (cutoff_ts,))


# Q2: Weekly trending – top 10 in the last ~7 days
def q2(conn, cutoff_ts):
    """Top 10 items by interaction count since cutoff_ts (≈ last 7 days)."""
    return _execute(conn, """
        SELECT i.item_id, i.title, COUNT(*) AS interaction_count
        FROM   interactions ia
        JOIN   items i ON ia.item_id = i.item_id
        WHERE  ia.timestamp >= %s
        GROUP  BY i.item_id, i.title
        ORDER  BY interaction_count DESC
        LIMIT  10
    """, (cutoff_ts,))


# Q3: User recent history – items interacted with in the last ~90 days
def q3(conn, user_id, cutoff_ts):
    """Items user X interacted with since cutoff_ts, newest first (limit 100)."""
    return _execute(conn, """
        SELECT i.item_id, i.title, ia.rating, ia.timestamp
        FROM   interactions ia
        JOIN   items i ON ia.item_id = i.item_id
        WHERE  ia.user_id   = %s
          AND  ia.timestamp >= %s
        ORDER  BY ia.timestamp DESC
        LIMIT  100
    """, (user_id, cutoff_ts))


# Q4: New items for user – first-time interactions inside a 30-day window
def q4(conn, user_id, window_start):
    """Items user X interacted with for the very first time since window_start."""
    return _execute(conn, """
        SELECT DISTINCT i.item_id, i.title
        FROM   interactions ia
        JOIN   items i ON ia.item_id = i.item_id
        WHERE  ia.user_id    = %s
          AND  ia.timestamp >= %s
          AND  ia.item_id NOT IN (
                   SELECT item_id FROM interactions
                   WHERE  user_id   = %s
                     AND  timestamp < %s
               )
        LIMIT  10
    """, (user_id, window_start, user_id, window_start))


# Q5: Item lifecycle – cold early then hot late (cold → hot pattern)
def q5(conn, mid_month, early_thr, late_thr):
    """Items with low early activity (month <= mid_month) but high late activity."""
    return _execute(conn, """
        SELECT i.item_id, i.title,
               SUM(CASE WHEN ia.month <= %s THEN 1 ELSE 0 END) AS early_count,
               SUM(CASE WHEN ia.month >  %s THEN 1 ELSE 0 END) AS late_count
        FROM   interactions ia
        JOIN   items i ON ia.item_id = i.item_id
        GROUP  BY i.item_id, i.title
        HAVING SUM(CASE WHEN ia.month <= %s THEN 1 ELSE 0 END) < %s
           AND SUM(CASE WHEN ia.month >  %s THEN 1 ELSE 0 END) >= %s
        ORDER  BY late_count DESC
        LIMIT  10
    """, (mid_month, mid_month, mid_month, early_thr, mid_month, late_thr))


# Q6: User activity trend – interaction count per synthetic month
def q6(conn, user_id):
    """Interaction count per synthetic month for user X (time-series view)."""
    return _execute(conn, """
        SELECT month, COUNT(*) AS interaction_count
        FROM   interactions
        WHERE  user_id = %s
        GROUP  BY month
        ORDER  BY month
    """, (user_id,))


# Q7: Popularity rank change – items that climbed most between two month windows
# PostgreSQL uses its native RANK() window function (single-pass CTE query).
def q7(conn, early_start, early_end, late_start, late_end):
    """Items whose popularity rank improved most between the early and late windows.

    Leverages PostgreSQL RANK() window function – executed as a single CTE query,
    avoiding the two-query + Python-ranking workaround needed in MongoDB / Neo4j.
    This is where PostgreSQL's relational engine has a measurable advantage.
    """
    return _execute(conn, """
        WITH early AS (
            SELECT item_id,
                   COUNT(*) AS cnt,
                   RANK() OVER (ORDER BY COUNT(*) DESC) AS rnk
            FROM   interactions
            WHERE  month BETWEEN %s AND %s
            GROUP  BY item_id
        ),
        late AS (
            SELECT item_id,
                   COUNT(*) AS cnt,
                   RANK() OVER (ORDER BY COUNT(*) DESC) AS rnk
            FROM   interactions
            WHERE  month BETWEEN %s AND %s
            GROUP  BY item_id
        )
        SELECT i.item_id, i.title,
               e.rnk  AS early_rank,
               l.rnk  AS late_rank,
               (e.rnk - l.rnk) AS rank_improvement
        FROM   early e
        JOIN   late  l ON e.item_id = l.item_id
        JOIN   items i ON e.item_id = i.item_id
        ORDER  BY rank_improvement DESC
        LIMIT  10
    """, (early_start, early_end, late_start, late_end))


# Q8: Co-interaction window – items attracting the most unique users in ~90 days
def q8(conn, cutoff_ts):
    """Top 10 items by unique user count since cutoff_ts."""
    return _execute(conn, """
        SELECT i.item_id, i.title, COUNT(DISTINCT ia.user_id) AS unique_users
        FROM   interactions ia
        JOIN   items i ON ia.item_id = i.item_id
        WHERE  ia.timestamp >= %s
        GROUP  BY i.item_id, i.title
        ORDER  BY unique_users DESC
        LIMIT  10
    """, (cutoff_ts,))
