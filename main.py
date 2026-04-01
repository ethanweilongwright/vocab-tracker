from src.db import get_connection, init_db, migrate_db, add_word, get_all_words, get_word_by_id, update_word, delete_word, update_word_schedule
from src.quiz import get_due_word
from src.stats import get_summary, get_streak, get_accuracy_by_word


def add_word_flow(conn):
    print("\nEnter the word details:")
    japanese = input("Japanese (e.g. 食べる): ").strip()
    reading  = input("Reading  (e.g. たべる): ").strip()
    meaning  = input("Meaning  (e.g. to eat): ").strip()

    if not japanese or not reading or not meaning:
        print("All fields are required.")
        return

    word_id = add_word(conn, japanese, reading, meaning)
    print(f"Saved! (id: {word_id})")


def view_words_flow(conn):
    words = get_all_words(conn)
    if not words:
        print("\nNo words yet. Add some first!")
        return

    print(f"\n{'ID':<4} {'Japanese':<12} {'Reading':<16} {'Meaning':<20} {'Interval':>8}  {'Next Review'}")
    print("-" * 75)
    for row in words:
        interval = f"{row['interval_days']:.1f}d" if row['interval_days'] else "-"
        next_review = row['next_review_at'][:10] if row['next_review_at'] else "-"
        print(f"{row['id']:<4} {row['japanese']:<12} {row['reading']:<16} {row['meaning']:<20} {interval:>8}  {next_review}")


def edit_word_flow(conn):
    view_words_flow(conn)
    try:
        word_id = int(input("\nEnter ID to edit: ").strip())
    except ValueError:
        print("Invalid ID.")
        return

    word = get_word_by_id(conn, word_id)
    if not word:
        print("Word not found.")
        return

    print("Press Enter to keep the current value.")
    japanese = input(f"Japanese [{word['japanese']}]: ").strip() or word['japanese']
    reading  = input(f"Reading  [{word['reading']}]: ").strip()  or word['reading']
    meaning  = input(f"Meaning  [{word['meaning']}]: ").strip()  or word['meaning']

    update_word(conn, word_id, japanese, reading, meaning)
    print("Updated!")


def delete_word_flow(conn):
    view_words_flow(conn)
    try:
        word_id = int(input("\nEnter ID to delete: ").strip())
    except ValueError:
        print("Invalid ID.")
        return

    word = get_word_by_id(conn, word_id)
    if not word:
        print("Word not found.")
        return

    confirm = input(f"Delete '{word['japanese']}' and all its reviews? (y/n): ").strip().lower()
    if confirm == "y":
        delete_word(conn, word_id)
        print("Deleted.")
    else:
        print("Cancelled.")


def stats_flow(conn):
    summary = get_summary(conn)
    streak  = get_streak(conn)

    print("\n--- Your Stats ---")
    print(f"Total words added : {summary['total_words']}")
    print(f"Total reviews     : {summary['total_reviews']}")
    print(f"Overall accuracy  : {summary['accuracy'] * 100:.1f}%")
    print(f"Mastered words    : {summary['mastered_words']}")
    print(f"Current streak    : {streak} day(s)")

    print("\n--- Accuracy by Word (weakest first) ---")
    for row in get_accuracy_by_word(conn):
        bar = "#" * int(row['accuracy_pct'] / 10)
        print(f"  {row['japanese']:<10} {row['reading']:<14} {row['reviews']:>3} reviews  {row['accuracy_pct']:>5.1f}%  {bar}")


def quiz_flow(conn):
    try:
        count = int(input("\nHow many words to review? ").strip())
        if count < 1:
            raise ValueError
    except ValueError:
        print("Please enter a valid number.")
        return

    correct_count = 0
    seen_ids = []
    for i in range(count):
        word = get_due_word(conn, exclude_ids=seen_ids)
        if not word:
            print(f"\nRan out of words after {i} review(s).")
            count = i
            break
        seen_ids.append(word['id'])

        print(f"\n[{i + 1}/{count}] {word['japanese']}  ({word['reading']})")
        answer = input("Meaning: ").strip().lower()
        meaning = word['meaning'].lower()
        correct = answer in meaning or meaning in answer

        if correct:
            print("Correct!")
            correct_count += 1
        else:
            print(f"Wrong. The answer was: {word['meaning']}")

        update_word_schedule(conn, word['id'], correct)

    if count > 0:
        print(f"\nSession complete! {correct_count}/{count} correct ({correct_count / count * 100:.0f}%)")


def main():
    conn = get_connection()
    init_db(conn)
    migrate_db(conn)

    while True:
        print("\n--- Japanese Vocab Tracker ---")
        print("1. Add word")
        print("2. View all words")
        print("3. Edit word")
        print("4. Delete word")
        print("5. Quiz")
        print("6. Stats")
        print("7. Quit")
        choice = input("Choice: ").strip()

        if choice == "1":
            add_word_flow(conn)
        elif choice == "2":
            view_words_flow(conn)
        elif choice == "3":
            edit_word_flow(conn)
        elif choice == "4":
            delete_word_flow(conn)
        elif choice == "5":
            quiz_flow(conn)
        elif choice == "6":
            stats_flow(conn)
        elif choice == "7":
            break
        else:
            print("Invalid choice, try again.")


if __name__ == "__main__":
    main()
