import urllib.request
import urllib.parse
import json


def get_sentences(word: str, limit: int = 3) -> list[dict]:
    url = (
        f"https://tatoeba.org/api_v0/search"
        f"?query={urllib.parse.quote(word)}&from=jpn&to=eng&limit={limit}"
    )
    try:
        with urllib.request.urlopen(url, timeout=5) as resp:
            data = json.loads(resp.read())
        results = []
        for item in data.get("results", [])[:limit]:
            translations = item.get("translations", [])
            # translations is a list of lists; first inner list contains direct translations
            english = ""
            for group in translations:
                for t in group:
                    if t.get("lang") == "eng" and t.get("text"):
                        english = t["text"]
                        break
                if english:
                    break
            if item.get("text") and english:
                results.append({"japanese": item["text"], "english": english})
        return results
    except Exception:
        return []
