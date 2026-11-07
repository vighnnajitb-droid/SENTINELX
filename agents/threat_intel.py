import json
import os

from langchain_openai import ChatOpenAI
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.output_parsers import PydanticOutputParser

from agents.schemas import ThreatIntelOutput, AgentInput
from agents.prompts import THREAT_INTEL_PROMPT


class ThreatIntelAgent:
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
            pydantic_object=ThreatIntelOutput
        )

        self.prompt = ChatPromptTemplate.from_messages([
            ("system", THREAT_INTEL_PROMPT),
            ("user", "Entities: {entities}\n\n{format_instructions}")
        ])

    def run(self, input_data: AgentInput) -> ThreatIntelOutput:
        if self.is_mock:
            return self._mock_run(input_data)

        try:
            chain = self.prompt | self.llm | self.parser

            result = chain.invoke({
                "entities": json.dumps(
                    input_data.context.get("entities_involved", []),
                    indent=2
                ),
                "format_instructions":
                    self.parser.get_format_instructions()
            })

            return result

        except Exception as e:
            print(
                f"LLM Error in ThreatIntelAgent: {e}, "
                "falling back to mock."
            )
            return self._mock_run(input_data)

    def _mock_run(self, input_data: AgentInput) -> ThreatIntelOutput:
        entities = input_data.context.get("entities_involved", [])
        enriched = []
        known_threat = False

        # Synthetic indicators for demonstration only.
        simulated_indicators = {
            "203.0.113.45",
            "198.51.100.22"
        }

        for entity in entities:
            if entity in simulated_indicators:
                enriched.append({
                    "indicator": entity,
                    "reputation": "simulated_malicious",
                    "notes": (
                        "Synthetic demo indicator; "
                        "not a verified real-world threat."
                    )
                })
                known_threat = True
            else:
                enriched.append({
                    "indicator": entity,
                    "reputation": "unknown",
                    "notes": (
                        "No verified threat-intelligence lookup "
                        "was performed in mock mode."
                    )
                })

        return ThreatIntelOutput(
            enriched_indicators=enriched,
            known_threats_found=known_threat
        )
