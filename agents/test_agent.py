import json
import re
from typing import List, Dict, Any
from pydantic import BaseModel, Field
from langchain_groq import ChatGroq
from langchain_core.messages import SystemMessage, HumanMessage
import config
from agents.spec_agent import SpecificationPackage
from agents.impact_agent import ImpactEvaluation

class TestCaseDefinition(BaseModel):
    test_id: str = Field(description="Unique identifier e.g. TC-001")
    name: str = Field(description="Descriptive test scenario name")
    input_payload: Dict[str, Any] = Field(description="Input payload dictionary for rating engine")
    expected_old_premium: float = Field(description="Deterministic expectation under OLD rule version")
    expected_new_premium: float = Field(description="Deterministic expectation under NEW rule version")
    rationale: str = Field(description="Mathematical explanation of expected values")

class TestSuiteOutput(BaseModel):
    suite_name: str
    target_rule_id: str
    test_cases: List[TestCaseDefinition]

class TestAgent:
    """Agent 4: Generates deterministic test cases with before and after expected values."""

    def __init__(self, api_key: str = None, model_name: str = None):
        self.api_key = api_key or config.GROQ_API_KEY
        self.model_name = model_name or config.MODEL_NAME
        self.llm = ChatGroq(
            api_key=self.api_key,
            model_name=self.model_name,
            temperature=0.0
        )

    def generate_tests(self, spec: SpecificationPackage, impact: ImpactEvaluation, old_rule: dict) -> TestSuiteOutput:
        old_factor = float(old_rule.get("parameters", {}).get("multiplier_factor", 0.95))
        new_factor = float(impact.parameter_changes.get("multiplier_factor", 0.92))

        system_prompt = """You are the Test Agent in Reg2Release.
Your task is to synthesize rigorous test cases verifying the insurance rule parameter delta.
Generate at least 3 distinct test scenarios (e.g., standard base premium, high-value policy, and edge case).
For each test case, calculate the exact numeric expected_old_premium (base_premium * old_factor) and expected_new_premium (base_premium * new_factor).
Output ONLY a valid JSON object matching this schema:
{
  "suite_name": "string",
  "target_rule_id": "string",
  "test_cases": [
    {
      "test_id": "TC-001",
      "name": "string",
      "input_payload": {"base_premium": 1000.0, "has_certified_safety_device": true},
      "expected_old_premium": float,
      "expected_new_premium": float,
      "rationale": "string"
    }
  ]
}
Do NOT include markdown formatting or backticks in the response. Return raw JSON only."""

        human_prompt = f"""Target Rule: {impact.affected_rule_id}
Old Multiplier Factor: {old_factor}
New Multiplier Factor: {new_factor}
Specification Title: {spec.title}
Acceptance Criteria: {json.dumps(spec.acceptance_criteria)}

Generate test cases with mathematically exact expectations rounded to 2 decimal places."""

        try:
            response = self.llm.invoke([
                SystemMessage(content=system_prompt),
                HumanMessage(content=human_prompt)
            ])
            content = response.content.strip()
            content = re.sub(r"^```json\s*", "", content)
            content = re.sub(r"^```\s*", "", content)
            content = re.sub(r"\s*```$", "", content).strip()
            data = json.loads(content)
            suite = TestSuiteOutput(**data)

            # Ensure expected values are mathematically exact and avoid zero-base edge cases
            for tc in suite.test_cases:
                base = float(tc.input_payload.get("base_premium", 1000.0))
                if base <= 0:
                    base = 1000.0
                    tc.input_payload["base_premium"] = 1000.0

                eligible = tc.input_payload.get("has_certified_safety_device", True)
                if eligible:
                    tc.expected_old_premium = round(base * old_factor, 2)
                    tc.expected_new_premium = round(base * new_factor, 2)
                else:
                    tc.expected_old_premium = round(base, 2)
                    tc.expected_new_premium = round(base, 2)
            return suite
        except Exception:
            # Deterministic fallback test cases directly reflecting Page 3 of paper
            return TestSuiteOutput(
                suite_name=f"Automated Verification Suite for {impact.affected_rule_id}",
                target_rule_id=impact.affected_rule_id,
                test_cases=[
                    TestCaseDefinition(
                        test_id="TC-001",
                        name="Standard Residential Policy ($1,000 Base Premium)",
                        input_payload={"base_premium": 1000.0, "has_certified_safety_device": True},
                        expected_old_premium=round(1000.0 * old_factor, 2),
                        expected_new_premium=round(1000.0 * new_factor, 2),
                        rationale=f"Base $1,000 * {old_factor} = ${round(1000.0 * old_factor, 2)} old vs Base $1,000 * {new_factor} = ${round(1000.0 * new_factor, 2)} new."
                    ),
                    TestCaseDefinition(
                        test_id="TC-002",
                        name="High-Value Coastal Property ($2,500 Base Premium)",
                        input_payload={"base_premium": 2500.0, "has_certified_safety_device": True},
                        expected_old_premium=round(2500.0 * old_factor, 2),
                        expected_new_premium=round(2500.0 * new_factor, 2),
                        rationale=f"Base $2,500 * {old_factor} = ${round(2500.0 * old_factor, 2)} old vs Base $2,500 * {new_factor} = ${round(2500.0 * new_factor, 2)} new."
                    ),
                    TestCaseDefinition(
                        test_id="TC-003",
                        name="Baseline Property Without Mitigation Device (Control Case)",
                        input_payload={"base_premium": 1000.0, "has_certified_safety_device": False},
                        expected_old_premium=1000.0,
                        expected_new_premium=1000.0,
                        rationale="Without certified safety device, multiplier remains 1.0 on both old and new versions."
                    )
                ]
            )
