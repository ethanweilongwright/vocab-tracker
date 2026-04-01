def get_due_word(conn, exclude_ids=None, tag=None):
    exclude_ids = exclude_ids or []

    if exclude_ids:
        placeholders = ",".join("?" * len(exclude_ids))
        exclude_clause = f"AND w.id NOT IN ({placeholders})"
    else:
        exclude_clause = ""

    if tag:
        tag_join = "JOIN word_tags wt ON wt.word_id = w.id JOIN tags t ON t.id = wt.tag_id"
        tag_clause = "AND t.name = ?"
        params_tag = [tag]
    else:
        tag_join = ""
        tag_clause = ""
        params_tag = []

    word = conn.execute(
        f"SELECT w.* FROM words w {tag_join} WHERE w.next_review_at <= datetime('now') {tag_clause} {exclude_clause} ORDER BY w.next_review_at ASC LIMIT 1",
        params_tag + exclude_ids
    ).fetchone()

    if not word:
        word = conn.execute(
            f"SELECT w.* FROM words w {tag_join} WHERE 1=1 {tag_clause} {exclude_clause} ORDER BY RANDOM() LIMIT 1",
            params_tag + exclude_ids
        ).fetchone()

    return word
