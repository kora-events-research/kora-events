# HANDOFF — kora-events platform (2026-11-24)

Purpose: let any future agent/maintainer recover and continue this project without
the original task agent. Read this first, then README.md.

## What this is

Static site on GitHub Pages: https://kora-events-research.github.io/kora-events/
Repo (public, MIT): https://github.com/kora-events-research/kora-events
Owner identity: agent-operated GitHub account `kora-events-research`
(login in the user's Vault as an agent entry; Agent Mail 67bq5i@mail.instinct.com).
Local working copy used during development: /downloads/kora-platform (git main).

Scope: open, anonymous, bilingual (AR/EN) football match-event analytics for
research/education. No odds, no betting signals, no staking, no monetary framing.
Light theme, Cairo font, minimal UI. Premier League (E0) 2026/27 only.

## Data sources and permissions (current, verified)

- Football-Data.co.uk: results + match events CSV (E0.csv season file) and
  fixtures.csv for upcoming fixtures. Only source as of 2026-11-24.
  We publish aggregates and fixture facts, never raw per-match rows.
- ESPN public scoreboard: RETRIEVAL STOPPED 2026-11-24 (commit f6ce485).
  Disney Terms of Use (https://disneytermsofuse.com/english/ — espn.com's own
  site links to this URL as its terms of use; the ToU page expressly covers
  ESPN-branded products), prohibited-uses clause x: no accessing/copying/
  extracting via robot/script/automated means, including building datasets.
  `ESPN_ENABLED = False` in src/export_site.py. Do not re-enable without a
  licensed basis. Never read odds/pickcenter fields from any source.
- Known gap: FD fixtures.csv is posted later in the week (typically Friday PM
  for the weekend round, Tuesday PM for midweek). Between rounds the upcoming-
  fixture list is sparse (as of 2026-11-24 it shows 1 match). The Friday cron
  restores breadth automatically.

## Architecture

- src/build_db.py → football_research.db (SQLite, not published raw)
- src/features.py, src/experiment.py → team state, logistic model, time-split
  evaluation vs running-average baseline (train on first ~71, test on last 38)
- src/export_site.py → data/snapshot.json + forecast log update + evaluation
- index.html + assets/app.js → static client rendering snapshot.json
- .github/workflows/update.yml → cron Fri/Tue 17:30 UTC, Sun/Wed 23:00 UTC;
  runs export, commits data/ if changed; manual workflow_dispatch works.

## Forecast log semantics (data/forecast_log.json)

- Key: (date, home, away). First recorded pre-kickoff forecast for a key is
  never overwritten by reruns (`if key not in log`); each entry stores model
  version + data cutoff. This is append-only application behavior — NOT a
  tamper-proof guarantee (git history itself is owner-mutable).
- Reschedule handling: a rescheduled match gets a new key (new date) and a new
  forecast; the old entry stays pending forever and never joins a result.
  That is intentional (immutability) but means stale pending entries
  accumulate; a future cleanup may mark them "void — rescheduled" without
  altering their stored probabilities.
- Evaluation joins results by the same key once FD results include the match.
- 20 entries recorded 2026-11-23 from the (now discontinued) ESPN supplement
  for matches 27 Nov–3 Dec; they remain immutable and evaluable when FD posts
  results. The 21st displayed fixture was 1 segregated retrospective entry
  used to demonstrate the evaluation path (not a live forecast).
- Public timestamp evidence = git commit history of data/forecast_log.json.

## Outstanding work (priority order)

1. REAL prospective evaluation: after 27 Nov matches, FD results let the log
   evaluate the 20 stored forecasts. This is the user's core requested proof.
   Needs: cron results ingestion (Sun/Wed 23:00 UTC runs) + honest report.
2. Historical chronological-holdout backtest across past E0 seasons (train
   earlier, test later; do NOT assume more seasons improves accuracy; report
   negative results honestly). Not yet started.
3. User-approved-pending features (2026-11-24 voice note, via Main):
   historical results archive (feasible statically from FD aggregates),
   broader upcoming schedule (blocked on compliant source — see gap above),
   email/password accounts + favorites (needs a free backend — Supabase or
   Firebase free tier; signup WITHOUT email verification code is supported
   (confirm-email off); passwords hashed by provider, recovery via email
   link. REQUIRES user approval for a new external service account — not yet
   granted as of 2026-11-24).

## Operational notes

- Pushes use short-lived fine-grained PATs created in the browser, used once,
  deleted immediately; token inventory verified empty after each cycle.
- Never display 100%/0% (use >99%/<1%); no certainty wording; joint tester
  numbers are descriptive historical co-occurrence with Wilson CIs, never
  multiplied marginals, never model joint forecasts.
- Fixture times displayed as UK time (GMT) with explicit label.
- Team-name mapping between sources must be verified programmatically.
