# Baseline execution status

Updated October 27, 2026. The owner approved/merged PRs #22, #23 and #24.
Only #22 reached main because the later PRs merged into their original stacked
bases. Integration PR #25 carries the already approved model/ledger changes to
main. The next assigned batch is LEDGER-002, COLLECT-001 and OUTCOME-001, reviewed
in that order. No hosted activation or real source acceptance is implied.

| Planning task | GitHub issue | Current status | Evidence / gate |
| --- | --- | --- | --- |
| BOOT-001 | [#1](https://github.com/Bixzare/baseline/issues/1) | Finished | Owner-reviewed PR #2 merged; issue closed. |
| SOURCE-001 | [#3](https://github.com/Bixzare/baseline/issues/3) | Finished | Owner merged PR #4; operational source gates remain. |
| DATA-001 | [#5](https://github.com/Bixzare/baseline/issues/5) | Finished | Owner merged PR #19, including #20/#21, into main on October 26; seed acceptance is separate. |
| DB-001 | [#6](https://github.com/Bixzare/baseline/issues/6) | In progress | Code in main and owner-approved; dedicated project and actual restricted/TLS checks pending. |
| DB-002 | [#7](https://github.com/Bixzare/baseline/issues/7) | In progress | Code in main and owner-approved; actual Auth/Storage permission checks remain gates. |
| DB-003 | [#8](https://github.com/Bixzare/baseline/issues/8) | In progress | History schemas, dry planner and fixture import; real seed and hosted gates remain blocked. |
| MODEL-001 | [#9](https://github.com/Bixzare/baseline/issues/9) | In progress | Minutes/rate preparation, full saved-roster cohort and snapshots tested on fixtures; actual input gates remain. |
| LEDGER-001 | [#10](https://github.com/Bixzare/baseline/issues/10) | In progress | Schema/role/bootstrap and concurrent-slot tests on real Postgres; hosted registration and actual publication remain gated. |
| LEDGER-002 | [#11](https://github.com/Bixzare/baseline/issues/11) | In progress | Protected SQL/client and disposable rehearsal implemented; hosted and operational gates remain. |
| COLLECT-001 | [#12](https://github.com/Bixzare/baseline/issues/12) | In progress | Fixture-tested shared collector, work lists and occurrence recovery; actual source routing remains blocked. |
| OUTCOME-001 | [#13](https://github.com/Bixzare/baseline/issues/13) | Backlog | Collection and protected ledger interfaces. |
| EVAL-001 | [#14](https://github.com/Bixzare/baseline/issues/14) | Backlog | Reconciled outcomes and coverage contracts. |
| OPS-001 | [#15](https://github.com/Bixzare/baseline/issues/15) | Backlog | Collection, publication, outcomes, evaluation. |
| OPS-002 | [#16](https://github.com/Bixzare/baseline/issues/16) | Backlog | Scheduled operations and actual Windows recovery evidence. |
| BACKUP-001 | [#17](https://github.com/Bixzare/baseline/issues/17) | Backlog | Persisted records/artifacts and independent sync/restore verification. |
| LAUNCH-001 | [#18](https://github.com/Bixzare/baseline/issues/18) | Backlog | All required prior tasks plus future-slate readiness. |

Finished means implemented and owner-reviewed, normally demonstrated by a merged
PR and closed issue. Passing local checks alone does not move a task to Finished.
DB-001 and DB-002 remain open until their required hosted acceptance checks pass,
even if the local implementation PRs are merged first.
Blocked prerequisites stay visible in the issue while its current column remains
Backlog or In progress. Preserve the board's actual column names when mapping.

The private [Baseline execution board](https://github.com/users/Bixzare/projects/1/views/2)
is linked to Bixzare/baseline. It was created after confirming there was no
existing open, closed, or repository-linked project. All sixteen issue memberships
and Status values are three Finished, seven In progress and six Backlog, read
back October 27. Finished still requires owner review; hosted gates
cannot be waived by moving a board card.
The board view groups columns by Status. The repository connector supplied issue
operations; the owner's authorized GitHub CLI/Projects API supplied board operations.

SOURCE-001 PR #4 was merged by the owner at `bdadf7d`. Its Linux and Windows CI jobs each
passed all 153 tests and fresh-kernel checks. Linux also passed lint, formatting,
types, boundaries, and package build. No merge, deployment, or source acceptance
is implied by CI alone. Its reviewed historical interface enables candidate work.

The original October 20 release date is past. The next milestone is readiness
for a future slate, with no backdated official forecasts. Later model, dashboard,
and awards issues are still detailed before their implementation under the
approved launch-first planning order; no empty future-scope issues are invented.
