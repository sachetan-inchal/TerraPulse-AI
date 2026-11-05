from models.base import BaseLLM


class GeminiLLM(BaseLLM):

    def generate(self, messages, tools=None):
        return {
            "provider": "gemini",
            "response": "Environmental analysis from Gemini"
        }


class OllamaLLM(BaseLLM):

    def generate(self, messages, tools=None):
        return {
            "provider": "ollama",
            "response": "Environmental analysis from Ollama"
        }


def run_test(model):

    messages = [
        {"role": "user", "content": "Investigate air pollution"}
    ]

    response = model.generate(messages)

    print(response)


gemini = GeminiLLM()
ollama = OllamaLLM()

run_test(gemini)
run_test(ollama)