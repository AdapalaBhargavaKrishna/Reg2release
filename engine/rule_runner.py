import time
import math

class DeterministicRuleRunner:
    """Deterministic Rule Engine that evaluates rating calculations and runs automated tests."""

    @staticmethod
    def calculate_premium(rule: dict, payload: dict) -> dict:
        """Deterministically applies rule parameters to calculate premium output."""
        base_premium = float(payload.get("base_premium", 1000.0))
        params = rule.get("parameters", {})
        
        multiplier = float(params.get("multiplier_factor", 1.0))
        discount_pct = float(params.get("discount_percent", 0.0))

        # Check eligibility flag if provided
        eligible = payload.get("has_certified_safety_device", True)
        if not eligible and "has_certified_safety_device" in payload:
            multiplier = 1.0
            discount_pct = 0.0

        final_premium = round(base_premium * multiplier, 2)
        applied_discount = round(base_premium - final_premium, 2)

        return {
            "rule_id": rule.get("rule_id"),
            "version": rule.get("version"),
            "base_premium": base_premium,
            "multiplier_used": multiplier,
            "discount_percent": discount_pct,
            "calculated_premium": final_premium,
            "discount_amount": applied_discount
        }

    @classmethod
    def execute_test_suite(cls, old_rule: dict, new_rule: dict, test_cases: list) -> list:
        """Runs test cases against both old and new rule versions and verifies before/after expectations."""
        results = []

        for idx, tc in enumerate(test_cases, 1):
            start_t = time.perf_counter()
            test_id = tc.get("test_id", f"TC-{idx:03d}")
            name = tc.get("name", f"Test Case {idx}")
            input_payload = tc.get("input_payload", {"base_premium": 1000.0})
            expected_old = float(tc.get("expected_old_premium", 950.0))
            expected_new = float(tc.get("expected_new_premium", 920.0))

            # Run on Old Rule
            old_run = cls.calculate_premium(old_rule, input_payload)
            actual_old = old_run["calculated_premium"]
            old_pass = math.isclose(actual_old, expected_old, abs_tol=0.01)

            # Run on New Rule
            new_run = cls.calculate_premium(new_rule, input_payload)
            actual_new = new_run["calculated_premium"]
            new_pass = math.isclose(actual_new, expected_new, abs_tol=0.01)

            # Regression sensitivity test: Old rule evaluated against NEW expectation must fail
            # for policies that qualify for the changed discount
            if not math.isclose(expected_old, expected_new, abs_tol=0.01):
                old_on_new_expectation_fails = not math.isclose(actual_old, expected_new, abs_tol=0.01)
                passed_overall = old_pass and new_pass and old_on_new_expectation_fails
            else:
                old_on_new_expectation_fails = False
                passed_overall = old_pass and new_pass

            exec_time_ms = round((time.perf_counter() - start_t) * 1000, 2)

            results.append({
                "test_id": test_id,
                "name": name,
                "input_payload": input_payload,
                "expected_old": expected_old,
                "actual_old": actual_old,
                "old_assertion_pass": old_pass,
                "expected_new": expected_new,
                "actual_new": actual_new,
                "new_assertion_pass": new_pass,
                "regression_flagged": old_on_new_expectation_fails,
                "status": "PASS" if passed_overall else "FAIL",
                "execution_time_ms": exec_time_ms
            })

        return results
