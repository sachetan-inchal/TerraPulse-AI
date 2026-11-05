# backend/test_openaq_latest.py
import os
from pathlib import Path
import httpx
from dotenv import load_dotenv

env_path = Path(__file__).resolve().parent.parent / ".env"
load_dotenv(env_path)

API_KEY = os.getenv("OPENAQ_API_KEY")
BASE_URL = "https://api.openaq.org/v3"

headers = {"X-API-Key": API_KEY}

def get_station_details(location_id: int):
    """Fetch station details and its attached sensors from OpenAQ v3."""
    url = f"{BASE_URL}/locations/{location_id}"
    response = httpx.get(url, headers=headers, timeout=20)
    response.raise_for_status()
    return response.json()

def get_latest_measurements(location_id: int):
    """Fetch latest available measurements for a monitoring station."""

    url = f"{BASE_URL}/locations/{location_id}/latest"

    response = httpx.get(
        url,
        headers=headers,
        params={"limit": 100},
        timeout=20
    )

    response.raise_for_status()
    return response.json()

if __name__ == "__main__":
    try:
        # Using ID 12 (IIT Kanpur) or you can pick any valid ID
        valid_id = 12
        
        print(f"Fetching details for Location ID {valid_id}...")
        data = get_station_details(valid_id)
        
        # OpenAQ v3 wraps single resource results inside "results" list or dictionary
        station = data.get("results", [data])[0] if isinstance(data.get("results"), list) else data
        
        print(f"\nStation Name: {station.get('name')}")
        print(f"Timezone: {station.get('timezone')}")
        
        print("\nAttached Sensors:")
        for sensor in station.get("sensors", []):
            param = sensor.get("parameter", {})
            print(f"- Sensor ID: {sensor.get('id')} | Pollutant: {param.get('name')} ({param.get('units')})")
            
    except httpx.HTTPStatusError as e:
        print(f"HTTP Error occurred: {e.response.status_code} - {e.response.text}")
    except Exception as e:
        print(f"Error: {e}")