import os
import json
from pathlib import Path

import httpx
from dotenv import load_dotenv


# Look one folder up from backend/ to find .env in the root
env_path = Path(__file__).resolve().parent.parent / ".env"
load_dotenv(env_path)

API_KEY = os.getenv("OPENAQ_API_KEY")

if not API_KEY:
    raise RuntimeError("OPENAQ_API_KEY is missing")


BASE_URL = "https://api.openaq.org/v3"


def fetch_hourly_measurements(sensor_id: int):
    headers = {
        "X-API-Key": API_KEY
    }

    params = {
        "limit": 24,
        "page": 1
    }

    response = httpx.get(
        f"{BASE_URL}/sensors/{sensor_id}/hours",
        headers=headers,
        params=params,
        timeout=20
    )

    response.raise_for_status()

    return response.json()


if __name__ == "__main__":
    sensor_id = int(input("Enter a sensor ID: "))

    data = fetch_hourly_measurements(sensor_id)

    print("\nAPI request successful")
    print("Measurements found:", data["meta"]["found"])

    for measurement in data["results"]:
        print(json.dumps(measurement, indent=2))