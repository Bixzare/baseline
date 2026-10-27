# Cloud batch operations

OPS-001 supplies nightly and dispatcher adapters plus default-off workflows.
No production schedule is activated by merging them. Both the explicit repository
enable variable and all reviewed readiness flags in `configs/operations.json`
must pass; flags are currently false. A disabled/read-only invocation never writes
a successful production heartbeat. No administrative credential enters these jobs.

## Stages and coordination

- Nightly, 07:17 UTC: reconcile persisted pending/recent finals, refresh the full
  schedule, renew only needed rosters and save seven/30-day/season reports.
- Dispatcher, minutes 7/22/37/52: reuse a current full inventory or refresh it,
  find due occurrences, refresh essential evidence, resolve relevant prior finals,
  prepare and publish missing batches, or confirm the original unverified batch.

The target is two hours before scheduled start. Recovery stops strictly at the
15-minute cutoff or on started/ineligible status. No delayed invocation backfills
a missed forecast. Existing batches are never regenerated after a lost response.
Fresh local-only roster uploads can be consumed while their original timestamps
remain fresh; absent local capability blocks that game rather than cloud stats
access or a guessed participant cohort.

One bounded shared request/time budget carries the source denial stop and minimum
gap across stages. Defaults are 16 requests and 600 operation seconds, with each
source run capped at 180 seconds. A source failure can leave unaffected reporting
available, but overall completion remains incomplete and the process fails.

A nonblocking Postgres session advisory lock coordinates cloud/Windows operations
outside network transactions. Failure/disconnect releases it. Overlap is recorded
as incomplete, not successful work. Protected occurrence locks, uniqueness and
database deadlines remain the ledger integrity mechanism. GitHub concurrency
also avoids cancellation of in-flight work; it is only an extra load guard.

Run start, each stage and operation completion have separate immutable events.
Only terminal operation completion can establish a successful operation heartbeat.
Source/check IDs, stage counts/durations and child run IDs retain provenance;
exception text/credentials are never included. Database failure leaves a local
report with durable completion explicitly unconfirmed.

## Rehearsal and deployment controls

```powershell
uv run --locked python -m scripts.rehearse_operations --operation nightly
uv run --locked python -m scripts.rehearse_operations --operation dispatcher
uv run --locked python -m scripts.rehearse_operations --operation dispatcher --fail-stage
uv run --locked python -m hoop.domains.nba.operations dispatcher --mode read-only --environment local --output artifacts/operations
```

Rehearsals require disposable local `BASELINE_TEST_DSN`, real Postgres and fixture
HTTP/Storage. The fixture namespace refuses a production/remote target. Both
adapters use the same stage code as production. The denial drill deliberately
returns failure. No live source access is implied.

After the workflow exists on the default branch, manual fixture dispatch is:

```powershell
gh workflow run nightly.yml -f fixture_rehearsal=true
gh workflow run dispatcher.yml -f fixture_rehearsal=true
```

The existing CI workflow also accepts `ops_rehearsal=true` and an optional
`ops_failure_drill=true` to exercise both reusable fixture jobs on a reviewed
branch without production secrets. Actual dispatch availability is verified
separately; an unmerged YAML file is not proof of scheduled execution.

Production jobs are main-only and use protected environment `baseline-production`.
Configure its branch restriction and review policy before adding runtime secrets.
Needed secrets: `BASELINE_RUNTIME_DSN`, backend artifact email/password. Nonsecret
variables: verified connection mode, Supabase URL/publishable key and backend
identity UUID. DSNs require supported direct/session TLS verification. Migration,
service and admin keys are excluded. Never expose private schemas publicly.

Activation/disable is the explicit `BASELINE_PRODUCTION_ENABLE` repository setting;
leave it unset/false until LAUNCH-001's source, fallback, backup and review gates.
Changing only that setting cannot override false readiness flags. Manual fixture
dispatch defaults true. Source work uses only owner-accepted environment routes;
default routes are empty. No production credential is available to fixture jobs.

Local smoke results: the dispatcher stored one fixture batch and receipt in 3.6
seconds with one HTTP fixture request; nightly saved three fixture reports in 3.8
seconds with one request. Memory is unavailable in this Windows measurement;
Linux rehearsal reports measured peak RSS. These do not estimate real source or
season workloads. Student credits and paid runners are not required.

GitHub cron can be delayed/dropped and schedules depend on default-branch/account
state; see [GitHub schedule behavior](https://docs.github.com/en/actions/reference/workflows-and-actions/events-that-trigger-workflows#schedule).
OPS-002 provides the independent checker. Actual owner failure-notification
delivery and unattended behavior remain separate acceptance gates. A failing exit
or registered workflow alone does not prove the owner received anything.
