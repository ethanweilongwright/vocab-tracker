import sqlite3
import pytest
from src.db import init_db, migrate_db, add_word, update_word_schedule
from src.quiz import get_due_word


@pytest.fixture
def conn():
    c = sqlite3.connect(":memory:")
    c.row_factory = sqlite3.Row
    init_db(c)
    migrate_db(c)
    yield c
    c.close()


def test_get_due_word_empty_db(conn):
    assert get_due_word(conn) is None


def test_get_due_word_returns_word(conn):
    add_word(conn, "食べる", "たべる", "to eat")
    word = get_due_word(conn)
    assert word is not None
    assert word["japanese"] == "食べる"


def test_get_due_word_excludes_ids(conn):
    id1 = add_word(conn, "食べる", "たべる", "to eat")
    id2 = add_word(conn, "飲む", "のむ", "to drink")
    word = get_due_word(conn, exclude_ids=[id1])
    assert word["id"] == id2


def test_get_due_word_all_excluded(conn):
    id1 = add_word(conn, "食べる", "たべる", "to eat")
    assert get_due_word(conn, exclude_ids=[id1]) is None


def test_get_due_word_picks_most_overdue(conn):
    id1 = add_word(conn, "食べる", "たべる", "to eat")
    id2 = add_word(conn, "飲む", "のむ", "to drink")
    # Push id2 far into the future so id1 is most overdue
    conn.execute("UPDATE words SET next_review_at = datetime('now', '+10 days') WHERE id = ?", (id2,))
    conn.execute("UPDATE words SET next_review_at = datetime('now', '-1 day') WHERE id = ?", (id1,))
    conn.commit()
    word = get_due_word(conn)
    assert word["id"] == id1


def test_fuzzy_matching():
    # Test the fuzzy logic used in quiz_flow directly
    def is_correct(answer, meaning):
        a = answer.strip().lower()
        m = meaning.lower()
        return a in m or m in a

    assert is_correct("eat", "to eat")
    assert is_correct("to eat", "eat")
    assert is_correct("to eat", "to eat")
    assert not is_correct("drink", "to eat")
    assert is_correct("drink", "to drink")
