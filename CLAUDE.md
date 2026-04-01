# Vocab Tracker

A Python web app to help learn Japanese vocabulary, with a CLI fallback.

## What it does
- Add, edit, and delete Japanese words with hiragana readings and English meanings
- Quiz mode with spaced repetition — overdue words are shown first
- Fuzzy answer matching (partial answers accepted)
- Stats: accuracy, mastered word count, daily streak
- Flask web UI with dashboard, words table, and interactive quiz

## Stack
- Python 3
- SQLite (via `sqlite3` standard library) for storage
- Flask for the web UI
- No frontend framework — plain HTML, CSS, JavaScript

## Running the app
```bash
# Web app (recommended)
python3 app.py
# then open http://localhost:5000

# CLI
python3 main.py

# Tests
python3 -m pytest tests/ -v
```

## Conventions
- All business logic in `src/` — Flask routes in `app.py` are thin wrappers
- Database file: `vocab.db` (never commit this)
- Keep functions small and focused
- `src/db.py` is the only file that touches the database

## Project structure
```
vocab-tracker/
├── CLAUDE.md
├── .gitignore
├── app.py              # Flask entry point and routes
├── main.py             # CLI entry point
├── src/
│   ├── db.py           # database setup and all queries
│   ├── quiz.py         # word selection logic (spaced repetition)
│   └── stats.py        # summary, streak, accuracy queries
├── templates/          # HTML templates (Jinja2)
├── static/
│   └── style.css       # all styles
└── tests/
    ├── test_db.py
    ├── test_quiz.py
    └── test_stats.py
```

## Spaced repetition algorithm
- Correct answer: `interval_days *= 2.5`
- Wrong answer: `interval_days = 1.0`
- A word is "mastered" when `interval_days >= 8`
- Quiz always picks the most overdue word first; falls back to random if nothing is due
