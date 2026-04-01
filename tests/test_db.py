import sqlite3
import pytest
from src.db import init_db, migrate_db, add_word, get_all_words, get_word_by_id, update_word, delete_word, update_word_schedule


@pytest.fixture
def conn():
    c = sqlite3.connect(":memory:")
    c.row_factory = sqlite3.Row
    init_db(c)
    migrate_db(c)
    yield c
    c.close()


def test_add_word(conn):
    word_id = add_word(conn, "食べる", "たべる", "to eat")
    assert word_id is not None
    word = get_word_by_id(conn, word_id)
    assert word["japanese"] == "食べる"
    assert word["reading"] == "たべる"
    assert word["meaning"] == "to eat"


def test_get_all_words(conn):
    add_word(conn, "食べる", "たべる", "to eat")
    add_word(conn, "飲む", "のむ", "to drink")
    words = get_all_words(conn)
    assert len(words) == 2


def test_get_word_by_id_not_found(conn):
    assert get_word_by_id(conn, 999) is None


def test_update_word(conn):
    word_id = add_word(conn, "食べる", "たべる", "to eat")
    update_word(conn, word_id, "食べる", "たべる", "to eat (updated)")
    word = get_word_by_id(conn, word_id)
    assert word["meaning"] == "to eat (updated)"


def test_delete_word_removes_word(conn):
    word_id = add_word(conn, "食べる", "たべる", "to eat")
    delete_word(conn, word_id)
    assert get_word_by_id(conn, word_id) is None


def test_delete_word_removes_reviews(conn):
    word_id = add_word(conn, "食べる", "たべる", "to eat")
    update_word_schedule(conn, word_id, correct=True)
    delete_word(conn, word_id)
    reviews = conn.execute("SELECT * FROM reviews WHERE word_id = ?", (word_id,)).fetchall()
    assert len(reviews) == 0


def test_update_word_schedule_correct(conn):
    word_id = add_word(conn, "食べる", "たべる", "to eat")
    update_word_schedule(conn, word_id, correct=True)
    word = get_word_by_id(conn, word_id)
    assert word["interval_days"] == 1.0 * 2.5


def test_update_word_schedule_wrong(conn):
    word_id = add_word(conn, "食べる", "たべる", "to eat")
    update_word_schedule(conn, word_id, correct=True)  # first make interval > 1
    update_word_schedule(conn, word_id, correct=False)  # then get it wrong
    word = get_word_by_id(conn, word_id)
    assert word["interval_days"] == 1.0


def test_update_word_schedule_records_review(conn):
    word_id = add_word(conn, "食べる", "たべる", "to eat")
    update_word_schedule(conn, word_id, correct=True)
    reviews = conn.execute("SELECT * FROM reviews WHERE word_id = ?", (word_id,)).fetchall()
    assert len(reviews) == 1
    assert reviews[0]["correct"] == 1


def test_migrate_db_idempotent(conn):
    # running migrate again should not raise
    migrate_db(conn)
    migrate_db(conn)
