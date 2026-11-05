import requests

url = "https://api.openaq.org/v3/locations/3409385/latest"
headers = {"X-API-Key": "b4a8c794d96da4a830115259d4ff7e63d4d58c98444d450bcc5e665a7ba1f9b6"}

response = requests.get(url, headers=headers)

if response.status_code == 200:
    data = response.json()
    for result in data.get("results", []):
        parameter = result.get("parameter", {}).get("name")
        value = result.get("value")
        datetime_utc = result.get("datetime", {}).get("utc")
        print(
            f"Parameter: {parameter}, Value: {value}, Last Updated (UTC):"
            f" {datetime_utc}"
        )
else:
    print(f"Error {response.status_code}: {response.text}")