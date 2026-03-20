"""Thin wrapper over google-genai for Plan Coach chat."""
from __future__ import annotations

from google import genai
from google.genai import errors as genai_errors
from google.genai import types

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
        RuntimeError: If GEMINI_API_KEY is not configured or the API returns an error.
    """
    settings = get_settings()
    if not settings.gemini_api_key:
        raise RuntimeError("GEMINI_API_KEY is not configured")

    client = genai.Client(api_key=settings.gemini_api_key)

    # All messages except the final user turn become history
    history = [
        types.Content(
            role="model" if m["role"] == "assistant" else "user",
            parts=[types.Part(text=m["content"])],
        )
        for m in messages[:-1]
    ]

    chat = client.chats.create(
        model="gemini-2.0-flash-lite",
        history=history,
        config=types.GenerateContentConfig(system_instruction=system_prompt),
    )
    last_content = messages[-1]["content"] if messages else ""
    try:
        response = chat.send_message(last_content)
    except genai_errors.ClientError as exc:
        if exc.status_code == 429:
            raise RuntimeError(
                "Gemini API quota exceeded. Please try again later or upgrade your plan."
            ) from exc
        raise RuntimeError(f"Gemini API error ({exc.status_code})") from exc
    return response.text
