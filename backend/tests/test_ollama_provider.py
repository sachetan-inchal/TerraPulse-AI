from types import SimpleNamespace
from models.ollama_provider import OllamaLLM

class FakeOllamaClient:
    def chat(self, **kwargs):
        return SimpleNamespace(
            message=SimpleNamespace(
                content="PM2.5 levels are elevated."
            )
        )


def test_ollama_returns_standard_response():

    fake_client = FakeOllamaClient()
    model = OllamaLLM(client=fake_client)
    messages = [
        {
            "role": "user",
            "content": "Investigate air pollution."
        }
    ]
    response = model.generate(messages)
    
    assert response.type == "final"
    assert response.content == (
        "PM2.5 levels are elevated."
    )