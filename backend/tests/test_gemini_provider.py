from types import SimpleNamespace
from models.gemini_provider import GeminiLLM


class FakeGeminiModels:
    def generate_content(self, **kwargs):
        assert kwargs["model"] == "gemini-3.7-flash"
        assert len(kwargs["contents"]) == 1
        return SimpleNamespace(
            text="Air pollution increases respiratory risks."
        )


class FakeGeminiClient:
    def __init__(self):
        self.models = FakeGeminiModels()


def test_gemini_returns_standard_response():
    fake_client = FakeGeminiClient()
    model = GeminiLLM(client=fake_client)
    messages = [
        {
            "role": "user",
            "content": "What are the effects of air pollution?"
        }
    ]
    response = model.generate(messages)

    assert response.type == "final"
    assert response.content == (
        "Air pollution increases respiratory risks."
    )