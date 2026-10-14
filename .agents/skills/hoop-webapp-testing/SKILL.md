---
name: hoop-webapp-testing
description: Verify Baseline dashboard behavior in a browser, including filters, drilldowns, charts, responsive layouts, keyboard access, data states, and read-only Supabase access. Use for frontend feature acceptance and regressions.
license: Apache-2.0; upstream terms in LICENSE.txt
---

# Baseline web application testing

Locked project adaptation of Anthropic `webapp-testing`, approved October 12, 2026.
Source revision and review notes are in the repository's `skills/README.md`.
Use the existing dashboard test stack. Playwright is the proposed browser tool; its binding and commands must be established by the dashboard issue.

## Inspect, act, verify

1. Read `dashboard/package.json`, the lockfile, and test configuration; use the documented local server and fixture mode.
2. Use deterministic sanitized read responses. Never rely on a live NBA game to make a PR test pass.
3. Wait for the specific visible UI state or expected response; inspect the rendered page before choosing locators.
4. Prefer roles, accessible names, and stable test IDs. Exercise the same controls a user can reach.
5. Assert the resulting data, selected filters, status, and navigation context, not merely the absence of errors.
6. Capture useful screenshots and browser errors for the affected desktop and mobile states.

No mandatory network-idle wait: polling may keep requests active. Avoid fixed sleeps and use bounded, condition-based waits.
No upstream helper scripts are bundled. Use a reviewed project server lifecycle, and clean up only the processes started for the test.
Do not assume a global Python Playwright installation or install a second test stack for convenience.

## Required scenarios

- Successful, loading, empty, failed, and stale data for every affected view.
- Filter selection/reset, correct counts and metric denominators, drilldown/back navigation, and readable timezones.
- Tooltip access by keyboard or touch, visible focus, meaningful labels, status beyond color, and reduced motion.
- Mobile navigation, readable charts/tables, no clipped essential labels, and intentional table scrolling.
- A missing forecast versus abstention; confirmed DNP versus unresolved outcome; postponement versus completed result.
- Track Record and Model History values agree with the fixture evaluation report and model identity.
- Historical comparisons preserve forecast timestamps/versions and distinguish outcome revisions, unresolved results, and replay. Verify signed error as prediction minus actual and absolute error with units; winner and award displays must follow ADR 0010 rather than inventing numeric errors.
- Reads preserve public snapshot identity across a refresh. Fetching an old snapshot now must not hide its staleness.
- Model Health distinguishes a missed or unavailable check from a passing one.
- Awards views, when implemented, preserve strong candidates in the eligibility watch and handle unknown evidence honestly.

## Public boundary

Verify the browser receives only allowed public fields and contains no privileged credentials.
Prove write rejection separately using the actual anonymous database/API role against a disposable test environment.
A mocked browser response cannot prove database access control. Pair UI checks with real Postgres/API integration evidence when permissions change.
Test the last valid snapshot while collection/training is unavailable; do not imply batch refresh is in-game live tracking.

Return exact commands, browser/viewport coverage, checks passed or not run, and screenshots or failure traces that help review.
