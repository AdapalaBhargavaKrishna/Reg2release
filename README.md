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

## 🏗️ Architecture & 7 Pipeline Stages

```
[1. Regulatory Source] (PDF / Circular text)
         │
         ▼
[2. Intake Agent] (Extracts jurisdiction, clause citation, obligations, effective date)
         │
         ▼
[3. Impact Agent] (Matches Knowledge Base rules, computes parameter deltas & confidence)
         │
         ▼
[4. Spec Agent] (Drafts Jira user stories & Gherkin acceptance criteria linked to clause)
         │
         ▼
[5. Test Agent] (Synthesizes test scenarios with expected before/after values)
         │
         ▼
[6. Automated Tests] (Deterministic Python Rule Engine runs Old vs New version + Regression check)
         │
         ▼
[7. Human Review Gate] (Analyst reviews Old vs New diff, evidence, and approves / edits / rejects)
         │
         ▼
[Approved Change Package] (Traceability Matrix + Tamper-Evident SHA-256 Chained SQLite Audit Trail)
```

---

## 🛡️ Critical Design Decisions (Key Interview Talking Points)

1. **Where AI is Used vs. Where AI is NOT Used:**
   - **AI Used:** Ingesting unstructured legal prose, extracting structured Pydantic schemas, fuzzy rule retrieval reasoning, drafting Agile user stories and test scenarios.
   - **Deterministic Code Used (No AI):** The insurance premium calculations and test assertions are executed by a **pure Python deterministic engine** (and pytest). LLMs are not allowed to do insurance math to prevent hallucinations.
   - **Human-in-the-Loop Gate:** No rule is ever deployed directly to production by an AI. A human compliance analyst reviews the exact JSON diff and cited evidence before signing off.

2. **Why Groq with `openai/gpt-oss-120b` & LangChain:**
   - Ultra-fast token latency via Groq's LPU hardware, allowing multi-agent pipelines to execute sequentially in seconds rather than minutes.
   - Strong reasoning and structured JSON output capability from the 120B parameter model.
   - LangChain handles prompt templates, structured output schemas, and multi-agent coordination.

3. **Tamper-Evident Hash-Chained Audit Trail (Section 7):**
   - SQLite alone does not prevent unauthorized modifications.
   - Reg2Release enforces **append-only semantics via SQLite database triggers** (rejecting all `UPDATE` and `DELETE` operations).
   - Every audit record calculates a **SHA-256 cryptographic hash** containing:
     `Hash = SHA-256(Previous_Hash + Change_ID + Step + Timestamp + Input_Hash + Output_Payload + Decision)`
   - Any modification to a previous record immediately breaks the mathematical chain, which can be verified live via the UI button.

---

## 🚀 How to Run the Prototype

### 1. Launch the Streamlit Dashboard
```bash
streamlit run app.py
```
Open [http://localhost:8501](http://localhost:8501) in your browser.

### 2. Run Automated PyTest Suite
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
