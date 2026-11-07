import json
import hmac
from typing import Dict, Any, List
from langchain_openai import ChatOpenAI
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.output_parsers import PydanticOutputParser
from agents.schemas import AuditOutput, AgentInput
from agents.prompts import AUDIT_PROMPT
from utils.parser import generate_event_hash
import os


class AuditAgent:
    def __init__(self):
        self.api_key = os.getenv("OPENAI_API_KEY", "dummy")
        self.is_mock = (
            self.api_key == "dummy"
            or self.api_key.startswith("your_")
            or not self.api_key.strip()
        )

        if not self.is_mock:
            self.llm = ChatOpenAI(
                temperature=0,
                model="gpt-3.5-turbo"
            )

        self.parser = PydanticOutputParser(
            pydantic_object=AuditOutput
        )

        self.prompt = ChatPromptTemplate.from_messages([
            ("system", AUDIT_PROMPT),
            (
                "user",
                "Events: {events}\nContext: {context}\n\n{format_instructions}"
            )
        ])

    def _verify_hashes(self, events: List[Dict[str, Any]]) -> bool:
        """Verify every stored event hash against its original payload."""
        if not events:
            return False

        for event in events:
            if not isinstance(event, dict):
                return False

            stored_hash = event.get("event_hash")
            if not isinstance(stored_hash, str) or not stored_hash:
                return False

            original_payload = {
                "source_ip": event.get("source_ip") or "",
                "destination_ip": event.get("destination_ip") or "",
                "event_type": event.get("event_type") or "unknown",
                "timestamp": event.get("timestamp"),
                "raw_data": event.get("raw_data") or {}
            }

            try:
                calculated_hash = generate_event_hash(original_payload)
            except (TypeError, ValueError):
                return False

            if not hmac.compare_digest(stored_hash, calculated_hash):
                return False

        return True

    def _apply_integrity_result(
        self,
        result: AuditOutput,
        trail_valid: bool
    ) -> AuditOutput:
        result.audit_trail_valid = trail_valid

        if not trail_valid:
            result.evidence_verified = False
            if "Event hashes are invalid, missing, or tampered." not in result.discrepancies:
                result.discrepancies.append(
                    "Event hashes are invalid, missing, or tampered."
                )

        return result

    def run(self, input_data: AgentInput) -> AuditOutput:
        events = input_data.events
        trail_valid = self._verify_hashes(events)

        if self.is_mock:
            result = self._mock_run(input_data)
            return self._apply_integrity_result(result, trail_valid)

        try:
            chain = self.prompt | self.llm | self.parser

            result = chain.invoke({
                "events": json.dumps(events, indent=2),
                "context": json.dumps(input_data.context, indent=2),
                "format_instructions": self.parser.get_format_instructions()
            })

            return self._apply_integrity_result(result, trail_valid)

        except Exception as e:
            print(f"LLM Error in AuditAgent: {e}, falling back to mock.")
            result = self._mock_run(input_data)
            return self._apply_integrity_result(result, trail_valid)

    def _mock_run(self, input_data: AgentInput) -> AuditOutput:
        findings = input_data.context.get("detection_findings", [])

        evidence_verified = bool(input_data.events)
        discrepancies = []

        if not input_data.events:
            evidence_verified = False
            discrepancies.append("No events provided for audit.")

        return AuditOutput(
            evidence_verified=evidence_verified,
            discrepancies=discrepancies,
            audit_trail_valid=False
        )

