from src.imex import export_csv, parse_csv, parse_lines


# --- export_csv ---

def test_export_csv_header():
    content = export_csv([], {})
    # BOM is present; strip it before checking the text
    assert content.lstrip('\ufeff').startswith("japanese,reading,meaning,tags")


def test_export_csv_word_row():
    words = [{"id": 1, "japanese": "食べる", "reading": "たべる", "meaning": "to eat"}]
    word_tags = {1: ["N5", "verbs"]}
    csv = export_csv(words, word_tags)
    assert "食べる" in csv
    assert "たべる" in csv
    assert "to eat" in csv
    assert "N5" in csv


def test_export_csv_no_tags():
    words = [{"id": 1, "japanese": "犬", "reading": "いぬ", "meaning": "dog"}]
    csv = export_csv(words, {})
    lines = csv.strip().splitlines()
    assert len(lines) == 2  # header + 1 row


def test_export_csv_multiple_words():
    words = [
        {"id": 1, "japanese": "食べる", "reading": "たべる", "meaning": "to eat"},
        {"id": 2, "japanese": "飲む",   "reading": "のむ",   "meaning": "to drink"},
    ]
    csv = export_csv(words, {})
    lines = csv.strip().splitlines()
    assert len(lines) == 3


# --- parse_csv ---

def test_parse_csv_basic():
    content = "japanese,reading,meaning,tags\n食べる,たべる,to eat,N5\n"
    rows = parse_csv(content)
    assert len(rows) == 1
    assert rows[0]["japanese"] == "食べる"
    assert rows[0]["reading"]  == "たべる"
    assert rows[0]["meaning"]  == "to eat"
    assert rows[0]["tags"]     == ["N5"]


def test_parse_csv_multiple_tags():
    content = "japanese,reading,meaning,tags\n食べる,たべる,to eat,\"N5, verbs\"\n"
    rows = parse_csv(content)
    assert sorted(rows[0]["tags"]) == ["N5", "verbs"]


def test_parse_csv_no_tags_column():
    content = "japanese,reading,meaning\n犬,いぬ,dog\n"
    rows = parse_csv(content)
    assert rows[0]["tags"] == []


def test_parse_csv_skips_incomplete_rows():
    content = "japanese,reading,meaning,tags\n食べる,,to eat,\n犬,いぬ,dog,\n"
    rows = parse_csv(content)
    assert len(rows) == 1
    assert rows[0]["japanese"] == "犬"


def test_parse_csv_strips_whitespace():
    content = "japanese,reading,meaning,tags\n 食べる , たべる , to eat , N5 \n"
    rows = parse_csv(content)
    assert rows[0]["japanese"] == "食べる"
    assert rows[0]["tags"] == ["N5"]


def test_parse_csv_empty_file():
    assert parse_csv("japanese,reading,meaning,tags\n") == []


# --- parse_lines ---

def test_parse_lines_comma_separated():
    rows = parse_lines("食べる, たべる, to eat")
    assert len(rows) == 1
    assert rows[0] == {"japanese": "食べる", "reading": "たべる", "meaning": "to eat", "tags": []}


def test_parse_lines_tab_separated():
    rows = parse_lines("食べる\tたべる\tto eat")
    assert len(rows) == 1
    assert rows[0]["japanese"] == "食べる"


def test_parse_lines_multiple_lines():
    text = "食べる, たべる, to eat\n飲む, のむ, to drink\n"
    rows = parse_lines(text)
    assert len(rows) == 2


def test_parse_lines_with_tags():
    rows = parse_lines("食べる, たべる, to eat, N5")
    assert rows[0]["tags"] == ["N5"]


def test_parse_lines_skips_incomplete():
    text = "食べる, たべる\n犬, いぬ, dog\n"
    rows = parse_lines(text)
    assert len(rows) == 1
    assert rows[0]["japanese"] == "犬"


def test_parse_lines_skips_blank_lines():
    text = "食べる, たべる, to eat\n\n飲む, のむ, to drink\n"
    rows = parse_lines(text)
    assert len(rows) == 2


def test_parse_lines_empty_input():
    assert parse_lines("") == []
    assert parse_lines("   \n  \n") == []


def test_export_then_import_roundtrip():
    words = [{"id": 1, "japanese": "食べる", "reading": "たべる", "meaning": "to eat"}]
    word_tags = {1: ["N5"]}
    content = export_csv(words, word_tags)
    # Simulate what the import route does: decode bytes with utf-8-sig strips the BOM
    content_no_bom = content.encode("utf-8").decode("utf-8-sig")
    rows = parse_csv(content_no_bom)
    assert len(rows) == 1
    assert rows[0]["japanese"] == "食べる"
    assert rows[0]["tags"] == ["N5"]
