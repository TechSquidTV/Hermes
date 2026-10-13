"""Use each supported database's conflict-aware INSERT syntax."""

from __future__ import annotations

from typing import TYPE_CHECKING, cast

if TYPE_CHECKING:
    from pathlib import Path

    from sqlalchemy.engine import Dialect


from unittest.mock import AsyncMock, Mock

import pytest
from sqlalchemy.dialects import postgresql, sqlite
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models import DownloadFile
from app.services.download_files import register_download_file


@pytest.mark.parametrize(
    "dialect", [cast("type[Dialect]", postgresql.dialect)(), sqlite.aiosqlite.dialect()]
)
async def test_registration_uses_native_upsert(
    dialect: Dialect, tmp_path: Path
) -> None:
    output = tmp_path / "video.mp4"
    output.write_bytes(b"media")
    session = AsyncMock(spec=AsyncSession)
    session.get_bind.return_value.dialect.name = dialect.name
    final = DownloadFile(
        id="file",
        download_id="download",
        filepath=str(output),
        filename=output.name,
        file_size=5,
        file_type="video",
    )
    inserted = Mock()
    inserted.one.return_value = final
    session.scalars.side_effect = [[], inserted]
    assert await register_download_file(session, "download", str(output)) is final
    statement = session.scalars.await_args.args[0]
    compiled = statement.compile(dialect=dialect)
    assert "ON CONFLICT (id) DO UPDATE SET" in str(compiled)
    assert "RETURNING" in str(compiled)
    assert compiled.params["filepath"] == str(output.resolve())
    session.commit.assert_not_called()
