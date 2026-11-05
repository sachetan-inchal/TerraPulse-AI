import urllib.request
import json
import time

def post(url, payload=None):
    data = json.dumps(payload or {}).encode('utf-8')
    req = urllib.request.Request(url, data=data, headers={'Content-Type': 'application/json'}, method='POST')
    with urllib.request.urlopen(req, timeout=300) as resp:
        return json.loads(resp.read().decode('utf-8'))

def get(url):
    req = urllib.request.Request(url, method='GET')
    with urllib.request.urlopen(req, timeout=30) as resp:
        return json.loads(resp.read().decode('utf-8'))

print("1. Running all 31 Component Tests...")
t0 = time.time()
comp_res = post("http://localhost:8000/api/qa/component/batch")
print(f"Component tests finished in {time.time()-t0:.2f}s, total: {len(comp_res)}")
pass_comp = sum(1 for r in comp_res if r.get('status') == 'PASS')
fail_comp = sum(1 for r in comp_res if r.get('status') == 'FAIL')
print(f"Components -> PASS: {pass_comp}, FAIL: {fail_comp}")

print("\n2. Running all 12 Integration Tests...")
t0 = time.time()
integ_res = post("http://localhost:8000/api/qa/integration/batch")
print(f"Integration tests finished in {time.time()-t0:.2f}s, total: {len(integ_res)}")
pass_int = sum(1 for r in integ_res if r.get('status') == 'PASS')
fail_int = sum(1 for r in integ_res if r.get('status') == 'FAIL')
print(f"Integrations -> PASS: {pass_int}, FAIL: {fail_int}")

print("\n3. Running Agent Stopping Challenges (TC-14 to TC-19 & benchmarks)...")
t0 = time.time()
agent_res = post("http://localhost:8000/api/qa/agent/batch")
print(f"Agent tests finished in {time.time()-t0:.2f}s, total: {len(agent_res)}")
pass_agent = sum(1 for r in agent_res if r.get('status') == 'PASS')
fail_agent = sum(1 for r in agent_res if r.get('status') == 'FAIL')
print(f"Agent -> PASS: {pass_agent}, FAIL: {fail_agent}")

print("\n4. Fetching Updated Live Test Coverage Matrix...")
cov = get("http://localhost:8000/api/qa/coverage")
print("=== COVERAGE MATRIX SUMMARY ===")
print(f"Total Tests: {cov['overall']['total_tests']}")
print(f"Passed: {cov['overall']['passed']}")
print(f"Failed: {cov['overall']['failed']}")
print(f"Partial: {cov['overall']['partial']}")
print(f"Blocked: {cov['overall']['blocked']}")
print(f"Pending: {cov['overall']['pending']}")
print(f"Pass Rate: {cov['overall']['pass_rate_pct']}%")

print("\n=== CATEGORY BREAKDOWN ===")
for cat in cov['categories']:
    print(f"- {cat['category']}: {cat['passed']}/{cat['total_tests']} passed (failed: {cat['failed']}, pending: {cat['pending']})")
