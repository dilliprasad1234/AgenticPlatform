"""Deterministic offline LLM provider used for framework smoke tests."""

from __future__ import annotations

import json
from typing import Any

from src.llm.base import LLMProvider
from src.utils.slug import slugify


class MockLLMProvider(LLMProvider):
    """Provide deterministic placeholder responses without external APIs."""

    def generate_json(self, system_prompt: str, user_prompt: str) -> dict[str, Any]:
        """Return a schema-compatible response based on the generation prompt."""
        prompt = system_prompt.lower()

        if "agent specification" in prompt:
            name = "Generated Analysis Agent"
            return {
                "id": slugify(name),
                "agent": {
                    "name": name,
                    "details": "Generated enterprise analysis agent.",
                    "practice_area": "Software Engineering",
                    "good_at": "Analysis and structured reasoning",
                },
                "behaviour": {
                    "role": "Software Analysis Specialist",
                    "goal": user_prompt,
                    "back_story": "An experienced enterprise software analyst.",
                    "description": user_prompt,
                    "expected_output": "Structured analysis with evidence.",
                },
                "llm_configuration": {
                    "provider": "mock",
                    "model": "mock",
                    "temperature": 0,
                    "top_p": 1,
                    "max_iteration": 10,
                    "max_rpm": 60,
                    "max_execution_time": 120,
                },
                "tools": [],
                "agent_skills": ["analysis"],
                "kb": [],
                "guardrails": [],
                "prompt": [],
                "input_file": [],
                "input_data": [],
                "output_data": [],
                "input_format": ["text"],
                "output_format": ["text"],
            }

        if "workflow specification" in prompt:
            import re

            match = re.search(
                r'Available Agent IDs:\s*\[\s*[\'\"]?([A-Za-z0-9_-]+)',
                user_prompt,
            )
            selected_agent = (
                match.group(1)
                if match
                else "requirement_analyzer_v1"
            )
            return {
                "id": "generated_workflow",
                "name": "Generated Workflow",
                "description": user_prompt,
                "practice_area": "General",
                "good_at": "Workflow orchestration",
                "agents": [selected_agent],
            }

        if "guardrail specification" in prompt:
            return {
                "id": "generated_guardrail",
                "name": "Generated Guardrail",
                "description": user_prompt,
                "type": "input",
                "action": "block",
                "implementation_file": "generated_guardrail.py",
                "configuration": {},
                "enabled": True,
            }

        if "tool specification" in prompt:
            return {
                "id": "generated_tool",
                "name": "Generated Tool",
                "description": user_prompt,
                "purpose": "Offline smoke-test tool.",
                "inputs": [],
                "output_description": "A deterministic status response.",
                "implementation_file": "generated_tool.py",
            }

        if "behavioral test" in prompt:
            return {
                "tests": [
                    {
                        "name": "safe_value",
                        "value": "safe content",
                        "expected_pass": True,
                    }
                ]
            }

        return {}

    def generate(self, system_prompt: str, user_prompt: str) -> str:
        """Return deterministic placeholder Python for code-generation prompts."""
        prompt = system_prompt.lower()

        if "guardrail implementation" in prompt:
            return '"""Generated offline guardrail."""\n\nfrom guardrails.base import BaseGuardrail\n\n\nclass GeneratedGuardrailGuardrail(BaseGuardrail):\n    """Allow all values in the offline smoke-test implementation."""\n\n    def validate(self, value, context=None):\n        """Return the value unchanged."""\n        return True, value\n'

        if "tool implementation" in prompt:
            return '"""Generated offline tool."""\n\nfrom tools.base import BaseTool\n\n\nclass GeneratedTool(BaseTool):\n    """Return a deterministic offline smoke-test result."""\n\n    def execute(self):\n        """Return a deterministic status result."""\n        return {"status": "ok"}\n'

        return json.dumps({"status": "ok", "input": user_prompt})
