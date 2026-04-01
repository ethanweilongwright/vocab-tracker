from flask import Flask, render_template, request, redirect, url_for, flash, session
from src.db import get_connection, init_db, migrate_db, add_word, get_all_words, get_word_by_id, update_word, delete_word, update_word_schedule
from src.quiz import get_due_word
from src.stats import get_summary, get_streak, get_accuracy_by_word

app = Flask(__name__)
app.secret_key = "vocab-tracker-secret"


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
    accuracy_rows = get_accuracy_by_word(conn)
    return render_template("index.html", summary=summary, streak=streak, accuracy_rows=accuracy_rows)


@app.route("/words")
def words():
    conn = get_db()
    return render_template("words.html", words=get_all_words(conn))


@app.route("/words/add", methods=["POST"])
def words_add():
    japanese = request.form["japanese"].strip()
    reading  = request.form["reading"].strip()
    meaning  = request.form["meaning"].strip()
    add_word(get_db(), japanese, reading, meaning)
    flash(f"Added '{japanese}'", "success")
    return redirect(url_for("words"))


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
        flash("Word updated.", "success")
        return redirect(url_for("words"))

    return render_template("edit_word.html", word=word)


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
    return render_template("quiz_start.html")


@app.route("/quiz/start", methods=["POST"])
def quiz_start():
    session["quiz_count"]   = int(request.form.get("count", 10))
    session["quiz_index"]   = 0
    session["quiz_correct"] = 0
    session["quiz_seen"]    = []
    return redirect(url_for("quiz_question"))


@app.route("/quiz/question")
def quiz_question():
    total    = session.get("quiz_count", 0)
    index    = session.get("quiz_index", 0)
    seen_ids = session.get("quiz_seen", [])

    if index >= total:
        return redirect(url_for("quiz_done"))

    word = get_due_word(get_db(), exclude_ids=seen_ids)
    if not word:
        return redirect(url_for("quiz_done"))

    session["quiz_current_word_id"] = word["id"]
    return render_template("quiz_question.html",
                           word=word, current=index + 1, total=total)


@app.route("/quiz/answer", methods=["POST"])
def quiz_answer():
    word_id = int(request.form["word_id"])
    answer  = request.form["answer"].strip().lower()
    conn    = get_db()
    word    = get_word_by_id(conn, word_id)

    meaning = word["meaning"].lower()
    correct = answer in meaning or meaning in answer

    update_word_schedule(conn, word_id, correct)

    seen = session.get("quiz_seen", [])
    seen.append(word_id)
    session["quiz_seen"]    = seen
    session["quiz_index"]   = session.get("quiz_index", 0) + 1
    if correct:
        session["quiz_correct"] = session.get("quiz_correct", 0) + 1

    return render_template("quiz_result.html",
                           word=word, correct=correct,
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
