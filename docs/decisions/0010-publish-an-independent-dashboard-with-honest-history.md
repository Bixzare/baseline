# ADR 0010: Publish an independent dashboard with honest prediction history

Status: LOCKED by the project owner on October 12, 2026.

Date: October 12, 2026

Decision basis: [PRD dashboard requirements](../PRD.md#11-public-dashboard), [design hosting and historical comparisons](../design.md#14-dashboard-hosting-and-public-data), [storage and public access](0003-store-operational-records-and-versioned-artifacts.md), and [immutable publication](0004-enforce-immutable-pregame-publication.md). This record documents approved dashboard choices; hosting, permissions, and UI behavior have not been verified.

## Context

Baseline needs a public dashboard that explains forecasts, observed accuracy, and model operations. It must remain independently deployable and useful when collection or training stops. The owner also wants a browsable history of predictions versus outcomes, with errors that have a clear meaning for each target.

Dashboard work follows Phases 0 and 1. Neither hosting nor optional UI generation may delay the launch pipeline.

## Decision

- Keep an independently built React/Vite frontend in TypeScript with strict type checking and Tailwind CSS v4 in `dashboard/`, with its own dependency lockfile. Use a clean analytics layout for desktop analysis, adapted for mobile, with filters, tooltips, and drilldowns. Use the supplied Baseline logos and verify contrast, labels, keyboard access, and indicators that do not depend only on color.
- Reuse component libraries to reduce development overhead. The owner confirmed shadcn/ui for core controls and tables, with free Magic UI or Aceternity components used selectively for visual polish. Share Baseline design tokens and avoid competing implementations of the same control. Review copied source and licenses, import only needed components, and verify each selected component with Vite, TypeScript, and Tailwind v4. Paid templates are not part of this choice. Exact package versions are pinned during frontend bootstrap.
- Use GitHub Pages for initial testing and Vercel as the planned public host, subject to deployment checks. Start with the planned $0 personal noncommercial tier only after verifying eligibility and limits. Use PR previews for review; public releases require passing CI and owner review. No paid plan is approved.
- Treat Lovable as optional initial shell generation. Verify its export workflow before use, review generated code into `dashboard/` through the issue and PR process, and do not assume synchronization with the existing repository. Generated schema changes still require migrations. A custom domain and student benefits remain optional, with expiry, renewal cost, and a replacement path recorded when adopted.
- Keep the public app read-only, without accounts or training controls. The browser uses only a publishable Supabase key with explicit read grants and RLS. Expose deliberately small public read tables; keep private schemas, privileged credentials, request logs, and mutation controls inaccessible.
- Publish complete public snapshots transactionally, with a snapshot ID, generation time, and last-success time. Views must preserve snapshot identity across related reads and avoid combining partial refreshes. Use bounded filters, pagination, navigation/manual refresh, and a short cache. Derive staleness from source and publication timestamps. An API failure displays an error or labeled last-known data.
- Deliver Tonight, Results, Track Record, Player, Model Health, and Model History as specified in the PRD. Weekly awards views and history arrive in v1.5. In-game tracking remains later scope.
- Preserve original forecast timestamps and model versions in historical comparisons, identify outcome revisions, and keep replay separate from the official live record. Show unresolved outcomes, confirmed DNPs, abstentions, postponements, invalidations, and corrections distinctly. Missing outcomes cannot become zero error.
- For numeric targets, show prediction, validated actual, signed error defined as prediction minus actual, and absolute error in the target's units. A predicted total of 224 versus 218 means +6 signed error and 6 absolute error. The requested error margin means observed error; prediction intervals remain deferred until coverage is validated.
- For game winners, show the preferred winner, probability, eventual winner, and correct/incorrect status. A 0.5 home-win probability has no preferred winner. Show Brier score and calibration with counts over matched games, rather than assigning a percentage error to an individual result.
- Preserve weekly award ladders and their leaders. After verifying official results, show the eventual winner and their saved rank using the full candidate ranking when available. Otherwise distinguish outside the published top five from unknown candidate evidence. Before verification, show awaiting award result. Store official outcome versions independently; do not rewrite earlier ladders or invent a numeric award error.
- Start without FastAPI or websocket subscriptions. Add a service later only for a concrete computation, access-control, or external-client need, using the same public read contract. Hosting does not own collection, training, or ledger writes.

## Reason and alternatives

An independent static frontend serves the batch platform without another application server to operate. Small public read tables separate display needs from privileged pipeline records. Preserved snapshots and target-specific error displays make the public track record auditable.

Reusable components reduce styling and interaction work. Copied component source still needs project maintenance and tests; adding multiple libraries can increase dependencies and produce inconsistent styling. One primary component system with selective visual additions is the chosen tradeoff.

A mandatory UI generator or hosted backend would add dependencies without improving launch readiness. A server API becomes useful when its concrete requirements justify the additional deployment and maintenance work.

## Consequences

Public snapshots duplicate a bounded amount of display data and need permission and consistency tests. Frontend availability does not establish source freshness or model health. Free hosting limits, export behavior, and deployment configuration remain verification gates; a change in purpose or capacity requires reassessment rather than an automatic paid upgrade.

## Verification required during implementation

- Verify build configuration, asset paths, direct navigation, previews, deployment, rollback, current plan limits, eligibility, and expected cost on the selected hosts.
- Verify strict TypeScript checks, Tailwind v4 integration, and selected components in the actual Vite build. Review dependencies, licenses, generated CSS and bundle size; test focus behavior, keyboard/touch use, and reduced-motion preferences. Library defaults do not replace accessibility verification.
- Test public reads under the actual anonymous role, rejected writes, private-schema isolation, and absence of privileged credentials in browser assets and public responses.
- Test complete snapshot publication and reads across a refresh, pagination and filters, and successful, loading, empty, failed, and stale UI states. An old snapshot fetched now must remain labeled stale.
- Test overestimation, underestimation, exact matches, unresolved results, DNP, corrections, winner/no-preferred-winner cases, and award winners inside/outside the top five or absent from saved candidate evidence. Earlier forecasts and weekly ladders must remain unchanged.
- Reconcile displayed metrics, filters, counts, units, timestamps, and model identities with evaluation reports. Verify desktop/mobile layouts, keyboard navigation, readable chart summaries, and accessible color use.

## Compatibility evidence and incorporation

The owner requested TypeScript, Tailwind v4, and component library reuse on October 12, 2026, then confirmed shadcn/ui as the primary system with selective Magic UI or Aceternity additions. The owner locked this record, and the frontend stack is incorporated into technical design v1.1. The stack remains subject to the implementation checks above.

Official [shadcn/ui Tailwind v4 documentation](https://ui.shadcn.com/docs/tailwind-v4) and [Vite installation guide](https://ui.shadcn.com/docs/installation/vite) document the intended integration. [Magic UI installation](https://magicui.design/docs/installation) uses the shadcn CLI. [Aceternity's component integration notes](https://ui.aceternity.com/shadcn-blocks) identify Vite adaptations that may be needed for framework-specific imports. These documents support the proposed approach; compatibility of individual selected components has not been tested. Check [Tailwind's browser compatibility guidance](https://tailwindcss.com/docs/compatibility) when defining the dashboard browser support target.

Approval: the owner explicitly said "lock" on October 12, 2026. No host has been deployed, public permissions exercised, or dashboard behavior tested by this planning record.
