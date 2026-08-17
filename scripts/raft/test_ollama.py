import time
import requests

PROMPT = """<evidence chunk_id="kdigo_ckd_01">
KDIGO 2024 Clinical Guidelines: First-line pharmacological management for patients with CKD Stage 3a (eGFR 45-59 mL/min/1.73m2) and persistent albuminuria includes SGLT2 inhibitors and ACEi/ARB titration.
</evidence>

Question: What is the recommended first-line intervention for CKD Stage 3a?"""

print("Sending clinical inference query to local Ollama (careflow-qwen)...")
t0 = time.time()
res = requests.post(
    "http://localhost:11434/api/generate",
    json={
        "model": "careflow-qwen",
        "prompt": PROMPT,
        "stream": False,
    },
    timeout=30,
)
dt = time.time() - t0

if res.status_code == 200:
    data = res.json()
    print(f"\n[Generation Time]: {dt:.2f} seconds")
    print(f"[Total Tokens]:    {data.get('eval_count', 'N/A')}")
    print(f"[Token Speed]:     {data.get('eval_count', 0) / max(dt, 0.001):.1f} tokens/sec")
    print("\n--- CLINICAL RESPONSE ---")
    print(data.get("response", "").strip())
    print("-------------------------\n")
else:
    print(f"Error {res.status_code}: {res.text}")
