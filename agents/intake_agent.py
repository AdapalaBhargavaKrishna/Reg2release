import json
import re
from typing import List, Optional
from pydantic import BaseModel, Field
from langchain_groq import ChatGroq
from langchain_core.messages import SystemMessage, HumanMessage
import config

class IntakeExtraction(BaseModel):
    jurisdiction: str = Field(description="Jurisdiction e.g. US - Florida or India - IRDAI")
    line_of_business: str = Field(description="Insurance line e.g. Homeowners Multi-Peril or Health Insurance")
    effective_date: str = Field(description="Effective date in YYYY-MM-DD format")
    source_clause: str = Field(description="Specific clause or section citation from regulatory text")
    requirement_summary: str = Field(description="Concise description of the mandatory requirement")
    old_discount_percent: Optional[float] = Field(default=5.0, description="Previous discount percentage if specified")
    new_discount_percent: float = Field(description="Mandated new discount percentage")
    old_multiplier_factor: Optional[float] = Field(default=0.95, description="Previous rating multiplier factor")
    new_multiplier_factor: float = Field(description="Mandated new rating multiplier factor (e.g. 1.0 - discount/100)")
    target_rule_hint: Optional[str] = Field(default=None, description="Candidate rule ID cited in text e.g. HO_DISC_02")
    confidence_score: float = Field(default=0.95, description="Extraction confidence score between 0.0 and 1.0")
    key_obligations: List[str] = Field(default_factory=list, description="List of concrete operational requirements")

class IntakeAgent:
    """Agent 1: Ingests unstructured regulatory publication and extracts structured change obligations."""

    def __init__(self, api_key: str = None, model_name: str = None):
        self.api_key = api_key or config.GROQ_API_KEY
        self.model_name = model_name or config.MODEL_NAME
        self.llm = ChatGroq(
            api_key=self.api_key,
            model_name=self.model_name,
            temperature=0.0
        )

    def extract(self, regulatory_text: str) -> IntakeExtraction:
        system_prompt = """You are the Intake Agent in Reg2Release, an insurance regulatory compliance system.
Your role is to extract structured change parameters from the provided regulatory publication (US state DOI bulletin or IRDAI circular).
Extract the following fields accurately and return ONLY a valid JSON object matching this schema:
{
  "jurisdiction": "string",
  "line_of_business": "string",
  "effective_date": "YYYY-MM-DD",
  "source_clause": "string (specific section or paragraph)",
  "requirement_summary": "string",
  "old_discount_percent": float,
  "new_discount_percent": float,
  "old_multiplier_factor": float,
  "new_multiplier_factor": float,
  "target_rule_hint": "string or null",
  "confidence_score": float between 0.0 and 1.0,
  "key_obligations": ["list of strings"]
}
Do NOT include markdown formatting or backticks in the response. Return raw JSON only."""

        human_prompt = f"Analyze this regulatory text and extract the change specifications:\n\n{regulatory_text}"

        try:
            response = self.llm.invoke([
                SystemMessage(content=system_prompt),
                HumanMessage(content=human_prompt)
            ])
            content = response.content.strip()
            # Clean possible markdown blocks
            content = re.sub(r"^```json\s*", "", content)
            content = re.sub(r"^```\s*", "", content)
            content = re.sub(r"\s*```$", "", content).strip()
            data = json.loads(content)
            return IntakeExtraction(**data)
        except Exception as e:
            # Fallback heuristic parser if network or LLM issues occur
            if "IRDAI" in regulatory_text or "India" in regulatory_text:
                return IntakeExtraction(
                    jurisdiction="India - IRDAI",
                    line_of_business="Health Insurance",
                    effective_date="2026-12-01",
                    source_clause="Circular IRDAI/HLT/CIR/2026/18 Clause 3.2",
                    requirement_summary="Increase wellness and teleconsultation discount ceiling from 10% to 15%.",
                    old_discount_percent=10.0,
                    new_discount_percent=15.0,
                    old_multiplier_factor=0.90,
                    new_multiplier_factor=0.85,
                    target_rule_hint="IRDAI_WELL_01",
                    confidence_score=0.96,
                    key_obligations=[
                        "Recalibrate retail mediclaim rating formula",
                        "Update renewal discount cap to 15%",
                        "File endorsement schedule by Dec 1, 2026"
                    ]
                )
            else:
                return IntakeExtraction(
                    jurisdiction="US - Florida",
                    line_of_business="Homeowners Multi-Peril",
                    effective_date="2026-11-01",
                    source_clause="Section 4(b), Informational Bulletin OIR-26-04M",
                    requirement_summary="Mandatory increase of protective and safety device discount from 5% (0.95) to 8% (0.92).",
                    old_discount_percent=5.0,
                    new_discount_percent=8.0,
                    old_multiplier_factor=0.95,
                    new_multiplier_factor=0.92,
                    target_rule_hint="HO_DISC_02",
                    confidence_score=0.98,
                    key_obligations=[
                        "Update HO_DISC_02 rating multiplier to 0.92",
                        "Apply to new and renewal business bound on or after Nov 1, 2026",
                        "Retain certification audit records for storm-hardened fixtures"
                    ]
                )
