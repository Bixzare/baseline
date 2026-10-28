# Verified raw archives

[ADR 0017](decisions/0017-encode-large-raw-archives-with-verified-parts.md) was
locked on October 28, 2026. The platform module `hoop.platform.raw_archives` stores
exact recoverable source bytes using gzip and bounded immutable parts. It has no
NBA imports. Source checks, seed acceptance, and model activation are separate.

## Identity and limits

Each physical object uses its own SHA-256 and actual byte count. A JSON root
records the original source hash/size, compression version, ordered part hashes,
encoded hash/size, and registered part IDs. Normalized source-row lineage retains
the original source hash. A JSON root never claims to be the original response.
Parts are at most 16 MiB; each logical source file is at most 1 GiB and has at most
128 parts. Neither limit can be raised by a descriptor. Readers verify every
physical part, enforce bounded decoding, and verify the original hash and size.
Truncation, trailing data, extra gzip members, missing parts and mismatches fail.
A failed local reconstruction never finalizes its output or replaces another file.
Direct legacy CSV artifacts remain supported.

`encode_raw` and `verify_archive` operate locally. `retain_archive` uses existing
restricted runtime and backend identities, registers every part before the root,
and performs network work outside SQL transactions. Exact retries reuse objects
and registered identities. Partial parts remain harmless recoverable evidence;
they cannot establish an accepted source or successful import. `verify_raw`
checks logical bytes without writing a decompressed file. `materialize_raw`
reconstructs an actual file only after successful validation.

Supabase's [standard upload documentation](https://supabase.com/docs/guides/storage/uploads/standard-uploads)
recommends resumable uploads above 6 MB for reliability. This implementation keeps
the existing standard transport and its 16 MiB bound, with per-part exact retry
semantics rather than adding a second upload protocol. The [Free file limit](https://supabase.com/docs/guides/storage/uploads/file-limits)
is a separate provider constraint. Actual throughput and failures must be measured;
the 16 MiB client bound alone does not prove reliable hosted transfers.

## Controlled rehearsal

Default execution does not load private credentials, connect, or write:

```powershell
uv run --locked python -m scripts.rehearse_raw_archives
```

Given an explicitly staged local JSON set with a `files` map of archive
descriptors, retain it in a **rehearsal** run:

```powershell
uv run --locked python -m scripts.rehearse_raw_archives retain --archive PATH_TO_LOCAL_OBJECTS --staged PATH_TO_STAGED_JSON --confirm-rehearsal --report artifacts/raw-retention.json
```

This registers raw objects and rehearsal evidence only. It never accepts a
source, imports NBA facts, activates a model, or publishes predictions.
To check registered roots independently of local input files, configure
`BASELINE_RAW_ARCHIVE_ROOT_IDS` as up to 16 distinct comma-separated UUIDs:

```powershell
uv run --locked python -m scripts.rehearse_raw_archives check --confirm-rehearsal --report artifacts/raw-readback.json
```

The manual artifact-permission Actions workflow accepts the same IDs in its
optional `archive_root_ids` input. That additional step uses restricted runtime
and backend identities, with no migration DSN or administrator key. It reads
registered objects, then decodes and verifies the logical original checksums.
Its success does not accept the source data for modeling.

## Backup and recovery

Every registered part and root enters the existing artifact backup inventory.
Export and isolated restore independently reconstruct logical hashes from saved
backup bytes, without the original provider or laptop archive. Missing part IDs,
changed inventory metadata or inconsistent reconstructed originals fail the
backup check. The report includes encoded-file and logical-byte verification
counts. No full historical backup gate is waived by a local fixture or a current
hosted-only rehearsal; daily backup and remote restore remain mandatory.
