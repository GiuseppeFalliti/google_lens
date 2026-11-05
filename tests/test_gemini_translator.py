import json

import httpx
import pytest

from src.exceptions import TranslationConfigurationError, TranslationError
from src.translation.gemini_translator import GeminiTranslator


def _reply(translations):
    return httpx.Response(
        200,
        json={
            "candidates": [
                {
                    "content": {
                        "parts": [
                            {
                                "text": json.dumps(
                                    {"translations": translations},
                                    ensure_ascii=False,
                                )
                            }
                        ]
                    }
                }
            ]
        },
    )


def test_gemini_batch_preserves_region_ids_even_if_response_reordered():
    def handler(request: httpx.Request) -> httpx.Response:
        assert request.headers["x-goog-api-key"] == "test-secret"
        assert str(request.url).endswith(
            "/models/gemini-3.5-flash-lite:generateContent"
        )
        payload = json.loads(request.content)
        assert payload["generationConfig"]["responseMimeType"] == "application/json"
        prompt = payload["contents"][0]["parts"][0]["text"]
        segments = json.loads(prompt.split("\n", 1)[1])["segments"]
        assert [s["text"] for s in segments] == ["Hello.", "Be careful!"]
        return _reply(
            [{"id": 1, "text": "Fai attenzione!"}, {"id": 0, "text": "Ciao."}]
        )

    provider = GeminiTranslator(
        api_key="test-secret",
        transport=httpx.MockTransport(handler),
    )
    assert provider.translate_many(
        ["Hello.", "Be careful!"], "en", "it"
    ) == ["Ciao.", "Fai attenzione!"]


def test_gemini_single_translation_uses_batch_protocol():
    def handler(request):
        return _reply([{"id": 0, "text": "Assenza ingiustificata"}])

    provider = GeminiTranslator(
        api_key="test",
        transport=httpx.MockTransport(handler),
    )
    assert (
        provider.translate("Unexcused absence", "en", "it")
        == "Assenza ingiustificata"
    )


def test_gemini_splits_large_batches_and_keeps_order():
    calls = []

    def handler(request):
        payload = json.loads(request.content)
        entries = json.loads(
            payload["contents"][0]["parts"][0]["text"].split("\n", 1)[1]
        )["segments"]
        calls.append(entries)
        return _reply(
            [{"id": item["id"], "text": f"IT {item['text']}"} for item in entries]
        )

    provider = GeminiTranslator(
        api_key="test",
        transport=httpx.MockTransport(handler),
    )
    inputs = [f"Line {index}" for index in range(23)]
    result = provider.translate_many(inputs, "en", "it")
    assert result == [f"IT {line}" for line in inputs]
    assert [len(call) for call in calls] == [20, 3]


@pytest.mark.parametrize(
    "entries",
    [
        [{"id": 0, "text": "Uno"}, {"id": 0, "text": "Due"}],
        [{"id": 0, "text": "Uno"}],
        [{"id": 0, "text": "Uno"}, {"id": 9, "text": "Due"}],
        [{"id": 0, "text": "Uno"}, {"id": 1, "text": ""}],
    ],
)
def test_gemini_rejects_invalid_batch_responses(entries):
    provider = GeminiTranslator(
        api_key="test",
        transport=httpx.MockTransport(lambda request: _reply(entries)),
    )
    with pytest.raises(TranslationError):
        provider.translate_many(["One", "Two"], "en", "it")


def test_gemini_missing_api_key():
    provider = GeminiTranslator()
    with pytest.raises(TranslationConfigurationError):
        provider.translate("Hello", "en", "it")


def test_gemini_quota_error_has_helpful_message():
    provider = GeminiTranslator(
        api_key="test",
        transport=httpx.MockTransport(
            lambda request: httpx.Response(429, json={"error": {"code": 429}})
        ),
    )
    with pytest.raises(TranslationError, match="free-tier quota"):
        provider.translate("Hello", "en", "it")


def test_gemini_unavailable_model_error():
    provider = GeminiTranslator(
        api_key="test",
        model="gemini-3.5-flash-lite",
        transport=httpx.MockTransport(
            lambda request: httpx.Response(404, json={"error": {"code": 404}})
        ),
    )
    with pytest.raises(TranslationError, match="unavailable"):
        provider.translate("Hello", "en", "it")


def test_gemini_does_not_send_screen_images():
    def handler(request):
        payload = json.loads(request.content)
        assert "inlineData" not in json.dumps(payload)
        return _reply([{"id": 0, "text": "Ciao"}])

    provider = GeminiTranslator(
        api_key="test",
        transport=httpx.MockTransport(handler),
    )
    assert provider.translate("Hi", "en", "it") == "Ciao"
