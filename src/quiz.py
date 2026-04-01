def get_due_word(conn, exclude_ids=None):
    exclude_ids = exclude_ids or []

    if exclude_ids:
        placeholders = ",".join("?" * len(exclude_ids))
        exclude_clause = f"AND id NOT IN ({placeholders})"
    else:
        exclude_clause = ""

    word = conn.execute(
        f"SELECT * FROM words WHERE next_review_at <= datetime('now') {exclude_clause} ORDER BY next_review_at ASC LIMIT 1",
        exclude_ids
    ).fetchone()

    if not word:
        word = conn.execute(
            f"SELECT * FROM words WHERE 1=1 {exclude_clause} ORDER BY RANDOM() LIMIT 1",
            exclude_ids
        ).fetchone()

    return word
