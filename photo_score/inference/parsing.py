"""Shared JSON extraction from model responses."""

import json
import re


def extract_json_from_response(content: str) -> dict:
    """Extract JSON object from a model response string.

    Handles:
    - Markdown code blocks (```json ... ```)
    - Balanced brace extraction
    - Trailing text after JSON

    Raises:
        ValueError: If no valid JSON found.
    """
    # First try markdown code block
    code_block_match = re.search(r"```(?:json)?\s*(\{.*?\})\s*```", content, re.DOTALL)
    if code_block_match:
        try:
            return json.loads(code_block_match.group(1))
        except json.JSONDecodeError:
            pass

    # Find first { and match balanced braces
    start_idx = content.find("{")
    if start_idx == -1:
        raise ValueError(f"No JSON found in response: {content}")

    depth = 0
    end_idx = start_idx
    for i, char in enumerate(content[start_idx:], start_idx):
        if char == "{":
            depth += 1
        elif char == "}":
            depth -= 1
            if depth == 0:
                end_idx = i + 1
                break

    json_str = content[start_idx:end_idx]
    try:
        return json.loads(json_str)
    except json.JSONDecodeError as e:
        raise ValueError(f"Invalid JSON in response: {e}\nContent: {content}")
