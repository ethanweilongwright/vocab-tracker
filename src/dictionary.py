import urllib.request
import urllib.parse
import json


def lookup(word: str) -> dict | None:
    url = f"https://jisho.org/api/v1/search/words?keyword={urllib.parse.quote(word)}"
    try:
        with urllib.request.urlopen(url, timeout=5) as resp:
            data = json.loads(resp.read())
        entries = data.get("data", [])
        if not entries:
            return None
        entry = entries[0]
        japanese = entry["japanese"][0]
        senses = entry["senses"][0]
        # jlpt is a list like ["jlpt-n5"] — normalise to "N5"
        jlpt_raw = entry.get("jlpt", [])
        tags = [j.replace("jlpt-", "").upper() for j in jlpt_raw]

        return {
            "word": japanese.get("word", word),
            "reading": japanese.get("reading", ""),
            "meaning": ", ".join(senses["english_definitions"]),
            "tags": tags,
        }
    except Exception:
        return None
