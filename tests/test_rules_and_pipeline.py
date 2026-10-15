import pytest
import os
import json
from engine.rule_store import RuleStore
from engine.rule_runner import DeterministicRuleRunner
from engine.audit_trail import AuditTrail

def test_rule_store_loading():
    store = RuleStore()
    rules = store.get_all_rules()
    assert len(rules) >= 3
    rule_ids = [r["rule_id"] for r in rules]
    assert "HO_DISC_02" in rule_ids
    assert "IRDAI_WELL_01" in rule_ids

def test_rule_search():
    store = RuleStore()
    matches = store.search_rules(query="safety device", line_of_business="Homeowners")
    assert len(matches) > 0
    assert matches[0]["rule_id"] == "HO_DISC_02"

def test_deterministic_calculation_and_regression():
    store = RuleStore()
    old_rule = store.get_rule_by_id("HO_DISC_02")
    # Propose new 8% discount (factor 0.92)
    new_rule = store.create_proposed_rule("HO_DISC_02", {"multiplier_factor": 0.92, "discount_percent": 8.0})

    test_cases = [
        {
            "test_id": "TC-001",
            "name": "Standard Homeowner with Certified Safety Device",
            "input_payload": {"base_premium": 1000.0, "has_certified_safety_device": True},
            "expected_old_premium": 950.0,
            "expected_new_premium": 920.0
        }
    ]

    results = DeterministicRuleRunner.execute_test_suite(old_rule, new_rule, test_cases)
    assert len(results) == 1
    assert results[0]["status"] == "PASS"
    assert results[0]["actual_old"] == 950.0
    assert results[0]["actual_new"] == 920.0
    # Old rule on new expectation must fail (proves regression sensitivity)
    assert results[0]["regression_flagged"] is True

def test_audit_trail_hash_chain():
    test_db = "test_audit.db"
    if os.path.exists(test_db):
        os.remove(test_db)

    audit = AuditTrail(db_path=test_db)
    change_id = "TEST-CHG-001"

    step1 = audit.log_step(
        change_id=change_id,
        step="INTAKE",
        source_clause="Section 4(b)",
        input_data={"raw": "test"},
        output_data={"extracted": True}
    )

    step2 = audit.log_step(
        change_id=change_id,
        step="IMPACT",
        source_clause="Section 4(b)",
        input_data={"rule": "HO_DISC_02"},
        output_data={"factor": 0.92}
    )

    # Verify chain
    assert step2["previous_hash"] == step1["record_hash"]
    integrity = audit.verify_chain_integrity(change_id)
    assert integrity["valid"] is True
    assert integrity["count"] == 2

    # Clean up test DB
    if os.path.exists(test_db):
        os.remove(test_db)
