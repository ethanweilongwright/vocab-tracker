# Vocab Tracker

A Python web app to help learn Japanese vocabulary, with a CLI fallback.

## What it does
- Add, edit, and delete Japanese words with hiragana readings and English meanings
- **Dictionary search** — type a Japanese word and have reading, meaning, and JLPT tag auto-filled via Jisho API
- **Bulk add** — paste multiple words at once (comma or tab-separated)
- **Import/Export** — CSV with UTF-8 BOM (Excel/Numbers compatible)
- **Tags/decks** — tag words with arbitrary labels (e.g. "verbs", "food"); JLPT levels (N5–N1) auto-tagged from Jisho and colour-coded throughout the UI
- **Quiz modes** — Normal (Japanese → English) and Reverse (English → reading); filter by tag; spaced repetition
- **Word detail page** — per-word stats, full review history, example sentences (Tatoeba API)
- **Dashboard** — streak, accuracy, due count, JLPT breakdown, 30-day review sparkline chart
- Fuzzy answer matching (partial answers accepted)

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
- External API calls isolated in `src/dictionary.py` and `src/sentences.py`
- Import/export logic in `src/imex.py` (pure functions, no Flask dependency)
- Jinja2 filters (`relative_date`, `fmt_date`, `tag_class`) registered in `app.py`

## Project structure
```
vocab-tracker/
├── CLAUDE.md
├── .gitignore
├── app.py                  # Flask entry point, routes, and Jinja filters
├── main.py                 # CLI entry point
├── src/
│   ├── db.py               # database setup and all queries
│   ├── quiz.py             # word selection logic (spaced repetition, tag filter)
│   ├── stats.py            # summary, streak, accuracy, due count, daily reviews, JLPT breakdown
│   ├── dictionary.py       # Jisho API lookup (word, reading, meaning, JLPT tags)
│   ├── sentences.py        # Tatoeba API — example sentences for word detail page
│   └── imex.py             # CSV export (UTF-8 BOM), CSV import, bulk-add line parser
├── templates/
│   ├── base.html           # shared layout and nav
│   ├── index.html          # dashboard
│   ├── words.html          # word list, add form, bulk add, import/export
│   ├── word_detail.html    # per-word stats, review history, example sentences
│   ├── edit_word.html      # edit form
│   ├── quiz_start.html     # quiz setup (mode, tag filter, count)
│   ├── quiz_question.html  # question card (normal and reverse modes)
│   ├── quiz_result.html    # answer result
│   └── quiz_done.html      # session summary
├── static/
│   └── style.css           # all styles
└── tests/
    ├── test_db.py
    ├── test_quiz.py
    ├── test_stats.py
    ├── test_sentences.py   # uses unittest.mock to avoid real HTTP calls
    └── test_imex.py
```

## Database schema
```sql
words     (id, japanese, reading, meaning, created_at, interval_days, next_review_at)
reviews   (id, word_id, reviewed_at, correct, next_review_at)
tags      (id, name UNIQUE)
word_tags (word_id, tag_id)  -- many-to-many
```

## Spaced repetition algorithm
- Correct answer: `interval_days *= 2.5`
- Wrong answer: `interval_days = 1.0`
- A word is "mastered" when `interval_days >= 8`
- Quiz always picks the most overdue word first; falls back to random if nothing is due

## Key API routes
| Method | Path | Description |
|--------|------|-------------|
| GET | `/` | Dashboard |
| GET | `/words` | Word list (optional `?tag=N5` filter) |
| POST | `/words/add` | Add single word |
| GET | `/words/<id>` | Word detail page |
| GET/POST | `/words/<id>/edit` | Edit word |
| POST | `/words/<id>/delete` | Delete word |
| GET | `/words/lookup?q=` | Jisho dictionary lookup (JSON) |
| POST | `/words/bulk_add` | Bulk add from textarea |
| GET | `/words/export.csv` | CSV download |
| POST | `/words/import` | CSV upload |
| GET/POST | `/quiz/start` | Start quiz session |
| GET | `/quiz/question` | Current question |
| POST | `/quiz/answer` | Submit answer |

## Next Steps
- **Search/filter** — text search on the words table (japanese, reading, meaning)
- **Keyboard shortcuts in quiz** — `1`/`2` for correct/wrong on result screen
- **Typing practice mode** — show kanji, type the hiragana reading
- **Kanji breakdown** — stroke order / radical info on word detail page
