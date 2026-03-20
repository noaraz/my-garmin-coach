"""Thin wrapper over google-generativeai for Plan Coach chat."""
from __future__ import annotations

import google.generativeai as genai  # noqa: F401 — migrate to google-genai>=1.0 on next image rebuild

from src.core.config import get_settings


def chat_completion(
    messages: list[dict[str, str]],
    system_prompt: str,
) -> str:
    """Send a list of {role, content} messages to Gemini Flash and return the reply text.

    Args:
        messages: Conversation history in [{role, content}] format.
                  Roles must be "user" or "assistant" (mapped to "model" for Gemini).
                  Must have at least one message. The last message is the current user turn.
        system_prompt: Injected as system instruction on the model.

    Returns:
        The assistant reply text.

    Raises:
        RuntimeError: If GEMINI_API_KEY is not configured.
    """
    settings = get_settings()
    if not settings.gemini_api_key:
        raise RuntimeError("GEMINI_API_KEY is not configured")

    genai.configure(api_key=settings.gemini_api_key)
    model = genai.GenerativeModel(
        model_name="gemini-1.5-flash",
        system_instruction=system_prompt,
    )

    # All messages except the final user turn become history
    gemini_history = [
        {
            "role": "model" if m["role"] == "assistant" else "user",
            "parts": [m["content"]],
        }
        for m in messages[:-1]
    ]

    chat = model.start_chat(history=gemini_history)
    last_content = messages[-1]["content"] if messages else ""
    response = chat.send_message(last_content)
    return response.text
