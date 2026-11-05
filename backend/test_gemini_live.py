import os
from dotenv import load_dotenv
from models.gemini_provider import GeminiLLM


load_dotenv()

print("API key loaded:", bool(os.getenv("GEMINI_API_KEY")))
model = GeminiLLM()

messages = [
    {
        "role": "system",
        "content": "You are TerraPulse, an environmental investigation assistant."
    },
    {
        "role": "user",
        "content": "Explain three major causes of air pollution in Chennai."
    }
]

response = model.generate(messages)

print(response.model_dump())