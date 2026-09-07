import sys
sys.stdout.reconfigure(encoding='utf-8')

from agent.task_classifier import classify_task

test_queries = [
    "What are the temperature thresholds for bearing inspection?",
    "What are the vibration thresholds for centrifugal pumps according to the SOP?",
    "Generate a Word document report on pump maintenance procedures",
    "Create a PDF report on industrial safety requirements",
    "Write a Python function to calculate centrifugal pump efficiency given input power 75 kW and output power 62 kW, then run it"
]

print("=== TASK CLASSIFIER TEST RESULTS ===", flush=True)
for q in test_queries:
    res = classify_task(query=q)
    print(f"\nQuery: '{q}'", flush=True)
    print(f"  -> Task Type    : {res.primary_task}", flush=True)
    print(f"  -> Is Multi-Step: {res.is_multi_step}", flush=True)
    print(f"  -> Tools        : {res.selected_tools}", flush=True)
    print(f"  -> Reason       : {res.reason}", flush=True)
