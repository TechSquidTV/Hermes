"""Configured admin bootstrap must fail closed without logging credentials."""

from pathlib import Path
from unittest.mock import AsyncMock

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.db.models import User
from app.db.repositories import UserRepository
from app.main import app, lifespan
from app.services.system_settings_service import system_settings_service


@pytest.mark.parametrize(
    "email,password",
    [
        ("owner@example.com", "secret"),
        ("invalid-email", "SecretSeedPassword123"),
        (None, "SecretSeedPassword123"),
    ],
)
async def test_failed_seed_never_serves_public_bootstrap(
    db_session: AsyncSession,
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    caplog: pytest.LogCaptureFixture,
    email: str | None,
    password: str,
) -> None:
    monkeypatch.setattr(settings, "initial_admin_username", "owner")
    monkeypatch.setattr(settings, "initial_admin_email", email)
    monkeypatch.setattr(settings, "initial_admin_password", password)
    monkeypatch.setattr(settings, "temp_dir", str(tmp_path / "temp"))
    monkeypatch.setattr(settings, "allow_public_signup", False)
    monkeypatch.setattr(
        system_settings_service,
        "get_allow_public_signup",
        AsyncMock(return_value=False),
    )
    with pytest.raises(
        RuntimeError, match="Initial administrator setup failed"
    ) as error:
        async with lifespan(app):
            pytest.fail("Server must not serve requests after configured seeding fails")
    assert password not in str(error.value) and password not in caplog.text
    assert "input_value" not in caplog.text
    assert await UserRepository(db_session).count() == 0


async def test_existing_installation_can_remove_seed_password(
    test_admin_user: User,
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(settings, "initial_admin_username", "owner")
    monkeypatch.setattr(settings, "initial_admin_email", "owner@example.com")
    monkeypatch.setattr(settings, "initial_admin_password", None)
    monkeypatch.setattr(settings, "temp_dir", str(tmp_path / "temp"))
    async with lifespan(app):
        assert test_admin_user.is_admin
