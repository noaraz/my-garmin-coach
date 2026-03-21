"""Unit tests for gemini_client.py — Gemini API wrapper."""
from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest

from src.services.gemini_client import chat_completion


class TestChatCompletion:
    """Tests for chat_completion()."""

    def test_chat_completion_when_safety_filter_blocks_raises_runtime_error(self):
        """Test that ValueError from response.text (safety filter) is caught and converted to RuntimeError."""
        # Arrange
        mock_client = MagicMock()
        mock_chat = MagicMock()
        mock_response = MagicMock()

        # response.text raises ValueError when safety filter blocks
        type(mock_response).text = property(
            lambda self: (_ for _ in ()).throw(ValueError("Response blocked by safety filter"))
        )

        mock_chat.send_message.return_value = mock_response
        mock_client.chats.create.return_value = mock_chat

        messages = [{"role": "user", "content": "test message"}]
        system_prompt = "You are a helpful assistant"

        # Act & Assert
        with patch("src.services.gemini_client.genai.Client", return_value=mock_client):
            with patch("src.services.gemini_client.get_settings") as mock_settings:
                mock_settings.return_value.gemini_api_key = "fake-key"

                with pytest.raises(RuntimeError, match="Gemini safety filter blocked the response"):
                    chat_completion(messages, system_prompt)

    def test_chat_completion_when_api_key_missing_raises_runtime_error(self):
        """Test that missing GEMINI_API_KEY raises RuntimeError."""
        # Arrange
        messages = [{"role": "user", "content": "test"}]
        system_prompt = "test"

        # Act & Assert
        with patch("src.services.gemini_client.get_settings") as mock_settings:
            mock_settings.return_value.gemini_api_key = None

            with pytest.raises(RuntimeError, match="GEMINI_API_KEY is not configured"):
                chat_completion(messages, system_prompt)

    def test_chat_completion_when_quota_exceeded_raises_runtime_error(self):
        """Test that 429 ClientError is caught and converted to quota exceeded message."""
        # Arrange
        from google.genai import errors as genai_errors

        mock_client = MagicMock()
        mock_chat = MagicMock()
        mock_client.chats.create.return_value = mock_chat

        # Simulate 429 error
        exc = genai_errors.ClientError("Quota exceeded", response_json={})
        exc.status_code = 429
        mock_chat.send_message.side_effect = exc

        messages = [{"role": "user", "content": "test"}]
        system_prompt = "test"

        # Act & Assert
        with patch("src.services.gemini_client.genai.Client", return_value=mock_client):
            with patch("src.services.gemini_client.get_settings") as mock_settings:
                mock_settings.return_value.gemini_api_key = "fake-key"

                with pytest.raises(RuntimeError, match="Gemini API quota exceeded"):
                    chat_completion(messages, system_prompt)

    def test_chat_completion_success_returns_text(self):
        """Test successful chat completion returns response text."""
        # Arrange
        mock_client = MagicMock()
        mock_chat = MagicMock()
        mock_response = MagicMock()
        mock_response.text = "Assistant reply"

        mock_chat.send_message.return_value = mock_response
        mock_client.chats.create.return_value = mock_chat

        messages = [{"role": "user", "content": "Hello"}]
        system_prompt = "You are helpful"

        # Act
        with patch("src.services.gemini_client.genai.Client", return_value=mock_client):
            with patch("src.services.gemini_client.get_settings") as mock_settings:
                mock_settings.return_value.gemini_api_key = "fake-key"

                result = chat_completion(messages, system_prompt)

        # Assert
        assert result == "Assistant reply"
        mock_chat.send_message.assert_called_once_with("Hello")
