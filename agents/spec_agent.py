import json
import re
from typing import List, Dict
from pydantic import BaseModel, Field
from langchain_groq import ChatGroq
from langchain_core.messages import SystemMessage, HumanMessage
import config
from agents.intake_agent import IntakeExtraction
from agents.impact_agent import ImpactEvaluation

class UserStory(BaseModel):
    story_id: str
    as_a: str
    i_want_to: str
    so_that: str

class SpecificationPackage(BaseModel):
    requirement_id: str = Field(default="REQ-REG-2026-001", description="Unique requirement ID")
    title: str = Field(description="Requirement title")
    business_rationale: str = Field(description="Business and regulatory context")
    target_rule_id: str = Field(description="Carrier rule ID being modified")
    source_clause_link: str = Field(description="Direct citation to regulatory source clause")
    user_stories: List[UserStory] = Field(description="Agile user stories")
    acceptance_criteria: List[str] = Field(description="BDD / Gherkin acceptance criteria")

class SpecAgent:
    """Agent 3: Drafts formal software requirements, user stories, and acceptance criteria linked to source clauses."""

    def __init__(self, api_key: str = None, model_name: str = None):
        self.api_key = api_key or config.GROQ_API_KEY
        self.model_name = model_name or config.MODEL_NAME
        self.llm = ChatGroq(
            api_key=self.api_key,
            model_name=self.model_name,
            temperature=0.0
        )

    def draft_specification(self, intake: IntakeExtraction, impact: ImpactEvaluation) -> SpecificationPackage:
        system_prompt = """You are the Spec Agent in Reg2Release.
Your task is to draft formal software requirements, Agile user stories, and Gherkin-style acceptance criteria linked to the regulatory clause.
Output ONLY a valid JSON object matching this schema:
{
  "requirement_id": "REQ-REG-2026-001",
  "title": "string",
  "business_rationale": "string",
  "target_rule_id": "string",
  "source_clause_link": "string",
  "user_stories": [
    {
      "story_id": "US-01",
      "as_a": "string",
      "i_want_to": "string",
      "so_that": "string"
    }
  ],
  "acceptance_criteria": [
    "Given ... When ... Then ..."
  ]
}
Do NOT include markdown formatting or backticks in the response. Return raw JSON only."""

        human_prompt = f"""Regulatory Intake:
- Source Clause: {intake.source_clause}
- Requirement: {intake.requirement_summary}
- Effective Date: {intake.effective_date}

Impact Assessment:
- Affected Rule: {impact.affected_rule_id} ({impact.affected_rule_name})
- Parameter Changes: {json.dumps(impact.parameter_changes)}
- Evidence Citation: {impact.evidence_citation}

Draft formal engineering specifications for the rule change."""

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
            return SpecificationPackage(**data)
        except Exception:
            # Fallback spec package
            return SpecificationPackage(
                requirement_id="REQ-REG-2026-08",
                title=f"Adjust Rating Multiplier for {impact.affected_rule_name}",
                business_rationale=f"Mandatory compliance with {intake.source_clause}. Failure to comply by {intake.effective_date} risks regulatory fines and rate filing rejections.",
                target_rule_id=impact.affected_rule_id,
                source_clause_link=intake.source_clause,
                user_stories=[
                    UserStory(
                        story_id="US-101",
                        as_a="Rating Engine",
                        i_want_to=f"apply updated factor {impact.parameter_changes.get('multiplier_factor', 0.92)} to qualifying policies",
                        so_that=f"policyholders receive the statutory {impact.parameter_changes.get('discount_percent', 8.0)}% credit"
                    ),
                    UserStory(
                        story_id="US-102",
                        as_a="Compliance Officer",
                        i_want_to="verify automated test coverage before production release",
                        so_that="auditability back to source clause is guaranteed"
                    )
                ],
                acceptance_criteria=[
                    f"Scenario 1: Given a base premium of $1,000 and certified protection, When rule {impact.affected_rule_id} calculates premium, Then the resulting premium must equal exactly ${round(1000 * impact.parameter_changes.get('multiplier_factor', 0.92), 2)}.",
                    f"Scenario 2: Given an existing policy bound prior to {intake.effective_date}, When evaluated under legacy rules, Then the baseline discount remains at {intake.old_discount_percent}%."
                ]
            )
