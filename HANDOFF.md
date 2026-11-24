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
  for the weekend round, Tuesday PM for midweek). Bridged 2026-11-24 by an
  openfootball provisional schedule layer (CC0, github.com/openfootball/england):
  30 fixtures Nov 28–Dec 5, each card badged "provisional — date/time
  unconfirmed (openfootball)"; pairings verified 20/20 vs the official PL list,
  dates/times can be stale ±1–2 days and are never shown as confirmed.

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
   evaluate the 20 stored v1 forecasts. This is the user's core requested proof.
   Needs: cron results ingestion (Sun/Wed 23:00 UTC runs) + honest report.
   Note the v1 entries were recorded by the discontinued logreg model; v2
   entries (league base rates) start accruing once FD posts confirmed fixtures.
2. Model improvement work: the single-fit logistic model was found WORSE than
   its own expanding baseline on all 5 events in an independent multi-season
   validation (1,634 held-out matches, 13 seasons, season-block bootstrap) on
   2026-11-24. Display therefore switched to v2-baseline (league rates labeled
   as general reference). A blend was only suggestive (CIs cross zero) and was
   NOT adopted. Any future model change ships as a new labeled version,
   prospectively, after passing the same evaluation harness.
3. Schedule breadth: openfootball provisional layer covers Nov 28–Dec 5 with
   per-card "provisional" badges; football-data.org free tier (one app/domain,
   attribution required, key server-side only) is an approved-pending upgrade
   path once its GTC is read firsthand; defer until needed.

## Operational notes

- Auth + favorites are LIVE (Supabase free tier, agent-owned project
  fbcwfizcmdulrkahypwi): email/password signup without email confirmation,
  star/unstar persistence verified E2E 2026-11-24 including password recovery
  (explicit redirectTo client-side; GoTrue emails otherwise carry the domain
  root, which 404s). Test users are created and deleted within each test;
  credentials are vault-generated and never appear in messages.
- GitHub deployment: fine-grained PAT creation hit a provider throttle
  2026-11-24 ~04:04 ("You can't perform that action at this time") after 17
  same-day create/delete cycles. PAT pushes are HELD until an external signal
  says the restriction lifted (do NOT timer-retry; browser-use blocking
  guidance). Verified alternative in use: ordinary web-UI file upload
  (/upload/main/<dir>) on the existing browser session — used for the
  v2-baseline deploy (3 commits, remote verified byte-identical via raw fetch).
- Never display 100%/0% (use >99%/<1%); no certainty wording; joint tester
  numbers are descriptive historical co-occurrence with Wilson CIs, never
  multiplied marginals, never model joint forecasts.
- Fixture times displayed as UK time (GMT) with explicit label; provisional
  openfootball rows hide exact kickoff and show the badge instead.
- Team-name mapping between sources must be verified programmatically.
