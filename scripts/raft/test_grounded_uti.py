import time
import requests

PROMPT_GROUNDED = """<evidence chunk_id="idsa_uti_guideline_2024">
Infectious Diseases Society of America (IDSA) Guidelines for Acute Uncomplicated Cystitis:
1. First-line regimens:
   - Nitrofurantoin monohydrate/macrocrystals (Macrobid): 100 mg PO BID for 5 days. (Preferred; active only in lower urinary tract, contraindicated if eGFR < 30 mL/min).
   - Trimethoprim-Sulfamethoxazole (TMP-SMX, Bactrim DS): 160/800 mg PO BID for 3 days (ONLY if local E. coli resistance is < 20% and patient has no sulfa allergy).
   - Fosfomycin trometamol: 3 g single-dose oral powder sachet.
2. Safety Warnings & Contraindications:
   - Amoxicillin-clavulanate is a penicillin derivative and is strictly contraindicated in patients with penicillin allergy.
   - Fluoroquinolones (Ciprofloxacin) must be avoided for uncomplicated cystitis due to FDA black-box warnings (tendon rupture, QT prolongation, CNS toxicities) and reserved only for pyelonephritis.
   - Macrolides (Azithromycin) have no role in coliform cystitis.
</evidence>

Question: What is the recommended first-line antibiotic for uncomplicated UTI, and what are the critical contraindications?"""

print("Testing CareFlow Grounded RAFT Inference...")
res = requests.post(
    "http://localhost:11434/api/generate",
    json={
        "model": "careflow-qwen",
        "prompt": PROMPT_GROUNDED,
        "stream": False,
    },
    timeout=30,
)

if res.status_code == 200:
    print("\n--- GROUNDED CLINICAL RESPONSE ---")
    print(res.json().get("response", "").strip())
    print("----------------------------------\n")
