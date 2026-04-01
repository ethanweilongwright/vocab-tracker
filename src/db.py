import sqlite3
import os
from datetime import datetime, timedelta

DB_PATH = os.path.join(os.path.dirname(os.path.dirname(__file__)), "vocab.db")


def get_connection():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def init_db(conn):
    conn.executescript("""
        CREATE TABLE IF NOT EXISTS words (
            id          INTEGER PRIMARY KEY AUTOINCREMENT,
            japanese    TEXT NOT NULL,
            reading     TEXT NOT NULL,
            meaning     TEXT NOT NULL,
            created_at  TEXT DEFAULT (datetime('now'))
        );

        CREATE TABLE IF NOT EXISTS reviews (
            id             INTEGER PRIMARY KEY AUTOINCREMENT,
            word_id        INTEGER REFERENCES words(id),
            reviewed_at    TEXT DEFAULT (datetime('now')),
            correct        INTEGER NOT NULL,
            next_review_at TEXT
        );
    """)
    conn.commit()


def add_word(conn, japanese, reading, meaning):
    cursor = conn.execute(
        "INSERT INTO words (japanese, reading, meaning) VALUES (?, ?, ?)",
        (japanese, reading, meaning)
    )
    conn.commit()
    return cursor.lastrowid


def get_all_words(conn):
    return conn.execute(
        "SELECT * FROM words ORDER BY created_at DESC"
    ).fetchall()


def get_word_by_id(conn, word_id):
    return conn.execute(
        "SELECT * FROM words WHERE id = ?", (word_id,)
    ).fetchone()


def delete_word(conn, word_id):
    conn.execute("DELETE FROM reviews WHERE word_id = ?", (word_id,))
    conn.execute("DELETE FROM words WHERE id = ?", (word_id,))
    conn.commit()


def update_word(conn, word_id, japanese, reading, meaning):
    conn.execute(
        "UPDATE words SET japanese = ?, reading = ?, meaning = ? WHERE id = ?",
        (japanese, reading, meaning, word_id)
    )
    conn.commit()


def migrate_db(conn):
    for sql in [
        "ALTER TABLE words ADD COLUMN interval_days REAL DEFAULT 1.0",
        "ALTER TABLE words ADD COLUMN next_review_at TEXT DEFAULT (datetime('now'))",
    ]:
        try:
            conn.execute(sql)
        except Exception:
            pass  # column already exists
    conn.commit()


def update_word_schedule(conn, word_id, correct):
    word = get_word_by_id(conn, word_id)
    current_interval = word["interval_days"] or 1.0

    new_interval = current_interval * 2.5 if correct else 1.0
    next_review = datetime.now() + timedelta(days=new_interval)

    conn.execute(
        "UPDATE words SET interval_days = ?, next_review_at = ? WHERE id = ?",
        (new_interval, next_review.isoformat(), word_id)
    )
    conn.execute(
        "INSERT INTO reviews (word_id, correct, reviewed_at) VALUES (?, ?, ?)",
        (word_id, 1 if correct else 0, datetime.now().isoformat())
    )
    conn.commit()
