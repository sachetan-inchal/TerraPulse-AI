from models.ollama_provider import OllamaLLM

model = OllamaLLM()
messages = [
    {
        "role": "user",
        "content": (
            "Explain three major causes of air "
            "pollution in urban environments."
        )
    }
]

response = model.generate(messages)
print(response.model_dump())