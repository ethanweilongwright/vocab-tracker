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


def get_all_words(conn, tag=None):
    if tag:
        return conn.execute("""
            SELECT DISTINCT w.* FROM words w
            JOIN word_tags wt ON wt.word_id = w.id
            JOIN tags t ON t.id = wt.tag_id
            WHERE t.name = ?
            ORDER BY w.created_at DESC
        """, (tag,)).fetchall()
    return conn.execute("SELECT * FROM words ORDER BY created_at DESC").fetchall()


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
        """CREATE TABLE IF NOT EXISTS tags (
            id   INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL UNIQUE
        )""",
        """CREATE TABLE IF NOT EXISTS word_tags (
            word_id INTEGER NOT NULL REFERENCES words(id),
            tag_id  INTEGER NOT NULL REFERENCES tags(id),
            PRIMARY KEY (word_id, tag_id)
        )""",
    ]:
        try:
            conn.execute(sql)
        except Exception:
            pass  # column/table already exists
    conn.commit()


def get_all_tags(conn):
    return conn.execute("SELECT * FROM tags ORDER BY name").fetchall()


def get_tags_for_word(conn, word_id):
    return conn.execute("""
        SELECT t.name FROM tags t
        JOIN word_tags wt ON wt.tag_id = t.id
        WHERE wt.word_id = ?
        ORDER BY t.name
    """, (word_id,)).fetchall()


def set_word_tags(conn, word_id, tag_names):
    conn.execute("DELETE FROM word_tags WHERE word_id = ?", (word_id,))
    for name in tag_names:
        name = name.strip()
        if not name:
            continue
        conn.execute("INSERT OR IGNORE INTO tags (name) VALUES (?)", (name,))
        tag_id = conn.execute("SELECT id FROM tags WHERE name = ?", (name,)).fetchone()["id"]
        conn.execute("INSERT OR IGNORE INTO word_tags (word_id, tag_id) VALUES (?, ?)", (word_id, tag_id))
    conn.commit()


def search_words(conn, query, tag=None):
    pattern = f"%{query}%"
    if tag:
        return conn.execute("""
            SELECT DISTINCT w.* FROM words w
            JOIN word_tags wt ON wt.word_id = w.id
            JOIN tags t ON t.id = wt.tag_id
            WHERE t.name = ?
              AND (w.japanese LIKE ? OR w.reading LIKE ? OR w.meaning LIKE ?)
            ORDER BY w.created_at DESC
        """, (tag, pattern, pattern, pattern)).fetchall()
    return conn.execute("""
        SELECT * FROM words
        WHERE japanese LIKE ? OR reading LIKE ? OR meaning LIKE ?
        ORDER BY created_at DESC
    """, (pattern, pattern, pattern)).fetchall()


def get_word_reviews(conn, word_id):
    return conn.execute(
        "SELECT reviewed_at, correct FROM reviews WHERE word_id = ? ORDER BY reviewed_at DESC",
        (word_id,)
    ).fetchall()


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
