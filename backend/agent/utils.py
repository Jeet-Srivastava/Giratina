"""
Shared utilities for agent nodes.
"""

import json
import re


def parse_llm_json(content: str) -> dict:
    """
    Robustly parse JSON from LLM output.
    Handles:
    - Markdown code blocks (```json ... ```)
    - Control characters in strings
    - Unescaped newlines inside JSON string values
    - Leading/trailing text around JSON
    """
    text = content.strip()

    # Remove markdown code blocks
    if "```" in text:
        parts = text.split("```")
        for part in parts[1:]:
            candidate = part.strip()
            if candidate.startswith("json"):
                candidate = candidate[4:].strip()
            if candidate.startswith("{"):
                text = candidate
                break

    # Try direct parse first
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        pass

    # Remove control characters (except \n \r \t)
    cleaned = re.sub(r'[\x00-\x08\x0b\x0c\x0e-\x1f\x7f]', '', text)
    try:
        return json.loads(cleaned)
    except json.JSONDecodeError:
        pass

    # Fix unescaped newlines inside JSON string values
    # Strategy: replace literal newlines between quotes with \\n
    def fix_newlines_in_strings(s):
        """Replace literal newlines inside JSON string values with \\n."""
        result = []
        in_string = False
        escape_next = False
        for ch in s:
            if escape_next:
                result.append(ch)
                escape_next = False
                continue
            if ch == '\\':
                result.append(ch)
                escape_next = True
                continue
            if ch == '"':
                in_string = not in_string
                result.append(ch)
                continue
            if in_string and ch == '\n':
                result.append('\\n')
                continue
            if in_string and ch == '\r':
                result.append('\\r')
                continue
            if in_string and ch == '\t':
                result.append('\\t')
                continue
            result.append(ch)
        return ''.join(result)

    fixed = fix_newlines_in_strings(cleaned)
    try:
        return json.loads(fixed)
    except json.JSONDecodeError:
        pass

    # Try to extract JSON object from surrounding text
    match = re.search(r'\{.*\}', fixed, re.DOTALL)
    if match:
        try:
            return json.loads(match.group())
        except json.JSONDecodeError:
            # Try fixing newlines on extracted portion too
            extracted = fix_newlines_in_strings(match.group())
            try:
                return json.loads(extracted)
            except json.JSONDecodeError:
                pass

    raise ValueError(f"Could not parse JSON from LLM output: {text[:200]}")
