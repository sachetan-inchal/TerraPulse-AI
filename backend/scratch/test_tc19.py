import sys, os
sys.path.insert(0, os.path.abspath("backend"))
import asyncio
from qa_engine import QAEngine

qa = QAEngine()
rec = asyncio.run(qa.run_agent_test(19))
print("TC-19 status:", rec.status)
print("Recommendation:", rec.actual_output["stopping_recommendation"])

