#!/usr/bin/env python3
"""
Parse raw vocabulary notes and output a CSV ready for import.

Usage:
    python3 scripts/parse_notes.py notes.txt [output.csv]

Output columns: japanese, reading, meaning, tags, _status, _note
  ok      → ready to import
  review  → parsed but something looks off — check _note
  skip    → blank line, section header, or full sentence

Before importing: fix 'review' rows, delete _status/_note columns,
delete 'skip' rows, then use the app's Import CSV button.
"""

import csv
import os
import re
import sys
import time
from concurrent.futures import ThreadPoolExecutor, as_completed

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from src.dictionary import lookup


# ── Text helpers ──────────────────────────────────────────────────────────────

# Normalise all dash/separator variants to ASCII hyphen
_DASH_RE = re.compile(r"[―—–ーｰ\u2015\u2014\u2013]")

def normalise(text):
    text = (text
        .replace("＝", "=").replace("（", "(").replace("）", ")")
        .replace("　", " ")
    )
    # Replace dash-like chars only when surrounded by spaces or at word boundary
    # (preserve ー inside Japanese words like コーヒー)
    text = re.sub(r"(?<!\w)" + _DASH_RE.pattern + r"(?!\w)|"
                  + _DASH_RE.pattern + r"(?=\s)", "-", text)
    return text


def is_japanese(text):
    for ch in text:
        cp = ord(ch)
        if (0x3040 <= cp <= 0x30FF or 0x4E00 <= cp <= 0x9FFF
                or 0xFF65 <= cp <= 0xFF9F):
            return True
    return False

def is_mostly_romaji(text):
    stripped = re.sub(r"[\s\-\(\)～~]", "", text)
    return len(stripped) > 0 and not is_japanese(stripped)

def looks_like_sentence(text):
    """
    Only flag as sentence if it contains explicit grammatical endings.
    Avoids false positives on words that happen to start with は/も/で.
    """
    if len(text) > 8 and is_japanese(text):
        for pat in [
            r"[ますませんいた]$",                          # polite endings
            r"(ています|ていない|ていません)",              # progressive/negative
            r"(なくては|ないと|ないといけない|なければ)",   # obligation
            r"(と思います|と思った)",                      # opinion
            r"(でしょう|でしょうか|ですか？)",             # question forms
        ]:
            if re.search(pat, text):
                return True
    return False

_CONJUGATION = re.compile(
    r"(んだ|った|いた|いだ|した|きた|んで|って|いて|いで"
    r"|なかった|ました|ません|ませんでした|れた|られた|せた|させた)$"
)
def is_conjugated(text):
    return is_japanese(text) and bool(_CONJUGATION.search(text))

_STOP = {"to","a","an","the","of","in","on","at","be","is","are","and","or","for","with","by"}
def meanings_overlap(a, b):
    def tok(s): return {w.lower() for w in re.findall(r"[a-zA-Z]+", s) if w.lower() not in _STOP}
    return bool(tok(a) & tok(b))

def romaji_result_plausible(romaji, reading):
    return len(reading) <= len(re.sub(r"\s+", "", romaji)) / 2 + 1


# ── Parsing ───────────────────────────────────────────────────────────────────

def extract_inline_reading(text):
    m = re.match(r"^(.+?)\s*[（(]\s*([ぁ-んァ-ンa-zA-Z ]+?)\s*[）)]\s*(.*)$", text)
    if m:
        return m.group(1).strip(), m.group(2).strip(), m.group(3).strip()
    return None

def strip_parentheticals(text):
    return re.sub(r"\s*[（(][^）)]*[）)]\s*", "", text).strip()

def is_section_header(line):
    """Skip lines that are organisational headers, not vocabulary."""
    # Ends with colon: "Particles:", "Words:", "Time:" etc.
    if re.search(r":\s*$", line):
        return True
    # Pure English prose (no Japanese, no separator) that's clearly a note
    if not is_japanese(line) and not re.search(r"[-=]", line):
        # Multi-word English sentence (3+ words) — probably a note
        words = line.split()
        if len(words) >= 4:
            return True
    return False

def parse_line(raw):
    line = normalise(raw.strip())
    if not line:
        return None
    if is_section_header(line):
        return None

    word = reading = meaning = ""

    # Separator: hyphen or equals (after normalisation all dashes are -)
    sep = re.search(r"\s*[-=]\s*", line)
    if sep:
        left  = line[:sep.start()].strip()
        right = line[sep.end():].strip()
        # Strip leading dashes from meaning (e.g. "- bookstore" → "bookstore")
        right = re.sub(r"^[-\s]+", "", right).strip()
        inline = extract_inline_reading(left)
        if inline:
            word, reading, _ = inline
            if is_mostly_romaji(reading):
                reading = ""
        else:
            word = strip_parentheticals(left)
        meaning = right
    else:
        inline = extract_inline_reading(line)
        if inline:
            word, reading, rest = inline
            if rest and is_japanese(rest):
                return {"word": word, "reading": reading, "meaning": "",
                        "_raw": raw, "_status": "review",
                        "_note": "extracted from sentence — check meaning"}
        else:
            word = line

    # Strip leading ~ or ～ from grammar pattern words like ～はじめます
    word = re.sub(r"^[～~]+", "", word).strip()

    if not word:
        return None

    return {"word": word, "reading": reading, "meaning": meaning, "_raw": raw}


# ── Jisho lookup with retry ───────────────────────────────────────────────────

def lookup_with_retry(word, retries=3):
    # Try the word as-is, then lowercase (helps capitalised romaji like "Zenbu")
    candidates = [word]
    if is_mostly_romaji(word) and word != word.lower():
        candidates.append(word.lower())
    for candidate in candidates:
        for attempt in range(retries):
            result = lookup(candidate)
            if result is not None:
                return result
            time.sleep(0.4 * (attempt + 1))
    return None

