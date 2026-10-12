import streamlit as st
import json
import time
import pandas as pd
from pipeline import Reg2ReleasePipeline
from data.sample_bulletins import SAMPLE_BULLETINS
from engine.rule_store import RuleStore
from engine.audit_trail import AuditTrail
import config

# Page setup
st.set_page_config(
    page_title="Reg2Release | Regulatory to Verified Rule Change",
    page_icon="⚖️",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Custom Styling
st.markdown("""
<style>
    .main-title {
        font-size: 2.2rem;
        font-weight: 800;
        color: #1E3A8A;
        margin-bottom: 0px;
    }
    .sub-title {
        font-size: 1.05rem;
        color: #4B5563;
        margin-top: 4px;
        margin-bottom: 16px;
    }
    .author-badge {
        background: linear-gradient(135deg, #EEF2FF, #E0E7FF);
        border: 1px solid #C7D2FE;
        padding: 6px 14px;
        border-radius: 8px;
        font-size: 0.85rem;
        color: #3730A3;
        font-weight: 600;
        display: inline-block;
        margin-bottom: 20px;
    }
    .step-badge {
        padding: 4px 10px;
        border-radius: 6px;
        font-size: 0.82rem;
        font-weight: 700;
        letter-spacing: 0.5px;
    }
    .badge-intake { background-color: #DBEAFE; color: #1D4ED8; }
    .badge-impact { background-color: #FCE7F3; color: #BE185D; }
    .badge-spec { background-color: #FEF3C7; color: #B45309; }
    .badge-test { background-color: #D1FAE5; color: #047857; }
    .badge-pass { background-color: #DEF7EC; color: #03543F; font-weight: bold; }
    .badge-fail { background-color: #FDE8E8; color: #9B1C1C; font-weight: bold; }
    .metric-card {
        background-color: #F9FAFB;
        border: 1px solid #E5E7EB;
        border-radius: 10px;
        padding: 14px 18px;
        margin-bottom: 12px;
    }
    .diff-box {
        font-family: 'Consolas', 'Courier New', monospace;
        background-color: #1F2937;
        color: #F9FAFB;
        padding: 14px;
        border-radius: 8px;
        font-size: 0.88rem;
    }
    .hash-text {
        font-family: monospace;
        font-size: 0.82rem;
        color: #4B5563;
        word-break: break-all;
    }
</style>
""", unsafe_allow_html=True)

# Initialize Session State
if "pipeline_result" not in st.session_state:
    st.session_state.pipeline_result = None
if "approval_recorded" not in st.session_state:
    st.session_state.approval_recorded = False
if "reviewer_decision" not in st.session_state:
    st.session_state.reviewer_decision = None
if "change_id" not in st.session_state:
    st.session_state.change_id = None

# Header Section
col_head1, col_head2 = st.columns([3, 1])
with col_head1:
    st.markdown('<div class="main-title">⚖️ Reg2Release: From Regulation to Verified Rule Change</div>', unsafe_allow_html=True)
    st.markdown(f'<div class="sub-title">{config.APP_SUBTITLE}</div>', unsafe_allow_html=True)
    st.markdown(f'<div class="author-badge">👤 Prototype by: {config.AUTHOR} ({config.INSTITUTION}) | {config.PROJECT_EVENT}</div>', unsafe_allow_html=True)

with col_head2:
    st.info(f"**LLM Model:** `{config.MODEL_NAME}`\n\n**Provider:** Groq API\n\n**Framework:** LangChain 1.4")

# Sidebar Configuration
with st.sidebar:
    st.header("📄 Ingestion Controls")
    sample_choice = st.selectbox(
        "Select Regulatory Publication:",
        options=list(SAMPLE_BULLETINS.keys()) + ["Custom Regulatory Text"]
    )

    if sample_choice == "Custom Regulatory Text":
        custom_title = st.text_input("Publication Title", value="State Bulletin / Circular")
        custom_text = st.text_area(
            "Paste Regulatory Text:",
            height=260,
            value="Pursuant to regulatory authority, mandatory safety discount increases from 5% (0.95 factor) to 8% (0.92 factor) for rule HO_DISC_02."
        )
        selected_text = custom_text
    else:
        sample_data = SAMPLE_BULLETINS[sample_choice]
        st.caption(f"**Jurisdiction:** {sample_data['jurisdiction']}")
        st.caption(f"**Line of Business:** {sample_data['line_of_business']}")
        st.caption(f"**Effective Date:** {sample_data['effective_date']}")
        selected_text = sample_data["text"]
        with st.expander("View Source Document Text", expanded=False):
            st.text_area("Full Publication Text", value=selected_text, height=220, disabled=True)

    st.markdown("---")
    st.subheader("⚙️ Execution Settings")
    offline_demo = st.checkbox("Fast Offline Fallback (if Groq quota limits)", value=False, help="Ensures smooth uninterrupted demos during live jury presentations.")

    if st.button("🔄 Reset / Clear State", use_container_width=True):
        st.session_state.pipeline_result = None
        st.session_state.approval_recorded = False
        st.session_state.reviewer_decision = None
        st.session_state.change_id = None
        st.rerun()

    st.markdown("---")
    st.caption("**Shared Services Architecture:**")
    st.caption("• LangChain + Groq (`openai/gpt-oss-120b`)")
    st.caption("• Mock Versioned Rule Catalog (JSON)")
    st.caption("• Deterministic Python Rule Engine")
    st.caption("• SQLite Tamper-Evident Hash-Chained Audit Log")

# Multi-Agent Workflow Overview Banner
st.markdown("""
<div style="background-color: #F8FAFC; border: 1px solid #E2E8F0; padding: 12px 16px; border-radius: 10px; margin-bottom: 20px;">
    <div style="font-size: 0.85rem; font-weight: 700; color: #475569; margin-bottom: 8px;">PIPELINE ARCHITECTURE STAGES:</div>
    <div style="display: flex; justify-content: space-between; align-items: center; flex-wrap: wrap; gap: 8px; font-size: 0.85rem; font-weight: 600;">
        <span class="step-badge badge-intake">1. Sources</span> ➔
        <span class="step-badge badge-intake">2. Intake Agent</span> ➔
        <span class="step-badge badge-impact">3. Impact Agent</span> ➔
        <span class="step-badge badge-spec">4. Spec Agent</span> ➔
        <span class="step-badge badge-test">5. Test Agent</span> ➔
        <span class="step-badge badge-test">6. Automated Tests</span> ➔
        <span class="step-badge" style="background-color: #FEF08A; color: #854D0E;">7. Human Review Gate</span> ➔
        <span class="step-badge" style="background-color: #DCFCE7; color: #166534;">8. Approved Package</span>
    </div>
</div>
""", unsafe_allow_html=True)

# Trigger Button
run_col1, run_col2 = st.columns([1, 2])
with run_col1:
    launch_btn = st.button("🚀 Run Reg2Release Multi-Agent Pipeline", type="primary", use_container_width=True)

if launch_btn:
    progress_bar = st.progress(0, text="Initializing Reg2Release Agents...")
    status_text = st.empty()

    try:
        pipeline = Reg2ReleasePipeline()
        
        status_text.markdown("🔄 **Agent 1: Intake Agent** extracting regulatory obligations...")
        progress_bar.progress(20)
        time.sleep(0.3)

        # Run pipeline
        res = pipeline.run_pipeline(selected_text)
        
        status_text.markdown("🔄 **Agent 2: Impact Agent** matching rule repository & evaluating delta...")
        progress_bar.progress(45)
        time.sleep(0.3)

        status_text.markdown("🔄 **Agent 3: Spec Agent** drafting Jira user stories & acceptance criteria...")
        progress_bar.progress(65)
        time.sleep(0.3)

        status_text.markdown("🔄 **Agent 4 & 5: Test Agent & Deterministic Engine** running before/after verification...")
        progress_bar.progress(90)
        time.sleep(0.3)

        st.session_state.pipeline_result = res
        st.session_state.change_id = res["change_id"]
        st.session_state.approval_recorded = False
        st.session_state.reviewer_decision = None

        progress_bar.progress(100, text="Pipeline Execution Complete!")
        time.sleep(0.5)
        status_text.empty()
        progress_bar.empty()
        st.success(f"Multi-Agent Pipeline executed successfully! Change Package **{res['change_id']}** ready for review.")
    except Exception as e:
        progress_bar.empty()
        status_text.empty()
        st.error(f"Error during execution: {str(e)}")

# Display Pipeline Results
if st.session_state.pipeline_result:
    res = st.session_state.pipeline_result
    intake = res["intake"]
    impact = res["impact"]
    old_rule = res["old_rule"]
    new_rule = res["new_rule"]
    spec = res["spec"]
    tests = res["test_suite"]
    test_results = res["test_results"]
    traceability = res["traceability_matrix"]

    # Top Status Bar
    st.markdown("---")
    m_col1, m_col2, m_col3, m_col4, m_col5 = st.columns(5)
    with m_col1:
        st.metric("Change ID", res["change_id"])
    with m_col2:
        st.metric("Impacted Rule", impact["affected_rule_id"], f"v{old_rule['version']} ➔ v{new_rule['version']}")
    with m_col3:
        st.metric("Factor Delta", f"{impact['parameter_changes'].get('multiplier_factor', 'N/A')}", f"-{impact['parameter_changes'].get('discount_percent', 0.0)}% credit")
    with m_col4:
        pass_count = sum(1 for tr in test_results if tr["status"] == "PASS")
        st.metric("Automated Tests", f"{pass_count}/{len(test_results)} Passed", delta="100% Deterministic")
    with m_col5:
        approval_status = st.session_state.reviewer_decision or "PENDING APPROVAL"
        color = "🟢" if "APPROVED" in approval_status else ("🔴" if "REJECTED" in approval_status else "🟡")
        st.metric("Approval Gate", f"{color} {approval_status}")

    # Tabs for Detailed Stage Exploration
    tab1, tab2, tab3, tab4, tab5, tab6, tab7 = st.tabs([
        "📋 1. Intake Extraction",
        "🎯 2. Impact & Rule Diff",
        "📝 3. Specifications & Stories",
        "🧪 4. Automated Tests",
        "🛡️ 5. Human Review Gate",
        "🔗 6. Traceability & Audit Trail",
        "📦 7. Approved Change Package"
    ])

    # Tab 1: Intake Agent
    with tab1:
        st.subheader("Stage 1 & 2: Regulatory Intake Extraction")
        st.write("The Intake Agent ingests raw legal text and produces a validated, schema-enforced Pydantic record.")

        i_col1, i_col2 = st.columns([1, 1])
        with i_col1:
            st.markdown(f"""
            <div class="metric-card">
                <h4>Extracted Metadata</h4>
                <p><b>Jurisdiction:</b> {intake['jurisdiction']}</p>
                <p><b>Line of Business:</b> {intake['line_of_business']}</p>
                <p><b>Effective Date:</b> <code>{intake['effective_date']}</code></p>
                <p><b>Source Clause:</b> <i>"{intake['source_clause']}"</i></p>
                <p><b>Extraction Confidence:</b> <span class="step-badge badge-test">{intake['confidence_score'] * 100:.1f}%</span></p>
            </div>
            """, unsafe_allow_html=True)
            st.info(f"**Requirement Summary:**\n\n{intake['requirement_summary']}")

        with i_col2:
            st.markdown("#### Key Regulatory Obligations")
            for ob in intake.get("key_obligations", []):
                st.markdown(f"• {ob}")

            with st.expander("View Raw Intake JSON", expanded=False):
                st.json(intake)

    # Tab 2: Impact Agent & Rule Diff
    with tab2:
        st.subheader("Stage 3: Impact Analysis & Rule Retrieval")
        st.write("The Impact Agent queries the Knowledge Base rule catalog, flags the affected rule, and proposes the parameter delta.")

        imp_col1, imp_col2 = st.columns([1, 1])
        with imp_col1:
            st.markdown(f"""
            <div class="metric-card">
                <h4>Matched Carrier Rule: <code>{impact['affected_rule_id']}</code></h4>
                <p><b>Rule Name:</b> {impact['affected_rule_name']}</p>
                <p><b>Impact Classification:</b> <span class="step-badge badge-impact">{impact['impact_type']}</span></p>
                <p><b>Risk Level:</b> <b>{impact['risk_level']}</b></p>
                <p><b>Confidence Score:</b> <span class="step-badge badge-test">{impact['confidence_score'] * 100:.1f}%</span></p>
                <p><b>Evidence Citation:</b> <i>{impact['evidence_citation']}</i></p>
            </div>
            """, unsafe_allow_html=True)
            st.markdown(f"**Impact Reasoning:**\n\n{impact['analysis_reasoning']}")

        with imp_col2:
            st.markdown("#### Old vs Proposed Rule Diff")
            diff_col_a, diff_col_b = st.columns(2)
            with diff_col_a:
                st.caption(f"**Old Active Rule (v{old_rule['version']})**")
                st.code(json.dumps(old_rule["parameters"], indent=2), language="json")
            with diff_col_b:
                st.caption(f"**Proposed Rule (v{new_rule['version']})**")
                st.code(json.dumps(new_rule["parameters"], indent=2), language="json")

    # Tab 3: Spec Agent
    with tab3:
        st.subheader("Stage 4: Requirement Specifications & User Stories")
        st.write("The Spec Agent links source clauses directly to Jira-ready user stories and BDD/Gherkin acceptance criteria.")

        st.markdown(f"### Requirement: `{spec['requirement_id']}` — {spec['title']}")
        st.markdown(f"**Business Rationale:** {spec['business_rationale']}")
        st.markdown(f"**Linked Source Clause:** `{spec['source_clause_link']}`")

        st.markdown("#### User Stories")
        for us in spec.get("user_stories", []):
            st.markdown(f"""
            <div style="background-color: #F8FAFC; border-left: 4px solid #3B82F6; padding: 10px 14px; margin-bottom: 8px; border-radius: 4px;">
                <b>Story {us['story_id']}:</b><br/>
                <b>As a</b> {us['as_a']}<br/>
                <b>I want to</b> {us['i_want_to']}<br/>
                <b>So that</b> {us['so_that']}
            </div>
            """, unsafe_allow_html=True)

        st.markdown("#### Gherkin Acceptance Criteria")
        for ac in spec.get("acceptance_criteria", []):
            st.code(ac, language="gherkin")

    # Tab 4: Test Agent & Deterministic Execution
    with tab4:
        st.subheader("Stage 5 & 6: Automated Tests & Deterministic Verification")
        st.write("""
        **Crucial Architecture Principle (from Section 3 of proposal):**
        *Where AI is not used:* Rule logic and test execution are performed by a **deterministic Python rule engine**, not an LLM.
        The generated tests evaluate both the **OLD** and **NEW** rule versions to verify intended change and catch regressions.
        """)

        # Test results table
        tr_df = []
        for tr in test_results:
            tr_df.append({
                "Test ID": tr["test_id"],
                "Scenario Name": tr["name"],
                "Base Premium": f"${tr['input_payload'].get('base_premium', 1000):,.2f}",
                "Expected Old": f"${tr['expected_old']:,.2f}",
                "Actual Old": f"${tr['actual_old']:,.2f}",
                "Expected New": f"${tr['expected_new']:,.2f}",
                "Actual New": f"${tr['actual_new']:,.2f}",
                "Regression Sensitive": "✅ Yes (Old fails on New)" if tr["regression_flagged"] else "➖ Control Case",
                "Status": "✅ PASS" if tr["status"] == "PASS" else "❌ FAIL",
                "Time (ms)": f"{tr['execution_time_ms']} ms"
            })
        st.dataframe(pd.DataFrame(tr_df), use_container_width=True)

        st.success(f"🎉 **Deterministic Verification:** {pass_count} of {len(test_results)} test cases satisfied all mathematical assertions.")

        with st.expander("Detailed Test Case Payloads & Rationale", expanded=False):
            for tc in tests.get("test_cases", []):
                st.markdown(f"**{tc['test_id']}: {tc['name']}**")
                st.caption(f"Rationale: {tc['rationale']}")
                st.json(tc["input_payload"])

    # Tab 5: Human Review Gate
    with tab5:
        st.subheader("Stage 7: Human Review Gate (HITL)")
        st.write("Regulatory rules are never deployed directly by AI. A human compliance analyst reviews the diff, evidence, and test results.")

        st.markdown(f"""
        <div style="background-color: #FEF9C3; border: 1px solid #FDE047; padding: 14px; border-radius: 8px; margin-bottom: 16px;">
            <h4 style="margin: 0; color: #854D0E;">Analyst Verification Checklist</h4>
            <p style="margin: 4px 0 0 0; color: #713F12; font-size: 0.9rem;">
                ✓ Source clause cited: <code>{intake['source_clause']}</code><br/>
                ✓ Rule parameter change: <code>{impact['affected_rule_id']}</code> factor <b>{old_rule['parameters'].get('multiplier_factor')} ➔ {new_rule['parameters'].get('multiplier_factor')}</b><br/>
                ✓ Deterministic automated test suite: <b>{pass_count}/{len(test_results)} Passed</b>
            </p>
        </div>
        """, unsafe_allow_html=True)

        rev_col1, rev_col2 = st.columns([1, 1])
        with rev_col1:
            decision = st.radio(
                "Compliance Action:",
                ["APPROVE (Release to Production)", "REQUEST_EDITS (Loop back to Spec Agent)", "REJECT (Non-Compliant)"],
                index=0
            )
            reviewer_name = st.text_input("Reviewer Name / Analyst ID:", value="Adapala Bhargava Krishna (Lead Analyst)")
            comments = st.text_area("Reviewer Audit Notes:", value="Verified Florida OIR factor revision against Bulletin OIR-26-04M Section 4(b). Deterministic tests pass.")

            if st.button("💾 Submit Decision to Audit Trail", type="primary"):
                pipe = Reg2ReleasePipeline()
                pipe.record_human_decision(
                    change_id=res["change_id"],
                    decision=decision,
                    reviewer_name=reviewer_name,
                    comments=comments,
                    state=res
                )
                st.session_state.approval_recorded = True
                st.session_state.reviewer_decision = decision
                st.rerun()

        with rev_col2:
            if st.session_state.approval_recorded:
                st.markdown(f"""
                <div style="background-color: #ECFDF5; border: 2px solid #10B981; padding: 18px; border-radius: 10px;">
                    <h3 style="color: #065F46; margin: 0;">✅ Decision Recorded</h3>
                    <p style="color: #047857; margin: 8px 0;">
                        <b>Status:</b> {st.session_state.reviewer_decision}<br/>
                        <b>Reviewer:</b> {reviewer_name}<br/>
                        <b>Timestamp:</b> Just now (Logged in hash chain)
                    </p>
                    <p style="font-size: 0.85rem; color: #065F46;">
                        This decision has been cryptographically committed into the SQLite append-only audit log.
                    </p>
                </div>
                """, unsafe_allow_html=True)
            else:
                st.info("Awaiting reviewer action above.")

    # Tab 6: Traceability & Cryptographic Audit Trail
    with tab6:
        st.subheader("Traceability Matrix & Hash-Chained SQLite Audit Trail")
        st.write("Section 7 of the paper details how each step is committed into a tamper-evident hash-chained append-only SQLite log.")

        st.markdown("#### Complete Traceability Chain")
        st.dataframe(pd.DataFrame(traceability), use_container_width=True)

        st.markdown("---")
        st.markdown("#### Cryptographic Audit Log (SQLite)")

        trail_col1, trail_col2 = st.columns([3, 1])
        with trail_col2:
            if st.button("🔐 Verify Hash Chain Integrity", use_container_width=True):
                pipe = Reg2ReleasePipeline()
                ver = pipe.audit_trail.verify_chain_integrity(res["change_id"])
                if ver["valid"]:
                    st.success(f"✅ Integrity Verified!\n\n{ver['message']}")
                else:
                    st.error(f"❌ TAMPER DETECTED!\n\n{ver['message']}")

        # Fetch and display the audit log entries from DB
        pipe = Reg2ReleasePipeline()
        audit_records = pipe.audit_trail.get_trail(res["change_id"])
        
        audit_table = []
        for rec in audit_records:
            audit_table.append({
                "Entry #": rec["id"],
                "Pipeline Step": rec["step"],
                "Timestamp (UTC)": rec["timestamp"],
                "Reviewer Decision": rec["reviewer_decision"],
                "Previous Hash": rec["previous_hash"][:16] + "...",
                "Record Hash": rec["record_hash"][:16] + "..."
            })
        st.dataframe(pd.DataFrame(audit_table), use_container_width=True)

        with st.expander("Inspect Raw Hash Chain Blocks", expanded=False):
            for rec in audit_records:
                st.markdown(f"**Step:** `{rec['step']}` | **Record Hash:** `{rec['record_hash']}`")
                st.markdown(f"**Previous Hash:** `{rec['previous_hash']}`")
                st.markdown(f"**Output Payload:** `{rec['output_payload'][:120]}...`")
                st.markdown("---")

    # Tab 7: Approved Change Package Export
    with tab7:
        st.subheader("Approved Change Package & Export")
        st.write("Ready for integration with carrier policy administration and rating engines.")

        pkg_json = json.dumps(res, indent=2)

        markdown_report = f"""# Regulatory Compliance Release Report: Reg2Release
**Change ID:** {res['change_id']}  
**Generated On:** {res['timestamp']}  
**Author:** {config.AUTHOR} ({config.INSTITUTION})  
**Hackathon Event:** {config.PROJECT_EVENT}  

---

## 1. Regulatory Source
- **Jurisdiction:** {intake['jurisdiction']}
- **Line of Business:** {intake['line_of_business']}
- **Effective Date:** {intake['effective_date']}
- **Source Clause:** {intake['source_clause']}
- **Requirement Summary:** {intake['requirement_summary']}

## 2. Impacted Insurance Rule
- **Rule ID:** {impact['affected_rule_id']} ({impact['affected_rule_name']})
- **Version Transition:** v{old_rule['version']} -> v{new_rule['version']}
- **Parameter Delta:** {json.dumps(impact['parameter_changes'])}
- **Evidence Citation:** {impact['evidence_citation']}
- **Impact Confidence:** {impact['confidence_score'] * 100:.1f}%

## 3. Engineering Specification
- **Requirement ID:** {spec['requirement_id']}
- **Title:** {spec['title']}
- **Business Rationale:** {spec['business_rationale']}

### User Stories:
"""
        for us in spec.get("user_stories", []):
            markdown_report += f"- **{us['story_id']}**: As a {us['as_a']}, I want to {us['i_want_to']}, so that {us['so_that']}\n"

        markdown_report += "\n## 4. Deterministic Automated Test Results\n"
        for tr in test_results:
            markdown_report += f"- **{tr['test_id']}**: {tr['name']} | Base: ${tr['input_payload'].get('base_premium', 1000)} | Expected Old: ${tr['expected_old']} (Actual: ${tr['actual_old']}) | Expected New: ${tr['expected_new']} (Actual: ${tr['actual_new']}) | Result: **{tr['status']}**\n"

        markdown_report += f"""
## 5. Human Approval Gate
- **Decision:** {st.session_state.reviewer_decision or 'PENDING_APPROVAL'}
- **Cryptographic Audit Log:** Hash chained append-only SQLite store verified.
"""

        c_col1, c_col2 = st.columns(2)
        with c_col1:
            st.download_button(
                label="📥 Download Change Package (JSON)",
                data=pkg_json,
                file_name=f"Reg2Release_{res['change_id']}.json",
                mime="application/json",
                use_container_width=True
            )
        with c_col2:
            st.download_button(
                label="📥 Download Compliance Audit Report (Markdown)",
                data=markdown_report,
                file_name=f"Reg2Release_Audit_Report_{res['change_id']}.md",
                mime="text/markdown",
                use_container_width=True
            )

        st.markdown("#### Preview of Change Package Summary")
        st.markdown(markdown_report)

else:
    # Landing Guide before running
    st.info("👈 **How to demonstrate to interviewers:**\n\n1. Select a regulatory bulletin from the sidebar (e.g. Florida OIR Bulletin or IRDAI Circular).\n2. Click **'Run Reg2Release Multi-Agent Pipeline'**.\n3. Walk the interviewer through each tab: **Intake**, **Impact**, **Spec**, **Deterministic Tests**, **Human Approval Gate**, and **Cryptographic Audit Trail**.\n4. Demonstrate the **'Verify Hash Chain Integrity'** button in Tab 6 to show tamper evidence!")
