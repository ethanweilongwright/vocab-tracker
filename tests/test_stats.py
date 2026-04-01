import sqlite3
import pytest
from datetime import datetime, timedelta
from src.db import init_db, migrate_db, add_word, update_word_schedule
from src.stats import get_summary, get_streak, get_accuracy_by_word


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


def test_accuracy_by_word_no_reviews(conn):
    add_word(conn, "食べる", "たべる", "to eat")
    rows = get_accuracy_by_word(conn)
    assert rows[0]["accuracy_pct"] == 0.0
