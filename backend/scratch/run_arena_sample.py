import urllib.request
import json
import time

def post(url, payload):
    data = json.dumps(payload).encode('utf-8')
    req = urllib.request.Request(url, data=data, headers={'Content-Type': 'application/json'}, method='POST')
    with urllib.request.urlopen(req, timeout=120) as resp:
        return json.loads(resp.read().decode('utf-8'))

for pid in ["P01", "P03", "P19", "P22"]:
    print(f"Running Prompt Arena {pid}...")
    t0 = time.time()
    try:
        res = post("http://localhost:8000/api/qa/prompt/run", {"prompt_id": pid})
        print(f"  {pid} finished in {time.time()-t0:.2f}s -> Status: {res.get('status')}")
    except Exception as e:
        print(f"  {pid} failed: {e}")

