import json
import os
from typing import Dict, Any

from langchain_openai import ChatOpenAI
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.output_parsers import PydanticOutputParser

from agents.schemas import DetectionOutput, AgentInput
from agents.prompts import DETECTION_PROMPT


class DetectionAgent:
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
            pydantic_object=DetectionOutput
        )

        self.prompt = ChatPromptTemplate.from_messages([
            ("system", DETECTION_PROMPT),
            ("user", "Events: {events}\n\n{format_instructions}")
        ])

    def run(self, input_data: AgentInput) -> DetectionOutput:
        if self.is_mock:
            return self._mock_run(input_data)

        try:
            chain = self.prompt | self.llm | self.parser

            result = chain.invoke({
                "events": json.dumps(
                    input_data.events,
                    indent=2
                ),
                "format_instructions":
                    self.parser.get_format_instructions()
            })

            return result

        except Exception as e:
            print(
                f"LLM Error in DetectionAgent: {e}, "
                "falling back to mock."
            )
            return self._mock_run(input_data)

    def _mock_run(self, input_data: AgentInput) -> DetectionOutput:
        suspicious = False
        findings = []
        related_ids = set()
        failed_logins = {}

        for event in input_data.events:
            event_type = event.get("event_type")
            evt_id = event.get("event_hash", "unknown_id")

            if (
                event_type == "login"
                and str(event.get("status", "")).lower() == "failed"
            ):
                ip = event.get("source_ip") or "unknown"

                failed_logins[ip] = failed_logins.get(ip, 0) + 1

                if failed_logins[ip] >= 3:
                    suspicious = True
                    finding = f"Repeated failed login attempts from {ip}"

                    if finding not in findings:
                        findings.append(finding)

                    related_ids.add(evt_id)

            elif event_type in ["data_exfiltration", "port_scan"]:
                suspicious = True

                finding = f"Suspicious event type: {event_type}"

                if finding not in findings:
                    findings.append(finding)

                related_ids.add(evt_id)

        return DetectionOutput(
            is_suspicious=suspicious,
            findings=findings,
            related_event_ids=sorted(related_ids)
        )
