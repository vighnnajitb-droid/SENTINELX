import json
import os

from langchain_openai import ChatOpenAI
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.output_parsers import PydanticOutputParser

from agents.schemas import RiskAssessmentOutput, AgentInput
from agents.prompts import RISK_ASSESSMENT_PROMPT


class RiskAssessmentAgent:
    def __init__(self):
        self.api_key = os.getenv("OPENAI_API_KEY", "dummy").strip()

        self.is_mock = (
            not self.api_key
            or self.api_key == "dummy"
            or self.api_key.startswith("your_")
        )

        if not self.is_mock:
            self.llm = ChatOpenAI(
                temperature=0,
                model="gpt-3.5-turbo"
            )

        self.parser = PydanticOutputParser(
            pydantic_object=RiskAssessmentOutput
        )

        self.prompt = ChatPromptTemplate.from_messages([
            ("system", RISK_ASSESSMENT_PROMPT),
            (
                "user",
                "Findings: {findings}\n"
                "Threat Intel: {intel}\n\n{format_instructions}"
            )
        ])

    def run(self, input_data: AgentInput) -> RiskAssessmentOutput:
        if self.is_mock:
            return self._mock_run(input_data)

        try:
            chain = self.prompt | self.llm | self.parser

            result = chain.invoke({
                "findings": json.dumps(
                    input_data.context.get("detection_findings", []),
                    indent=2
                ),
                "intel": json.dumps(
                    input_data.context.get("threat_intel", {}),
                    indent=2
                ),
                "format_instructions":
                    self.parser.get_format_instructions()
            })

            return result

        except Exception as e:
            print(
                f"LLM Error in RiskAssessmentAgent: {e}, "
                "falling back to mock."
            )
            return self._mock_run(input_data)

    def _mock_run(self, input_data: AgentInput) -> RiskAssessmentOutput:
        findings = input_data.context.get("detection_findings", [])
        intel = input_data.context.get("threat_intel", {})

        severity = "low"
        confidence = 0.5
        justification = "No significant findings in the supplied events."

        if findings:
            severity = "medium"
            confidence = 0.7
            justification = (
                "Suspicious activity was detected. "
                "This is a preliminary assessment."
            )

        if intel.get("known_threats_found"):
            severity = "high"
            confidence = 0.85
            justification = (
                "A synthetic threat-intelligence match was reported. "
                "Independent verification is required."
            )

        if any(
            isinstance(finding, str)
            and "exfiltration" in finding.lower()
            for finding in findings
        ):
            severity = "critical"
            confidence = 0.9
            justification = (
                "Possible data exfiltration was indicated by the supplied "
                "events. Human investigation is required."
            )

        return RiskAssessmentOutput(
            severity=severity,
            confidence_score=confidence,
            justification=justification
        )
