from flask import Flask, render_template, request, redirect, url_for, flash, session, jsonify
from src.db import get_connection, init_db, migrate_db, add_word, get_all_words, search_words, get_word_by_id, update_word, delete_word, update_word_schedule, get_all_tags, get_tags_for_word, set_word_tags, get_word_reviews
from src.sentences import get_sentences
from src.imex import export_csv, parse_csv, parse_lines
from src.quiz import get_due_word
from src.stats import get_summary, get_streak, get_accuracy_by_word, get_due_count, get_daily_reviews, get_jlpt_breakdown

app = Flask(__name__)
app.secret_key = "vocab-tracker-secret"

from datetime import date as _date

@app.template_filter('relative_date')
def relative_date_filter(value):
    if not value:
        return '—'
    try:
        d = _date.fromisoformat(str(value)[:10])
    except ValueError:
        return str(value)[:10]
    diff = (d - _date.today()).days
    if diff == 0:   return 'Today'
    if diff == 1:   return 'Tomorrow'
    if diff == -1:  return 'Yesterday'
    if diff < 0:    return f'{-diff}d overdue'
    return f'In {diff}d'

_JLPT_LEVELS = {"N5", "N4", "N3", "N2", "N1"}

@app.template_filter('tag_class')
def tag_class_filter(name):
    if name.upper() in _JLPT_LEVELS:
        return f"tag tag-{name.lower()}"
    return "tag"


@app.template_filter('fmt_date')
def fmt_date_filter(value):
    if not value:
        return ''
    try:
        return _date.fromisoformat(str(value)[:10]).strftime('%-d %b')
    except ValueError:
        return str(value)[:10]


def get_db():
    conn = get_connection()
    init_db(conn)
    migrate_db(conn)
    return conn


@app.route("/")
def index():
    conn = get_db()
    summary = get_summary(conn)
    streak = get_streak(conn)
    due_count = get_due_count(conn)
    daily_reviews = get_daily_reviews(conn)
    jlpt_breakdown = get_jlpt_breakdown(conn)
    accuracy_rows = get_accuracy_by_word(conn)
    return render_template("index.html", summary=summary, streak=streak, due_count=due_count,
                           daily_reviews=daily_reviews, jlpt_breakdown=jlpt_breakdown,
                           accuracy_rows=accuracy_rows)


@app.route("/words")
def words():
    conn = get_db()
    active_tag = request.args.get("tag", "")
    active_q   = request.args.get("q", "").strip()
    if active_q:
        all_words = search_words(conn, active_q, tag=active_tag or None)
    else:
        all_words = get_all_words(conn, tag=active_tag or None)
    word_tags = {w["id"]: [r["name"] for r in get_tags_for_word(conn, w["id"])] for w in all_words}
    return render_template("words.html", words=all_words, word_tags=word_tags,
                           all_tags=get_all_tags(conn), active_tag=active_tag, active_q=active_q)


@app.route("/words/add", methods=["POST"])
def words_add():
    conn     = get_db()
    japanese = request.form["japanese"].strip()
    reading  = request.form["reading"].strip()
    meaning  = request.form["meaning"].strip()
    tags     = request.form.get("tags", "").split(",")
    word_id  = add_word(conn, japanese, reading, meaning)
    set_word_tags(conn, word_id, tags)
    flash(f"Added '{japanese}'", "success")
    return redirect(url_for("words"))


@app.route("/words/<int:word_id>")
def word_detail(word_id):
    conn = get_db()
    word = get_word_by_id(conn, word_id)
    if not word:
        flash("Word not found.", "error")
        return redirect(url_for("words"))
    reviews = get_word_reviews(conn, word_id)
    tags = [r["name"] for r in get_tags_for_word(conn, word_id)]
    total = len(reviews)
    correct = sum(1 for r in reviews if r["correct"])
    accuracy = round(correct / total * 100, 1) if total else 0.0
    sentences = get_sentences(word["japanese"])
    return render_template("word_detail.html", word=word, reviews=reviews,
                           tags=tags, total=total, correct=correct, accuracy=accuracy,
                           sentences=sentences)


@app.route("/words/<int:word_id>/edit", methods=["GET", "POST"])
def words_edit(word_id):
    conn = get_db()
    word = get_word_by_id(conn, word_id)
    if not word:
        flash("Word not found.", "error")
        return redirect(url_for("words"))

    if request.method == "POST":
        update_word(conn, word_id,
                    request.form["japanese"].strip(),
                    request.form["reading"].strip(),
                    request.form["meaning"].strip())
        tags = request.form.get("tags", "").split(",")
        set_word_tags(conn, word_id, tags)
        flash("Word updated.", "success")
        return redirect(url_for("words"))

    word_tag_names = [r["name"] for r in get_tags_for_word(conn, word_id)]
    return render_template("edit_word.html", word=word, word_tags=word_tag_names)


@app.route("/words/export.csv")
def words_export():
    conn = get_db()
    all_words = get_all_words(conn)
    word_tags = {w["id"]: [r["name"] for r in get_tags_for_word(conn, w["id"])] for w in all_words}
    csv_content = export_csv(all_words, word_tags)
    return csv_content, 200, {
        "Content-Type": "text/csv; charset=utf-8",
        "Content-Disposition": "attachment; filename=vocab.csv",
    }


