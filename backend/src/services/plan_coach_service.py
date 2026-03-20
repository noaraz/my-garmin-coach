"""Plan Coach service — system prompt builder and chat orchestration."""
from __future__ import annotations

from datetime import date, datetime, timedelta, timezone

from sqlmodel import select
from sqlmodel.ext.asyncio.session import AsyncSession

from src.db.models import AthleteProfile, GarminActivity, HRZone, PaceZone, PlanCoachMessage
from src.services.gemini_client import chat_completion

# Maximum messages sent to Gemini (last 40 = 20 user/assistant pairs)
_HISTORY_TRUNCATION = 40

# Look-back window for recent Garmin activities
_ACTIVITY_LOOKBACK_DAYS = 28

_STEP_FORMAT_SPEC = """
Step format (one line per workout's steps_spec field):
  10m@Z1           — 10 minutes at pace zone 1
  5K@Z3            — 5 km at pace zone 3
  30s@Z5           — 30 seconds at pace zone 5
  6x(400m@Z5 + 200m@Z1)  — repeat group: 6 reps of 400m hard + 200m easy
  10m@Z1, 45m@Z2, 5m@Z1  — comma-separated steps (mixed time and distance ok)

Units: m = minutes, s = seconds, K = km. Zones: Z1–Z5 (pace zones only).
"""

_OUTPUT_INSTRUCTION = """
When you are ready to provide the training plan, emit a fenced JSON block exactly like this:

```json
[
  {
    "date": "2026-04-01",
    "name": "Easy Run",
    "description": "Recovery run at comfortable pace",
    "steps_spec": "10m@Z1, 30m@Z2, 5m@Z1",
    "sport_type": "running"
  }
]
```

Each object must have: date (ISO 8601), name, description, steps_spec, sport_type.
Do not include any other text inside the JSON block.
If the plan is not ready yet (user is still refining), respond conversationally without a JSON block.
"""


def _format_pace(sec_per_km: float) -> str:
    """Convert seconds/km to mm:ss/km string."""
    minutes = int(sec_per_km) // 60
    seconds = int(sec_per_km) % 60
    return f"{minutes}:{seconds:02d}/km"


def build_system_prompt(
    profile: AthleteProfile,
    hr_zones: list[HRZone],
    pace_zones: list[PaceZone],
    recent_activities: list[GarminActivity],
) -> str:
    """Build the Gemini system prompt from athlete data. Pure function, no I/O."""
    lines: list[str] = [
        "You are a running coach helping an athlete create a multi-week training plan.",
        "",
        "## Athlete Profile",
    ]

    if profile.lthr:
        lines.append(f"- LTHR (lactate threshold HR): {profile.lthr} bpm")
    if profile.threshold_pace:
        lines.append(f"- Threshold pace: {_format_pace(profile.threshold_pace)}")
    if profile.max_hr:
        lines.append(f"- Max HR: {profile.max_hr} bpm")

    if hr_zones:
        lines.append("")
        lines.append("## Heart Rate Zones")
        for z in sorted(hr_zones, key=lambda x: x.zone_number):
            lines.append(
                f"- Z{z.zone_number}: {z.lower_bpm:.0f}–{z.upper_bpm:.0f} bpm"
            )

    if pace_zones:
        lines.append("")
        lines.append("## Pace Zones")
        for z in sorted(pace_zones, key=lambda x: x.zone_number):
            lines.append(
                f"- Z{z.zone_number}: {_format_pace(z.lower_pace)}–{_format_pace(z.upper_pace)}"
            )

    if recent_activities:
        lines.append("")
        lines.append(f"## Recent Training (last {_ACTIVITY_LOOKBACK_DAYS} days)")
        for act in recent_activities:
            parts = [f"- {act.date} {act.activity_type}"]
            dur_min = act.duration_sec / 60
            parts.append(f"{dur_min:.0f}min")
            if act.distance_m:
                parts.append(f"{act.distance_m / 1000:.1f}km")
            if act.avg_pace_sec_per_km:
                parts.append(f"avg {_format_pace(act.avg_pace_sec_per_km)}")
            lines.append(" ".join(parts))

    lines.append("")
    lines.append("## Step Format")
    lines.append(_STEP_FORMAT_SPEC.strip())
    lines.append("")
    lines.append("## Output Instructions")
    lines.append(_OUTPUT_INSTRUCTION.strip())

    return "\n".join(lines)


async def get_chat_history(session: AsyncSession, user_id: int) -> list[PlanCoachMessage]:
    """Return all chat messages for the user, oldest first."""
    result = await session.exec(
        select(PlanCoachMessage)
        .where(PlanCoachMessage.user_id == user_id)
        .order_by(PlanCoachMessage.created_at)
    )
    return list(result.all())


async def send_chat_message(
    session: AsyncSession,
    user_id: int,
    content: str,
    profile: AthleteProfile,
    hr_zones: list[HRZone],
    pace_zones: list[PaceZone],
) -> PlanCoachMessage:
    """Append user message, call Gemini, append assistant response, return assistant message."""
    # 1. Load existing history and recent activities before touching the DB
    all_messages = await get_chat_history(session, user_id)

    cutoff = datetime.now(timezone.utc).replace(tzinfo=None)
    cutoff_date = date(cutoff.year, cutoff.month, cutoff.day)
    lookback_date = cutoff_date - timedelta(days=_ACTIVITY_LOOKBACK_DAYS)

    activity_result = await session.exec(
        select(GarminActivity)
        .where(GarminActivity.user_id == user_id)
        .where(GarminActivity.date >= lookback_date)
        .order_by(GarminActivity.date.desc())
    )
    recent_activities = list(activity_result.all())

    # 2. Build system prompt and Gemini message list (include new user message)
    system_prompt = build_system_prompt(profile, hr_zones, pace_zones, recent_activities)
    truncated = all_messages[-(_HISTORY_TRUNCATION - 1):]
    gemini_messages = [{"role": m.role, "content": m.content} for m in truncated]
    gemini_messages.append({"role": "user", "content": content})

    # 3. Call Gemini — only persist if this succeeds (avoids orphaned user messages)
    reply_text = chat_completion(gemini_messages, system_prompt)

    # 4. Persist user + assistant in a single commit; no refresh needed after commit
    user_msg = PlanCoachMessage(
        user_id=user_id,
        role="user",
        content=content,
        created_at=datetime.now(timezone.utc).replace(tzinfo=None),
    )
    assistant_msg = PlanCoachMessage(
        user_id=user_id,
        role="assistant",
        content=reply_text,
        created_at=datetime.now(timezone.utc).replace(tzinfo=None),
    )
    session.add(user_msg)
    session.add(assistant_msg)
    await session.commit()

    return assistant_msg
