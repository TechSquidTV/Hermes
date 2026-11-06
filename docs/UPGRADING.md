# Upgrading Hermes

Use `scripts/upgrade.py` from the target release together with its Compose files.
The command manages the bundled prebuilt stack: one API, worker, scheduler, and
frontend, using one Redis broker. Python 3.11+, Linux/macOS, and Docker Compose
2.24.4+ are required. Start with a healthy, running stack and keep the existing
database, storage mounts, Redis URL, and secrets. Do database moves separately.
External API clients, workers and schedulers must be stopped separately; this
command only coordinates the selected Compose project and rejects extra workers.

**Authentication change:** existing browser sessions must sign in again after
this release. Access, refresh and live-event credentials are now bound to the
password that issued them. Changing a password signs the user out on every
device as soon as the password update commits.

**Breaking deployment change:** worker and scheduler containers now verify the
schema instead of migrating it themselves. Start the API or run the migration
command first. Bundled Compose dependencies and the managed upgrade handle this
ordering automatically.

```bash
# Run from the installation directory, with its existing .env and data mounts.
python3 scripts/upgrade.py 1.2.3

# Custom files: pass the same files, project name and environment on every run.
COMPOSE_PROJECT_NAME=hermes python3 scripts/upgrade.py 1.2.3 \
  --file docker-compose.example.yml --file local-overrides.yml --env-file .env
```

Replace `1.2.3` with an exact published version. The command sets the image tag
for this invocation; leave the old tag in `.env` until it succeeds. Use
`--skip-pull` only when matching release images are already loaded locally.
Source-build and development stacks are intentionally excluded: build and test
release images first, or follow the native/manual procedure below.

The upgrade records the resolved Compose project name and reuses it explicitly
for every subsequent step and recovery, even in a fresh shell with different
environment variables. The upgrade pulls images and validates the backend
version and worker visibility while the old stack is serving. It then stops the frontend, API and scheduler,
lets queued, active, reserved and scheduled tasks finish, pauses consumers, and
checks again before stopping the worker. A drain timeout (15 minutes by default,
adjustable with `--drain-timeout SECONDS`) resumes the original containers and
consumers without killing downloads or changing the database.

A persistent maintenance gate blocks direct API traffic with HTTP 503 while the
replacement services are checked. Health endpoints remain available. Failed
upgrades keep the gate closed, including across container restarts. Recovery
clears it; after a manual forward fix and verification, reopen admission with
`python -m app.manage maintenance off` in the backend's normal environment.

During maintenance it creates a private SQLite online backup or PostgreSQL custom
dump at `/app/data/backups/<upgrade-id>/`, records the old image IDs and `.env`,
and migrates under a shared lock. It starts matching images, waits for API
readiness and worker health, verifies image IDs and schema, starts scheduling,
and updates `.env`. Keep the backup and `.hermes-upgrades/<upgrade-id>/` recovery
record together; the latter contains a private copy of the old configuration.
Backups are retained until you remove them. Copy them to separate storage too.

Redis itself is kept running; update the broker separately when required.
This is a planned maintenance window. It does not promise zero downtime for
arbitrary schema changes. Do not run another deployment command concurrently.
Ordinary manual Compose stops allow workers 15 minutes to finish; unlike the
upgrade command, Docker can force-stop them when that allowance expires.

## Failed upgrades and recovery

Failures before migration restart the original containers. SIGINT, SIGTERM and
SIGHUP request cancellation at a safe checkpoint: the current Docker operation
finishes before cleanup starts. If the host or operator process is killed before
migration, resume the original containers without restoring the database:

```bash
python3 scripts/upgrade.py --recover .hermes-upgrades/<upgrade-id>/state.json
```

This clears maintenance and resumes any paused consumers. It also works after a
backup finished if no migration started. Do not add `--restore-database` in these
phases; the database has not changed. Recovery records must include a saved
Compose project identity; older records without one require manual recovery
using the installation's explicit project name.

Failures during migration or replacement startup leave requests and scheduling offline and print
the recovery record. Prefer a forward fix when practical. **An older image alone
cannot safely roll back a newer database schema.**

The explicit recovery command stops services, drains a running worker if needed,
restores the pre-upgrade database snapshot, then starts the recorded previous
image IDs and configuration:

```bash
python3 scripts/upgrade.py \
  --recover .hermes-upgrades/<upgrade-id>/state.json --restore-database
```

**Restoring replaces the database and discards writes after the snapshot.** Media
files are retained; reconcile files created after the snapshot if necessary.
Recovery records when database restoration finishes. If service startup is
interrupted afterward, repeating recovery resumes startup without restoring the
database again or discarding subsequent writes.
Do not delete or prune the recorded old images until recovery is no longer needed.
Automatic recovery is refused for completed upgrades because users may already
have made new changes. For a later rollback, stop every backend process, make a
new backup of the current database, explicitly restore the selected snapshot with
the command below, then deploy its matching images and configuration. Restore
PostgreSQL into a database you own; do not restore unrelated application schemas.

```bash
# All APIs, workers and schedulers must be stopped first.
docker compose -f docker-compose.example.yml run --rm --no-deps \
  --entrypoint python api -m app.manage restore \
  /app/data/backups/<upgrade-id>/database.sqlite --confirm-stopped
# PostgreSQL snapshots are named database.dump instead.
```

Do not run a blind `alembic stamp head` or automatically downgrade a failed
migration. Preserve the failed database and logs when diagnosis is needed.

## Backups and native deployments

The backend image includes PostgreSQL client tools. The dump client must be at
least as new as the server; native PostgreSQL installations need `pg_dump` and
`pg_restore` on PATH. URL credentials and supported TLS options are passed through
the environment rather than printed in command lines. Backups preserve data;
restores must be rehearsed on a disposable database before relying on them.

```bash
# Consistent backup of a running Compose deployment. Choose a new directory.
docker compose -f docker-compose.example.yml run --rm --no-deps \
  --entrypoint python api -m app.manage backup /app/data/backups/manual-20261106

# Native deployment, from packages/hermes-api with its usual environment.
uv run --locked python -m app.manage backup /safe/backups/hermes-20261106
# Stop publishers, drain work and stop all backend processes before upgrading.
uv run --locked python -m app.manage migrate
uv run --locked python -m app.manage check-schema
# Start API, worker and scheduler from the same release, then reopen traffic.
```

API startup also runs this migration path. All online Alembic commands share a
PostgreSQL advisory lock or a SQLite lock file beside the database, with a
two-minute lock wait. Never remove the SQLite lock file while processes are
running. Keep it on the shared database mount; migrations need the downloads
filesystem mounted for historical path canonicalization.

Older native installs created tables without an Alembic revision. The migrator
validates their schema before adopting a recognized baseline and applying later
migrations, preserving accounts and downloads. Unrecognized schemas stop without
stamping or modifying their tables and require operator reconciliation.

`/api/v1/health/` remains a liveness check. `/api/v1/health/ready` returns 503 when
the database, Redis, or release schema is unavailable; bundled Compose health
checks use readiness. Browser tabs check the deployed frontend build without
using GitHub release availability. They prompt for an explicit reload and leave
the current page and session intact until the user chooses it.
Tabs opened before this feature was installed need one manual reload; they
cannot receive code introduced by a later release until that first reload.
