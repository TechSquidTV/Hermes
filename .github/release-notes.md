## SQLite runtime and recovery

The backend image includes checksum-verified SQLite 3.54.1, including the
[upstream WAL-reset fix](https://sqlite.org/wal.html#walreset). This replaces the
unverified runtime in 1.0.0. Keep 1.0.0's tags and images intact for diagnosis;
use this corrected release for a new upgrade rehearsal.

**SQLite storage requirement:** every process accessing a live database must
share the same host and local filesystem, including backup and diagnostic
readers. Keep Docker databases on a Linux-native volume. Do not open a live
container database with a macOS host tool over a shared mount. PostgreSQL remains
the supported option for database access across hosts.

Use the native online backup command or a consistent stopped-process checkpoint.
Copying a live database file alone can omit committed writes. Preserve journal,
WAL and shared-memory files; do not delete them to clear locks. Rehearse both
upgrade and restoration on an isolated copy before production deployment.

## Before upgrading

**Database migration and coordinated service upgrade required.** Use the target
release's upgrade script and Compose files with your existing installation's
`.env` and data mounts. Back up the database and keep the recovery record.

From the installation directory:

```bash
python3 scripts/upgrade.py {{VERSION}}
```

The command drains work, backs up and migrates the database, then upgrades the
frontend, API, worker and scheduler together. This requires a maintenance window.
Do not upgrade the API and worker independently. Native deployments must stop
all backend processes and follow the manual migration procedure.

**Sign in again after upgrading.** Older sessions are rejected. Changing a
password now signs the user out on every device.

See the [upgrade and recovery guide](https://github.com/TechSquidTV/Hermes/blob/v{{VERSION}}/docs/UPGRADING.md)
for prerequisites, custom Compose files, backup retention and recovery.