def lookup_key(entry):
    word    = entry.get("word", "").strip()
    reading = entry.get("reading", "").strip()
    meaning = entry.get("meaning", "").strip()
    if not word or looks_like_sentence(word):
        return None
    if is_conjugated(word) or is_mostly_romaji(word) or not reading or not meaning:
        return word
    return None


# ── Enrichment ────────────────────────────────────────────────────────────────

def enrich(entry, cache):
    word    = entry.get("word", "").strip()
    reading = entry.get("reading", "").strip()
    meaning = entry.get("meaning", "").strip()

    if not word:
        entry["_status"] = "skip"
        return entry

    if looks_like_sentence(word):
        entry["_status"] = "skip"
        entry["_note"]   = "looks like a full sentence"
        return entry

    if is_conjugated(word):
        entry["_status"] = "review"
        entry["_note"]   = "conjugated form — find the base form (e.g. 転んだ → 転ぶ)"
        result = cache.get(word)
        if result:
            entry["_tags"] = result.get("tags", [])
            if not reading: entry["reading"] = result.get("reading", "")
            if not meaning: entry["meaning"] = result.get("meaning", "")
        return entry

    need_lookup = is_mostly_romaji(word) or not reading or not meaning
    user_meaning = meaning

    if need_lookup:
        result = cache.get(word)
        if result:
            romaji_input = word if is_mostly_romaji(word) else None
            if romaji_input:
                jisho_reading = result.get("reading", "")
                if not romaji_result_plausible(romaji_input, jisho_reading):
                    entry["_status"] = "review"
                    entry["_note"]   = (f"Jisho returned '{result['word']}' — reading too long "
                                        f"for '{word}', check entry")
                    entry["word"]    = result["word"]
                    entry["reading"] = jisho_reading
                    if not meaning: entry["meaning"] = result.get("meaning", "")
                    entry["_tags"] = result.get("tags", [])
                    return entry
                entry["word"]    = result["word"]
                entry["reading"] = result["reading"]

            if not reading: entry["reading"] = result.get("reading", "")
            if not meaning: entry["meaning"] = result.get("meaning", "")
            entry["_tags"] = result.get("tags", [])

            # Only flag mismatch for romaji lookups — for Japanese input,
            # trust the user's meaning (they likely paraphrased correctly).
            if romaji_input and user_meaning and not meanings_overlap(user_meaning, result.get("meaning", "")):
                entry["_status"] = "review"
                entry["_note"]   = (f"Jisho meaning '{result.get('meaning','')}' doesn't match "
                                    f"your note '{user_meaning}' — check entry")
                return entry
        else:
            entry["_status"] = "review"
            entry["_note"]   = "Jisho lookup failed — fill in manually"
            return entry

    if not entry.get("reading") or not entry.get("meaning"):
        entry["_status"] = "review"
        entry["_note"]   = "missing reading or meaning after lookup"
    else:
        entry.setdefault("_status", "ok")

    return entry


# ── Main ──────────────────────────────────────────────────────────────────────

def main():
    if len(sys.argv) < 2:
        print("Usage: python3 scripts/parse_notes.py notes.txt [output.csv]")
        sys.exit(1)

    input_path  = sys.argv[1]
    output_path = sys.argv[2] if len(sys.argv) > 2 else "notes_import.csv"

    with open(input_path, encoding="utf-8-sig") as f:
        lines = f.readlines()

    # Phase 1: parse
    print(f"Parsing {len(lines)} lines…")
    parsed = [e for raw in lines for e in [parse_line(raw)] if e is not None]
    print(f"  {len(parsed)} entries after filtering headers/blanks")

    # Phase 2: collect unique lookup keys
    keys = {lookup_key(e) for e in parsed} - {None}
    print(f"Fetching {len(keys)} unique Jisho lookups (4 workers, with retry)…")

    # Phase 3: parallel fetch — 4 workers to avoid rate limiting
    cache = {}
    done  = 0
    def fetch(w):
        return w, lookup_with_retry(w)

    with ThreadPoolExecutor(max_workers=4) as pool:
        futures = {pool.submit(fetch, w): w for w in keys}
        for fut in as_completed(futures):
            word, result = fut.result()
            cache[word] = result
            done += 1
            sys.stdout.write(f"\r  {done}/{len(keys)} fetched…  ")
            sys.stdout.flush()
    print()

    # Phase 4: enrich
    entries = [enrich(e, cache) for e in parsed]

    # Write CSV
    with open(output_path, "w", newline="", encoding="utf-8-sig") as f:
        writer = csv.writer(f)
        writer.writerow(["japanese", "reading", "meaning", "tags", "_status", "_note"])
        for e in entries:
            if e.get("_status") == "skip" and not e.get("_note"):
                continue
            writer.writerow([
                e.get("word", ""),
                e.get("reading", ""),
                e.get("meaning", ""),
                ", ".join(e.get("_tags", [])),
                e.get("_status", "review"),
                e.get("_note", ""),
            ])

    ok     = sum(1 for e in entries if e.get("_status") == "ok")
    review = sum(1 for e in entries if e.get("_status") == "review")
    skip   = sum(1 for e in entries if e.get("_status") == "skip")

    print(f"\nDone → {output_path}")
    print(f"  {ok} ready to import")
    print(f"  {review} need review")
    print(f"  {skip} skipped (sentences / blanks / headers)")
    print()
    print("Next steps:")
    print("  1. Open the CSV and review any 'review' rows")
    print("  2. Delete the _status and _note columns")
    print("  3. Delete rows where _status was 'skip'")
    print("  4. Import via the app's Import CSV button")


if __name__ == "__main__":
    main()
