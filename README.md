# Vocab Tracker

A Japanese vocabulary learning app with spaced repetition. Built with Python and Flask.

## Features

- Add, edit, and delete Japanese words with hiragana readings and English meanings
- Quiz mode — type the meaning from the Japanese word
- Spaced repetition — words you know get pushed further out, words you miss come back sooner
- Stats dashboard — accuracy, mastered words, and daily streak
- Fuzzy answer matching — "eat" counts as correct for "to eat"

## Getting Started

### Requirements
- Python 3
- Flask (`pip install flask`)

### Run the web app

```bash
python3 app.py
```

Then open [http://localhost:5000](http://localhost:5000) in your browser.

### Run the CLI

```bash
python3 main.py
```

### Run tests

```bash
python3 -m pytest tests/ -v
```

## Project Structure

```
vocab-tracker/
├── app.py              # Flask web app
├── main.py             # CLI
├── src/
│   ├── db.py           # database logic
│   ├── quiz.py         # word selection and spaced repetition
│   └── stats.py        # accuracy, streak, mastered count
├── templates/          # HTML pages
├── static/
│   └── style.css
└── tests/
```

## How Spaced Repetition Works

Every time you answer a word correctly, the next review is pushed further into the future (interval × 2.5). Answer wrong and it resets to 1 day. A word is considered **mastered** once its interval reaches 8+ days.
