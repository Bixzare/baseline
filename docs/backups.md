# Independent backup operations

BACKUP-001 supplies a default-off local backup job. OneDrive is the owner-selected
provider. A real current-state application export was independently downloaded
from the matching personal OneDrive and restored into an isolated local target.
Full historical archive coverage and daily task activation remain release gates.

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

Native PostgreSQL subprocesses preserve the public PGSSLROOTCERT trust-anchor
setting when the DSN does not specify sslrootcert. An explicit DSN certificate
wins. Privileged BASELINE environment variables remain excluded from child tools,
and database passwords are passed through environment provisioning only.

## Controlled current-state rehearsal

The personal OneDrive remote was matched to the Windows sync account identifier.
Only Files.Read and offline_access were requested; readback never uploads or
deletes remote files. The existing OneDrive client provides synchronization.
The actual 5 GiB account reported 3,113,851,289 free bytes at setup. PostgreSQL
17.11 client tools came from the provider's official EDB archive and rclone
v1.75.2 matched the publisher's release digest and checksum list. Tools live only
in the ignored project cache; no Windows database service was installed.

The adapter now preserves Windows SYSTEMROOT, required for DNS, while excluding
PGPASSWORD and privileged BASELINE variables. The native database tools preserve
the public CA separately. These boundaries have regression tests.

The versioned rehearsal script defaults to a plan with no network or writes:

```powershell
uv run --locked python -m scripts.rehearse_hosted_backup
uv run --locked --env-file .env python -m scripts.rehearse_hosted_backup export
uv run --locked --env-file .env python -m scripts.rehearse_hosted_backup restore
```

Export is controlled and explicitly limited to current application records and
registered artifacts. Restore first downloads and verifies the actual remote
set. BASELINE_RESTORE_ADMIN_DSN must name a loopback baseline_test database;
the helper creates a new randomly named baseline_restore database, applies
provider scaffolding only there, verifies rows/artifacts and denied runtime
mutation, then removes that exact temporary database. No production restore or
provider API reactivation occurs. Original source credentials are unnecessary
for the restore operation. Private paths and credentials stay in .env.

The initial actual remote drill restored 27 tables and one registered 1,937-byte
rehearsal artifact. It downloaded 173,969 logical bytes, preserved every original
row digest and URI, and removed its isolated target in 60.266 seconds. Backup ID
b5559324-d59f-4449-a590-f5c5625d0325 had manifest SHA-256
cb50669ecc824fa03c4679fb49dc2af7526e4835ca9d5a3a3bf82c5abae39f0b.
Its represented cutoff was October 28 at 09:16:56 UTC. It had no historical
archive and no forecasts. off_device_verified=true applies to this set only;
launch_backup_gate_satisfied=false and automation_enabled=false remain explicit.

Full launch backup still needs the reviewed complete historical inventory,
provider recovery setup and daily execution/health evidence. Do not turn the
prelaunch rehearsal into a backup-health success event or reset its cutoff merely
because the same set is downloaded again.

The versioned command on commit 729988d also passed: backup ID
bc7a65c2-56b4-4cdd-a4f8-c4dae3517088, manifest SHA-256
eca4c72459efe08ec8a632b9a5a649850a1c5fd21446372ceafc4bccebd84016,
represented cutoff October 28 at 09:40:26 UTC, the same 27 table digests and one
artifact, 173,969 bytes downloaded and verified, 36.359 seconds for readback plus
restore, and its isolated target removed. The launch gate remains false.
