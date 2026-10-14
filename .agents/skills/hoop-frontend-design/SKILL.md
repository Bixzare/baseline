---
name: hoop-frontend-design
description: Design or revise Baseline React/Vite dashboard screens, reusable components, chart presentation, filters, tooltips, and drilldowns. Use for the public NBA analytics interface and its desktop/mobile layout.
license: Apache-2.0; upstream terms in LICENSE.txt
---

# Baseline frontend design

Locked project adaptation of Anthropic `frontend-design`, approved October 12, 2026.
Source revision and review notes are in the repository's `skills/README.md`.

## Confirmed direction

The owner chose a clean analytics dashboard, filters/tooltips/drilldowns, and desktop analysis adapted for mobile.
The main job is to explain predictions and the evidence behind their track record.
Visual clarity, honest states, and repeatable components matter more than decoration.
The product is Baseline. Supplied SVGs are in the repository's `logos/`: `baseline-logo.svg`, `baseline-logo-reversed.svg`, `baseline-mark.svg`, and `baseline-mark-reversed.svg`.
Their brand colors are navy `#0B2D6E`, orange `#FF7A1A`, and cream `#F5F1E8`. Derive UI tokens from these and verify contrast; brand colors are not automatically suitable for small text or semantic chart states.
Use the provided assets instead of redrawing them. Use image URLs or unique clip-path IDs when embedding multiple inline SVGs.
The owner requested a TypeScript frontend with strict type checking and Tailwind CSS v4. UI fonts and the chart package remain implementation choices for the dashboard issue.
The owner confirmed shadcn/ui for core controls and tables, with free Magic UI or Aceternity components used selectively for polish. Locked ADR 0010 records this choice, incorporated into design v1.1.
Use shared Baseline tokens and only the components needed. Review copied source, licenses, dependencies, and Vite/TypeScript/Tailwind v4 compatibility. Copied components remain project-maintained code; verify focus, keyboard/touch use, reduced motion, and bundle impact. Paid templates are not authorized by this choice.

## Design process

1. Identify the view, question answered, primary comparison, available fields, and important missing-data states.
2. Inspect the existing React/Vite shell. Reuse its component system and tokens when sound; Lovable output still needs review.
3. Specify a compact layout and tokens for spacing, type hierarchy, neutral surfaces, accent, and semantic status colors.
4. Build the main information hierarchy first: prediction/result, timing and version, then context and details.
5. Inspect rendered desktop and mobile layouts, then adjust density, alignment, labels, and interaction affordances.

Prefer aligned numeric columns, readable tables, restrained chart marks, and clear section titles.
Use responsive stacking and intentional table overflow on small screens without hiding critical status or preventing navigation.
Motion should explain an interaction and respect reduced-motion preferences.
Do not invent polished live records. Fixtures and demonstrations must be visibly labeled.

## Charts and interactions

- Use lines for trends, bars/dots for comparisons, and suitable calibration/error plots when the metric calls for them.
- Label units, date window, timezone when relevant, sample size, coverage, and model/baseline identity.
- Match denominators across comparisons. Never replace missing results with zeros or smooth gaps into implied observations.
- Offer the filters required by the view, a clear reset, and a visible summary of the selection.
- Drilldowns preserve context and provide a clear route back. Do not add linked-chart brushing or a custom chart engine without scope approval.
- Tooltips supplement visible labels. Provide keyboard/touch access and an accompanying numeric summary or table.
- Color is not the only carrier of rank movement, risk, error, or health; add labels and suitable shapes/icons.

## Trust and states

Design loading, successful, empty, unavailable/error, and stale states for each data surface.
Distinguish no scheduled games, unpublished forecasts, abstentions, DNP, unresolved results, and postponed games.
Show actual publication/snapshot time and the generating model version. Explain limited samples and unknown evidence.
Track Record shows poor results as clearly as good results; Model Health cannot equate an unrun check with healthy.
Awards v1.5 displays weekly top five, movement/New entrant, and a separate eligibility watch for leading candidates at risk.
Eligibility risk and statistical rank are separate; do not imply winning probabilities or approved exceptions.

## Delivery boundaries

The dashboard is standalone, public, read-only React/Vite with TypeScript and Tailwind CSS v4, using sanctioned Supabase reads.
Do not add authentication, betting displays, training controls, live game streams, or a server framework to satisfy a design preference.
Keep private infrastructure detail out of normal fan-facing flows; expose useful technical evidence in Model Health/History.
Return screenshots at desktop/mobile sizes, interaction/state coverage, and the tradeoff behind any new dependency.
