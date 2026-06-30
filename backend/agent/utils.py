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


def format_memory_context(memory_context: dict | None) -> str:
    """Format retailer memory into compact prompt context."""
    if not memory_context:
        return "No prior retailer memory available."

    recent = memory_context.get("recent_queries", [])[:3]
    escalations = memory_context.get("escalation_history", [])[:3]
    open_tickets = memory_context.get("open_tickets", [])[:3]

    if not recent and not escalations and not open_tickets:
        return "No prior retailer queries or escalations found for this retailer/session."

    lines = []
    if recent:
        lines.append("Recent queries:")
        for item in recent:
            lines.append(
                "- "
                f"{item.get('created_at', '')}: {item.get('query', '')[:160]} "
                f"(intent={item.get('intent', 'unknown')}, status={item.get('status', 'open')})"
            )
    if escalations:
        lines.append("Escalation history:")
        for item in escalations:
            lines.append(
                "- "
                f"{item.get('created_at', '')}: {item.get('query', '')[:140]} "
                f"-> {item.get('assigned_team', 'General Support')} "
                f"because {item.get('escalation_reason', 'not specified')}"
            )
    if open_tickets:
        lines.append("Open or assigned tickets:")
        for item in open_tickets:
            lines.append(
                "- "
                f"{item.get('query', '')[:140]} "
                f"(status={item.get('status', 'open')}, product_area={item.get('product_area', 'general')})"
            )

    return "\n".join(lines)
