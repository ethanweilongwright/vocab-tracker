# Vocab Tracker

A Python CLI app to help learn Japanese vocabulary.

## What it does
- Add Japanese words with readings (hiragana/katakana) and English meanings
- Quiz mode to test yourself
- Spaced repetition to schedule reviews based on performance
- Track learning stats

## Stack
- Python 3
- SQLite (via `sqlite3` standard library) for storage
- No external dependencies unless necessary

## Conventions
- All code in `src/`
- Entry point: `main.py`
- Database file: `vocab.db` (never commit this)
- Keep functions small and focused
- CLI interface using `argparse` or simple input prompts

## Project structure
```
vocab-tracker/
├── CLAUDE.md
├── README.md
├── .gitignore
├── main.py
└── src/
    ├── db.py        # database setup and queries
    ├── quiz.py      # quiz and spaced repetition logic
    └── stats.py     # learning stats
```
