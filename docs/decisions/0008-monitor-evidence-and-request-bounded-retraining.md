# ADR 0008: Monitor evidence and request bounded retraining

Status: LOCKED by the project owner on October 12, 2026.

Date: October 12, 2026

Decision basis: [PRD accuracy and drift monitoring](../PRD.md#mon-02-accuracy-and-drift-remaining-v1), [retraining requirements](../PRD.md#model-01-retraining), and [design Section 11](../design.md#11-monitoring-and-the-training-loop). This record documents approved policies; drift calibration, resource measurements, and automated training remain outstanding.

## Context

Baseline should detect source failures, distribution changes, and worsening predictions, then respond under explicit rules. A distribution change alone does not establish lost accuracy. Training requests also need valid data, available compute, and a separate promotion decision.

The owner needs local experiment comparison and a public production history without maintaining a hosted MLflow service. Automation must operate independently of notebook clicks or the local experiment UI.

## Decision

- After nightly reconciliation, produce 7-day and 30-day accuracy reports with population manifests, outcome revisions, coverage, and sample counts. Keep the official live track record separate from fixed-current-champion replay used for baseline-relative degradation checks.
- Request extra training for a component when its 30-day primary loss is greater than 1.05 times matched baseline loss, with at least 100 distinct games, on three consecutive dated daily checks. If baseline loss is zero, any positive champion loss satisfies the loss comparison. Reset the streak when the condition clears, evidence is insufficient, data validation fails, or the champion changes.
- Schedule weekly training on Monday after reconciliation when enough new valid data is available. Apply a seven-day cooldown between extra performance-triggered training starts per component. Deduplicate scheduled and extra requests for the same component/data cutoff; a scheduled run can satisfy a pending request. Prevent concurrent training for the same component.
- Respect the evaluation cutoff in [ADR 0007](0007-promote-only-chronologically-evaluated-artifacts.md). If no new valid training data precedes the current evaluation interval, record a skipped request. Training completion does not authorize activation.
- Monitor selected feature distributions, prediction distributions, missingness, and source behavior against versioned reference data. Use earlier development periods and representative stable windows to calibrate drift thresholds, then inspect shifted fixtures, false alerts, and sample sensitivity in the monitoring notebook.
- Enable drift severity alerts only after the versioned calibration report and minimum-sample policy are approved. Missing configuration or insufficient samples stays explicitly disabled or insufficient; do not invent a default threshold. Drift alone requests investigation, not retraining or promotion.
- Use Evidently for batch drift reports only after dependency and resource checks. Keep its output behind the platform monitoring interface and introduce it after launch.
- Use local MLflow with SQLite metadata and local artifacts for development comparisons. Export selected experiment configurations and metrics into the platform evidence format. Automated jobs write canonical run summaries, evaluations, model versions, and promotion decisions to Supabase, with detailed immutable report artifacts.
- Link local experiments and exported evidence through shared platform run IDs and artifact references, retaining MLflow run IDs where applicable. Production operations do not require a running local MLflow service.
- Before enabling cloud training, rehearse a complete training, evaluation, and report-upload cycle on the actual GitHub Actions runner using one candidate configuration and bounded CPU threads. Record runtime, peak memory, artifact size, storage usage, requests, and readable uploaded reports.
- Enable scheduled cloud execution only after reliable completion within available free resources. If it does not fit, reduce the workload or run the same command through Windows Task Scheduler with machine availability documented. Paid compute requires a separate owner decision.
- Log training requests, skips, failures, completions, and evaluation decisions. Invalid data blocks affected training and promotion. A failed training job leaves a healthy champion forecasting; activation remains controlled by ADR 0007.

## Reason and alternatives

Paired baseline comparisons connect extra training to observed performance on the same population. Persistence and cooldown limit repeated work, while calibrated drift diagnostics provide evidence for investigation. The resource rehearsal establishes whether the planned unattended cycle can fit the budget.

Retraining on every drift alert would spend compute without establishing that training addresses the change. Deploying after every successful training run would bypass validation. Hosting MLflow from the start would add another service to operate for a solo project. Those alternatives are not selected.

## Consequences

Three overlapping daily windows show persistence, not three independent experiments. The thresholds are starting operating policies rather than guarantees of statistical significance or weekly model improvement. An invalid source or insufficient evidence can legitimately prevent a new candidate.

Local experiment comparison and public production history have different interfaces, connected by IDs and manifests. Local automated fallback depends on an awake, connected machine. Drift thresholds and runner capacity cannot be claimed suitable until their required measurements pass. None of this work delays Phases 0 and 1.

## Verification required during implementation

- Test the strict 1.05 loss boundary, zero baseline loss, 99 versus 100 games, three distinct daily checks, every streak reset, and separation of mixed-version live results from fixed-champion replay.
- Test weekly and extra requests, cooldown boundaries, duplicate/concurrent requests, no new eligible data, invalid sources, skipped or failed training, and successful training without activation.
- Exercise stable and shifted distributions, missingness, small samples, disabled configuration, calibration evidence, and drift signals that cannot independently start training.
- Reproduce reports from their population/outcome manifests and trace exported local experiments to canonical run records and artifact identities.
- Rehearse the complete cycle on the chosen runner, including report upload/readback and failure recovery. Verify a failed candidate run preserves the active champion and publication path.

Approval: the owner explicitly said "lock" on October 12, 2026. No monitoring thresholds have been calibrated, cloud training enabled, or autonomous cycle verified by this record.
