# Independent Windows recovery and health

OPS-002 adds a separate checker, append-only alert migration and versioned Task
Scheduler definitions. Production, local fallback and automatic desktop notices
remain disabled. Reviewed migrations 0009 and 0010 are applied to the hosted
project; this does not establish accepted operational sources or recovery.

## Health and recovery

The checker reads a repeatable database snapshot using `baseline_runtime` and
database UTC time. It distinguishes starts, successful operation completion and
stage events. It reports schedule/status/roster freshness by source capability
and collection environment, pending outcomes, observed game coverage, backup
evidence and capacity. Participant coverage comes from evaluation reports, not
the limited health window. Missing measurements remain unverified.

| Condition | Behavior |
| --- | --- |
| Dispatcher start or successful completion at least 45 minutes old during a publication window | Separate warnings. |
| No successful nightly completion today at 09:17 UTC | Alert; guarded nightly recovery if enabled. |
| Missing valid forecast at 90 minutes before start | Shared dispatcher recovery only with fresh essential evidence and fallback enabled. |
| At or after 15 minutes before start, or a started/final game | Missed/unverified coverage; no new publication or late confirmation. |
| Source denial | Persisted stop across automatic invocations until later owner-reviewed verification. |
| Final status with incomplete outcome | Visible unresolved-final condition; no guessed finish time or DNP. |
| Verified backup cutoff older than 24 hours | Alert. A new upload of an old snapshot does not reset age. |
| Verified allowance at 60%, or measured projected overflow | Warn. |
| Verified allowance at 80% | Pause optional extra season reports; preserve official evidence and required reports. |

Cloud and local work share a session advisory lock, source request spacing,
bounded request/time budgets and protected ledger commands. Recovery preserves
the original batch identity and only confirms that batch while eligible.
An assessment appends stable open, acknowledgment and resolution events. A
complete authoritative snapshot resolves conditions that cease to apply;
database failure cannot resolve them. Repeated unchanged desktop alerts are
suppressed locally. GitHub's own workflow notifications may repeat.

Database usage uses `pg_database_size`, including indexes. Registered artifact
bytes are an estimate that excludes possible orphan objects. Actual provider
object usage, account allowances and season projection remain unverified.
BACKUP-001 must supply a verified manifest and remote readback: the checker
requires the represented backup cutoff and matching manifest hash, not only a
successful upload. No real backup exists from this task.

## Commands and task definitions

Use the project environment. Do not put secrets in command arguments or XML.
`BASELINE_RUNTIME_DSN` and artifact identity credentials must be configured
privately in the environment inherited by the intended Windows login session.

```powershell
uv run --locked python -m hoop.domains.nba.watchdog --mode read-only --output artifacts/health
uv run --locked python -m scripts.windows_tasks plan --output artifacts/windows-tasks
uv run --locked python -m scripts.windows_tasks rehearse --output artifacts/windows-task-rehearsal
# Install disabled definitions after owner review; existing tasks are refused.
uv run --locked python -m scripts.windows_tasks register-disabled --output artifacts/windows-tasks
```

The persistent names are `Baseline-Watchdog` and `Baseline-LocalCollector`.
Definitions use the current user's SID, interactive login, least privilege,
`.venv/Scripts/pythonw.exe`, repository working directory, 15-minute recurrence,
start when available, no overlapping instance and a 12-minute execution limit.
Local collection runs the same `local_sources` operation and refreshes only
accepted local routes; it does not publish forecasts. Definitions are disabled
by default. No persistent task has been registered or enabled yet.

The owner must be logged in, awake and connected. Catch-up after sleep reassesses
current eligibility. These tasks do not wake the machine or change global power,
execution policy or security settings. Environment changes may require a new
login session. Verify inherited credentials without printing their values.
If definitions are later enabled, disable them with:

```powershell
Disable-ScheduledTask -TaskName Baseline-Watchdog
Disable-ScheduledTask -TaskName Baseline-LocalCollector
```

Production additionally requires all six readiness flags, the explicit production
environment setting, accepted routes, reviewed hosted migrations and
`local_fallback_enabled=true`. Desktop alerts separately require
`desktop_notifications_enabled=true`. These switches are not approved for
activation by this implementation.