@app.route("/words/import", methods=["POST"])
def words_import():
    file = request.files.get("csv_file")
    if not file or not file.filename:
        flash("No file selected.", "error")
        return redirect(url_for("words"))
    content = file.read().decode("utf-8-sig")  # utf-8-sig strips BOM if present
    rows = parse_csv(content)
    conn = get_db()
    added = skipped = 0
    for row in rows:
        exists = conn.execute(
            "SELECT id FROM words WHERE japanese = ?", (row["japanese"],)
        ).fetchone()
        if exists:
            skipped += 1
            continue
        word_id = add_word(conn, row["japanese"], row["reading"], row["meaning"])
        set_word_tags(conn, word_id, row["tags"])
        added += 1
    parts = []
    if added:   parts.append(f"{added} word{'s' if added != 1 else ''} imported")
    if skipped: parts.append(f"{skipped} skipped (already exist)")
    flash(", ".join(parts) or "Nothing to import.", "success")
    return redirect(url_for("words"))


@app.route("/words/bulk_add", methods=["POST"])
def words_bulk_add():
    text = request.form.get("bulk_text", "")
    rows = parse_lines(text)
    conn = get_db()
    added = skipped = 0
    for row in rows:
        exists = conn.execute(
            "SELECT id FROM words WHERE japanese = ?", (row["japanese"],)
        ).fetchone()
        if exists:
            skipped += 1
            continue
        word_id = add_word(conn, row["japanese"], row["reading"], row["meaning"])
        set_word_tags(conn, word_id, row["tags"])
        added += 1
    parts = []
    if added:   parts.append(f"{added} word{'s' if added != 1 else ''} added")
    if skipped: parts.append(f"{skipped} skipped (already exist)")
    flash(", ".join(parts) or "Nothing to add.", "success")
    return redirect(url_for("words"))


@app.route("/words/lookup")
def words_lookup():
    q = request.args.get("q", "").strip()
    if not q:
        return jsonify({"error": "No query"}), 400
    from src.dictionary import lookup
    result = lookup(q)
    if result is None:
        return jsonify({"error": "Not found"}), 404
    return jsonify(result)


@app.route("/words/<int:word_id>/delete", methods=["POST"])
def words_delete(word_id):
    conn = get_db()
    word = get_word_by_id(conn, word_id)
    if word:
        delete_word(conn, word_id)
        flash(f"Deleted '{word['japanese']}'", "success")
    return redirect(url_for("words"))


@app.route("/quiz")
def quiz():
    return render_template("quiz_start.html", all_tags=get_all_tags(get_db()))


@app.route("/quiz/start", methods=["POST"])
def quiz_start():
    session["quiz_count"]   = int(request.form.get("count", 10))
    session["quiz_index"]   = 0
    session["quiz_correct"] = 0
    session["quiz_seen"]    = []
    session["quiz_tag"]     = request.form.get("tag", "") or None
    session["quiz_mode"]    = request.form.get("mode", "normal")
    return redirect(url_for("quiz_question"))


@app.route("/quiz/question")
def quiz_question():
    total    = session.get("quiz_count", 0)
    index    = session.get("quiz_index", 0)
    seen_ids = session.get("quiz_seen", [])

    if index >= total:
        return redirect(url_for("quiz_done"))

    word = get_due_word(get_db(), exclude_ids=seen_ids, tag=session.get("quiz_tag"))
    if not word:
        return redirect(url_for("quiz_done"))

    session["quiz_current_word_id"] = word["id"]
    return render_template("quiz_question.html",
                           word=word, current=index + 1, total=total,
                           mode=session.get("quiz_mode", "normal"))


@app.route("/quiz/answer", methods=["POST"])
def quiz_answer():
    word_id = int(request.form["word_id"])
    answer  = request.form["answer"].strip().lower()
    conn    = get_db()
    word    = get_word_by_id(conn, word_id)

    mode = session.get("quiz_mode", "normal")
    if mode == "reverse":
        target = word["reading"].lower()
    else:
        target = word["meaning"].lower()
    correct = answer in target or target in answer

    update_word_schedule(conn, word_id, correct)

    seen = session.get("quiz_seen", [])
    seen.append(word_id)
    session["quiz_seen"]    = seen
    session["quiz_index"]   = session.get("quiz_index", 0) + 1
    if correct:
        session["quiz_correct"] = session.get("quiz_correct", 0) + 1

    return render_template("quiz_result.html",
                           word=word, correct=correct, mode=mode,
                           current=session["quiz_index"],
                           total=session["quiz_count"])


@app.route("/quiz/next")
def quiz_next():
    return redirect(url_for("quiz_question"))


@app.route("/quiz/done")
def quiz_done():
    correct = session.get("quiz_correct", 0)
    total   = session.get("quiz_index", 0)
    return render_template("quiz_done.html", correct=correct, total=total)


if __name__ == "__main__":
    app.run(debug=True, port=5000)
