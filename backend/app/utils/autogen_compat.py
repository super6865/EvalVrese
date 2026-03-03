"""
Compatibility patches for third-party libraries.

Currently patches AutoGen to tolerate OpenAI-compatible responses that omit
the `usage` field (i.e. `usage: null`), which otherwise raises:
AttributeError: 'NoneType' object has no attribute 'prompt_tokens'
"""

from __future__ import annotations

from typing import Any, Dict, Tuple


def _extract_usage_numbers(usage: Any) -> Tuple[int, int, int]:
    """Return (prompt_tokens, completion_tokens, total_tokens) safely."""
    if usage is None:
        return 0, 0, 0

    # Some OpenAI-compatible gateways return a dict usage payload
    if isinstance(usage, dict):
        prompt = int(usage.get("prompt_tokens") or usage.get("input_tokens") or 0)
        completion = int(usage.get("completion_tokens") or usage.get("output_tokens") or 0)
        total = usage.get("total_tokens")
        total_i = int(total) if total is not None else int(prompt + completion)
        return prompt, completion, total_i

    # OpenAI SDK returns a Usage object with attributes
    prompt = int(getattr(usage, "prompt_tokens", 0) or 0)
    completion = int(getattr(usage, "completion_tokens", 0) or 0)
    total = getattr(usage, "total_tokens", None)
    total_i = int(total) if total is not None else int(prompt + completion)
    return prompt, completion, total_i


def patch_autogen_usage_extraction() -> None:
    """
    Patch AutoGen's OpenAIClient.get_usage to handle missing `response.usage`.

    This avoids crashes for OpenAI-compatible providers that return `usage: null`.
    """
    try:
        from autogen.oai import client as autogen_client  # type: ignore
    except Exception:
        return

    OpenAIClient = getattr(autogen_client, "OpenAIClient", None)
    if OpenAIClient is None:
        return

    if getattr(OpenAIClient, "_evalverse_usage_patch_applied", False):
        return

    def _patched_get_usage(response: Any) -> Dict[str, Any]:
        usage = getattr(response, "usage", None)
        prompt, completion, total = _extract_usage_numbers(usage)
        return {
            "prompt_tokens": prompt,
            "completion_tokens": completion,
            "total_tokens": total,
            "cost": getattr(response, "cost", 0) or 0,
            "model": getattr(response, "model", None),
        }

    # AutoGen defines get_usage as a @staticmethod; preserve that contract.
    OpenAIClient.get_usage = staticmethod(_patched_get_usage)  # type: ignore[attr-defined]
    OpenAIClient._evalverse_usage_patch_applied = True  # type: ignore[attr-defined]

