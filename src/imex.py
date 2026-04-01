import csv
import io


def export_csv(words, word_tags: dict) -> str:
    output = io.StringIO()
    output.write('\ufeff')  # UTF-8 BOM — required for Excel/Numbers to read Japanese correctly
    writer = csv.writer(output)
    writer.writerow(["japanese", "reading", "meaning", "tags"])
    for word in words:
        tags = ", ".join(word_tags.get(word["id"], []))
        writer.writerow([word["japanese"], word["reading"], word["meaning"], tags])
    return output.getvalue()


def parse_lines(text: str) -> list[dict]:
    """Parse bulk-add text into word dicts.

    Each line: japanese, reading, meaning [, tags]
    Accepts tab-separated (spreadsheet paste) or comma-separated.
    Lines with fewer than 3 fields are skipped.
    """
    rows = []
    for line in text.splitlines():
        line = line.strip()
        if not line:
            continue
        sep = '\t' if '\t' in line else ','
        parts = [p.strip() for p in line.split(sep)]
        if len(parts) < 3:
            continue
        japanese, reading, meaning = parts[0], parts[1], parts[2]
        if not japanese or not reading or not meaning:
            continue
        tags = [t.strip() for t in parts[3].split(',') if t.strip()] if len(parts) > 3 else []
        rows.append({"japanese": japanese, "reading": reading, "meaning": meaning, "tags": tags})
    return rows


def parse_csv(content: str) -> list[dict]:
    """Parse CSV content into a list of word dicts.

    Returns dicts with keys: japanese, reading, meaning, tags (list[str]).
    Rows missing required fields are silently skipped.
    """
    rows = []
    reader = csv.DictReader(io.StringIO(content))
    for row in reader:
        japanese = row.get("japanese", "").strip()
        reading  = row.get("reading",  "").strip()
        meaning  = row.get("meaning",  "").strip()
        if not japanese or not reading or not meaning:
            continue
        tags = [t.strip() for t in row.get("tags", "").split(",") if t.strip()]
        rows.append({"japanese": japanese, "reading": reading, "meaning": meaning, "tags": tags})
    return rows
