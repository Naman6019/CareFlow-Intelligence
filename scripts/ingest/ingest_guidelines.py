import asyncio
import sys
from pathlib import Path

# Add apps/api and root to python path
PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(PROJECT_ROOT))
sys.path.insert(0, str(PROJECT_ROOT / "apps" / "api"))

from app.database import async_session_factory
from app.document_agent.chunking import extract_pages, chunk_pages
from scripts.ingest.store_helper import store_medical_document

# Core curated clinical guidelines
CURATED_GUIDELINES = [
    {
        "filename": "ADA_Standards_of_Care_Diabetes_Management.md",
        "title": "American Diabetes Association (ADA) Standards of Care: Comprehensive Clinical Summary",
        "content": """# ADA Standards of Care: Diagnosis and Management of Diabetes Mellitus

**Authority**: American Diabetes Association (ADA) Professional Practice Committee  
**Target Population**: Adults and pediatric patients with Type 1, Type 2, or Gestational Diabetes  
**Evidence Level**: Grade A / Grade B Clinical Practice Guidelines  

---

## 1. Diagnostic Criteria for Diabetes

Diagnosis requires two abnormal test results from the same sample or in two separate test samples:
- **Hemoglobin A1c (HbA1c)**: $\\ge 6.5\\%$ ($48\\text{ mmol/mol}$) using an NGSP-certified assay.
- **Fasting Plasma Glucose (FPG)**: $\\ge 126\\text{ mg/dL}$ ($7.0\\text{ mmol/L}$) after an 8-hour fast.
- **2-Hour 75g Oral Glucose Tolerance Test (OGTT)**: $\\ge 200\\text{ mg/dL}$ ($11.1\\text{ mmol/L}$).
- **Random Plasma Glucose**: $\\ge 200\\text{ mg/dL}$ in individuals with classic hyperglycemic crisis (polyuria, polydipsia, unexplained weight loss).

### Prediabetes Criteria
- Fasting Plasma Glucose: $100\\text{ to }125\\text{ mg/dL}$ (Impaired Fasting Glucose).
- 2-Hour OGTT: $140\\text{ to }199\\text{ mg/dL}$ (Impaired Glucose Tolerance).
- HbA1c: $5.7\\%$ to $6.4\\%$.

---

## 2. Glycemic Goals and Monitoring
- **Standard Adult Target**: HbA1c $< 7.0\\%$ ($53\\text{ mmol/mol}$) for most nonpregnant adults without significant hypoglycemia.
- **Stringent Target (HbA1c $< 6.5\\%$)**: Feasible in newly diagnosed patients, young patients, or those with long life expectancy and no severe CVD.
- **Relaxed Target (HbA1c $< 8.0\\%$ or $< 8.5\\%$)**: Appropriate for patients with limited life expectancy, extensive comorbid conditions, or severe hypoglycemia history.

---

## 3. Pharmacologic Therapy Algorithm for Type 2 Diabetes

### First-Line Therapy
- **Lifestyle modifications** (medical nutrition therapy, physical activity $\\ge 150\\text{ min/week}$, weight management).
- **Metformin**: Initiate at $500\\text{ mg}$ once daily with meals, titrate to $1000\\text{ mg}$ twice daily as tolerated. Monitor eGFR and Vitamin B12 levels.
  - Contraindicated if eGFR $< 30\\text{ mL/min/1.73 m}^2$.
  - Dose reduction recommended if eGFR $30\\text{ to }44\\text{ mL/min/1.73 m}^2$.

### Organ-Protection Add-on Selection (Independent of Baseline A1c)
1. **Atherosclerotic Cardiovascular Disease (ASCVD) Predominance**:
   - Add a **GLP-1 Receptor Agonist (GLP-1 RA)** with proven CVD benefit (e.g., Dulaglutide, Semaglutide, Liraglutide) OR an **SGLT2 Inhibitor** with proven CVD benefit (e.g., Empagliflozin, Dapagliflozin).
2. **Heart Failure (HFrEF or HFpEF) Predominance**:
   - Add an **SGLT2 Inhibitor** (Empagliflozin or Dapagliflozin).
3. **Chronic Kidney Disease (CKD with eGFR $20\\text{ to }60$ or UACR $> 30\\text{ mg/g}$)**:
   - Add an **SGLT2 Inhibitor** as first choice to reduce CKD progression and CV events.
   - If SGLT2i not tolerated or contraindicated, use a **GLP-1 RA** with renal outcomes.

---

## 4. Blood Pressure and Lipid Management in Diabetes
- **Blood Pressure Target**: $< 130/80\\text{ mmHg}$ if cardiovascular risk is high.
- **First-Line Antihypertensive**: ACE inhibitor or ARB (especially in patients with urinary albumin-to-creatinine ratio $\\ge 30\\text{ mg/g}$).
- **Lipid Management**:
  - Primary prevention (age 40–75 without ASCVD): Moderate-intensity statin (e.g., Atorvastatin $20\\text{ mg}$).
  - Secondary prevention (age 40–75 with established ASCVD): High-intensity statin (Atorvastatin $80\\text{ mg}$ or Rosuvastatin $40\\text{ mg}$) aiming for LDL-C reduction $\\ge 50\\%$ and LDL-C $< 55\\text{ mg/dL}$.
"""
    },
    {
        "filename": "AHA_ACC_Hypertension_Clinical_Practice_Guideline.md",
        "title": "AHA/ACC Clinical Practice Guideline for the Prevention, Detection, Evaluation, and Management of High Blood Pressure",
        "content": """# AHA/ACC Clinical Practice Guideline for High Blood Pressure in Adults

**Issuing Organizations**: American Heart Association (AHA) and American College of Cardiology (ACC)  
**Publication Standard**: Practice Guideline & Evidence-Based Consensus  

---

## 1. Blood Pressure Classification in Adults

| BP Category | Systolic BP (mmHg) | | Diastolic BP (mmHg) |
| :--- | :--- | :--- | :--- |
| **Normal** | $< 120$ | AND | $< 80$ |
| **Elevated** | $120 - 129$ | AND | $< 80$ |
| **Stage 1 Hypertension** | $130 - 139$ | OR | $80 - 89$ |
| **Stage 2 Hypertension** | $\\ge 140$ | OR | $\\ge 90$ |
| **Hypertensive Crisis** | $> 180$ | AND/OR | $> 120$ |

*Diagnosis requires average of $\\ge 2$ readings obtained on $\\ge 2$ occasions.*

---

## 2. Treatment Thresholds and Target Goals

- **Target Blood Pressure**: $< 130/80\\text{ mmHg}$ for all confirmed hypertensive adults.
- **Stage 1 Hypertension**:
  - If 10-year ASCVD risk $< 10\\%$: Nonpharmacologic lifestyle therapy for 3–6 months.
  - If 10-year ASCVD risk $\\ge 10\\%$ or presence of Diabetes or CKD: Initiate monotherapy medication + lifestyle.
- **Stage 2 Hypertension** (BP $\\ge 140/90\\text{ mmHg}$ or $\\ge 20/10\\text{ mmHg}$ above target):
  - Initiate **2 first-line antihypertensive agents of different classes** simultaneously.

---

## 3. First-Line Antihypertensive Drug Classes

1. **Thiazide or Thiazide-Type Diuretics**:
   - Chlorthalidone ($12.5 - 25\\text{ mg}$ daily) preferred over hydrochlorothiazide due to longer half-life.
2. **Angiotensin-Converting Enzyme (ACE) Inhibitors**:
   - Lisinopril ($10 - 40\\text{ mg}$ daily), Enalapril, Ramipril.
   - *Boxed Warning*: Fetal toxicity; contraindicated in pregnancy.
3. **Angiotensin Receptor Blockers (ARBs)**:
   - Losartan ($50 - 100\\text{ mg}$ daily), Valsartan, Telmisartan.
   - Note: Do NOT combine an ACE inhibitor and an ARB (increased risk of renal failure and hyperkalemia).
4. **Calcium Channel Blockers (Dihydropyridines)**:
   - Amlodipine ($2.5 - 10\\text{ mg}$ daily), Nifedipine ER.

---

## 4. Special Clinical Populations
- **Chronic Kidney Disease (CKD Stage 3+ or Albuminuria $\\ge 300\\text{ mg/day}$)**: Initial choice should be an ACEi or ARB to slow renal deterioration.
- **Heart Failure with Reduced Ejection Fraction (HFrEF)**: Guideline-directed medical therapy includes ARNI/ACEi/ARB, beta-blocker (Carvedilol, Metoprolol succinate), MRA (Spironolactone), and SGLT2i.
- **Resistant Hypertension**: Defined as BP remaining above target despite adherence to 3 full-dose antihypertensive agents of different classes (including a diuretic). Step 4 treatment is adding an Aldosterone Antagonist (Spironolactone $25 - 50\\text{ mg}$ daily).
"""
    },
    {
        "filename": "KDIGO_CKD_Staging_and_Management_Guideline.md",
        "title": "KDIGO Clinical Practice Guideline for the Evaluation and Management of Chronic Kidney Disease",
        "content": """# KDIGO Clinical Practice Guideline for Chronic Kidney Disease (CKD)

**Issuing Organization**: Kidney Disease: Improving Global Outcomes (KDIGO)  
**Scope**: Classification, Prognosis, and Interventions in CKD  

---

## 1. Definition and Staging of CKD

CKD is defined as abnormalities of kidney structure or function present for $> 3\\text{ months}$.

### GFR Staging (G1 to G5)
- **G1**: Normal or high (eGFR $\\ge 90\\text{ mL/min/1.73 m}^2$ with kidney damage)
- **G2**: Mildly decreased (eGFR $60 - 89$)
- **G3a**: Mild to moderately decreased (eGFR $45 - 59$)
- **G3b**: Moderately to severely decreased (eGFR $30 - 44$)
- **G4**: Severely decreased (eGFR $15 - 29$)
- **G5**: Kidney failure (eGFR $< 15\\text{ mL/min/1.73 m}^2$)

### Albuminuria Staging (A1 to A3 - Urine Albumin-to-Creatinine Ratio UACR)
- **A1 (Normal to mildly increased)**: $< 30\\text{ mg/g}$ ($< 3\\text{ mg/mmol}$)
- **A2 (Moderately increased)**: $30 - 300\\text{ mg/g}$ ($3 - 30\\text{ mg/mmol}$)
- **A3 (Severely increased)**: $> 300\\text{ mg/g}$ ($> 30\\text{ mg/mmol}$, includes nephrotic range)

---

## 2. Renoprotective Pharmacotherapy
1. **Renin-Angiotensin System (RAS) Blockade**:
   - ACE inhibitor or ARB titrated to maximum tolerated approved dose in patients with hypertension, CKD, and severely increased albuminuria (A3) or diabetes with A2.
   - Monitor serum creatinine and potassium within 2–4 weeks of initiation or dose increase. Up to a $30\\%$ increase in serum creatinine is acceptable.
2. **SGLT2 Inhibitors**:
   - Recommended in patients with CKD and eGFR $\\ge 20\\text{ mL/min/1.73 m}^2$ with UACR $> 200\\text{ mg/g}$ (regardless of diabetes status).
3. **Nonsteroidal Mineralocorticoid Receptor Antagonist (ns-MRA)**:
   - Finerenone recommended in patients with Type 2 Diabetes, eGFR $\ge 25\text{ mL/min/1.73 m}^2$, normal serum potassium, and persistent albuminuria (UACR $> 30\text{ mg/g}$) despite maximum tolerated RAS inhibitor.
"""
    },
    {
        "filename": "IDSA_Acute_Uncomplicated_Cystitis_UTI_Guideline.md",
        "title": "Infectious Diseases Society of America (IDSA) Guidelines for Acute Uncomplicated Cystitis",
        "content": """# IDSA Clinical Practice Guideline for the Treatment of Acute Uncomplicated Cystitis and Pyelonephritis in Women

**Authority**: Infectious Diseases Society of America (IDSA) / European Society for Microbiology and Infectious Diseases (ESCMID)  
**Target Population**: Non-pregnant adult females with acute uncomplicated lower urinary tract infection (cystitis)  

---

## 1. First-Line Antimicrobial Regimens
1. **Nitrofurantoin Monohydrate/Macrocrystals (Macrobid)**:
   - Dosage: $100\text{ mg}$ orally twice daily with food for $5\text{ days}$.
   - Pharmacokinetics: High urinary concentration with minimal systemic tissue penetration. 
   - Safety: Contraindicated in severe renal impairment (eGFR $< 30\text{ mL/min}$). Ineffective for pyelonephritis. Low propensity for collateral damage and minimal resistance.
2. **Trimethoprim-Sulfamethoxazole (TMP-SMX, Bactrim DS)**:
   - Dosage: One double-strength tablet ($160\text{ mg TMP} / 800\text{ mg SMX}$) orally twice daily for $3\text{ days}$.
   - Threshold Rule: Appropriate first-line therapy ONLY if local uropathogen *E. coli* resistance rates do NOT exceed $20\%$, and the patient has no known sulfa allergy.
3. **Fosfomycin Trometamol**:
   - Dosage: $3\text{ g}$ single-dose oral powder sachet mixed in 3-4 oz water.
   - Indication: Convenient single-dose therapy; slightly lower clinical cure rates compared to nitrofurantoin.
4. **Pivmecillinam**:
   - Dosage: $400\text{ mg}$ orally three times daily for $3\text{ to }5\text{ days}$.

---

## 2. Second-Line & Alternative Regimens
- **Oral Beta-Lactams**:
  - Amoxicillin-clavulanate ($500/125\text{ mg}$ PO BID for $5-7\text{ days}$), Cefdinir ($300\text{ mg}$ PO BID), Cefaclor, or Cephalexin ($500\text{ mg}$ PO QID).
  - Note: Beta-lactams have lower clinical and microbiological cure rates and higher adverse events than first-line agents.
  - **CRITICAL CONTRAINDICATION**: Amoxicillin-clavulanate is a penicillin derivative and is strictly contraindicated in patients with known penicillin or beta-lactam allergies (risk of severe anaphylaxis).

---

## 3. Agents to Strictly Avoid or Reserve
- **Fluoroquinolones (Ciprofloxacin, Levofloxacin)**:
  - Strongly discouraged for uncomplicated cystitis due to FDA black box warnings (tendon rupture, peripheral neuropathy, aortic dissection, QT prolongation) and high collateral resistance risk. Reserved strictly for acute pyelonephritis.
- **Amoxicillin or Ampicillin Monotherapy**:
  - Not recommended empirically due to worldwide resistance rates $> 30-50\%$.
- **Macrolides (Azithromycin)**:
  - Ineffective against common Gram-negative uropathogens causing cystitis.
"""
    },
    {
        "filename": "GOLD_COPD_Management_Guideline.md",
        "title": "Global Initiative for Chronic Obstructive Lung Disease (GOLD) Strategy",
        "content": """# GOLD Strategy: Global Initiative for Chronic Obstructive Lung Disease

**Authority**: Global Initiative for Chronic Obstructive Lung Disease (GOLD)  
**Scope**: Diagnosis, Assessment, and Treatment of COPD  

---

## 1. Diagnosis and Assessment
- **Definition**: COPD is a common, preventable, and treatable disease characterized by persistent respiratory symptoms and airflow limitation due to airway and/or alveolar abnormalities.
- **Spirometry**: Post-bronchodilator $FEV_1/FVC < 0.70$ confirms the presence of persistent airflow limitation.
- **Assessment**: Assessment is based on symptom burden (mMRC or CAT scores) and history of moderate-to-severe exacerbations.

## 2. Pharmacological Treatment (ABCD Assessment Tool)
- **Group A (Low risk, fewer symptoms)**: A bronchodilator (short- or long-acting).
- **Group B (Low risk, more symptoms)**: A long-acting bronchodilator (LABA or LAMA).
- **Group E (High risk, exacerbations)**:
  - Initial therapy: Dual bronchodilation (LABA + LAMA) is preferred.
  - Triple therapy (LABA + LAMA + ICS) recommended if blood eosinophil counts $\ge 300\text{ cells}/\mu\text{L}$.

## 3. Non-Pharmacological Management
- **Smoking Cessation**: The single most effective and cost-effective intervention to reduce risk of developing COPD and stopping its progression.
- **Vaccination**: Influenza, Pneumococcal, COVID-19, and Tdap vaccines are recommended.
- **Pulmonary Rehabilitation**: Indicated for patients with dyspnea, reduced exercise tolerance, or recent exacerbations.
"""
    }
]


