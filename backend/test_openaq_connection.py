import os
from pathlib import Path

import httpx
from dotenv import load_dotenv


# Look one folder up from backend/ to find .env in the root
env_path = Path(__file__).resolve().parent.parent / ".env"
load_dotenv(env_path)

API_KEY = os.getenv("OPENAQ_API_KEY")

if not API_KEY:
    raise RuntimeError("OPENAQ_API_KEY is missing from .env")


BASE_URL = "https://api.openaq.org/v3"


def fetch_air_quality_locations():
    headers = {
        "X-API-Key": API_KEY
    }

    params = {
        "iso": "IN",
        "limit": 5
    }

    response = httpx.get(
        f"{BASE_URL}/locations",
        headers=headers,
        params=params,
        timeout=20
    )

    response.raise_for_status()

    return response.json()


if __name__ == "__main__":
    data = fetch_air_quality_locations()

    print("API connection successful")
    print("Total matching locations:", data["meta"]["found"])

    for location in data["results"]:
        print("\nStation:", location["name"])
        print("Location ID:", location["id"])

        for sensor in location["sensors"]:
            parameter = sensor["parameter"]

            print(
                "Pollutant:",
                parameter["name"],
                "| Unit:",
                parameter["units"],
                "| Sensor ID:",
                sensor["id"]
            )