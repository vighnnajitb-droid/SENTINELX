import json
from typing import Dict, Any, List
from langchain_openai import ChatOpenAI
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.output_parsers import PydanticOutputParser
from agents.schemas import InvestigationOutput, AgentInput
from agents.prompts import INVESTIGATION_PROMPT
import os

class InvestigationAgent:
    def __init__(self):
        self.api_key = os.getenv("OPENAI_API_KEY", "dummy")
        self.is_mock = self.api_key == "dummy" or self.api_key.startswith("your_")
        if not self.is_mock:
            self.llm = ChatOpenAI(temperature=0, model_name="gpt-3.5-turbo")
        self.parser = PydanticOutputParser(pydantic_object=InvestigationOutput)
        self.prompt = ChatPromptTemplate.from_messages([
            ("system", INVESTIGATION_PROMPT),
            ("user", "Detection Findings: {findings}\nEvents: {events}\n\n{format_instructions}")
        ])

    def run(self, input_data: AgentInput) -> InvestigationOutput:
        if self.is_mock:
            return self._mock_run(input_data)
        
        try:
            chain = self.prompt | self.llm | self.parser
            findings_str = json.dumps(input_data.context.get("detection_findings", []), indent=2)
            events_str = json.dumps(input_data.events, indent=2)
            result = chain.invoke({
                "findings": findings_str,
                "events": events_str,
                "format_instructions": self.parser.get_format_instructions()
            })
            return result
        except Exception as e:
            print(f"LLM Error in InvestigationAgent: {e}, falling back to mock.")
            return self._mock_run(input_data)

    def _mock_run(self, input_data: AgentInput) -> InvestigationOutput:
        events = input_data.events
        entities = set()
        timeline = []
        
        for e in sorted(events, key=lambda x: x.get("timestamp", "")):
            ts = e.get("timestamp", "")
            desc = f"{e.get('event_type')} from {e.get('source_ip')} to {e.get('destination_ip')} ({e.get('status')})"
            timeline.append({"timestamp": ts, "description": desc})
            if e.get("source_ip"): entities.add(e.get("source_ip"))
            if e.get("destination_ip"): entities.add(e.get("destination_ip"))
            if e.get("user"): entities.add(e.get("user"))
            
        summary = "Multiple related events detected." if len(events) > 1 else "Single event analyzed."
        
        return InvestigationOutput(
            correlation_summary=summary,
            timeline=timeline,
            entities_involved=list(entities)
        )