async def ingest_curated_guidelines():
    print("\n[Guidelines] Ingesting core clinical practice guidelines...")
    async with async_session_factory() as session:
        for g in CURATED_GUIDELINES:
            res = await store_medical_document(
                session=session,
                filename=g["filename"],
                content=g["content"],
                classification="public",
                content_type="text/markdown",
            )
            if res.is_duplicate:
                print(f"  [Exists] {g['filename']} ({res.chunk_count} chunks)")
            else:
                print(f"  [Indexed] {g['filename']} -> {res.chunk_count} chunks")


async def ingest_local_pdf(pdf_path: Path):
    if not pdf_path.exists():
        print(f"[Guidelines] File not found: {pdf_path}")
        return

    print(f"[Guidelines] Processing PDF: {pdf_path.name}...")
    pages = extract_pages(pdf_path, ".pdf")
    chunks = chunk_pages(pages)
    full_text = "\n\n".join(p.text for p in pages)
    custom_chunk_strings = [c.content for c in chunks]

    async with async_session_factory() as session:
        res = await store_medical_document(
            session=session,
            filename=pdf_path.name,
            content=full_text,
            classification="public",
            content_type="application/pdf",
            custom_chunks=custom_chunk_strings,
        )
        print(f"[Guidelines] Stored {pdf_path.name}: {res.chunk_count} chunks (Duplicate: {res.is_duplicate})")


async def main():
    await ingest_curated_guidelines()
    if len(sys.argv) > 1:
        custom_target = Path(sys.argv[1])
        if custom_target.is_file() and custom_target.suffix.lower() == ".pdf":
            await ingest_local_pdf(custom_target)
        elif custom_target.is_dir():
            for pdf_file in custom_target.glob("*.pdf"):
                await ingest_local_pdf(pdf_file)


if __name__ == "__main__":
    asyncio.run(main())
