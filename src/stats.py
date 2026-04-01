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
