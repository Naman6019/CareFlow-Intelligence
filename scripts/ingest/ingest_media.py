import asyncio
import sys
from pathlib import Path

# Add apps/api and root to python path
PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(PROJECT_ROOT))
sys.path.insert(0, str(PROJECT_ROOT / "apps" / "api"))

from app.database import async_session_factory
from scripts.ingest.store_helper import store_medical_document

CURATED_MEDIA_TRANSCRIPTS = [
    {
        "filename": "Grand_Rounds_Resistant_Hypertension_Cardiology.md",
        "title": "Hospital Grand Rounds: Diagnosis and Workup of Resistant Hypertension",
        "media_type": "Grand Rounds Lecture Transcript",
        "content": """# Clinical Grand Rounds: Diagnosis & Management of Resistant Hypertension

**Speaker**: Prof. Elena Vance, MD, FACC (Chief of Preventive Cardiology)  
**Session Type**: Academic Medical Center Grand Rounds (Audio Transcript)  
**Clinical Focus**: Refractory blood pressure, secondary workup, and pharmacotherapy pathways  

---

### [00:00 - 05:30] Introduction and True Definition of Resistant Hypertension
"Thank you, everyone. Today we are addressing a common clinical challenge: patients whose blood pressure remains stubbornly elevated despite multiple medications. By definition, **Resistant Hypertension** is confirmed when a patient's office blood pressure is $\\ge 130/80\\text{ mmHg}$ despite concurrent adherence to **three antihypertensive agents of different pharmacological classes**, one of which **must be a diuretic**, all prescribed at guideline-recommended doses.

Furthermore, patients whose blood pressure is controlled ($< 130/80\\text{ mmHg}$) but requires **four or more medications** are also classified as having resistant hypertension."

---

### [05:31 - 12:45] Ruling Out Pseudo-Resistance and Medication Non-Adherence
"Before initiating extensive secondary hypertension workups or adding 4th-line agents, we must rigorously rule out **pseudo-resistance**:
1. **White-Coat Effect**: We must confirm elevated home blood pressure using 24-hour Ambulatory Blood Pressure Monitoring (ABPM) or standardized home BP logs.
2. **Improper Measurement Technique**: Using a blood pressure cuff that is too small for a patient's arm circumference falsely elevates systolic readings by $5\\text{ to }15\\text{ mmHg}$.
3. **Medication Non-Adherence**: Studies show up to $50\\%$ of patients with apparent resistant hypertension are partially or fully non-adherent.
4. **Interfering Substances**: Always ask about high dietary sodium intake, regular NSAID use (ibuprofen, naproxen), systemic corticosteroids, pseudoephedrine/decongestants, and excessive alcohol consumption."

---

### [12:46 - 22:15] Secondary Causes: When to Screen for Primary Aldosteronism
"In resistant hypertension, the prevalence of **Primary Aldosteronism (Conn's Syndrome)** is between $10\\%$ and $20\\%$. Do not rely on hypokalemia to trigger testing—more than half of primary aldosteronism patients have normal serum potassium levels.

**Screening Protocol**:
- Obtain a morning **Plasma Aldosterone Concentration (PAC)** to **Plasma Renin Activity (PRA)** ratio (ARR).
- An ARR $> 20$ with PAC $> 10\\text{ ng/dL}$ is positive and warrants confirmatory oral sodium loading or saline infusion testing followed by adrenal CT imaging."

---

### [22:16 - 32:00] Stepwise Pharmacotherapy: The 4th-Line Agent
"What is the most effective fourth-line agent? The landmark **PATHWAY-2 trial** provided unequivocal evidence:
- **Spironolactone** ($25\\text{ to }50\\text{ mg}$ once daily) is the single most effective 4th-line add-on therapy.
- In patients who cannot tolerate spironolactone due to gynecomastia or breast tenderness, **Eplerenone** ($50\\text{ mg}$ twice daily) or **Amiloride** ($5 - 10\\text{ mg}$ daily) are first-choice alternatives.
- Caution: Check serum creatinine and potassium at 2 and 4 weeks post-initiation. Do not initiate if baseline potassium is $> 5.0\\text{ mEq/L}$ or eGFR $< 30\\text{ mL/min/1.73 m}^2$."
"""
    },
    {
        "filename": "Clinical_Podcast_Cardiorenal_Metabolic_Syndrome.md",
        "title": "Clinical Practice Podcast: GLP-1 RA and SGLT2 Inhibitor Synergies in Cardiorenal Disease",
        "media_type": "Medical Podcast Audio Transcript",
        "content": """# Clinical Podcast: SGLT2i and GLP-1 RA Dual Therapy in Type 2 Diabetes & Cardiorenal Syndrome

**Hosts**: Dr. Marcus Reed (Internal Medicine) & Dr. Sarah Lin (Nephrology)  
**Format**: Clinical Review Podcast (Transcribed from Audio)  

---

### [00:00 - 08:20] The Paradigm Shift in Type 2 Diabetes Management
"Welcome back to Clinical Review. For decades, our diabetes algorithms were purely glucocentric—we adjusted medications solely to lower HbA1c below $7\\%$. Today, following landmark cardiovascular and renal outcome trials (EMPA-REG OUTCOME, DAPA-CKD, LEADER, SUSTAIN-6), our primary goal is organ protection."

---

### [08:21 - 16:40] SGLT2 Inhibitor Mechanisms: Glomerular Hemodynamics
"Why are SGLT2 inhibitors like Empagliflozin and Dapagliflozin so uniquely protective for the kidneys? 
By blocking sodium and glucose reabsorption in the proximal convoluted tubule, more sodium reaches the macula densa. This triggers **tubuloglomerular feedback**, leading to afferent arteriolar constriction. 

This reduces intra-glomerular hypertension and hyperfiltration. Clinicians often notice an acute, reversible drop in eGFR of $3\\text{ to }5\\text{ mL/min}$ in the first 4 weeks. **Do not discontinue the medication for this expected dip**—it reflects hemodynamic relief, and the long-term eGFR trajectory is preserved far better than in placebo."

---

### [16:41 - 25:10] Combining SGLT2i and GLP-1 RA: Synergistic Benefits
"Can we combine an SGLT2 inhibitor with a GLP-1 receptor agonist like Semaglutide or Tirzepatide?
Absolutely. Their mechanisms are complementary:
- **SGLT2 Inhibitors**: Strongest on reducing heart failure hospitalizations (HFrEF/HFpEF) and slowing CKD progression.
- **GLP-1 Receptor Agonists**: Strongest on atherosclerotic cardiovascular disease (ASCVD) risk reduction (non-fatal MI, stroke, CV death) and significant weight loss.
- In dual therapy, patients experience additive A1c reduction without increased risk of hypoglycemia (unless combined with insulin or sulfonylureas)."
"""
    }
]


async def ingest_curated_media():
    print("\n[Media] Ingesting clinical podcast and lecture transcripts...")
    async with async_session_factory() as session:
        for item in CURATED_MEDIA_TRANSCRIPTS:
            res = await store_medical_document(
                session=session,
                filename=item["filename"],
                content=item["content"],
                classification="public",
                content_type="text/markdown",
            )
            if res.is_duplicate:
                print(f"  [Exists] {item['filename']} ({res.chunk_count} chunks)")
            else:
                print(f"  [Indexed] {item['filename']} -> {res.chunk_count} chunks")


async def main():
    await ingest_curated_media()


if __name__ == "__main__":
    asyncio.run(main())
