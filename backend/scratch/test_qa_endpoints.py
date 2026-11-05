import httpx

client = httpx.Client(base_url="http://localhost:8000", timeout=120.0)

test_ids = [23, 24, 25, 26, 20, 21, 22]
for tid in test_ids:
    resp = client.post("/api/qa/agent/run", json={"test_case_id": tid})
    data = resp.json()
    status = data.get("status")
    name = data.get("component")
    dur = data.get("execution_duration_ms")
    print(f"[{status}] {name} ({dur}ms)")
    if data.get("failure_explanation"):
        print(f"   Failure Explanation: {data.get('failure_explanation')}")
