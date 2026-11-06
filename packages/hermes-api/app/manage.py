"""Operator commands. Run with python -m app.manage (uv run for native installs)."""

import argparse
import asyncio
import json
from pathlib import Path

from sqlalchemy import text
from sqlalchemy.engine import make_url

from app.core.config import settings
from app.core.maintenance import in_maintenance, set_maintenance
from app.db.backup import backup_database, restore_database
from app.db.base import engine
from app.db.migrations import check_schema, expected_revision, migrate_database


async def preflight_database() -> None:
    url = make_url(settings.database_url)
    if url.get_backend_name() == "sqlite" and not Path(url.database or "").is_file():
        raise RuntimeError(
            "Existing SQLite database not found; verify the installation's database mount"
        )
    try:
        async with engine.connect() as connection:
            await connection.execute(text("SELECT 1"))
    finally:
        await engine.dispose()


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    commands = parser.add_subparsers(dest="command", required=True)
    commands.add_parser(
        "migrate", help="Apply migrations under the shared database lock"
    )
    commands.add_parser("check-schema", help="Verify this release's schema")
    backup = commands.add_parser(
        "backup", help="Take a consistent SQLite or PostgreSQL snapshot"
    )
    backup.add_argument("destination", type=Path)
    restore = commands.add_parser(
        "restore", help="Restore a snapshot while ALL backend services are stopped"
    )
    restore.add_argument("snapshot", type=Path)
    restore.add_argument("--confirm-stopped", action="store_true", required=True)
    commands.add_parser("preflight", help="Validate upgrade tooling without migrating")
    maintenance = commands.add_parser(
        "maintenance", help="Close or reopen API admission during a managed upgrade"
    )
    maintenance.add_argument("state", choices=("on", "off"))
    args = parser.parse_args()
    if args.command == "migrate":
        asyncio.run(migrate_database())
    elif args.command == "check-schema":
        asyncio.run(check_schema())
    elif args.command == "backup":
        print(json.dumps({"snapshot": str(backup_database(args.destination))}))
    elif args.command == "restore":
        restore_database(args.snapshot.resolve())
    elif args.command == "preflight":
        from shutil import which

        if in_maintenance():
            raise RuntimeError(
                "An upgrade is already in maintenance; recover or complete it before starting another"
            )

        if make_url(
            settings.database_url
        ).get_backend_name() == "postgresql" and not all(
            which(tool) for tool in ("pg_dump", "pg_restore")
        ):
            raise RuntimeError(
                "PostgreSQL client tools are required for backup and restore"
            )
        asyncio.run(preflight_database())
        print(
            json.dumps(
                {
                    "version": settings.api_version.lstrip("v"),
                    "revision": expected_revision(),
                }
            )
        )
    elif args.command == "maintenance":
        set_maintenance(args.state == "on")


if __name__ == "__main__":
    main()
