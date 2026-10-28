# Independent backup operations

BACKUP-001 supplies a default-off local backup job. OneDrive is the owner-selected
provider. No real OneDrive backup, private Auth session, remote restoration or
daily task activation has been verified yet. Those remain release gates.

## Data flow and integrity

1. The privileged local export connection validates applied migration hashes and
   takes a session lock. It records a conservative database cutoff before
   acquiring a repeatable snapshot.
2. The same snapshot supplies application table counts/digests, required artifact
   descriptors, migration history and supported provider metadata. Matching-major
   pg_dump uses the exported snapshot. A concurrent write after acquisition does
   not enter either the inventory or the dump.
3. Close the snapshot transaction before downloading immutable artifact bytes.
   Verify every registered object and every reviewed historical archive input by
   SHA-256 and size. Missing bytes or a changed archive fail the complete set.
4. Stage outside the sync folder. Content-addressed objects are shared across
   immutable sets; write the complete manifest/marker last. No automatic deletion
   or credential export occurs. Existing unequal bytes are refused.
5. Download the marker, manifest and every object from the configured **OneDrive**
   remote into a fresh location outside both staging and sync. Verify all bytes.
   Local presence, a sync icon or successful copy cannot establish off-device
   delivery. A local/alias rclone backend is refused.
6. Only after actual remote verification, retain the manifest and append a
   `backup_remote_verified` event. OPS-002 uses its represented cutoff, manifest
   hash and explicit off-device flag. A new upload does not change the cutoff.

The application dump contains platform/nba/api records, grants and owned objects.
It excludes provider Auth passwords/tokens and unrelated managed data. The
manifest includes provider migration IDs and Storage policy definitions when
available, plus nonsecret application role metadata. Administrative setup and
backend credentials must be reprovisioned separately.

Copy/readback budgets are bounded, as are subprocess and network operations.
The daily task has a 60-minute execution limit. Disk checks conservatively include
registered objects, archives and database size before export and sync copy.
Actual OneDrive quota and season growth remain unmeasured. Required artifacts
retain the existing 16 MiB client bound; complete manifests have an 8 MiB bound.
These limits do not repair the already documented oversized raw-seed blocker.

## Setup and commands

Keep actual paths, OAuth configuration and credentials private. The tracked
`.env.example` lists variables only. The source DSN must match the configured
Supabase project and use supported TLS/direct or session pooling. Ordinary cloud
jobs receive no privileged backup credentials.

- Install/verify native Postgres 17 pg_dump and pg_restore. Set BASELINE_PG_BIN
  to their directory. Matching major versions are enforced.
- Install a verified/pinned rclone release. Configure a dedicated OneDrive remote
  interactively with `rclone config`; complete Microsoft sign-in yourself. Keep
  its configuration/tokens outside Git and chat. Configure BASELINE_RCLONE_BIN,
  BASELINE_RCLONE_VERSION and BASELINE_BACKUP_REMOTE, for example a dedicated
  remote folder `baseline-backup:Baseline backups`. No upload/delete command is
  used by the verification adapter; the existing OneDrive client supplies sync.
- Configure three separate directories: sync destination, nonsynced staging and
  nonsynced remote readback. Actual folder/account mapping needs verification.
- Supply a reviewed historical archive inventory as a private JSON list with
  label, source path, expected SHA-256 and byte_count per required original file.
  Accepted source manifests establish completeness; a guessed directory scan
  does not. Known credential files and symlinks are refused.
- Verify a clean local restore database with the required controlled roles and
  provider dependencies. It must have a disposable baseline_restore_ or
  baseline_test_ name, loopback host, matching major and no application schemas.
  Restore never resets production or overwrites existing schemas.

After reviewed setup and actual prerequisites, both `configs/backup.json` enabled
and `BASELINE_BACKUP_ENABLE=true` must be set. Until then:

```powershell
uv run --locked python -m hoop.platform.backup run --output artifacts/backup-health
# Expected now: disabled, off_device_verified false.
uv run --locked python -m scripts.windows_tasks plan --output artifacts/windows-tasks
```

Enabled operations are run, verify and restore. Verify/restore additionally need
explicit --backup-id and --manifest-hash. Private environment configuration chooses
all account/path/connection values. Load a local file explicitly with uv run's
`--env-file .env`; it is not automatically read by the package.

The rendered `Baseline-Backup` task runs daily at **08:17 UTC**, using the current
interactive owner and project pythonw. It starts disabled, does not wake the
machine and changes no global settings. Registration is a separate reviewed
operation; all persistent Baseline tasks are still absent. An awake, connected,
logged-in machine is required. Disable an installed task with:

```powershell
Disable-ScheduledTask -TaskName Baseline-Backup
```

## Restore and evidence limits

Validate a remotely downloaded complete set before restore. Source-project,
clean-target and application-role checks precede pg_restore. The restore uses
one transaction, compares every application table's original row digest/count
and leaves automation disabled. ArchiveArtifacts provides an explicit read-only
mapping from unchanged original Storage references to verified archived bytes.
It does not rewrite ledger rows or claim that a replacement provider API is
already configured. Provision backend Auth/buckets and verify real permissions
before any runtime reactivation.

The local synthetic rehearsal exported and restored **27 tables, 10 numeric
predictions and one publication receipt**. Original IDs, values, timestamps and
all registered bytes matched; the post-snapshot concurrent write was absent.
The measured complete fixture path took **10.000 seconds**, with **209,199 logical
bytes**, backup ID `8f01de40-1f51-4751-a34a-c444f15ea618`. Its manifest SHA-256 was
`465ac84d72da9b568b579c3bcb273683572b9c74c0bb697dd44b4ec91bdf59fe`.
This used real Postgres and a synthetic remote boundary, so off_device_verified
remained false. It is not a production RPO/RTO or season capacity estimate.

Focused checks cover stale/partial delivery, missing/corrupt objects, unsafe
paths, incorrect hashes, immutable retry/deduplication, credential-file refusal,
wrong remote backend, original-reference resolution and denied runtime writes.
The full suite retains source, leakage and ledger timing checks. Linux CI uses
its pinned Postgres service's matching client tools; Windows compatibility checks
explicitly exclude Postgres tests. Local Docker tool mode is fixture-only and
cannot be selected by the production backup CLI.

Real OneDrive OAuth/readback, current project export, independently downloaded
restore, provider configuration, daily execution and owner review remain pending.
Sources: [Postgres snapshot export](https://www.postgresql.org/docs/17/app-pgdump.html),
[Supabase backup scope](https://supabase.com/docs/guides/platform/backups),
[rclone OneDrive](https://rclone.org/onedrive/), and
[remote backend verification](https://rclone.org/commands/rclone_listremotes/).