## Offline behavior and actual evidence

Database/evidence failure saves a dated local UTC incident log, capped at 1 MiB
per day, and reports durable database recording as false. A bounded cached
snapshot retains its original time and age; it is never deadline authority.
No blind recovery occurs. Optional desktop notification failure is reported
without discarding the health result. Logs and XML stay in ignored artifacts.

On October 27 the actual current interactive Windows session ran disposable
`Baseline-Rehearsal-04c258af7060` at 15:04:59 UTC. Task Scheduler reported Ready
and exit 0; the matching invocation was
`98af9ae4-4843-47a8-88a0-3ca1c5e7b263`. The fixture assessment detected simulated
missing cloud work; notification queuing succeeded. The disposable task was
removed. This run used no provider access or production forecasts. The owner
reported that no desktop notification was visible. Delivery therefore failed
this drill despite successful queuing; diagnose intended-session Windows
notification behavior and repeat the delivery check before acceptance. Actual local source
upload and production recovery cannot pass until source and hosted gates pass.

[Cloud fixture run](https://github.com/Bixzare/baseline/actions/runs/40496627455)
passed both adapters: nightly produced three reports in 1.276 seconds with
188,686,336 bytes peak RSS; dispatcher produced one batch and receipt in 1.558
seconds with 181,161,984 bytes peak RSS. Each used one HTTP fixture request.
[Intentional failure drill](https://github.com/Bixzare/baseline/actions/runs/40498186657)
failed its dispatcher job as expected while nightly and normal CI passed.
The owner confirmed receipt of the GitHub failure notification. GitHub delivery
passes this manual drill; Windows desktop delivery remains failed.

These are manual fixture rehearsals. Unattended operation, actual notification
delivery, accepted sources, real backup restoration and future-slate timely
publication remain release gates. The independent recovery reliability gate is
not passed merely because XML, a task exit code or a queued notice exists.


## October 29 notification follow-up

The old helper slept for 3.5 seconds without a UI message loop. The replacement
runs a hidden WinForms application context for at most ten seconds, disposes its
tray icon/timer, and returns a bounded JSON acknowledgment. It runs in a child
process with only Windows/session path settings and the rehearsal flag; database,
provider and Auth credentials are not inherited. No Windows settings, installed
apps or persistent tasks change.

Microsoft documents the [NotifyIcon message-loop example](https://learn.microsoft.com/en-us/dotnet/api/system.windows.forms.notifyicon?view=netframework-4.8.1)
and the [BalloonTipShown event](https://learn.microsoft.com/en-us/dotnet/api/system.windows.forms.notifyicon.balloontipshown).
A shell event is separate from owner-visible delivery. Notification timing is
controlled by system settings, so the helper's lifetime is bounded independently.
See [ShowBalloonTip](https://learn.microsoft.com/en-us/dotnet/api/system.windows.forms.notifyicon.showballoontip).

The actual disposable task reported exit 0 and `shell_shown_event=true`; its exact
task was removed afterward. The report in
`docs/reports/2026-10-29-windows-notification.json` records the actual UTC check
time. On October 30 the owner confirmed that the notice was not visible, so this
delivery check failed despite the shell callback. The cause remains unresolved.
The earlier failed drill remains evidence, and production/fallback/desktop
automation remain disabled.
No current source collection, hosted recovery or production heartbeat is implied.


### Notification-state diagnosis

A read-only October 30 Shell API query returned `busy`. This describes the current
session; it does not establish the cause of the earlier missed notice. The helper
now queries [SHQueryUserNotificationState](https://learn.microsoft.com/en-us/windows/win32/api/shellapi/nf-shellapi-shqueryusernotificationstate)
before creating a notification. It defers notices while Windows reports busy,
locked/absent, full-screen, presentation, quiet-time or another blocked state.
A query failure stays unverified. Suppression is recorded separately from queuing,
so it cannot count as successful delivery or suppress a later eligible retry.

No registry, Do Not Disturb, presentation or power setting is changed. Unit tests
cover state acknowledgment and redaction; the exact native query succeeded in
the actual session. A new visible-delivery drill is pending owner readiness in an
unlocked, notification-accepting session. Production notification acceptance stays
failed until that drill is observed.
