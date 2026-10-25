# Baseline execution status

Updated October 25, 2026. Issue publication and implementation are separate.
The owner authorized sequential execution and board synchronization;
the DATA-001, DB-001 and DB-002 batch is authorized for sequential implementation.
DB-002 is prepared on DB-001 for review; hosted activation remains separate.

| Planning task | GitHub issue | Current status | Evidence / gate |
| --- | --- | --- | --- |
| BOOT-001 | [#1](https://github.com/Bixzare/baseline/issues/1) | Finished | Owner-reviewed PR #2 merged; issue closed. |
| SOURCE-001 | [#3](https://github.com/Bixzare/baseline/issues/3) | Finished | Owner merged PR #4 at bdadf7d; historical interface reviewed. Source gates remain. |
| DATA-001 | [#5](https://github.com/Bixzare/baseline/issues/5) | In progress | Candidate archive and fixture notebook; incomplete seed report awaits review. |
| DB-001 | [#6](https://github.com/Bixzare/baseline/issues/6) | In progress | Real local migrations/roles and export/restore tested; project creation and hosted verification pending. |
| DB-002 | [#7](https://github.com/Bixzare/baseline/issues/7) | Backlog | DB-001 and reviewed source evidence contracts. |
| DB-003 | [#8](https://github.com/Bixzare/baseline/issues/8) | Backlog | Accepted DATA-001 seed and private artifacts. |
| MODEL-001 | [#9](https://github.com/Bixzare/baseline/issues/9) | Backlog | Reviewed compact history interfaces. |
| LEDGER-001 | [#10](https://github.com/Bixzare/baseline/issues/10) | Backlog | DB-003 and baseline descriptors. |
| LEDGER-002 | [#11](https://github.com/Bixzare/baseline/issues/11) | Backlog | Protected ledger and baseline operations. |
| COLLECT-001 | [#12](https://github.com/Bixzare/baseline/issues/12) | Backlog | Fresh accepted sources, DB-003, LEDGER-002. |
| OUTCOME-001 | [#13](https://github.com/Bixzare/baseline/issues/13) | Backlog | Collection and protected ledger interfaces. |
| EVAL-001 | [#14](https://github.com/Bixzare/baseline/issues/14) | Backlog | Reconciled outcomes and coverage contracts. |
| OPS-001 | [#15](https://github.com/Bixzare/baseline/issues/15) | Backlog | Collection, publication, outcomes, evaluation. |
| OPS-002 | [#16](https://github.com/Bixzare/baseline/issues/16) | Backlog | Scheduled operations and actual Windows recovery evidence. |
| BACKUP-001 | [#17](https://github.com/Bixzare/baseline/issues/17) | Backlog | Persisted records/artifacts and independent sync/restore verification. |
| LAUNCH-001 | [#18](https://github.com/Bixzare/baseline/issues/18) | Backlog | All required prior tasks plus future-slate readiness. |

Finished means implemented and owner-reviewed, normally demonstrated by a merged
PR and closed issue. Passing local checks alone does not move a task to Finished.
Blocked prerequisites stay visible in the issue while its current column remains
Backlog or In progress. Preserve the board's actual column names when mapping.

The private [Baseline execution board](https://github.com/users/Bixzare/projects/1/views/2)
is linked to Bixzare/baseline. It was created after confirming there was no
existing open, closed, or repository-linked project. All sixteen issue memberships
and Status values were read back after PR #4 merged: two Finished, one In progress,
thirteen Backlog. Later batch status changes need their own readback.
The board view groups columns by Status. The repository connector supplied issue
operations; the owner's authorized GitHub CLI/Projects API supplied board operations.

SOURCE-001 PR #4 was merged by the owner. Its Linux and Windows CI jobs each
passed all 153 tests and fresh-kernel checks. Linux also passed lint, formatting,
types, boundaries, and package build. No merge, deployment, or source acceptance
is implied by CI alone. The merged historical interface enables candidate-seed work.

The original October 20 release date is past. The next milestone is readiness
for a future slate, with no backdated official forecasts. Later model, dashboard,
and awards issues are still detailed before their implementation under the
approved launch-first planning order; no empty future-scope issues are invented.
