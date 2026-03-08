#!/usr/bin/env python3
"""
Bootstrap script -- run once after first deploy to create admin user + invite codes.

Usage:
  docker exec <container> python scripts/create_admin.py admin@example.com
"""
from __future__ import annotations

import asyncio
import sys


async def main(email: str) -> None:
    import secrets

    from sqlalchemy.ext.asyncio import create_async_engine
    from sqlalchemy.orm import sessionmaker
    from sqlmodel import SQLModel
    from sqlmodel.ext.asyncio.session import AsyncSession

    from src.auth.models import InviteCode, User
    from src.auth.passwords import hash_password
    from src.db.models import AthleteProfile  # noqa: F401 -- register tables
    import src.auth.models  # noqa: F401

    password = input(f"Password for {email}: ")
    engine = create_async_engine("sqlite+aiosqlite:////data/garmincoach.db")
    async with engine.begin() as conn:
        await conn.run_sync(SQLModel.metadata.create_all)

    async_session = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
    async with async_session() as session:
        user = User(email=email, password_hash=hash_password(password), is_active=True)
        session.add(user)
        await session.flush()

        codes = [InviteCode(code=secrets.token_urlsafe(12), created_by=user.id) for _ in range(5)]
        session.add_all(codes)
        await session.commit()

        print(f"Admin user created: {email}")
        print("Invite codes:")
        for c in codes:
            print(f"   {c.code}")

    await engine.dispose()


if __name__ == "__main__":
    email = sys.argv[1] if len(sys.argv) > 1 else input("Admin email: ")
    asyncio.run(main(email))
