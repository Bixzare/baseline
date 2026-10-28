# ADR 0016: Corroborate concealed Storage mutation results

Status: LOCKED by the owner on October 28, 2026. No permission gate is waived.

## Evidence

The actual private Storage API permits create/read and explicitly refuses
replacement/upsert. A backend delete returns HTTP 200 with an empty list;
move and bucket administration conceal resources behind canonical NoSuchKey
and NoSuchBucket responses. The original object survives. Status alone cannot
prove these three permission boundaries, so the existing rehearsal stays false.

## Decision

Add an explicit optional verification mode using the restricted database login
to read the active Storage policy catalog before and after the API rehearsal.
It must prove both tables have RLS, the authenticated API role has neither bypass
nor inherited owner privileges, object policies permit only SELECT/INSERT,
and no bucket policy permits mutation. Unexpected policy/role state fails.
Fingerprint the policy evidence and require it to remain unchanged.

For every tested mutation, first verify the actual existing fixture bytes and
verify those bytes again immediately afterward. For move, also verify the unique
destination is absent before and after. For an empty delete result, require valid
JSON [] and the policy proof of no DELETE access. For concealed mutation errors,
require the exact canonical provider code and status plus the corresponding
policy proof and known resource. Generic 404, malformed responses, changed bytes,
new destinations, nominal mutation success, or missing policy evidence fail.

Report explicit authorization denial separately from prevented mutation backed
by policy and byte evidence. Do not relabel an HTTP 200 response as HTTP 403.
Retain strict status-only behavior when the optional mode is not selected.
No grants, provider policies, privileged API fallback or production switches change.

## Tradeoff and limits

The optional rehearsal needs the existing restricted runtime DSN and public CA,
but no migration credential or server key. Its read-only catalog transactions
finish before network requests. This adds verification complexity to distinguish
expected RLS filtering from broken endpoints or actually permitted mutations.
It does not attest against a malicious administrator changing and restoring
policies between observations; administrators remain outside the runtime boundary.

## Acceptance before use

Owner lock, deterministic API fault tests, real Postgres policy/role regression
tests, matching Windows and actual Actions evidence, and unchanged production
activation gates. Broader policies, disabled RLS, bypass roles, generic missing
endpoints and unexpected mutation effects must never produce a passing report.
