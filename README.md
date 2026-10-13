# Reg2Release: From Regulation to Verified Rule Change

> **Multi-Agent Architecture with Automated Tests and a Human Approval Gate**  
> **Author:** Adapala Bhargava Krishna | B.E. Information Technology, CBIT Hyderabad  
> **Proposal:** Flarre AI Inc Hackathon 2026

---

## 🌟 Overview & Problem Statement

Insurance carriers in the US (state DOI bulletins) and India (IRDAI circulars) process thousands of regulatory amendments every year.
- **The bottleneck isn't knowing that a regulation changed**—it is determining *which specific rating and underwriting rules are impacted*, authoring software specifications, modifying rating parameters, and mathematically verifying the updates before deployment.
- **Existing compliance tools** only track *what changed* (text search and diff alerts).
- **Reg2Release focuses on checking that the rule change was implemented as intended**, providing a complete verifiable chain from statutory clause to production rule change.

---

## 🏗️ Architecture & Pipeline Stages (100% Prototype Implementation)

```
[1. Regulatory Source] (PDF File Ingestion via PyMuPDF / Web Bulletin)
         │
         ▼
[2. Intake Agent] (Extracts jurisdiction, clause citation, obligations, effective date)
         │
         ▼
[3. Impact Agent] (Hybrid Semantic + Structural Rule Retrieval from Knowledge Base)
         │
         ▼
[4. Spec Agent] (Drafts Jira user stories & Gherkin acceptance criteria linked to clause) ◄───┐
         │                                                                                    │
         ▼                                                                                    │ (Stage 7 -> 4
[5. Test Agent] (Synthesizes test scenarios with expected before/after values)                │  Review Loopback)
         │                                                                                    │
         ▼                                                                                    │
[6. Automated Tests] (Deterministic Python Rule Engine runs Old vs New + Regression check)   │
         │                                                                                    │
         ▼                                                                                    │
[7. Human Review Gate] (Analyst reviews diff: Approve / Request Edits / Reject) ──────────────┘
         │
         ▼
[Approved Package] (Traceability Matrix + Tamper-Evident SHA-256 Chained SQLite Audit Trail)
```

---

## 🌟 Key Features of the 100% Complete Prototype

1. **Direct PDF Document Ingestion (Stage 1):**
   - High-fidelity PDF extraction using `PyMuPDF`. Upload any state bulletin or IRDAI circular PDF or use pre-packaged official publications (`data/sample_documents/`).

2. **Semantic Knowledge Base Rule Retrieval (Stage 3):**
   - Hybrid matching computing both structural metadata compatibility and continuous semantic relevance scores.

3. **Deterministic Automated Rule Engine (Stage 6):**
   - Pure Python execution. Eliminates LLM math hallucinations and asserts that legacy rules fail under new expectations (regression sensitivity).

4. **Interactive Human-in-the-Loop Review & Loopback (Stage 7 ➔ Stage 4):**
   - Selecting "REQUEST EDITS" enables the analyst to input directives that re-trigger the Spec Agent and regenerate tests automatically, closing the feedback loop from Figure 1.

5. **Tamper-Evident Hash-Chained SQLite Audit Trail (Section 7):**
   - Append-only enforcement via SQLite database triggers prohibiting `UPDATE` and `DELETE`.
   - Every transaction is sealed with `SHA-256(previous_hash + change_id + step + payload + decision)`.
   - Live cryptographic integrity verification directly from the UI.

6. **Section 9 Benchmark & Evaluation Dashboard:**
   - Benchmarks cycle time (sub-10s vs 4-6h manual), 100% traceability coverage, 100% test detection rate, and 100% mathematical determinism.

7. **Docker Containerization:**
   - Ready for containerized deployment via `docker-compose.yml` and `Dockerfile`.

---

## 🚀 How to Run

### Method A: Local Launch (Windows / Streamlit)
```bash
.\run.bat
# or
streamlit run app.py
```
Open **http://localhost:8501** in your browser.

### Method B: Docker Container
```bash
docker compose up --build
```

### Method C: Run Automated PyTest Suite
```bash
pytest tests/test_rules_and_pipeline.py
```

---

## 🎤 Interviewer Walkthrough Script (Step-by-Step Demo)

1. **Introduction:**
   > *"Hi, I built Reg2Release to solve the insurance regulatory implementation gap. Instead of just alerting teams that a regulation changed, Reg2Release takes the regulatory text and automatically produces a verified, tested, and traceable rule change package."*

2. **Run Pipeline:**
   > *"Let's select the Florida Office of Insurance Regulation bulletin (FL-OIR-2026-04) from the sidebar and click 'Run Multi-Agent Pipeline'. Behind the scenes, we use LangChain with Groq running `openai/gpt-oss-120b`."*

3. **Show Tab 1 (Intake Extraction):**
   > *"The Intake Agent parses the legal text into a strict Pydantic JSON schema: extracting Florida Homeowners, effective date 2026-11-01, citing Section 4(b), and recognizing the discount increase from 5% (0.95 factor) to 8% (0.92 factor)."*

4. **Show Tab 2 (Impact & Rule Diff):**
   > *"The Impact Agent queries our rule catalog, flags carrier rule `HO_DISC_02`, and provides statutory evidence. Notice the side-by-side JSON diff showing multiplier_factor transitioning from 0.95 to 0.92."*

5. **Show Tab 3 (Specifications):**
   > *"The Spec Agent generates Jira-ready user stories and Gherkin acceptance criteria linked directly to Section 4(b)."*

6. **Show Tab 4 (Automated Tests):**
   > *"Here is where we do something different: AI generated the test cases, but the tests run on a deterministic Python rule engine! We run each test on both the OLD rule (factor 0.95, giving $950) and the NEW rule (factor 0.92, giving $920). We also assert that the old rule fails against the new expectation, proving regression sensitivity."*

7. **Show Tab 5 & 6 (Human Review Gate & Tamper-Evident Audit Trail):**
   > *"Before anything is released, a human analyst reviews and approves it. Every step is cryptographically linked in a SHA-256 hash chain in SQLite with append-only triggers. Clicking 'Verify Hash Chain Integrity' mathematically validates that the audit log has not been tampered with."*

8. **Show Tab 7 (Export Package):**
   > *"Finally, we can download the complete compliance audit report and approved JSON package for immediate ingestion into carrier policy administration systems."*
