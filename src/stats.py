from datetime import datetime, timedelta


def get_summary(conn):
    total_words   = conn.execute("SELECT COUNT(*) FROM words").fetchone()[0]
    total_reviews = conn.execute("SELECT COUNT(*) FROM reviews").fetchone()[0]
    accuracy_raw  = conn.execute("SELECT AVG(correct) FROM reviews").fetchone()[0]
    mastered      = conn.execute("SELECT COUNT(*) FROM words WHERE interval_days >= 8").fetchone()[0]

    return {
        "total_words":   total_words,
        "total_reviews": total_reviews,
        "accuracy":      accuracy_raw or 0.0,
        "mastered_words": mastered,
    }


def get_streak(conn):
    rows = conn.execute(
        "SELECT reviewed_at FROM reviews WHERE correct = 1 ORDER BY reviewed_at DESC"
    ).fetchall()

    reviewed_dates = {row["reviewed_at"][:10] for row in rows}

    streak = 0
    day = datetime.now().date()
    while str(day) in reviewed_dates:
        streak += 1
        day -= timedelta(days=1)
    return streak


def get_daily_reviews(conn, days=30):
    rows = conn.execute("""
        SELECT substr(reviewed_at, 1, 10) as day, COUNT(*) as count
        FROM reviews
        WHERE reviewed_at >= date('now', ?)
        GROUP BY day
    """, (f"-{days} days",)).fetchall()
    counts = {row["day"]: row["count"] for row in rows}
    today = datetime.now().date()
    return [
        {"date": str(today - timedelta(days=i)), "count": counts.get(str(today - timedelta(days=i)), 0)}
        for i in range(days - 1, -1, -1)
    ]


JLPT_LEVELS = ["N5", "N4", "N3", "N2", "N1"]


def get_jlpt_breakdown(conn):
    rows = conn.execute("""
        SELECT t.name, COUNT(DISTINCT wt.word_id) as count
        FROM tags t
        JOIN word_tags wt ON wt.tag_id = t.id
        WHERE t.name IN ('N5','N4','N3','N2','N1')
        GROUP BY t.name
    """).fetchall()
    counts = {r["name"]: r["count"] for r in rows}
    return {level: counts.get(level, 0) for level in JLPT_LEVELS}


def get_due_count(conn):
    return conn.execute(
        "SELECT COUNT(*) FROM words WHERE next_review_at <= datetime('now')"
    ).fetchone()[0]


def get_accuracy_by_word(conn):
    return conn.execute("""
        SELECT w.japanese, w.reading,
               COUNT(r.id) as reviews,
               ROUND(COALESCE(AVG(r.correct), 0) * 100, 1) as accuracy_pct
        FROM words w
        LEFT JOIN reviews r ON r.word_id = w.id
        GROUP BY w.id
        ORDER BY accuracy_pct ASC
    """).fetchall()
