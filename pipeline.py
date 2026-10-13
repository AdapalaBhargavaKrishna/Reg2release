import uuid
import datetime
import json
from agents.intake_agent import IntakeAgent, IntakeExtraction
from agents.impact_agent import ImpactAgent, ImpactEvaluation
from agents.spec_agent import SpecAgent, SpecificationPackage
from agents.test_agent import TestAgent, TestSuiteOutput
from engine.rule_store import RuleStore
from engine.rule_runner import DeterministicRuleRunner
from engine.audit_trail import AuditTrail
import config

class Reg2ReleasePipeline:
    """End-to-end multi-agent orchestration pipeline for Reg2Release."""

    def __init__(self, api_key: str = None, model_name: str = None):
        self.api_key = api_key or config.GROQ_API_KEY
        self.model_name = model_name or config.MODEL_NAME
        self.rule_store = RuleStore()
        self.audit_trail = AuditTrail()

        self.intake_agent = IntakeAgent(api_key=self.api_key, model_name=self.model_name)
        self.impact_agent = ImpactAgent(api_key=self.api_key, model_name=self.model_name)
        self.spec_agent = SpecAgent(api_key=self.api_key, model_name=self.model_name)
        self.test_agent = TestAgent(api_key=self.api_key, model_name=self.model_name)

    def run_pipeline(self, regulatory_text: str, change_id: str = None) -> dict:
        change_id = change_id or f"CHG-{uuid.uuid4().hex[:8].upper()}"

        # ----------------- Step 1 & 2: Intake Agent -----------------
        intake_res: IntakeExtraction = self.intake_agent.extract(regulatory_text)
        self.audit_trail.log_step(
            change_id=change_id,
            step="1. INTAKE_EXTRACTION",
            source_clause=intake_res.source_clause,
            input_data={"raw_text_length": len(regulatory_text)},
            output_data=intake_res.model_dump(),
            confidence_score=intake_res.confidence_score
        )

        # ----------------- Step 3: Impact Agent -----------------
        candidate_rules = self.rule_store.search_rules(
            query=intake_res.target_rule_hint or intake_res.requirement_summary,
            jurisdiction=intake_res.jurisdiction,
            line_of_business=intake_res.line_of_business
        )
        impact_res: ImpactEvaluation = self.impact_agent.evaluate_impact(intake_res, candidate_rules)

        # Retrieve base rule & create proposed new rule
        old_rule = self.rule_store.get_rule_by_id(impact_res.affected_rule_id)
        if not old_rule:
            old_rule = candidate_rules[0]

        new_rule = self.rule_store.create_proposed_rule(
            base_rule_id=old_rule["rule_id"],
            new_parameters=impact_res.parameter_changes
        )

        self.audit_trail.log_step(
            change_id=change_id,
            step="2. IMPACT_ANALYSIS",
            source_clause=impact_res.evidence_citation,
            input_data={"candidate_count": len(candidate_rules), "target_rule": old_rule["rule_id"]},
            output_data=impact_res.model_dump(),
            confidence_score=impact_res.confidence_score
        )

        # ----------------- Step 4: Spec Agent -----------------
        spec_res: SpecificationPackage = self.spec_agent.draft_specification(intake_res, impact_res)
        self.audit_trail.log_step(
            change_id=change_id,
            step="3. SPEC_GENERATION",
            source_clause=spec_res.source_clause_link,
            input_data={"requirement_id": spec_res.requirement_id},
            output_data=spec_res.model_dump(),
            confidence_score=0.98
        )

        # ----------------- Step 5: Test Agent -----------------
        tests_res: TestSuiteOutput = self.test_agent.generate_tests(spec_res, impact_res, old_rule)
        self.audit_trail.log_step(
            change_id=change_id,
            step="4. TEST_SYNTHESIS",
            source_clause=spec_res.source_clause_link,
            input_data={"test_count": len(tests_res.test_cases)},
            output_data=tests_res.model_dump(),
            confidence_score=0.99
        )

        # ----------------- Step 6: Automated Tests Execution (Deterministic) -----------------
        test_run_results = DeterministicRuleRunner.execute_test_suite(
            old_rule=old_rule,
            new_rule=new_rule,
            test_cases=[tc.model_dump() for tc in tests_res.test_cases]
        )
        all_passed = all(tr["status"] == "PASS" for tr in test_run_results)

        self.audit_trail.log_step(
            change_id=change_id,
            step="5. DETERMINISTIC_TEST_EXECUTION",
            source_clause=spec_res.source_clause_link,
            input_data={"old_version": old_rule.get("version"), "new_version": new_rule.get("version")},
            output_data={"all_passed": all_passed, "results": test_run_results},
            confidence_score=1.0  # Mathematical proof
        )

        # Build Traceability Matrix (Source Clause -> Rule -> User Story -> Test Case)
        traceability_matrix = []
        for idx, tc in enumerate(tests_res.test_cases):
            story = spec_res.user_stories[idx % len(spec_res.user_stories)]
            test_res = test_run_results[idx] if idx < len(test_run_results) else None
            traceability_matrix.append({
                "source_clause": intake_res.source_clause,
                "requirement_id": spec_res.requirement_id,
                "impacted_rule": f"{old_rule['rule_id']} (v{old_rule['version']} -> v{new_rule['version']})",
                "user_story": f"{story.story_id}: {story.i_want_to}",
                "test_case": f"{tc.test_id}: {tc.name}",
                "verification_status": test_res["status"] if test_res else "UNKNOWN"
            })

        return {
            "change_id": change_id,
            "timestamp": datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "intake": intake_res.model_dump(),
            "impact": impact_res.model_dump(),
            "old_rule": old_rule,
            "new_rule": new_rule,
            "spec": spec_res.model_dump(),
            "test_suite": tests_res.model_dump(),
            "test_results": test_run_results,
            "all_tests_passed": all_passed,
            "traceability_matrix": traceability_matrix,
            "review_status": "PENDING_APPROVAL"
        }

    def record_human_decision(self, change_id: str, decision: str, reviewer_name: str, comments: str, state: dict):
        """Records Human Approval Gate decision in the tamper-evident audit log."""
        self.audit_trail.log_step(
            change_id=change_id,
            step="6. HUMAN_APPROVAL_GATE",
            source_clause=state.get("intake", {}).get("source_clause", ""),
            input_data={"reviewed_by": reviewer_name, "comments": comments},
            output_data={"decision": decision, "timestamp": datetime.datetime.now(datetime.timezone.utc).isoformat()},
            confidence_score=1.0,
            reviewer_decision=f"{decision} by {reviewer_name}"
        )

    def rerun_spec_loop_with_feedback(self, current_state: dict, reviewer_feedback: str, reviewer_name: str) -> dict:
        """Stage 7 -> Stage 4 Review Feedback Loop: Refines spec & re-tests based on human analyst instructions."""
        change_id = current_state["change_id"]
        
        # 1. Log the loopback in audit log
        self.audit_trail.log_step(
            change_id=change_id,
            step="7b. REVIEWER_EDIT_LOOPBACK",
            source_clause=current_state.get("intake", {}).get("source_clause", ""),
            input_data={"reviewer_name": reviewer_name, "feedback_instructions": reviewer_feedback},
            output_data={"action": "RETRIGGER_SPEC_AGENT", "timestamp": datetime.datetime.now(datetime.timezone.utc).isoformat()},
            confidence_score=1.0,
            reviewer_decision=f"REQUEST_EDITS by {reviewer_name}"
        )

        # 2. Refine Specification via SpecAgent
        from agents.spec_agent import SpecificationPackage
        from agents.impact_agent import ImpactEvaluation
        current_spec_obj = SpecificationPackage(**current_state["spec"])
        impact_obj = ImpactEvaluation(**current_state["impact"])
        
        revised_spec = self.spec_agent.refine_specification_with_feedback(current_spec_obj, reviewer_feedback)
        
        self.audit_trail.log_step(
            change_id=change_id,
            step="4b. SPEC_REVISED_PER_FEEDBACK",
            source_clause=revised_spec.source_clause_link,
            input_data={"feedback": reviewer_feedback},
            output_data=revised_spec.model_dump(),
            confidence_score=0.99
        )

        # 3. Regenerate Test Suite via TestAgent
        revised_tests = self.test_agent.generate_tests(revised_spec, impact_obj, current_state["old_rule"])
        
        # 4. Re-run Deterministic Tests
        revised_test_results = DeterministicRuleRunner.execute_test_suite(
            old_rule=current_state["old_rule"],
            new_rule=current_state["new_rule"],
            test_cases=[tc.model_dump() for tc in revised_tests.test_cases]
        )
        all_passed = all(tr["status"] == "PASS" for tr in revised_test_results)

        self.audit_trail.log_step(
            change_id=change_id,
            step="5b. DETERMINISTIC_TEST_RE_EXECUTION",
            source_clause=revised_spec.source_clause_link,
            input_data={"revised_spec_id": revised_spec.requirement_id},
            output_data={"all_passed": all_passed, "results": revised_test_results},
            confidence_score=1.0
        )

        # 5. Update Traceability Matrix
        updated_traceability = []
        for idx, tc in enumerate(revised_tests.test_cases):
            story = revised_spec.user_stories[idx % len(revised_spec.user_stories)]
            test_res = revised_test_results[idx] if idx < len(revised_test_results) else None
            updated_traceability.append({
                "source_clause": current_state["intake"]["source_clause"],
                "requirement_id": revised_spec.requirement_id,
                "impacted_rule": f"{current_state['old_rule']['rule_id']} (v{current_state['old_rule']['version']} -> v{current_state['new_rule']['version']})",
                "user_story": f"{story.story_id}: {story.i_want_to}",
                "test_case": f"{tc.test_id}: {tc.name}",
                "verification_status": test_res["status"] if test_res else "UNKNOWN"
            })

        # Update state
        new_state = dict(current_state)
        new_state["spec"] = revised_spec.model_dump()
        new_state["test_suite"] = revised_tests.model_dump()
        new_state["test_results"] = revised_test_results
        new_state["all_tests_passed"] = all_passed
        new_state["traceability_matrix"] = updated_traceability
        new_state["review_status"] = "PENDING_APPROVAL (REVISED)"
        new_state["loop_iteration"] = new_state.get("loop_iteration", 0) + 1

        return new_state

