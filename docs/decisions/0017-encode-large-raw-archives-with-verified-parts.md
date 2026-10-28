# ADR 0017: Encode large raw archives with verified parts

Status: LOCKED by the owner on October 28, 2026. Implementation is authorized; seed acceptance and production activation remain separate gates.

## Evidence

On October 28, 2026, the four pinned Eoin 525 input files totalled
438,321,084 bytes. A local gzip level 6 audit produced 60,615,087 bytes.
Decompressing every output reproduced its original byte count and SHA-256.
The largest output was PlayerStatistics.csv at 52,563,266 bytes, exceeding
the existing verified 16 MiB per-object client bound. No cloud upload occurred.
The original candidate manifest is
`1a98b146ef110647fcd165c7928abeb8b7df42d5ca3521cb413d1033449db123`.

## Decision

Add a domain independent archive operation that streams a verified local raw
file through gzip and splits the encoded stream into content addressed parts,
each at most 16 MiB. Retain seven parts for this measured input set, plus one
small versioned JSON descriptor per original file. All physical objects use
their own actual byte counts and SHA-256 identities. The descriptor records
codec/version, ordered part identities, total encoded size, and the original
raw SHA-256 and byte count. Reuse verifies existing bytes; replacement stays
forbidden. Encoding parameters are explicit; source identity remains the
original raw checksum, independent of codec or Python version.

A source check references the raw archive descriptor and explicitly reports
that representation in validation evidence. It must never present the JSON or
compressed payload as the original HTTP response. Normalized source-row lineage
keeps the original raw checksum. Upload and verify all required objects before
committing dependent database evidence. No network calls occur inside SQL
transactions. Failed uploads can leave harmless immutable objects for reuse.

A reader verifies the descriptor and every ordered part, streams decoding to a
local temporary file, and checks the declared original size and SHA-256 before
returning the file. Enforce configured maximum logical bytes, maximum parts,
encoded byte totals, and decompression bounds. The implementation caps a logical
file at 1 GiB and a descriptor at 128 parts. Missing, reordered, corrupted,
truncated, trailing, oversized, or unsupported inputs fail closed. Never load
the whole 438 MB archive into memory. Existing direct raw objects remain readable;
this does not increase the ordinary private-object size bound.

Backups include every registered part and descriptor. Restoration must reproduce
original source bytes from remotely downloaded parts. The full local archive
still needs its independent backup; compression does not satisfy that gate.
Seed acceptance, quarantine resolution, date semantics, and source readiness
remain separate requirements. This decision does not authorize hosted import,
model activation, publication, or production scheduling.

## Tradeoff

Measured cloud payload falls from about 438 MB to 61 MB, leaving more room for
season evidence. This adds a small versioned encoding and reconstruction layer,
streaming I/O, and extra storage objects. It uses Python's standard library,
requires no new service or paid plan, and keeps exact source bytes recoverable.
The local measured result is not a cloud upload or throughput guarantee.

## Acceptance before use

Owner lock; bounded roundtrip, corruption, missing/reordered part, decompression,
resume, and identity tests; real Postgres provenance tests; deterministic fixture
notebook execution; actual restricted-identity upload/readback from Windows and
Actions; remote backup/restore reconstruction. Preserve production off switches.
