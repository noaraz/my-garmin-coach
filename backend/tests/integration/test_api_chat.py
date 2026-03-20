"""Integration tests for Plan Coach chat endpoints (Phase 4)."""
from __future__ import annotations

from unittest.mock import patch

from httpx import AsyncClient
from sqlmodel import select
from sqlmodel.ext.asyncio.session import AsyncSession

from src.db.models import PlanCoachMessage


class TestGetChatHistory:
    async def test_get_history_empty_for_new_user(self, client: AsyncClient) -> None:
        resp = await client.get("/api/v1/plans/chat/history")
        assert resp.status_code == 200
        assert resp.json() == []

    async def test_get_history_returns_messages_in_order(
        self, client: AsyncClient, session: AsyncSession
    ) -> None:
        from datetime import datetime, timezone, timedelta
        now = datetime.now(timezone.utc).replace(tzinfo=None)
        for i, role in enumerate(["user", "assistant", "user"]):
            session.add(PlanCoachMessage(
                user_id=1,
                role=role,
                content=f"message {i}",
                created_at=now + timedelta(seconds=i),
            ))
        await session.commit()

        resp = await client.get("/api/v1/plans/chat/history")
        assert resp.status_code == 200
        data = resp.json()
        assert len(data) == 3
        assert data[0]["role"] == "user"
        assert data[1]["role"] == "assistant"
        assert data[2]["role"] == "user"
        assert data[0]["content"] == "message 0"


class TestPostChatMessage:
    async def test_post_message_rejects_empty_content(self, client: AsyncClient) -> None:
        resp = await client.post("/api/v1/plans/chat/message", json={"content": "  "})
        assert resp.status_code == 422

    async def test_post_message_persists_user_and_assistant_messages(
        self, client: AsyncClient, session: AsyncSession
    ) -> None:
        with patch(
            "src.services.plan_coach_service.chat_completion",
            return_value="Here is your plan: great training!",
        ):
            resp = await client.post(
                "/api/v1/plans/chat/message",
                json={"content": "Build me a 5K plan"},
            )

        assert resp.status_code == 200
        data = resp.json()
        assert data["role"] == "assistant"
        assert data["content"] == "Here is your plan: great training!"
        assert "id" in data
        assert "created_at" in data

        # Both messages should be persisted in DB
        result = await session.exec(
            select(PlanCoachMessage).where(PlanCoachMessage.user_id == 1)
        )
        messages = list(result.all())
        assert len(messages) == 2
        assert messages[0].role == "user"
        assert messages[0].content == "Build me a 5K plan"
        assert messages[1].role == "assistant"

    async def test_post_message_returns_503_when_gemini_not_configured(
        self, client: AsyncClient
    ) -> None:
        with patch(
            "src.services.plan_coach_service.chat_completion",
            side_effect=RuntimeError("GEMINI_API_KEY is not configured"),
        ):
            resp = await client.post(
                "/api/v1/plans/chat/message",
                json={"content": "Hello"},
            )
        assert resp.status_code == 503

    async def test_post_message_queries_recent_garmin_activities(
        self, client: AsyncClient, session: AsyncSession
    ) -> None:
        from datetime import datetime, timezone
        from src.db.models import GarminActivity

        # Seed a recent activity
        today = datetime.now(timezone.utc).date()
        session.add(GarminActivity(
            user_id=1,
            garmin_activity_id="act_test_001",
            activity_type="running",
            name="Test Run",
            start_time=datetime.now(timezone.utc).replace(tzinfo=None),
            date=today,
            duration_sec=3600.0,
            distance_m=10000.0,
        ))
        await session.commit()

        captured_messages: list = []

        def _capture(messages: list, system_prompt: str) -> str:
            captured_messages.extend(messages)
            # Verify system prompt includes the activity
            assert "Test Run" in system_prompt or "running" in system_prompt
            return "Great plan!"

        with patch("src.services.plan_coach_service.chat_completion", side_effect=_capture):
            resp = await client.post(
                "/api/v1/plans/chat/message",
                json={"content": "Build me a plan"},
            )
        assert resp.status_code == 200

    async def test_post_message_truncates_history_to_40_messages(
        self, client: AsyncClient, session: AsyncSession
    ) -> None:
        from datetime import datetime, timezone, timedelta

        # Seed 50 prior messages
        now = datetime.now(timezone.utc).replace(tzinfo=None)
        for i in range(50):
            role = "user" if i % 2 == 0 else "assistant"
            session.add(PlanCoachMessage(
                user_id=1,
                role=role,
                content=f"old message {i}",
                created_at=now + timedelta(seconds=i),
            ))
        await session.commit()

        sent_count: list[int] = []

        def _capture_count(messages: list, system_prompt: str) -> str:
            sent_count.append(len(messages))
            return "Reply"

        with patch("src.services.plan_coach_service.chat_completion", side_effect=_capture_count):
            resp = await client.post(
                "/api/v1/plans/chat/message",
                json={"content": "New message"},
            )
        assert resp.status_code == 200
        # 50 old + 1 new user = 51 total, truncated to last 40
        assert sent_count[0] == 40
