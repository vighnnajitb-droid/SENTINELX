import json
import os
from typing import Dict, Any

from langchain_openai import ChatOpenAI
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.output_parsers import PydanticOutputParser

from agents.schemas import ResponseOutput, AgentInput
from agents.prompts import RESPONSE_PROMPT


class ResponseAgent:
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
            pydantic_object=ResponseOutput
        )

        self.prompt = ChatPromptTemplate.from_messages([
            ("system", RESPONSE_PROMPT),
            ("user", "Context: {context}\n\n{format_instructions}")
        ])

    def run(self, input_data: AgentInput) -> ResponseOutput:
        if self.is_mock:
            result = self._mock_run(input_data)
        else:
            try:
                chain = self.prompt | self.llm | self.parser

                result = chain.invoke({
                    "context": json.dumps(
                        input_data.context,
                        indent=2
                    ),
                    "format_instructions":
                        self.parser.get_format_instructions()
                })

            except Exception as e:
                print(
                    f"LLM Error in ResponseAgent: {e}, "
                    "falling back to mock."
                )
                result = self._mock_run(input_data)

        # Proposed automated actions always require human approval.
        if result.automated_actions_proposed:
            result.requires_human_approval = True

        return result

    def _mock_run(self, input_data: AgentInput) -> ResponseOutput:
        severity = (
            input_data.context
            .get("risk_assessment", {})
            .get("severity", "low")
        )

        entities = input_data.context.get(
            "entities_involved", []
        )

        recommendations = ["Continue monitoring."]
        requires_approval = False
        automated = []

        if severity in ["high", "critical"]:
            recommendations.extend([
                "Review suspicious IP addresses.",
                "Review credentials for potentially affected users."
            ])
            requires_approval = True

            automated = [
                f"Review blocking recommendation for {ip}"
                for ip in entities
                if isinstance(ip, str) and "." in ip
            ]

        elif severity == "medium":
            recommendations.append(
                "Increase logging for involved entities."
            )

        return ResponseOutput(
            recommendations=recommendations,
            requires_human_approval=(
                requires_approval or bool(automated)
            ),
            automated_actions_proposed=automated
        )
