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

