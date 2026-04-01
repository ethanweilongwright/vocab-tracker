import json
from unittest.mock import patch, MagicMock
from src.sentences import get_sentences


def _mock_response(data: dict):
    mock = MagicMock()
    mock.read.return_value = json.dumps(data).encode()
    mock.__enter__ = lambda s: s
    mock.__exit__ = MagicMock(return_value=False)
    return mock


SAMPLE_RESPONSE = {
    "results": [
        {
            "text": "彼女は毎日パンを食べる。",
            "translations": [[{"lang": "eng", "text": "She eats bread every day."}]],
        },
        {
            "text": "猫は魚を食べる。",
            "translations": [[{"lang": "eng", "text": "Cats eat fish."}]],
        },
    ]
}


def test_get_sentences_returns_list():
    with patch("urllib.request.urlopen", return_value=_mock_response(SAMPLE_RESPONSE)):
        results = get_sentences("食べる")
    assert len(results) == 2


def test_get_sentences_structure():
    with patch("urllib.request.urlopen", return_value=_mock_response(SAMPLE_RESPONSE)):
        results = get_sentences("食べる")
    assert results[0]["japanese"] == "彼女は毎日パンを食べる。"
    assert results[0]["english"] == "She eats bread every day."


def test_get_sentences_respects_limit():
    with patch("urllib.request.urlopen", return_value=_mock_response(SAMPLE_RESPONSE)):
        results = get_sentences("食べる", limit=1)
    assert len(results) == 1


def test_get_sentences_empty_results():
    with patch("urllib.request.urlopen", return_value=_mock_response({"results": []})):
        results = get_sentences("xyzxyz")
    assert results == []


def test_get_sentences_api_unavailable():
    with patch("urllib.request.urlopen", side_effect=Exception("timeout")):
        results = get_sentences("食べる")
    assert results == []


def test_get_sentences_skips_entry_missing_translation():
    data = {
        "results": [
            {"text": "日本語の文。", "translations": []},
            {
                "text": "別の文。",
                "translations": [[{"lang": "eng", "text": "Another sentence."}]],
            },
        ]
    }
    with patch("urllib.request.urlopen", return_value=_mock_response(data)):
        results = get_sentences("テスト")
    assert len(results) == 1
    assert results[0]["japanese"] == "別の文。"
