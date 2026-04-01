import sqlite3
import pytest
from src.db import init_db, migrate_db, add_word, get_all_words, get_word_by_id, update_word, delete_word, update_word_schedule, get_all_tags, get_tags_for_word, set_word_tags, get_word_reviews


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


def test_set_and_get_tags(conn):
    word_id = add_word(conn, "食べる", "たべる", "to eat")
    set_word_tags(conn, word_id, ["N5", "verbs"])
    tags = [r["name"] for r in get_tags_for_word(conn, word_id)]
    assert sorted(tags) == ["N5", "verbs"]


def test_get_all_tags(conn):
    word_id = add_word(conn, "食べる", "たべる", "to eat")
    set_word_tags(conn, word_id, ["N5", "food"])
    tags = [r["name"] for r in get_all_tags(conn)]
    assert "N5" in tags
    assert "food" in tags


def test_set_word_tags_replaces_existing(conn):
    word_id = add_word(conn, "食べる", "たべる", "to eat")
    set_word_tags(conn, word_id, ["N5", "verbs"])
    set_word_tags(conn, word_id, ["N4"])
    tags = [r["name"] for r in get_tags_for_word(conn, word_id)]
    assert tags == ["N4"]


def test_set_word_tags_empty_clears_tags(conn):
    word_id = add_word(conn, "食べる", "たべる", "to eat")
    set_word_tags(conn, word_id, ["N5"])
    set_word_tags(conn, word_id, [])
    tags = get_tags_for_word(conn, word_id)
    assert len(tags) == 0


def test_set_word_tags_ignores_blank(conn):
    word_id = add_word(conn, "食べる", "たべる", "to eat")
    set_word_tags(conn, word_id, ["N5", "  ", ""])
    tags = [r["name"] for r in get_tags_for_word(conn, word_id)]
    assert tags == ["N5"]


def test_get_all_words_filter_by_tag(conn):
    id1 = add_word(conn, "食べる", "たべる", "to eat")
    id2 = add_word(conn, "犬", "いぬ", "dog")
    set_word_tags(conn, id1, ["N5"])
    set_word_tags(conn, id2, ["N4"])
    words = get_all_words(conn, tag="N5")
    assert len(words) == 1
    assert words[0]["id"] == id1


def test_get_all_words_no_filter_returns_all(conn):
    add_word(conn, "食べる", "たべる", "to eat")
    add_word(conn, "犬", "いぬ", "dog")
    assert len(get_all_words(conn)) == 2


def test_get_word_reviews_empty(conn):
    word_id = add_word(conn, "食べる", "たべる", "to eat")
    assert get_word_reviews(conn, word_id) == []


def test_get_word_reviews_returns_history(conn):
    word_id = add_word(conn, "食べる", "たべる", "to eat")
    update_word_schedule(conn, word_id, correct=True)
    update_word_schedule(conn, word_id, correct=False)
    reviews = get_word_reviews(conn, word_id)
    assert len(reviews) == 2


def test_get_word_reviews_ordered_newest_first(conn):
    word_id = add_word(conn, "食べる", "たべる", "to eat")
    conn.execute("INSERT INTO reviews (word_id, correct, reviewed_at) VALUES (?, 1, '2024-01-01')", (word_id,))
    conn.execute("INSERT INTO reviews (word_id, correct, reviewed_at) VALUES (?, 0, '2024-01-05')", (word_id,))
    conn.commit()
    reviews = get_word_reviews(conn, word_id)
    assert reviews[0]["reviewed_at"] == "2024-01-05"
    assert reviews[1]["reviewed_at"] == "2024-01-01"


def test_get_word_reviews_only_own_word(conn):
    id1 = add_word(conn, "食べる", "たべる", "to eat")
    id2 = add_word(conn, "飲む", "のむ", "to drink")
    update_word_schedule(conn, id1, correct=True)
    update_word_schedule(conn, id2, correct=True)
    assert len(get_word_reviews(conn, id1)) == 1
    assert len(get_word_reviews(conn, id2)) == 1


def test_migrate_db_idempotent(conn):
    # running migrate again should not raise
    migrate_db(conn)
    migrate_db(conn)
