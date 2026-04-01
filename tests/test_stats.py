import sqlite3
import pytest
from datetime import datetime, timedelta
from src.db import init_db, migrate_db, add_word, update_word_schedule, set_word_tags
from src.stats import get_summary, get_streak, get_accuracy_by_word, get_due_count, get_daily_reviews, get_jlpt_breakdown


@pytest.fixture
def conn():
    c = sqlite3.connect(":memory:")
    c.row_factory = sqlite3.Row
    init_db(c)
    migrate_db(c)
    yield c
    c.close()


def test_summary_empty_db(conn):
    summary = get_summary(conn)
    assert summary["total_words"] == 0
    assert summary["total_reviews"] == 0
    assert summary["accuracy"] == 0.0
    assert summary["mastered_words"] == 0


def test_summary_counts_words(conn):
    add_word(conn, "食べる", "たべる", "to eat")
    add_word(conn, "飲む", "のむ", "to drink")
    summary = get_summary(conn)
    assert summary["total_words"] == 2


def test_summary_accuracy(conn):
    word_id = add_word(conn, "食べる", "たべる", "to eat")
    update_word_schedule(conn, word_id, correct=True)
    update_word_schedule(conn, word_id, correct=False)
    summary = get_summary(conn)
    assert summary["total_reviews"] == 2
    assert summary["accuracy"] == 0.5


def test_summary_mastered(conn):
    word_id = add_word(conn, "食べる", "たべる", "to eat")
    conn.execute("UPDATE words SET interval_days = 8 WHERE id = ?", (word_id,))
    conn.commit()
    summary = get_summary(conn)
    assert summary["mastered_words"] == 1


def test_streak_no_reviews(conn):
    assert get_streak(conn) == 0


def test_streak_reviewed_today(conn):
    word_id = add_word(conn, "食べる", "たべる", "to eat")
    update_word_schedule(conn, word_id, correct=True)
    assert get_streak(conn) == 1


def test_streak_consecutive_days(conn):
    word_id = add_word(conn, "食べる", "たべる", "to eat")
    today = datetime.now().date()
    for days_ago in range(3):
        date = today - timedelta(days=days_ago)
        conn.execute(
            "INSERT INTO reviews (word_id, correct, reviewed_at) VALUES (?, 1, ?)",
            (word_id, date.isoformat())
        )
    conn.commit()
    assert get_streak(conn) == 3


def test_streak_broken(conn):
    word_id = add_word(conn, "食べる", "たべる", "to eat")
    today = datetime.now().date()
    # reviewed today and 2 days ago (gap on yesterday)
    for days_ago in [0, 2]:
        date = today - timedelta(days=days_ago)
        conn.execute(
            "INSERT INTO reviews (word_id, correct, reviewed_at) VALUES (?, 1, ?)",
            (word_id, date.isoformat())
        )
    conn.commit()
    assert get_streak(conn) == 1


def test_accuracy_by_word(conn):
    id1 = add_word(conn, "食べる", "たべる", "to eat")
    id2 = add_word(conn, "飲む", "のむ", "to drink")
    update_word_schedule(conn, id1, correct=True)
    update_word_schedule(conn, id2, correct=False)
    rows = get_accuracy_by_word(conn)
    # weakest first — id2 (0%) should come before id1 (100%)
    assert rows[0]["japanese"] == "飲む"
    assert rows[1]["japanese"] == "食べる"


def test_jlpt_breakdown_all_zero_when_empty(conn):
    breakdown = get_jlpt_breakdown(conn)
    assert breakdown == {"N5": 0, "N4": 0, "N3": 0, "N2": 0, "N1": 0}


def test_jlpt_breakdown_counts_tagged_words(conn):
    id1 = add_word(conn, "食べる", "たべる", "to eat")
    id2 = add_word(conn, "飲む", "のむ", "to drink")
    set_word_tags(conn, id1, ["N5"])
    set_word_tags(conn, id2, ["N5"])
    breakdown = get_jlpt_breakdown(conn)
    assert breakdown["N5"] == 2
    assert breakdown["N4"] == 0


def test_jlpt_breakdown_only_counts_jlpt_tags(conn):
    word_id = add_word(conn, "食べる", "たべる", "to eat")
    set_word_tags(conn, word_id, ["verbs", "N3"])
    breakdown = get_jlpt_breakdown(conn)
    assert breakdown["N3"] == 1
    assert sum(breakdown.values()) == 1


def test_daily_reviews_returns_30_days(conn):
    rows = get_daily_reviews(conn)
    assert len(rows) == 30


def test_daily_reviews_zeros_with_no_reviews(conn):
    rows = get_daily_reviews(conn)
    assert all(r["count"] == 0 for r in rows)


def test_daily_reviews_counts_today(conn):
    word_id = add_word(conn, "食べる", "たべる", "to eat")
    update_word_schedule(conn, word_id, correct=True)
    rows = get_daily_reviews(conn)
    today = str(__import__("datetime").date.today())
    today_row = next(r for r in rows if r["date"] == today)
    assert today_row["count"] == 1


def test_daily_reviews_old_reviews_excluded(conn):
    word_id = add_word(conn, "食べる", "たべる", "to eat")
    conn.execute(
        "INSERT INTO reviews (word_id, correct, reviewed_at) VALUES (?, 1, ?)",
        (word_id, "2000-01-01")
    )
    conn.commit()
    rows = get_daily_reviews(conn)
    assert all(r["count"] == 0 for r in rows)


def test_due_count_none_due(conn):
    word_id = add_word(conn, "食べる", "たべる", "to eat")
    conn.execute("UPDATE words SET next_review_at = datetime('now', '+1 day') WHERE id = ?", (word_id,))
    conn.commit()
    assert get_due_count(conn) == 0


def test_due_count_past_due(conn):
    word_id = add_word(conn, "食べる", "たべる", "to eat")
    conn.execute("UPDATE words SET next_review_at = datetime('now', '-1 day') WHERE id = ?", (word_id,))
    conn.commit()
    assert get_due_count(conn) == 1


def test_due_count_future_not_counted(conn):
    word_id = add_word(conn, "食べる", "たべる", "to eat")
    conn.execute("UPDATE words SET next_review_at = datetime('now', '+1 day') WHERE id = ?", (word_id,))
    conn.commit()
    assert get_due_count(conn) == 0


def test_accuracy_by_word_no_reviews(conn):
    add_word(conn, "食べる", "たべる", "to eat")
    rows = get_accuracy_by_word(conn)
    assert rows[0]["accuracy_pct"] == 0.0
