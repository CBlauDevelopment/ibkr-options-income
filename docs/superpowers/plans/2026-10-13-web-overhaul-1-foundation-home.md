# Web Overhaul, Part 1: Foundation, Shell and Home — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task (native execution, chosen by the operator 2026-10-13). The plan is split into five sections; every section opens with **entry checks** that must all pass before its first task starts. Each section carries a **model label** (sonnet / opus) so an orchestrator that delegates a section to a subagent knows which model to spawn. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Replace the web console's dark Spotify-style world with the "payslip" design system
(light default, dark toggle, follow-OS option), regroup navigation into Home / Trades / Portfolio /
Activity / Research / News / More, and ship the new Home page: strategy switcher, scrubbable
account-value hero, collapsible monthly pay stub, positions with status words, and proposal cards
with Claude's reasoning collapsible above the stub.

**Architecture:** The semantic token names every component already uses (`bg-surface`,
`text-content`, …) are re-pointed to the new palette, so the whole app reskins in Task 1 and stays
usable while pages are recomposed. New code lives in `web/components/ui/` (data-free primitives),
`web/components/shell/` (rail, tab bar, bot card) and `web/features/home/` (data-fetching Home
pieces). Three read-only backend additions feed Home: `GET /portfolio/value`, `GET /pnl/month`
and `GET /spreads/positions`, each a thin route over a pure builder in `src/reporting/` or a
read-only SQLite engine, inside every existing fence.

**Tech Stack:** Next.js 15 App Router, React 19, Tailwind CSS v4, @tanstack/react-query,
lightweight-charts 4, lucide-react (new), Vitest + Testing Library; FastAPI, SQLAlchemy, pytest.

**Spec:** `web/DESIGN.md` (design system, status draft; the authority for every visual value).
The direction mockups live outside the repo; `web/DESIGN.md` § Surfaces → Home is the contract.

## Execution model

| Section | Tasks | Model | Why this model |
|---|---|---|---|
| **A — Foundation** | 1–4 | **sonnet** | New, self-contained files with every line of code given; low judgment, high volume. |
| **B — Navigation and shell** | 5–6 | **opus** | Moves live pages, rewrites links across existing files, relocates the halt / resume / autonomy controls (safety friction) and edits legacy tests: needs judgment about code the plan only describes. |
| **C — Read-only APIs** | 7–9 | **opus** | Python across four fences (web, spreads, news, reporting tier), config loading, schemas, New York month boundaries, and the regenerated OpenAPI contract. A subtle mistake here is a fence break or a wrong money figure. |
| **D — Home page** | 10–13 | **sonnet** | Fully specified components and tests against interfaces Sections A and C already pinned. |
| **E — Assembly, docs and finish** | 14 | **opus** | Visual review against DESIGN.md, the doc sweep across six files, the `next build` gate and the design ratification: judgment over the whole branch. |

**How a section runs (native):**

1. Run that section's **entry checks** (below each section heading), in order.
2. **Any check fails → stop.** Report what failed with its output, and do not start the section's
   first task. A failure that belongs to the previous section is fixed there (reopen its last
   task, record the ruling) before re-running the checks.
3. **All checks pass →** record a row for them in the Progress log ("Section X entry", gate
   result, date) and start the first task. No operator confirmation is needed between green
   sections.
4. An orchestrator delegating instead of running natively spawns one subagent per section on
   the labelled model, hands it this plan plus `web/DESIGN.md`, and runs the next section's
   entry checks itself before spawning the next subagent.

## Progress log

| Section / task | Status | Commits | Gate | Date | Rulings |
|---|---|---|---|---|---|
| **A entry checks** (baseline) | done | main a731d59 | pytest 3520+1 skip, vitest 496, tsc/lint/ruff/mypy green | 2026-10-13 | tsc baseline had 9 test-file errors; fixed first in 6273d87 on main at operator's choice |
| 1 Tokens, fonts, theme | done | 323cd4f | vitest 508 (496+12), tsc 0, lint clean | 2026-10-13 | web/CLAUDE.md: also removed stale "Dark-only in P1." sentence and changed "focus is blue" to "focus is ink" (both contradicted the new invariants; plan listed only the bullets) |
| 2 Primitives A | done | f7ccc23 | vitest 519 (508+11), tsc 0, lint clean | 2026-10-13 | none |
| 3 Primitives B | done | 93c7814 | vitest 532 (519+13), tsc 0, lint clean | 2026-10-13 | `useFocusTrap` reads `onEscape` through a ref (plan listed it in the effect deps, so a parent re-rendering with an inline onClose, as polling Home will, re-ran the effect and pulled focus to the Close button); +1 test (RED then GREEN). The plan's "11 tests" is 12 from its own code, 13 with the ruling's test. Sheet shadow `rgba(0,0,0,0.18)` kept as written (DESIGN.md allows one ambient sheet shadow) |
| 4 Strategy filter | done | 5b165f8 | vitest 542 (532+10), tsc 0, lint clean; after the review fix pass vitest 548, tsc 0, lint clean | 2026-10-13 | none for the task itself (the brief's "11 tests" is 10 from its own code). **Section A review fix pass (I1 `useThemePref` hydration mismatch, I2 follow-OS listener moved into `THEME_INIT_SCRIPT`, I3 focusable `Sheet` panel): one extra commit `fix(web): theme hydration, follow-OS app-wide, sheet keys when focus is on body` after Task 4, so every later entry-check commit count on this branch shifts by +1 (B1 expects five commits on `main..HEAD`, not four).** |
| **B entry checks** | done | main..HEAD = 5 (323cd4f f7ccc23 93c7814 5b165f8 f1e5a67) | vitest 548, tsc/lint green, B3-B6 pass | 2026-10-13 | B1 counts five commits, not four (Section A's review fix pass, f1e5a67) |
| 5 Routes and redirects | done | 8fab3c3 | vitest 552 (548+4), tsc 0, lint clean | 2026-10-13 | Step 5 link rewrite touched navigation links only: `app/trades/[approvalId]/page.tsx`, `components/options/{ApprovalCard,ApprovalDetail,AssessedRow,ShortsRow}.tsx`, `components/shell/RailSection.tsx`; tests `components/options/AssessedRow.test.tsx` (1 href) and `ShortsTable.test.tsx` (2 hrefs). The grep's other hits are API paths (`apiFetch("/options/...")`, `/pnl/...`, `/universe`, `lib/api-types.ts`, `lib/commands.ts`) and code comments; they stay, since rewriting them would break the API calls. More test fixture uses `rows: []` (SystemStatusCard's real body), as Step 1 directs |
| 6 Shell | done | 429511f; Section B review fix pass in one extra commit after it | vitest 565 (552+4 nav+10 shell+1 More-2 ControlsStrip; Rail's 3 replaced 3), tsc 0, lint clean; after the review fix pass vitest 571 (565+6), tsc 0, lint clean, scratch-copy `next build` green; `next build` green (15 routes); real browser: 307s, five pages render, halt / RESUME / rung change from the bot sheet against a mock API | 2026-10-13 | `HaltedBanner` also says "No new orders will be queued or transmitted; profit-take closes still run": Step 1's copied ControlsStrip wording assertion failed against the plan's banner (RED then GREEN). `ControlsStrip.test.tsx`: dropped the `halted-banner` null check and the two banner tests (the null-time case is now `shell.test` "omits the time"; the banner omits the time instead of saying "unknown time", and `HaltControl` still says it). `text-on-flag` on sunk measured 6.95/10.17 (hover 6.19/8.90): kept. Build gate run in a scratch copy of `web/` (node_modules symlinked) because the operator's own `next dev` on :3000 shares `web/.next`. HaltControl, AutonomyControl, ConfirmAction and DecideControls (via ApprovalCard.test) tests unchanged and green. **Section B review fix pass (one extra commit `fix(web): scope halt copy to the wheel, drain warning in the sheet, dialog keys over the sheet, Universe and Ledger links`), so the later entry-check commit counts shift by a further +1: C1 expects 8 commits on `main..HEAD`, D1 11, E1 15.** I1: the plan's banner text "Trading is halted" is amended to "Wheel trading is halted" plus "No new CSP or covered-call orders will be queued or sent. Credit spreads have their own halt and are not stopped by this one." (the profit-take clause is dropped); the bot card's halted state reads "Wheel halted · paper" (the web halt is the wheel's `system_settings` switch; the spreads service honours only its own halt file). I2: the plan's `BotSheet` code is amended to render the "not draining" warning above the controls, through `DrainWarning`, now exported from `ControlsStrip.tsx` and shared by both surfaces. I3: `useFocusTrap` hands Escape (unstopped) and Tab (into the nested dialog) to a nested `[role=dialog]` while one is open, even with focus on the panel. I4: More also links Universe (`/research/universe`) and Ledger (`/ledger`) |
| **C entry checks** | done | main..HEAD = 8 (323cd4f f7ccc23 93c7814 5b165f8 f1e5a67 8fab3c3 429511f d055ef4) | pytest 3520+1 skip, vitest 571, tsc/lint/ruff/mypy green, build green, fences 50, C1-C5 pass | 2026-10-14 | C1 counts eight commits, not six (Section A and Section B review fix passes, +2); C2's `next build` ran in a scratch copy of `web/` (the operator's `next dev` shares `web/.next`) |
| 7 Account value API | done | 375242b | pytest 3532 (3520+12) + 1 skip, ruff/mypy clean, fences 50, OpenAPI regenerated, vitest 571, tsc 0, lint clean | 2026-10-14 | `latest` is the newest snapshot unless the journal holds a close from a later New York day (the plan took any snapshot first, so a monitor stopped for days made today's change = stale snapshot minus yesterday's close); compared by ET day, not timestamp, so a same-day close plotted at 16:00 ET cannot beat a live snapshot (and the route test cannot flake on a UTC+8 machine); +2 builder tests (8, not 6). Route parameter is `Annotated[AccountValueRange, Query(alias="range")] = "1m"` (ruff B008; same OpenAPI). Module docstring avoids the literal `src.claude` (the reporting fence greps raw text) |
| 8 Spreads read API | done | b3bcc5c | pytest 3539 (3532+7) + 1 skip, ruff/mypy clean, fences 51 (50+1), OpenAPI regenerated, vitest 571, tsc 0, lint clean | 2026-10-14 | The open probe is `SELECT count(*) FROM sqlite_master`, not `SELECT 1` (which never reads the file, so a non-SQLite `spreads.db` answered `available: true` with an empty book), and a failed probe closes its session. `read_spread_rows` types its `text()` select (`expiry` Date, `opened_at`/`closed_at` DateTime): raw SQL returned strings, so the router's `as_utc` branch never ran and timestamps left the API without an offset. +2 tests (6, not 4), each RED against the plan's code first |
| 9 Monthly pay API | done | b124c2f; Section C review fix pass in one extra commit after it | pytest 3556 (3539+17) + 1 skip, ruff/mypy clean, fences 51, OpenAPI regenerated, vitest 571, tsc 0, lint clean; D4's field list matches Task 10's `types.ts` | 2026-10-14 | An expired or assigned leg closes on its `expiry` date in the month buckets (`build_legs` stamps those as naive midnight on the expiry date, which read as UTC fell on the previous ET day, so a May 1 expiry counted in April); +1 builder test (10, not 9). `pay.py` docstring avoids the literal `src.claude` (the reporting fence greps raw text). Route tests: an autouse fixture keeps them off the operator's real `data/spreads.db` (the plan's `strategy=all` tests read it), the `seed_leg` test asks for the month its naive-local fill lands in (UTC+8 flake from 04:00 to 12:00 local on each 1st), and +3 tests (7, not 4): only the book's own spreads count, the target is `web.monthly_income_target_pct` of the month-start value, and the setting's 0 < x <= 20 bound **Section C review fix pass (one extra commit, so `main..HEAD` after it is 13 with the orchestrator's 020f00d: D1 expects 13, not 11): pytest 3572 + 1 skip (3556 + 17 new - 1 superseded), ruff/mypy clean, fences 51, OpenAPI regenerated, vitest 571, tsc 0, lint clean.** C1: `previous_close` is the close before the New York day `latest` belongs to, and `change_today`/`change_today_pct` are null unless that day is today (weekends, before the day's first snapshot); the stale-snapshot test's pinned 0.0 corrected. I3+I4: a journal close competes with the snapshot as an instant, and only once its 16:00 ET is at or before `now`; a row whose close is still ahead is not a close at all (not plotted, not `previous_close`); 1d/1w also end on `latest` after the close; the route test freezes the route's clock. I5: a net liquidation of 0 or less is unknown (never a point, `latest`, `previous_close` or month-start value); the newest snapshot with a known value is searched among the last 50. I1: `PnlLeg.open_commissions` (additive, the SELL fills' commissions) and pay charges each side in the month it was paid; `fill_economics`, `classify_outcome`, the reconciler and every existing `PnlLeg` value unchanged; two Task 9 tests that pinned the double count corrected. I2: `MonthPayResponse.spreads_available` (false only when a spreads book is in scope and `data/spreads.db` could not be read, absent included); Task 10 `types.ts`, the Task 11 PayCard sentence and the Task 11/14 fixtures amended to match |
| **D entry checks** | not started | | | | |
| 10 Home hero | not started | | | | |
| 11 Pay card | not started | | | | |
| 12 Positions card | not started | | | | |
| 13 Proposals and review sheet | not started | | | | |
| **E entry checks** | not started | | | | |
| 14 Home assembly, docs, finish | not started | | | | |

## Roadmap (this plan is Part 1 of 4)

Each later part is written as its own plan when the previous part merges, against the code as it
then stands. They are listed so this part's structure does not paint them into a corner.

- **Part 2 — Trades.** `/trades` recomposed: strategy switcher, Proposals / Working / Decided /
  Assessed / Spreads segments, proposal cards at full width (reusing Task 13's `ProposalCard` and
  `ReviewSheet`), the spreads menu-and-pick view over a second read-only `/spreads/*` route, and
  "Propose a roll" moved onto position rows. Legacy `components/options/*` styles migrated.
- **Part 3 — Portfolio and Activity.** Positions / Campaigns / Expiry calendar on the new rows;
  Activity becomes Pay (P&L summary + equity) / Ledger / Fills and orders / System; ledger tables
  in the figure face.
- **Part 4 — Research, News, More and cleanup.** Research, stock page, Universe, News and Explain
  restyled; legacy `components/<domain>` folders folded into `features/`; the unused `GET /nav`
  route removed with its test.

## Global Constraints

- Every colour comes from a semantic token; never a raw palette class (`bg-white`, `bg-gray-800`)
  or a hex literal in a component. Canvas charts read tokens from CSS custom properties at mount.
- Light is the default theme; dark and "follow OS" are user choices persisted in `localStorage`
  key `ibkr-theme`; first paint must already be in the chosen theme (no flash).
- Fonts: Hanken Grotesk (400, 500, 600, 700, 800, 900) for everything; Red Hat Mono (400, 500,
  600) for stub and ledger figures. No IBM Plex.
- Lime (`primary`, `#a6eb6e`) only on primary actions, the pending-count badge, the pay meter
  fill and the "Expires today" status word.
- Unknown values render `n/a` with the `.hatch` texture, never `$0`, `0%` or a blank. A genuine
  zero renders `$0`.
- No state by colour alone: signed money carries `+`/`−`, flags carry a word, selected carries an
  ink fill (never lime or green).
- Charts never animate their data in. Only touched things move (MOTION 2): chevron 180ms,
  sheet 240ms in, button press scale 0.98; all removed under `prefers-reduced-motion`.
- No shadow anywhere except the review sheet (and the existing confirm dialog).
- Zero em dashes in UI copy; banned words: "seamless", "robust", "unlock", "elevate".
- Safety friction unchanged: every order intent still goes through `DecideControls` →
  `ConfirmAction`; halt stays one tap; resume still needs the typed word RESUME; the second LIVE
  confirmation stays.
- Old URLs keep working: `/options`, `/options/:id`, `/pnl`, `/universe` redirect (307).
- Backend: the API writes nothing new (still exactly one table, `app_commands`); nothing under
  `src/api/` imports `src.spreads`; nothing under `src/reporting/` imports `src.claude` or
  `src.api`; engine / execution / strategies import none of the new modules.
- Quality gate after every task: `cd web && npx vitest run && npx tsc --noEmit && npm run lint`;
  for backend tasks also `python -m pytest -q && ruff check . && mypy src` from the repo root.

- UI work goes through the da-vinci skill (operator, 2026-10-14): Section D's subagent invokes
  `da-vinci` before writing any UI code, and Task 14 Step 5a runs da-vinci `critique` and `audit`
  over the surfaces Sections A and B built before it was in the loop. da-vinci never changes the
  design system (colour, font, radius, elevation) without the operator, and never ratifies
  `web/DESIGN.md` before Task 14 Step 7.

## Review Focus

1. **Theme on first paint.** A stored `dark` (or `system` on a dark OS) preference must paint dark
   before React hydrates, and a `localStorage` that throws must fall back to light, not crash →
   Task 1 tests `THEME_INIT_SCRIPT` under all three cases.
2. **Dialog inside a sheet.** Approve opens `ConfirmAction` *inside* the review sheet; Escape or
   Tab inside that dialog must not close or escape the sheet → Task 3 test
   "a nested dialog keeps its own keys".
3. **Unknown inputs in money math.** A null premium, no income target, or no month-start value
   must give `n/a` lines and "No target set", never `$0` or `0%` → Task 9 builder tests and Task 11
   / Task 13 component tests.
4. **Month boundaries in New York time.** A leg opened 2026-10-31 22:00 ET (02:00 UTC on Nov 1)
   belongs to October's pay → Task 9 test `test_month_is_new_york_time`.
5. **Spreads database absent or unreadable.** A fresh install with no `data/spreads.db` must answer
   `available: false` and Home must still render its other cards → Task 8 test and Task 12 test
   "renders option rows when spreads are unavailable".
6. **A junk `?strategy=` value** (`?strategy=foo`) shows All, never an empty page → Task 4 test.

---

## File structure

```
web/
  app/
    globals.css                     MODIFY  payslip tokens, light + dark, sheet keyframe
    layout.tsx                      MODIFY  fonts, no-flash theme script, shell
    page.tsx                        MODIFY  Task 5: re-export research; Task 14: Home
    page.test.tsx                   MOVE→   app/research/page.test.tsx (Task 5), new Home test (14)
    research/page.tsx               CREATE  (moved from app/page.tsx)
    research/universe/page.tsx      CREATE  (moved from app/universe/page.tsx)
    trades/page.tsx                 CREATE  (moved from app/options/page.tsx)
    trades/page.test.tsx            CREATE  (moved from app/options/page.test.tsx)
    trades/[approvalId]/page.tsx    CREATE  (moved from app/options/[approvalId]/page.tsx)
    activity/page.tsx               CREATE  (moved from app/pnl/page.tsx)
    more/page.tsx                   CREATE  theme, system status, links
  next.config.ts                    MODIFY  redirects
  next.config.test.ts               CREATE
  components/ui/                    CREATE  Button, Card, SegmentedControl, StatusWord, Meter,
                                            Disclosure, Stub, Sheet (+ tests)
  components/shell/                 MODIFY  Rail (rewrite), TabBar, BotCard, BotSheet,
                                            HaltedBanner, ThemeToggle (new)
  features/home/                    CREATE  types, AccountHero, HeroChart, hero.ts, PayCard,
                                            PositionsCard, positions.ts, ProposalCard,
                                            proposal.ts, WhyDisclosure, ReviewSheet, NeedsYou,
                                            ProposalsBanner, HomePage (+ tests)
  lib/theme.ts, lib/useThemePref.ts CREATE
  lib/useFocusTrap.ts               CREATE
  lib/strategy.ts, lib/useStrategyFilter.ts  CREATE
  lib/nav.ts                        CREATE
  CLAUDE.md, DESIGN.md              MODIFY
src/
  common/config.py                  MODIFY  WebCfg (monthly_income_target_pct)
  common/schemas.py                 MODIFY  AccountValuePoint, AccountValueSeries, MonthPay
  reporting/account_value.py        CREATE  account_value_series, month_start_value
  reporting/pay.py                  CREATE  SpreadPayInput, build_month_pay
  api/spreads_db.py                 CREATE  read-only engine over data/spreads.db
  api/models/spreads.py             CREATE
  api/models/portfolio.py           MODIFY  AccountValueResponse
  api/models/pnl.py                 MODIFY  MonthPayResponse
  api/routers/spreads.py            CREATE  GET /spreads/positions
  api/routers/portfolio.py          MODIFY  GET /portfolio/value
  api/routers/pnl.py                MODIFY  GET /pnl/month
  api/main.py                       MODIFY  include spreads router
config/examples/settings.yaml       MODIFY  web.monthly_income_target_pct
tests/test_reporting_account_value.py, tests/test_api_portfolio_value.py,
tests/test_api_spreads.py, tests/test_reporting_pay.py, tests/test_api_pnl_month.py  CREATE
docs/web/openapi.json, docs/web/api.md, ARCHITECTURE.md, STATUS.md, CLAUDE.md  MODIFY
```

---

## Section A — Foundation (Tasks 1–4) · model: sonnet

Tokens, fonts and the theme switch, the eight UI primitives, and the strategy filter. Every file
is new except `globals.css`, `layout.tsx` and `web/CLAUDE.md`; nothing here fetches data.

**Entry checks (the baseline; run from the repo root on `main` before Task 1 Step 1):**

- [x] **A1. Clean starting point.** `git status --short` shows nothing except the two untracked
  files this plan's Task 1 commits (`web/DESIGN.md`, this plan file) and, optionally,
  `web/design-preview.html`. `git branch --show-current` prints `main`.
- [x] **A2. Baseline is green.** All of these pass; record the pytest and vitest test counts in the
  Progress log row, because every later gate compares against them:

  ```bash
  python -m pytest -q && ruff check . && mypy src
  cd web && npx vitest run && npx tsc --noEmit && npm run lint && cd ..
  ```

  A red baseline is not this plan's to fix: stop and report it.
- [x] **A3. The spec is valid.** `python3 ~/.claude/skills/da-vinci/scripts/design_md_check.py web/DESIGN.md`
  exits 0.
- [x] **A4. Dependencies resolve.** `cd web && npm ls next react lightweight-charts @tanstack/react-query clsx`
  prints versions with no `missing` or `invalid`.

**Section exit:** four commits on `feat/web-overhaul-1`, Tasks 1–4 ticked in the Progress log.

---

### Task 1: Payslip tokens, fonts and the theme switch

**Files:**
- Modify: `web/app/globals.css` (whole file)
- Modify: `web/app/layout.tsx`
- Create: `web/lib/theme.ts`, `web/lib/theme.test.ts`
- Create: `web/lib/useThemePref.ts`, `web/lib/useThemePref.test.tsx`
- Create: `web/app/globals.test.ts`
- Modify: `web/CLAUDE.md` (Invariants section), `web/package.json` (lucide-react)

**Interfaces:**
- Produces: `ThemePref = "light" | "dark" | "system"`, `THEME_STORAGE_KEY`, `parsePref`,
  `resolveTheme`, `applyTheme`, `THEME_INIT_SCRIPT` (lib/theme.ts); `useThemePref(): [ThemePref,
  (p: ThemePref) => void]` (lib/useThemePref.ts). Tailwind colour utilities: `background surface
  elevated sunk sunk-deep content muted border control perforation gain loss unknown focus scrim
  primary primary-deep on-primary flag on-flag`. CSS var `--chart-line` for canvas charts.

- [x] **Step 1: Branch and worktree**

Run from the repo root:

```bash
git switch -c feat/web-overhaul-1
```

If executing in a separate worktree (superpowers:using-git-worktrees), symlink the main `.venv`
and `web/node_modules` into it and run `python -c "from src.storage.db import init_db; init_db()"`
(memory: a fresh worktree otherwise fails four monitor tests with "no such table: fills").

- [x] **Step 2: Install lucide-react**

```bash
cd web && npm install lucide-react@0.468.0
```

Expected: `package.json` gains `"lucide-react": "^0.468.0"` under dependencies.

- [x] **Step 3: Write the failing tests for the theme library**

`web/lib/theme.test.ts`:

```ts
import { afterEach, describe, expect, it, vi } from "vitest";
import {
  THEME_INIT_SCRIPT,
  THEME_STORAGE_KEY,
  applyTheme,
  parsePref,
  resolveTheme,
} from "./theme";

function runInitScript() {
  // The script is shipped as a string into <head>; run it the same way the browser does.
  new Function(THEME_INIT_SCRIPT)();
}

function stubSystemDark(dark: boolean) {
  vi.stubGlobal("matchMedia", (q: string) => ({
    matches: dark && q === "(prefers-color-scheme: dark)",
    media: q,
    addEventListener: () => {},
    removeEventListener: () => {},
  }));
}

afterEach(() => {
  vi.unstubAllGlobals();
  delete document.documentElement.dataset.theme;
  delete document.documentElement.dataset.themePref;
});

describe("parsePref", () => {
  it("defaults anything unknown to light", () => {
    expect(parsePref(null)).toBe("light");
    expect(parsePref("purple")).toBe("light");
  });
  it("keeps the three real values", () => {
    expect(parsePref("light")).toBe("light");
    expect(parsePref("dark")).toBe("dark");
    expect(parsePref("system")).toBe("system");
  });
});

describe("resolveTheme", () => {
  it("follows the OS only for system", () => {
    expect(resolveTheme("system", true)).toBe("dark");
    expect(resolveTheme("system", false)).toBe("light");
    expect(resolveTheme("light", true)).toBe("light");
    expect(resolveTheme("dark", false)).toBe("dark");
  });
});

describe("THEME_INIT_SCRIPT", () => {
  it("paints light when nothing is stored", () => {
    stubSystemDark(true);
    runInitScript();
    expect(document.documentElement.dataset.theme).toBe("light");
  });
  it("paints dark when dark is stored", () => {
    localStorage.setItem(THEME_STORAGE_KEY, "dark");
    runInitScript();
    expect(document.documentElement.dataset.theme).toBe("dark");
  });
  it("paints dark for system on a dark OS", () => {
    stubSystemDark(true);
    localStorage.setItem(THEME_STORAGE_KEY, "system");
    runInitScript();
    expect(document.documentElement.dataset.theme).toBe("dark");
    expect(document.documentElement.dataset.themePref).toBe("system");
  });
  it("falls back to light when storage throws", () => {
    vi.spyOn(Storage.prototype, "getItem").mockImplementation(() => {
      throw new Error("blocked");
    });
    runInitScript();
    expect(document.documentElement.dataset.theme).toBe("light");
  });
});

describe("applyTheme", () => {
  it("writes the resolved theme and the preference onto <html>", () => {
    stubSystemDark(false);
    expect(applyTheme("system")).toBe("light");
    expect(document.documentElement.dataset.theme).toBe("light");
    expect(document.documentElement.dataset.themePref).toBe("system");
  });
});
```

`web/app/globals.test.ts` (pins that every light token has a dark twin):

```ts
import { readFileSync } from "node:fs";
import { resolve } from "node:path";
import { describe, expect, it } from "vitest";

const css = readFileSync(resolve(__dirname, "globals.css"), "utf8");

function block(selector: string): string {
  const start = css.indexOf(`${selector} {`);
  expect(start, `missing ${selector} block`).toBeGreaterThanOrEqual(0);
  return css.slice(start, css.indexOf("}", start));
}

function names(src: string): string[] {
  return [...src.matchAll(/(--[a-z0-9-]+)\s*:/g)].map((m) => m[1]).sort();
}

describe("globals.css theme tokens", () => {
  it("defines every light token again for dark", () => {
    expect(names(block(':root[data-theme="dark"]'))).toEqual(names(block(":root")));
  });
  it("keeps the semantic names components already use", () => {
    const light = names(block(":root"));
    for (const n of [
      "--bg-background",
      "--bg-surface",
      "--bg-elevated",
      "--text-content",
      "--text-muted",
      "--border-border",
      "--color-gain",
      "--color-loss",
      "--color-unknown",
      "--color-focus",
      "--color-scrim",
    ]) {
      expect(light).toContain(n);
    }
  });
});
```

- [x] **Step 4: Run them to verify they fail**

Run: `cd web && npx vitest run lib/theme.test.ts app/globals.test.ts`
Expected: FAIL (`./theme` not found; no `:root[data-theme="dark"]` block).

- [x] **Step 5: Write `web/lib/theme.ts`**

```ts
/**
 * Theme preference: light is the default, dark and "follow the OS" are choices.
 * The resolved theme lands on <html data-theme>, which globals.css keys every token off.
 * Every storage access is wrapped: a private window or blocked storage falls back to
 * light rather than breaking the page.
 */
export type ThemePref = "light" | "dark" | "system";
export type ResolvedTheme = "light" | "dark";

export const THEME_STORAGE_KEY = "ibkr-theme";

export function parsePref(raw: string | null | undefined): ThemePref {
  return raw === "dark" || raw === "system" || raw === "light" ? raw : "light";
}

export function resolveTheme(pref: ThemePref, systemDark: boolean): ResolvedTheme {
  if (pref === "system") return systemDark ? "dark" : "light";
  return pref;
}

export function readPref(): ThemePref {
  try {
    return parsePref(localStorage.getItem(THEME_STORAGE_KEY));
  } catch {
    return "light";
  }
}

export function writePref(pref: ThemePref): void {
  try {
    localStorage.setItem(THEME_STORAGE_KEY, pref);
  } catch {
    // Storage blocked: the choice still applies for this page view.
  }
}

export function systemPrefersDark(): boolean {
  try {
    return window.matchMedia("(prefers-color-scheme: dark)").matches;
  } catch {
    return false;
  }
}

export function applyTheme(pref: ThemePref): ResolvedTheme {
  const resolved = resolveTheme(pref, systemPrefersDark());
  document.documentElement.dataset.theme = resolved;
  document.documentElement.dataset.themePref = pref;
  return resolved;
}

/**
 * Runs in <head> before first paint so a dark preference never flashes light.
 * Kept as a string because it must execute before React; mirrors parsePref/resolveTheme.
 */
export const THEME_INIT_SCRIPT = `(function(){try{var p=localStorage.getItem("${THEME_STORAGE_KEY}");if(p!=="dark"&&p!=="system")p="light";var d=p==="dark"||(p==="system"&&window.matchMedia("(prefers-color-scheme: dark)").matches);document.documentElement.dataset.theme=d?"dark":"light";document.documentElement.dataset.themePref=p;}catch(e){document.documentElement.dataset.theme="light";}})();`;
```

- [x] **Step 6: Rewrite `web/app/globals.css`**

```css
@import "tailwindcss";

/*
  The payslip world (web/DESIGN.md). Light is the default; [data-theme="dark"] is the
  user's choice (set before first paint by THEME_INIT_SCRIPT in lib/theme.ts).
  Components consume colour ONLY through the semantic utilities below - never a raw
  palette class or a hex literal. The old names (background/surface/elevated/content/
  muted/border/gain/loss/unknown/focus/scrim) are kept and re-pointed, so every legacy
  component reskins without an edit.
*/
:root {
  color-scheme: light;
  --bg-background: #f2f4ef; /* sage paper: the page */
  --bg-surface: #ffffff; /* card white */
  --bg-elevated: #e6eadf; /* pressed sage: fills inside a card ("sunk") */
  --bg-sunk-deep: #d9ded3; /* hover on a sunk fill */

  --text-content: #111410; /* ink */
  --text-muted: #575d55; /* muted ink */

  --border-border: #dce0d7; /* hairline: decorative only */
  --border-control: #7a8276; /* input and checkbox edges (3:1+) */
  --color-perforation: #c9cfc2; /* the dashed rule that opens every stub */

  --color-gain: #187a42;
  --color-loss: #c8322f;
  --color-unknown: #6e7569;
  /* Focus is ink, never lime or green, so "selected" can never read as "up". */
  --color-focus: #111410;
  --color-scrim: rgba(0, 0, 0, 0.5);

  --color-primary: #a6eb6e; /* lime: primary actions only */
  --color-primary-deep: #8fdb55;
  --color-on-primary: #111410;
  --color-flag: #fff1d6; /* warning fill: "Assignment likely" */
  --color-on-flag: #6b4500;

  --chart-line: #111410;
}

:root[data-theme="dark"] {
  color-scheme: dark;
  --bg-background: #0f110f;
  --bg-surface: #191c19;
  --bg-elevated: #232723;
  --bg-sunk-deep: #2c312c;

  --text-content: #eef1eb;
  --text-muted: #a3aa9f;

  --border-border: #262a26;
  --border-control: #7d8579;
  --color-perforation: #3a4038;

  --color-gain: #5bd58a;
  --color-loss: #ff7468;
  --color-unknown: #8a9286;
  --color-focus: #eef1eb;
  --color-scrim: rgba(0, 0, 0, 0.6);

  --color-primary: #a6eb6e;
  --color-primary-deep: #8fdb55;
  --color-on-primary: #0f110f;
  --color-flag: #3a2e12;
  --color-on-flag: #f5cf7a;

  --chart-line: #eef1eb;
}

@theme inline {
  --color-background: var(--bg-background);
  --color-surface: var(--bg-surface);
  --color-elevated: var(--bg-elevated);
  --color-sunk: var(--bg-elevated);
  --color-sunk-deep: var(--bg-sunk-deep);
  --color-content: var(--text-content);
  --color-muted: var(--text-muted);
  --color-border: var(--border-border);
  --color-control: var(--border-control);
  --color-perforation: var(--color-perforation);
  --color-gain: var(--color-gain);
  --color-loss: var(--color-loss);
  --color-unknown: var(--color-unknown);
  --color-focus: var(--color-focus);
  --color-scrim: var(--color-scrim);
  --color-primary: var(--color-primary);
  --color-primary-deep: var(--color-primary-deep);
  --color-on-primary: var(--color-on-primary);
  --color-flag: var(--color-flag);
  --color-on-flag: var(--color-on-flag);

  --font-sans: var(--font-sans), system-ui, sans-serif;
  --font-mono: var(--font-mono), ui-monospace, monospace;
}

html,
body {
  background: var(--bg-background);
  color: var(--text-content);
}

/* Numbers align in columns like a ledger. Hanken Grotesk's default figures are already
   tabular; this keeps the guarantee for the mono face and any fallback. */
.tabular {
  font-variant-numeric: tabular-nums;
  font-feature-settings: "tnum" 1;
}

/* The unknown state carries texture as well as colour, so it never reads as a zero
   and never depends on colour alone. */
.hatch {
  background-image: repeating-linear-gradient(
    45deg,
    var(--color-unknown) 0 1px,
    transparent 1px 5px
  );
}

::selection {
  background: var(--color-primary);
  color: var(--color-on-primary);
}

:focus-visible {
  outline: 2px solid var(--color-focus);
  outline-offset: 3px;
}

@media (prefers-reduced-motion: reduce) {
  *,
  *::before,
  *::after {
    animation-duration: 0.01ms !important;
    animation-iteration-count: 1 !important;
    transition-duration: 0.01ms !important;
  }
}

/* Dialog / receipt entry: a short opacity step-in (unchanged from P2). */
@keyframes receipt-entry {
  from {
    opacity: 0;
  }
  to {
    opacity: 1;
  }
}

.animate-receipt-entry {
  animation: receipt-entry 0.15s ease-out;
}
```

- [x] **Step 7: Update `web/app/layout.tsx`**

```tsx
import type { Metadata } from "next";
import { Hanken_Grotesk, Red_Hat_Mono } from "next/font/google";
import "./globals.css";
import { Rail } from "@/components/shell/Rail";
import { Providers } from "@/app/providers";
import { THEME_INIT_SCRIPT } from "@/lib/theme";

const sans = Hanken_Grotesk({
  subsets: ["latin"],
  weight: ["400", "500", "600", "700", "800", "900"],
  variable: "--font-sans",
});

const mono = Red_Hat_Mono({
  subsets: ["latin"],
  weight: ["400", "500", "600"],
  variable: "--font-mono",
});

export const metadata: Metadata = {
  title: "IBKR Income",
  description: "Options income console",
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    // data-theme is set by THEME_INIT_SCRIPT before paint; suppressHydrationWarning
    // because the server always renders "light" and the script may have changed it.
    <html
      lang="en"
      data-theme="light"
      className={`${sans.variable} ${mono.variable}`}
      suppressHydrationWarning
    >
      <head>
        <script dangerouslySetInnerHTML={{ __html: THEME_INIT_SCRIPT }} />
      </head>
      <body
        className="bg-background text-content font-sans antialiased"
        suppressHydrationWarning
      >
        <Providers>
          <div className="flex h-screen overflow-hidden">
            <Rail />
            <main className="flex-1 overflow-y-auto overflow-x-hidden">{children}</main>
          </div>
        </Providers>
      </body>
    </html>
  );
}
```

- [x] **Step 8: Write the hook test, then the hook**

`web/lib/useThemePref.test.tsx`:

```tsx
import { act, renderHook } from "@testing-library/react";
import { afterEach, describe, expect, it } from "vitest";
import { THEME_STORAGE_KEY } from "./theme";
import { useThemePref } from "./useThemePref";

afterEach(() => {
  delete document.documentElement.dataset.theme;
});

describe("useThemePref", () => {
  it("starts from the stored preference", () => {
    localStorage.setItem(THEME_STORAGE_KEY, "dark");
    const { result } = renderHook(() => useThemePref());
    expect(result.current[0]).toBe("dark");
  });
  it("persists and applies a new choice", () => {
    const { result } = renderHook(() => useThemePref());
    act(() => result.current[1]("dark"));
    expect(localStorage.getItem(THEME_STORAGE_KEY)).toBe("dark");
    expect(document.documentElement.dataset.theme).toBe("dark");
    expect(result.current[0]).toBe("dark");
  });
});
```

`web/lib/useThemePref.ts`:

```ts
"use client";

import { useCallback, useEffect, useState } from "react";
import { type ThemePref, applyTheme, readPref, writePref } from "./theme";

/**
 * The current theme preference and a setter that persists and applies it. While the
 * preference is "system", an OS switch (e.g. sunset on the phone) re-applies live.
 */
export function useThemePref(): [ThemePref, (p: ThemePref) => void] {
  const [pref, setPrefState] = useState<ThemePref>(() =>
    typeof window === "undefined" ? "light" : readPref(),
  );

  useEffect(() => {
    if (pref !== "system") return;
    let mq: MediaQueryList;
    try {
      mq = window.matchMedia("(prefers-color-scheme: dark)");
    } catch {
      return;
    }
    const onChange = () => applyTheme("system");
    mq.addEventListener("change", onChange);
    return () => mq.removeEventListener("change", onChange);
  }, [pref]);

  const setPref = useCallback((p: ThemePref) => {
    writePref(p);
    applyTheme(p);
    setPrefState(p);
  }, []);

  return [pref, setPref];
}
```

- [x] **Step 9: Run the tests and the full web suite**

Run: `cd web && npx vitest run`
Expected: the new tests PASS. Existing tests that assert on legacy class names still pass (names
were kept). Any test asserting the old IBM Plex font or a removed CSS rule fails: fix the
assertion to the new world and record each such edit as a ruling in the Progress log.

- [x] **Step 10: Update `web/CLAUDE.md` Invariants**

Replace the first and third bullets of `## Invariants`, and add two:

```markdown
- **Light by default, dark by choice.** `data-theme` on `<html>` is set before paint by
  `THEME_INIT_SCRIPT` (`lib/theme.ts`); the preference (light / dark / system) lives in
  `localStorage` key `ibkr-theme`. `web/DESIGN.md` is the visual authority.
- **Hanken Grotesk** for everything; **Red Hat Mono** for stub and ledger figures. Apply
  `.tabular` to every numeric column so figures align.
- **Lime means act.** `bg-primary` only on primary actions, the pending-count badge, the pay
  meter and the "Expires today" status word.
- **No shadows** except the review sheet and the confirm dialog; elevation is tonal
  (`background` → `surface` → `sunk`).
```

Also in the same section, change "the dark token system in `app/globals.css`" in the opening
paragraph to "the token system in `app/globals.css`".

- [x] **Step 11: Gate and commit**

```bash
cd web && npx vitest run && npx tsc --noEmit && npm run lint
cd .. && git add web/app/globals.css web/app/globals.test.ts web/app/layout.tsx web/lib/theme.ts \
  web/lib/theme.test.ts web/lib/useThemePref.ts web/lib/useThemePref.test.tsx web/CLAUDE.md \
  web/DESIGN.md web/package.json web/package-lock.json \
  docs/superpowers/plans/2026-10-13-web-overhaul-1-foundation-home.md
git commit -m "feat(web): payslip tokens, Hanken Grotesk, light default with dark and system themes"
```

---

### Task 2: Primitives A — Button, Card, SegmentedControl, StatusWord, Meter

**Files:**
- Create: `web/components/ui/Button.tsx`, `Card.tsx`, `SegmentedControl.tsx`, `StatusWord.tsx`,
  `Meter.tsx`, and `web/components/ui/primitives-a.test.tsx`

**Interfaces:**
- Consumes: Task 1 colour utilities.
- Produces:
  - `Button(props: ButtonHTMLAttributes & { variant?: "primary" | "secondary" | "quiet"; block?: boolean })`
  - `Card(props: HTMLAttributes<HTMLElement> & { as?: "section" | "div" | "article" | "aside" })`
  - `SegmentedControl<T extends string>({ label, options, value, onChange, appearance })` where
    `options: { value: T; label: string; count?: number | null }[]`,
    `appearance?: "track" | "chips" | "quiet"` (default `"track"`)
  - `StatusWord({ tone?: "neutral" | "flag" | "today"; children })`
  - `Meter({ value: number | null; max: number | null; label: string })`

- [x] **Step 1: Write the failing tests** — `web/components/ui/primitives-a.test.tsx`

```tsx
import { fireEvent, render, screen } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";
import { Button } from "./Button";
import { Card } from "./Card";
import { Meter } from "./Meter";
import { SegmentedControl } from "./SegmentedControl";
import { StatusWord } from "./StatusWord";

describe("Button", () => {
  it("defaults to type=button so it never submits a form by accident", () => {
    render(<Button>Review</Button>);
    expect(screen.getByRole("button", { name: "Review" })).toHaveAttribute("type", "button");
  });
  it("marks its variant and fires onClick", () => {
    const onClick = vi.fn();
    render(
      <Button variant="primary" onClick={onClick}>
        Review
      </Button>,
    );
    const b = screen.getByRole("button", { name: "Review" });
    expect(b).toHaveAttribute("data-variant", "primary");
    fireEvent.click(b);
    expect(onClick).toHaveBeenCalledOnce();
  });
  it("does not fire when disabled", () => {
    const onClick = vi.fn();
    render(
      <Button variant="primary" disabled onClick={onClick}>
        Review
      </Button>,
    );
    fireEvent.click(screen.getByRole("button", { name: "Review" }));
    expect(onClick).not.toHaveBeenCalled();
  });
});

describe("Card", () => {
  it("renders as a section by default and as the requested element otherwise", () => {
    const { container, rerender } = render(<Card>pay</Card>);
    expect(container.firstElementChild?.tagName).toBe("SECTION");
    rerender(<Card as="aside">pay</Card>);
    expect(container.firstElementChild?.tagName).toBe("ASIDE");
  });
});

describe("SegmentedControl", () => {
  const options = [
    { value: "all", label: "All" },
    { value: "csp", label: "CSPs", count: 3 },
    { value: "cc", label: "CCs", count: 0 },
    { value: "spread", label: "Credit spreads", count: null },
  ] as const;

  it("is a labelled group whose selected button is aria-pressed", () => {
    render(
      <SegmentedControl label="Strategy" options={[...options]} value="csp" onChange={() => {}} />,
    );
    expect(screen.getByRole("group", { name: "Strategy" })).toBeInTheDocument();
    expect(screen.getByRole("button", { name: /CSPs/ })).toHaveAttribute("aria-pressed", "true");
    expect(screen.getByRole("button", { name: "All" })).toHaveAttribute("aria-pressed", "false");
  });
  it("shows a real zero count but no count at all when it is unknown", () => {
    render(
      <SegmentedControl label="Strategy" options={[...options]} value="all" onChange={() => {}} />,
    );
    expect(screen.getByRole("button", { name: "CCs 0" })).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Credit spreads" })).toBeInTheDocument();
  });
  it("calls onChange with the option value", () => {
    const onChange = vi.fn();
    render(<SegmentedControl label="Strategy" options={[...options]} value="all" onChange={onChange} />);
    fireEvent.click(screen.getByRole("button", { name: /CSPs/ }));
    expect(onChange).toHaveBeenCalledWith("csp");
  });
});

describe("StatusWord", () => {
  it("carries its tone as data so the word, not the colour, is the signal", () => {
    render(<StatusWord tone="flag">Assignment likely</StatusWord>);
    expect(screen.getByText("Assignment likely")).toHaveAttribute("data-tone", "flag");
  });
});

describe("Meter", () => {
  it("reports progress as a percentage", () => {
    render(<Meter value={1413.6} max={2000} label="October target" />);
    const m = screen.getByRole("progressbar", { name: "October target" });
    expect(m).toHaveAttribute("aria-valuenow", "71");
    expect(m).toHaveAttribute("aria-valuetext", "71%");
  });
  it("caps at 100 and floors at 0", () => {
    const { rerender } = render(<Meter value={5000} max={2000} label="t" />);
    expect(screen.getByRole("progressbar")).toHaveAttribute("aria-valuenow", "100");
    rerender(<Meter value={-50} max={2000} label="t" />);
    expect(screen.getByRole("progressbar")).toHaveAttribute("aria-valuenow", "0");
  });
  it("is hatched and says n/a when there is no target", () => {
    render(<Meter value={300} max={null} label="t" />);
    const m = screen.getByRole("progressbar");
    expect(m).not.toHaveAttribute("aria-valuenow");
    expect(m).toHaveAttribute("aria-valuetext", "n/a");
    expect(m.className).toContain("hatch");
  });
});
```

- [x] **Step 2: Run to verify failure**

Run: `cd web && npx vitest run components/ui/primitives-a.test.tsx`
Expected: FAIL (modules not found).

- [x] **Step 3: Implement the five primitives**

`web/components/ui/Button.tsx`:

```tsx
import clsx from "clsx";
import { forwardRef, type ButtonHTMLAttributes } from "react";

export type ButtonVariant = "primary" | "secondary" | "quiet";

export type ButtonProps = ButtonHTMLAttributes<HTMLButtonElement> & {
  variant?: ButtonVariant;
  block?: boolean;
};

const VARIANT: Record<ButtonVariant, string> = {
  // Lime means act: only the primary variant may carry it.
  primary: "bg-primary text-on-primary enabled:hover:bg-primary-deep",
  secondary: "bg-sunk text-content enabled:hover:bg-sunk-deep",
  quiet: "bg-transparent text-content enabled:hover:bg-sunk",
};

export const Button = forwardRef<HTMLButtonElement, ButtonProps>(function Button(
  { variant = "secondary", block = false, className, type = "button", ...rest },
  ref,
) {
  return (
    <button
      ref={ref}
      type={type}
      data-variant={variant}
      className={clsx(
        "inline-flex min-h-11 items-center justify-center gap-2 rounded-full px-[18px]",
        "text-[0.9375rem] font-bold transition-transform duration-[90ms] enabled:active:scale-[0.98]",
        "disabled:cursor-default disabled:bg-sunk disabled:text-muted",
        VARIANT[variant],
        block && "w-full",
        className,
      )}
      {...rest}
    />
  );
});
```

`web/components/ui/Card.tsx`:

```tsx
import clsx from "clsx";
import type { HTMLAttributes } from "react";

type CardElement = "section" | "div" | "article" | "aside";

export function Card({
  as: Tag = "section",
  className,
  ...rest
}: HTMLAttributes<HTMLElement> & { as?: CardElement }) {
  // Tonal elevation: white on sage paper, no border, no shadow (DESIGN.md Elevation).
  return <Tag className={clsx("rounded-[18px] bg-surface px-4 py-4 sm:px-[18px]", className)} {...rest} />;
}
```

`web/components/ui/SegmentedControl.tsx`:

```tsx
import clsx from "clsx";

export type SegmentOption<T extends string> = {
  value: T;
  label: string;
  /** null/undefined hides the count; 0 is a real count and shows. */
  count?: number | null;
};

type Appearance = "track" | "chips" | "quiet";

const TRACK: Record<Appearance, string> = {
  track: "rounded-full bg-surface p-1",
  chips: "",
  quiet: "",
};

const BUTTON: Record<Appearance, string> = {
  track: "px-3.5 py-[7px] text-[0.84375rem]",
  chips: "px-[11px] py-1 text-xs",
  quiet: "px-[11px] py-1 text-xs",
};

const UNSELECTED: Record<Appearance, string> = {
  track: "text-muted hover:text-content",
  chips: "bg-sunk text-muted hover:text-content",
  quiet: "text-muted hover:text-content",
};

export function SegmentedControl<T extends string>({
  label,
  options,
  value,
  onChange,
  appearance = "track",
  className,
}: {
  label: string;
  options: SegmentOption<T>[];
  value: T;
  onChange: (value: T) => void;
  appearance?: Appearance;
  className?: string;
}) {
  return (
    <div
      role="group"
      aria-label={label}
      className={clsx("inline-flex max-w-full flex-wrap gap-1.5", TRACK[appearance], className)}
    >
      {options.map((o) => {
        const on = o.value === value;
        return (
          <button
            key={o.value}
            type="button"
            aria-pressed={on}
            onClick={() => onChange(o.value)}
            className={clsx(
              "rounded-full font-semibold",
              BUTTON[appearance],
              // Selected is an ink fill - never lime, never green - so it cannot read as "up".
              on ? "bg-content text-background" : UNSELECTED[appearance],
            )}
          >
            {o.label}
            {o.count !== null && o.count !== undefined && (
              <span className="ml-1 font-medium opacity-75"> {o.count}</span>
            )}
          </button>
        );
      })}
    </div>
  );
}
```

(The accessible name of a button with a count is "CSPs 3": the space inside the count span keeps
the label and number apart for screen readers and for `getByRole({ name })`.)

`web/components/ui/StatusWord.tsx`:

```tsx
import clsx from "clsx";
import type { ReactNode } from "react";

export type StatusTone = "neutral" | "flag" | "today";

const TONE: Record<StatusTone, string> = {
  neutral: "bg-sunk text-muted",
  flag: "bg-flag text-on-flag",
  today: "bg-primary text-on-primary",
};

export function StatusWord({ tone = "neutral", children }: { tone?: StatusTone; children: ReactNode }) {
  return (
    <span
      data-tone={tone}
      className={clsx(
        "inline-block whitespace-nowrap rounded-[6px] px-2 py-px text-xs font-bold tracking-[0.02em]",
        TONE[tone],
      )}
    >
      {children}
    </span>
  );
}
```

`web/components/ui/Meter.tsx`:

```tsx
import clsx from "clsx";
import { UNKNOWN } from "@/lib/format";

export function Meter({ value, max, label }: { value: number | null; max: number | null; label: string }) {
  const known = value !== null && max !== null && max > 0;
  const pct = known ? Math.max(0, Math.min(100, (value / max) * 100)) : null;
  return (
    <div
      role="progressbar"
      aria-label={label}
      aria-valuemin={0}
      aria-valuemax={100}
      aria-valuenow={pct === null ? undefined : Math.round(pct)}
      aria-valuetext={pct === null ? UNKNOWN : `${Math.round(pct)}%`}
      className={clsx("h-2 overflow-hidden rounded-full bg-sunk", pct === null && "hatch")}
    >
      {pct !== null && <div className="h-full rounded-full bg-primary" style={{ width: `${pct}%` }} />}
    </div>
  );
}
```

- [x] **Step 4: Run tests to verify they pass**

Run: `cd web && npx vitest run components/ui/primitives-a.test.tsx`
Expected: PASS (11 tests).

- [x] **Step 5: Gate and commit**

```bash
cd web && npx vitest run && npx tsc --noEmit && npm run lint
cd .. && git add web/components/ui
git commit -m "feat(web): ui primitives - Button, Card, SegmentedControl, StatusWord, Meter"
```

---

### Task 3: Primitives B — Disclosure, Stub, Sheet (with a focus trap that respects nested dialogs)

**Files:**
- Create: `web/components/ui/Disclosure.tsx`, `Stub.tsx`, `Sheet.tsx`
- Create: `web/lib/useFocusTrap.ts`
- Create: `web/components/ui/primitives-b.test.tsx`
- Modify: `web/app/globals.css` (append the sheet keyframe)

**Interfaces:**
- Consumes: `Button` (Task 2), `UNKNOWN` (`lib/format.ts`), `formatMoneyCell` (`lib/money.ts`).
- Produces:
  - `Disclosure({ summary: ReactNode; children: ReactNode; defaultOpen?: boolean; tone?: "sunk" | "plain" })`
  - `type StubLineData = { label: string; value: number | null; format?: "money" | "signed-money" | "percent"; explain?: string; total?: boolean }`
  - `Stub({ lines: StubLineData[]; label: string })`, `formatStubValue(v, format)`
  - `useFocusTrap(ref: RefObject<HTMLElement | null>, active: boolean, onEscape: () => void)`
  - `Sheet({ open: boolean; onClose: () => void; title: string; children: ReactNode })`

- [x] **Step 1: Write the failing tests** — `web/components/ui/primitives-b.test.tsx`

```tsx
import { fireEvent, render, screen } from "@testing-library/react";
import { useState } from "react";
import { describe, expect, it, vi } from "vitest";
import { Disclosure } from "./Disclosure";
import { Sheet } from "./Sheet";
import { Stub, formatStubValue } from "./Stub";

describe("Disclosure", () => {
  it("starts closed, opens and closes on its button", () => {
    render(<Disclosure summary="Why this trade">IV rank 62</Disclosure>);
    const btn = screen.getByRole("button", { name: /Why this trade/ });
    expect(btn).toHaveAttribute("aria-expanded", "false");
    expect(screen.getByText("IV rank 62")).not.toBeVisible();
    fireEvent.click(btn);
    expect(btn).toHaveAttribute("aria-expanded", "true");
    expect(screen.getByText("IV rank 62")).toBeVisible();
  });
  it("can start open", () => {
    render(
      <Disclosure summary="October pay" defaultOpen>
        stub
      </Disclosure>,
    );
    expect(screen.getByRole("button", { name: /October pay/ })).toHaveAttribute("aria-expanded", "true");
  });
});

describe("formatStubValue", () => {
  it("never turns unknown into zero", () => {
    expect(formatStubValue(null, "money")).toBe("n/a");
    expect(formatStubValue(Number.NaN, "percent")).toBe("n/a");
  });
  it("formats signed money with a real minus sign", () => {
    expect(formatStubValue(235, "signed-money")).toBe("+$235.00");
    expect(formatStubValue(-1.3, "signed-money")).toBe("−$1.30");
    expect(formatStubValue(0, "signed-money")).toBe("$0");
  });
  it("formats percent to two places", () => {
    expect(formatStubValue(12.2, "percent")).toBe("12.20%");
  });
});

describe("Stub", () => {
  const lines = [
    { label: "Premium", value: 235, format: "signed-money" as const, explain: "1 contract × $2.35 × 100 shares." },
    { label: "Cash held aside", value: null },
    { label: "A year", value: 12.2, format: "percent" as const, total: true },
  ];
  it("is a labelled group of lines", () => {
    render(<Stub label="AAPL put math" lines={lines} />);
    expect(screen.getByRole("group", { name: "AAPL put math" })).toBeInTheDocument();
    expect(screen.getByText("+$235.00")).toBeInTheDocument();
    expect(screen.getByText("12.20%")).toBeInTheDocument();
  });
  it("hatches an unknown value", () => {
    render(<Stub label="m" lines={lines} />);
    expect(screen.getByText("n/a").className).toContain("hatch");
  });
  it("explains a line in one sentence when tapped", () => {
    render(<Stub label="m" lines={lines} />);
    const line = screen.getByRole("button", { name: /Premium/ });
    expect(line).toHaveAttribute("aria-expanded", "false");
    fireEvent.click(line);
    expect(screen.getByText("1 contract × $2.35 × 100 shares.")).toBeVisible();
  });
});

function SheetHarness({ onClose }: { onClose: () => void }) {
  const [nested, setNested] = useState(false);
  return (
    <Sheet open onClose={onClose} title="Review trade">
      <button type="button">First</button>
      <button type="button" onClick={() => setNested(true)}>
        Approve
      </button>
      {nested && (
        <div role="dialog" aria-modal="true" aria-label="Confirm">
          <button type="button" onClick={() => setNested(false)}>
            Cancel
          </button>
        </div>
      )}
    </Sheet>
  );
}

describe("Sheet", () => {
  it("is a labelled modal dialog that closes on Escape and on the scrim", () => {
    const onClose = vi.fn();
    render(<SheetHarness onClose={onClose} />);
    expect(screen.getByRole("dialog", { name: "Review trade" })).toHaveAttribute("aria-modal", "true");
    fireEvent.keyDown(screen.getByRole("dialog", { name: "Review trade" }), { key: "Escape" });
    expect(onClose).toHaveBeenCalledTimes(1);
    fireEvent.click(screen.getByTestId("sheet-scrim"));
    expect(onClose).toHaveBeenCalledTimes(2);
  });
  it("moves focus inside on open", () => {
    render(<SheetHarness onClose={() => {}} />);
    expect(screen.getByRole("dialog", { name: "Review trade" })).toContainElement(
      document.activeElement as HTMLElement,
    );
  });
  it("a nested dialog keeps its own keys", () => {
    const onClose = vi.fn();
    render(<SheetHarness onClose={onClose} />);
    fireEvent.click(screen.getByRole("button", { name: "Approve" }));
    const cancel = screen.getByRole("button", { name: "Cancel" });
    cancel.focus();
    fireEvent.keyDown(cancel, { key: "Escape" });
    fireEvent.keyDown(cancel, { key: "Tab" });
    expect(onClose).not.toHaveBeenCalled();
    expect(document.activeElement).toBe(cancel);
  });
  it("renders nothing when closed", () => {
    render(
      <Sheet open={false} onClose={() => {}} title="Review trade">
        x
      </Sheet>,
    );
    expect(screen.queryByRole("dialog")).toBeNull();
  });
});
```

- [x] **Step 2: Run to verify failure**

Run: `cd web && npx vitest run components/ui/primitives-b.test.tsx`
Expected: FAIL (modules not found).

- [x] **Step 3: Implement**

`web/components/ui/Disclosure.tsx`:

```tsx
"use client";

import clsx from "clsx";
import { ChevronDown } from "lucide-react";
import { useId, useState, type ReactNode } from "react";

export function Disclosure({
  summary,
  children,
  defaultOpen = false,
  tone = "sunk",
}: {
  summary: ReactNode;
  children: ReactNode;
  defaultOpen?: boolean;
  tone?: "sunk" | "plain";
}) {
  const [open, setOpen] = useState(defaultOpen);
  const panelId = useId();
  return (
    <div className={clsx("rounded-xl", tone === "sunk" && "bg-sunk px-3 py-2.5")}>
      <button
        type="button"
        aria-expanded={open}
        aria-controls={panelId}
        onClick={() => setOpen((o) => !o)}
        className="flex w-full items-center justify-between gap-2.5 text-left"
      >
        <span className="min-w-0 flex-1">{summary}</span>
        <span
          aria-hidden="true"
          className={clsx(
            "grid h-[22px] w-[22px] flex-none place-items-center rounded-full",
            "transition-transform duration-[180ms] ease-out motion-reduce:transition-none",
            tone === "sunk" ? "bg-surface" : "bg-sunk",
            open && "rotate-180",
          )}
        >
          <ChevronDown size={14} strokeWidth={2.25} />
        </span>
      </button>
      {/* The panel appears in place: no height animation (DESIGN.md Motion). */}
      <div id={panelId} hidden={!open} className="pt-2">
        {children}
      </div>
    </div>
  );
}
```

`web/components/ui/Stub.tsx`:

```tsx
"use client";

import clsx from "clsx";
import { useState } from "react";
import { UNKNOWN } from "@/lib/format";
import { formatMoneyCell } from "@/lib/money";

export type StubFormat = "money" | "signed-money" | "percent";

export type StubLineData = {
  label: string;
  value: number | null;
  format?: StubFormat;
  /** One sentence; when present the line becomes a button that reveals it. */
  explain?: string;
  /** The sum line: hairline above, bold. */
  total?: boolean;
};

const MINUS = "−";

export function formatStubValue(value: number | null, format: StubFormat = "money"): string {
  if (value === null || Number.isNaN(value)) return UNKNOWN;
  if (format === "percent") return `${value.toFixed(2)}%`;
  if (format === "signed-money") {
    if (value === 0) return "$0";
    return `${value > 0 ? "+" : MINUS}${formatMoneyCell(Math.abs(value))}`;
  }
  return formatMoneyCell(value);
}

function StubLine({ line }: { line: StubLineData }) {
  const [open, setOpen] = useState(false);
  const unknown = line.value === null || Number.isNaN(line.value);
  const row = (
    <>
      <span>{line.label}</span>
      <span className={clsx(unknown && "hatch text-unknown")}>{formatStubValue(line.value, line.format)}</span>
    </>
  );
  const rowClass = clsx(
    "flex w-full justify-between gap-2.5 text-left",
    line.total && "mt-1 border-t border-border pt-1.5 font-semibold",
  );
  if (!line.explain) return <div className={rowClass}>{row}</div>;
  return (
    <div>
      <button type="button" aria-expanded={open} onClick={() => setOpen((o) => !o)} className={rowClass}>
        {row}
      </button>
      <p hidden={!open} className="pb-1 pt-0.5 font-sans text-xs text-muted">
        {line.explain}
      </p>
    </div>
  );
}

/** The payslip signature: a perforation, then a short line-by-line sum. */
export function Stub({ lines, label }: { lines: StubLineData[]; label: string }) {
  return (
    <div
      role="group"
      aria-label={label}
      className="tabular mt-3 grid gap-0.5 border-t-2 border-dashed border-perforation pt-2.5 font-mono text-[0.84375rem]"
    >
      {lines.map((l) => (
        <StubLine key={l.label} line={l} />
      ))}
    </div>
  );
}
```

`web/lib/useFocusTrap.ts`:

```ts
"use client";

import { useEffect, type RefObject } from "react";

const FOCUSABLE =
  'a[href], button:not([disabled]), input:not([disabled]), select:not([disabled]), textarea:not([disabled]), [tabindex]:not([tabindex="-1"])';

/**
 * Traps Tab inside `ref`, calls onEscape on Escape, focuses the first control on
 * activation and returns focus to the previous element on deactivation.
 *
 * Keys pressed inside a NESTED dialog (e.g. ConfirmAction opened from inside a sheet) are
 * left to that dialog: the listener is on the container itself and ignores any event whose
 * nearest [role="dialog"] is not this container.
 */
export function useFocusTrap(
  ref: RefObject<HTMLElement | null>,
  active: boolean,
  onEscape: () => void,
): void {
  useEffect(() => {
    const el = ref.current;
    if (!active || !el) return;
    const previous = document.activeElement;
    el.querySelector<HTMLElement>(FOCUSABLE)?.focus();

    function onKeyDown(e: KeyboardEvent) {
      const target = e.target as Element | null;
      if (target?.closest('[role="dialog"]') !== el) return;
      if (e.key === "Escape") {
        e.stopPropagation();
        onEscape();
        return;
      }
      if (e.key !== "Tab" || !el) return;
      const items = Array.from(el.querySelectorAll<HTMLElement>(FOCUSABLE)).filter(
        (n) => n.closest('[role="dialog"]') === el,
      );
      if (items.length === 0) return;
      const first = items[0];
      const last = items[items.length - 1];
      if (e.shiftKey && document.activeElement === first) {
        e.preventDefault();
        last.focus();
      } else if (!e.shiftKey && document.activeElement === last) {
        e.preventDefault();
        first.focus();
      }
    }

    el.addEventListener("keydown", onKeyDown);
    return () => {
      el.removeEventListener("keydown", onKeyDown);
      if (previous instanceof HTMLElement) previous.focus();
    };
  }, [ref, active, onEscape]);
}
```

`web/components/ui/Sheet.tsx`:

```tsx
"use client";

import { X } from "lucide-react";
import { useId, useRef, type ReactNode } from "react";
import { useFocusTrap } from "@/lib/useFocusTrap";
import { Button } from "./Button";

/**
 * Bottom sheet on phones, right-side sheet from 640px. The only element besides the
 * confirm dialog allowed a shadow (DESIGN.md Elevation & Depth).
 */
export function Sheet({
  open,
  onClose,
  title,
  children,
}: {
  open: boolean;
  onClose: () => void;
  title: string;
  children: ReactNode;
}) {
  const panelRef = useRef<HTMLDivElement>(null);
  const titleId = useId();
  useFocusTrap(panelRef, open, onClose);
  if (!open) return null;
  return (
    <div className="fixed inset-0 z-50 flex items-end justify-center sm:items-stretch sm:justify-end">
      <div data-testid="sheet-scrim" aria-hidden="true" className="absolute inset-0 bg-scrim" onClick={onClose} />
      <div
        ref={panelRef}
        role="dialog"
        aria-modal="true"
        aria-labelledby={titleId}
        className="animate-sheet-in relative max-h-[92vh] w-full overflow-y-auto rounded-t-[24px] bg-surface p-6 shadow-[0_-8px_40px_rgba(0,0,0,0.18)] motion-reduce:animate-none sm:h-full sm:max-h-none sm:w-[440px] sm:rounded-none sm:rounded-l-[24px]"
      >
        <div className="mb-4 flex items-center justify-between gap-3">
          <h2 id={titleId} className="text-2xl font-extrabold tracking-[-0.015em]">
            {title}
          </h2>
          <Button variant="quiet" aria-label="Close" onClick={onClose} className="!min-h-9 !px-2">
            <X size={18} strokeWidth={2.25} />
          </Button>
        </div>
        {children}
      </div>
    </div>
  );
}
```

Append to `web/app/globals.css`:

```css
/* Review sheet entry: 240ms ease-out slide-and-fade. Exit is instant (unmount). */
@keyframes sheet-in {
  from {
    opacity: 0;
    transform: translateY(16px);
  }
  to {
    opacity: 1;
    transform: translateY(0);
  }
}

.animate-sheet-in {
  animation: sheet-in 0.24s ease-out;
}
```

Note: the Close button is the first focusable inside the panel only if it comes first in DOM
order; it does not (the title row is first, then children). `useFocusTrap` focuses the first
focusable in DOM order, which is the Close button in the header. The test "moves focus inside on
open" accepts any element inside the dialog.

- [x] **Step 4: Run tests to verify they pass**

Run: `cd web && npx vitest run components/ui/primitives-b.test.tsx`
Expected: PASS (11 tests).

- [x] **Step 5: Gate and commit**

```bash
cd web && npx vitest run && npx tsc --noEmit && npm run lint
cd .. && git add web/components/ui web/lib/useFocusTrap.ts web/app/globals.css
git commit -m "feat(web): Disclosure, Stub and Sheet primitives with a nested-dialog-safe focus trap"
```

---

### Task 4: Strategy kinds and the URL-backed strategy filter

**Files:**
- Create: `web/lib/strategy.ts`, `web/lib/strategy.test.ts`
- Create: `web/lib/useStrategyFilter.ts`, `web/lib/useStrategyFilter.test.tsx`

**Interfaces:**
- Produces:
  - `type StrategyKind = "csp" | "cc" | "spread"`; `type StrategyFilter = "all" | StrategyKind`
  - `STRATEGY_FILTERS: StrategyFilter[]`, `STRATEGY_LABEL: Record<StrategyFilter, string>`,
    `STRATEGY_EYEBROW: Record<StrategyKind, string>`
  - `kindOf(strategy: string | null | undefined, right: string | null | undefined): StrategyKind | null`
  - `parseStrategyFilter(raw: string | null | undefined): StrategyFilter`
  - `matchesFilter(kind: StrategyKind | null, filter: StrategyFilter): boolean`
  - `useStrategyFilter(): [StrategyFilter, (f: StrategyFilter) => void]`

- [x] **Step 1: Write the failing tests**

`web/lib/strategy.test.ts`:

```ts
import { describe, expect, it } from "vitest";
import { kindOf, matchesFilter, parseStrategyFilter } from "./strategy";

describe("kindOf", () => {
  it("maps the backend's strategy names", () => {
    expect(kindOf("cash_secured_put", "P")).toBe("csp");
    expect(kindOf("covered_call", "C")).toBe("cc");
    expect(kindOf("credit_spread", null)).toBe("spread");
  });
  it("files a roll under the side it rolls", () => {
    expect(kindOf("roll", "P")).toBe("csp");
    expect(kindOf("roll", "C")).toBe("cc");
    expect(kindOf("roll", null)).toBeNull();
  });
  it("returns null for anything it does not know", () => {
    expect(kindOf("iron_condor", "P")).toBeNull();
    expect(kindOf(undefined, undefined)).toBeNull();
  });
});

describe("parseStrategyFilter", () => {
  it("treats a junk or missing value as All", () => {
    expect(parseStrategyFilter("foo")).toBe("all");
    expect(parseStrategyFilter(null)).toBe("all");
  });
  it("keeps real values", () => {
    expect(parseStrategyFilter("csp")).toBe("csp");
    expect(parseStrategyFilter("spread")).toBe("spread");
  });
});

describe("matchesFilter", () => {
  it("All matches everything, even an unknown kind", () => {
    expect(matchesFilter(null, "all")).toBe(true);
    expect(matchesFilter("cc", "all")).toBe(true);
  });
  it("a specific filter matches only its kind", () => {
    expect(matchesFilter("cc", "csp")).toBe(false);
    expect(matchesFilter(null, "csp")).toBe(false);
    expect(matchesFilter("csp", "csp")).toBe(true);
  });
});
```

`web/lib/useStrategyFilter.test.tsx`:

```tsx
import { act, renderHook } from "@testing-library/react";
import { beforeEach, describe, expect, it, vi } from "vitest";

const nav = vi.hoisted(() => ({
  replace: vi.fn(),
  params: new URLSearchParams(),
  pathname: "/",
}));

vi.mock("next/navigation", () => ({
  useRouter: () => ({ replace: nav.replace }),
  useSearchParams: () => nav.params,
  usePathname: () => nav.pathname,
}));

import { useStrategyFilter } from "./useStrategyFilter";

beforeEach(() => {
  nav.replace.mockReset();
  nav.params = new URLSearchParams();
  nav.pathname = "/";
});

describe("useStrategyFilter", () => {
  it("reads the filter from ?strategy=", () => {
    nav.params = new URLSearchParams("strategy=cc");
    const { result } = renderHook(() => useStrategyFilter());
    expect(result.current[0]).toBe("cc");
  });
  it("shows All for a junk value", () => {
    nav.params = new URLSearchParams("strategy=foo");
    const { result } = renderHook(() => useStrategyFilter());
    expect(result.current[0]).toBe("all");
  });
  it("writes the choice into the URL and drops it for All, keeping other params", () => {
    nav.params = new URLSearchParams("x=1");
    const { result } = renderHook(() => useStrategyFilter());
    act(() => result.current[1]("csp"));
    expect(nav.replace).toHaveBeenLastCalledWith("/?x=1&strategy=csp", { scroll: false });
    act(() => result.current[1]("all"));
    expect(nav.replace).toHaveBeenLastCalledWith("/?x=1", { scroll: false });
  });
});
```

- [x] **Step 2: Run to verify failure**

Run: `cd web && npx vitest run lib/strategy.test.ts lib/useStrategyFilter.test.tsx`
Expected: FAIL (modules not found).

- [x] **Step 3: Implement**

`web/lib/strategy.ts`:

```ts
/** The three kinds of trade the console groups everything by (DESIGN.md Strategy switcher). */
export type StrategyKind = "csp" | "cc" | "spread";
export type StrategyFilter = "all" | StrategyKind;

export const STRATEGY_FILTERS: StrategyFilter[] = ["all", "csp", "cc", "spread"];

export const STRATEGY_LABEL: Record<StrategyFilter, string> = {
  all: "All",
  csp: "CSPs",
  cc: "CCs",
  spread: "Credit spreads",
};

export const STRATEGY_EYEBROW: Record<StrategyKind, string> = {
  csp: "Cash-secured put",
  cc: "Covered call",
  spread: "Credit spread",
};

/**
 * Backend strategy name (+ option right for rolls) to a kind. A roll is filed under the side
 * it rolls: a put roll is still the CSP book. Unknown strategies return null and show only
 * under All - never guessed into a kind.
 */
export function kindOf(
  strategy: string | null | undefined,
  right: string | null | undefined,
): StrategyKind | null {
  if (strategy === "cash_secured_put") return "csp";
  if (strategy === "covered_call") return "cc";
  if (strategy === "credit_spread") return "spread";
  if (strategy === "roll") {
    if (right === "P") return "csp";
    if (right === "C") return "cc";
  }
  return null;
}

export function parseStrategyFilter(raw: string | null | undefined): StrategyFilter {
  return (STRATEGY_FILTERS as string[]).includes(raw ?? "") ? (raw as StrategyFilter) : "all";
}

export function matchesFilter(kind: StrategyKind | null, filter: StrategyFilter): boolean {
  return filter === "all" || kind === filter;
}
```

`web/lib/useStrategyFilter.ts`:

```ts
"use client";

import { usePathname, useRouter, useSearchParams } from "next/navigation";
import { useCallback } from "react";
import { type StrategyFilter, parseStrategyFilter } from "./strategy";

/**
 * The strategy switcher's value, kept in `?strategy=` so a reload or a shared link keeps it.
 * A page using this must render inside <Suspense> (Next's useSearchParams rule).
 */
export function useStrategyFilter(): [StrategyFilter, (f: StrategyFilter) => void] {
  const params = useSearchParams();
  const router = useRouter();
  const pathname = usePathname();
  const value = parseStrategyFilter(params.get("strategy"));

  const set = useCallback(
    (f: StrategyFilter) => {
      const next = new URLSearchParams(params.toString());
      if (f === "all") next.delete("strategy");
      else next.set("strategy", f);
      const qs = next.toString();
      router.replace(qs ? `${pathname}?${qs}` : pathname, { scroll: false });
    },
    [params, router, pathname],
  );

  return [value, set];
}
```

- [x] **Step 4: Run tests to verify they pass**

Run: `cd web && npx vitest run lib/strategy.test.ts lib/useStrategyFilter.test.tsx`
Expected: PASS (11 tests).

- [x] **Step 5: Gate and commit**

```bash
cd web && npx vitest run && npx tsc --noEmit && npm run lint
cd .. && git add web/lib/strategy.ts web/lib/strategy.test.ts web/lib/useStrategyFilter.ts web/lib/useStrategyFilter.test.tsx
git commit -m "feat(web): strategy kinds and a URL-backed strategy filter"
```

---

## Section B — Navigation and shell (Tasks 5–6) · model: opus

Moves the live pages to their new routes, adds redirects from the old URLs, and replaces the rail
with the new shell. Relocates the halt, resume and autonomy controls into the bot sheet without
changing their behaviour.

**Entry checks (run before Task 5):**

- [x] **B1. Section A landed.** `git log --oneline main..HEAD` shows four commits; Tasks 1–4 are
  ticked with commit hashes in the Progress log.
- [x] **B2. Web gate green, no regressions.**
  `cd web && npx vitest run && npx tsc --noEmit && npm run lint`. The vitest count is the A2 baseline
  plus Section A's new tests, with zero failures and zero skipped tests that were not skipped at
  baseline.
- [x] **B3. Section A's interfaces exist.** This prints nothing:

  ```bash
  cd web && for f in components/ui/{Button,Card,SegmentedControl,StatusWord,Meter,Disclosure,Stub,Sheet}.tsx \
    lib/{theme,useThemePref,useFocusTrap,strategy,useStrategyFilter}.ts; do [ -f "$f" ] || echo "MISSING $f"; done
  ```

- [x] **B4. No raw colour crept in.** This prints nothing:

  ```bash
  cd web && grep -rnE "#[0-9a-fA-F]{3,8}\b|\b(bg|text|border)-(white|black|gray|zinc|neutral|slate|green|red|lime)-?" \
    components/ui lib --include=*.tsx --include=*.ts | grep -v "\.test\."
  ```

- [x] **B5. Copy rules.** `grep -rn "—" web/components/ui --include=*.tsx | grep -v "\.test\."` shows
  no em dash inside JSX text or a string literal (an em dash in a code comment is allowed).
- [x] **B6. The theme works in a real browser.** `cd web && npm run dev -- -p 3001`, open
  `http://localhost:3001/`; in DevTools run `localStorage.setItem("ibkr-theme","dark")` and reload:
  the page paints dark with no light flash. Set it back to `"light"`. Stop the server.

**Section exit:** two more commits; `/trades`, `/activity`, `/research`, `/research/universe` and
`/more` render; `/options/41` redirects to `/trades/41`; halt, resume and autonomy work from the
bot sheet.

---

### Task 5: New routes, redirects and the More page

**Files:**
- Move (git mv): `web/app/options/page.tsx` → `web/app/trades/page.tsx`;
  `web/app/options/page.test.tsx` → `web/app/trades/page.test.tsx`;
  `web/app/options/[approvalId]/page.tsx` → `web/app/trades/[approvalId]/page.tsx`;
  `web/app/pnl/page.tsx` → `web/app/activity/page.tsx`;
  `web/app/universe/page.tsx` → `web/app/research/universe/page.tsx`;
  `web/app/page.tsx` → `web/app/research/page.tsx`;
  `web/app/page.test.tsx` → `web/app/research/page.test.tsx`
- Create: `web/app/page.tsx` (temporary re-export, replaced in Task 14)
- Create: `web/app/more/page.tsx`, `web/app/more/page.test.tsx`
- Create: `web/components/shell/ThemeToggle.tsx`
- Modify: `web/next.config.ts`; Create: `web/next.config.test.ts`
- Modify: every in-app link to an old path (found in Step 5)

**Interfaces:**
- Consumes: `SegmentedControl` (Task 2), `useThemePref` (Task 1), existing `SystemStatusCard`.
- Produces: routes `/trades`, `/trades/[approvalId]`, `/activity`, `/research`,
  `/research/universe`, `/more`; `ThemeToggle()`.

- [x] **Step 1: Write the failing tests**

`web/next.config.test.ts`:

```ts
import { describe, expect, it } from "vitest";
import config from "./next.config";

describe("redirects", () => {
  it("keeps every old URL working", async () => {
    const redirects = await config.redirects!();
    const map = Object.fromEntries(redirects.map((r) => [r.source, r]));
    expect(map["/options"].destination).toBe("/trades");
    expect(map["/options/:approvalId"].destination).toBe("/trades/:approvalId");
    expect(map["/pnl"].destination).toBe("/activity");
    expect(map["/universe"].destination).toBe("/research/universe");
  });
  it("uses temporary redirects while the overhaul is in flight", async () => {
    const redirects = await config.redirects!();
    expect(redirects.every((r) => r.permanent === false)).toBe(true);
  });
});
```

`web/app/more/page.test.tsx`:

```tsx
import { fireEvent, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";
import { renderWithQuery } from "@/lib/test-query";
import { THEME_STORAGE_KEY } from "@/lib/theme";
import MorePage from "./page";

const status = { as_of: new Date().toISOString(), systems: [] };

describe("More page", () => {
  it("offers light, dark and follow-OS themes and persists the choice", () => {
    renderWithQuery(<MorePage />, { "/system/status": status });
    const group = screen.getByRole("group", { name: "Theme" });
    expect(group).toBeInTheDocument();
    fireEvent.click(screen.getByRole("button", { name: "Follow OS" }));
    expect(localStorage.getItem(THEME_STORAGE_KEY)).toBe("system");
  });
  it("links to the pages that have no tab on a phone", () => {
    renderWithQuery(<MorePage />, { "/system/status": status });
    expect(screen.getByRole("link", { name: /How it works/ })).toHaveAttribute("href", "/explain");
    expect(screen.getByRole("link", { name: /Research/ })).toHaveAttribute("href", "/research");
    expect(screen.getByRole("link", { name: /News/ })).toHaveAttribute("href", "/news");
    expect(screen.getByRole("link", { name: /Import a statement/ })).toHaveAttribute("href", "/ledger/import");
  });
});
```

Before writing the More test's `status` fixture, open `web/components/shell/SystemStatusCard.test.tsx`
and copy the minimal valid `GET /system/status` body it uses; replace the `status` constant above
with it if the field names differ (`systems` is a placeholder name only if that file shows another).

- [x] **Step 2: Run to verify failure**

Run: `cd web && npx vitest run next.config.test.ts app/more/page.test.tsx`
Expected: FAIL (`redirects` undefined; `./page` not found).

- [x] **Step 3: Move the pages**

```bash
cd web
mkdir -p app/trades app/activity app/research/universe app/more
git mv app/options/page.tsx app/trades/page.tsx
git mv app/options/page.test.tsx app/trades/page.test.tsx
git mv "app/options/[approvalId]" "app/trades/[approvalId]"
git mv app/pnl/page.tsx app/activity/page.tsx
git mv app/universe/page.tsx app/research/universe/page.tsx
git mv app/page.tsx app/research/page.tsx
git mv app/page.test.tsx app/research/page.test.tsx
```

Fix relative imports inside the moved files and their tests (e.g. `./page` stays `./page`; any
`../` paths gain one level). Run `npx tsc --noEmit` to find them.

Create `web/app/page.tsx` (temporary: Research stays at `/` until Task 14 builds Home):

```tsx
export { default } from "./research/page";
```

- [x] **Step 4: Redirects** — `web/next.config.ts`

```ts
import type { NextConfig } from "next";

const nextConfig: NextConfig = {
  reactStrictMode: true,
  // Old URLs keep working (DESIGN.md Brief: stable URLs). Temporary (307) while the
  // overhaul is in flight so no browser caches a destination that may still move.
  async redirects() {
    return [
      { source: "/options", destination: "/trades", permanent: false },
      { source: "/options/:approvalId", destination: "/trades/:approvalId", permanent: false },
      { source: "/pnl", destination: "/activity", permanent: false },
      { source: "/universe", destination: "/research/universe", permanent: false },
    ];
  },
};

export default nextConfig;
```

- [x] **Step 5: Update in-app links**

Run: `cd web && grep -rnE "[\"'\`]/(options|pnl|universe)([/\"'\`?]|$)" app components lib --include=*.tsx --include=*.ts | grep -v test`

For every hit, change `/options/` → `/trades/`, `/options` → `/trades`, `/pnl` → `/activity`,
`/universe` → `/research/universe`. Then run the same grep over `*.test.tsx` and update test
expectations the same way (a test asserting `href="/options/41"` now asserts `/trades/41`).
Record the file list as a ruling in the Progress log.

- [x] **Step 6: ThemeToggle and the More page**

`web/components/shell/ThemeToggle.tsx`:

```tsx
"use client";

import { SegmentedControl } from "@/components/ui/SegmentedControl";
import type { ThemePref } from "@/lib/theme";
import { useThemePref } from "@/lib/useThemePref";

const OPTIONS: { value: ThemePref; label: string }[] = [
  { value: "light", label: "Light" },
  { value: "dark", label: "Dark" },
  { value: "system", label: "Follow OS" },
];

export function ThemeToggle() {
  const [pref, setPref] = useThemePref();
  return <SegmentedControl label="Theme" options={OPTIONS} value={pref} onChange={setPref} />;
}
```

`web/app/more/page.tsx`:

```tsx
"use client";

import Link from "next/link";
import { ChevronRight } from "lucide-react";
import { SystemStatusCard } from "@/components/shell/SystemStatusCard";
import { ThemeToggle } from "@/components/shell/ThemeToggle";
import { Card } from "@/components/ui/Card";

const LINKS = [
  { href: "/research", label: "Research", sub: "Search, watchlist, sectors, universe" },
  { href: "/news", label: "News", sub: "Feed, calendar and ticker briefs" },
  { href: "/explain", label: "How it works", sub: "The pipeline in plain English" },
  { href: "/ledger/import", label: "Import a statement", sub: "Upload an IBKR activity CSV" },
];

export default function MorePage() {
  return (
    <div className="mx-auto max-w-[720px] px-4 py-6 md:px-7">
      <h1 className="text-2xl font-extrabold tracking-[-0.015em]">More</h1>

      <Card className="mt-6">
        <h2 className="text-[1.0625rem] font-bold">Theme</h2>
        <p className="mt-1 text-sm text-muted">Light is the default. Follow OS switches with your device.</p>
        <div className="mt-3">
          <ThemeToggle />
        </div>
      </Card>

      <Card className="mt-4" as="div">
        <ul>
          {LINKS.map((l) => (
            <li key={l.href} className="border-t border-border first:border-t-0">
              <Link href={l.href} className="flex items-center justify-between gap-3 py-3">
                <span>
                  <span className="block font-bold">{l.label}</span>
                  <span className="block text-[0.8125rem] text-muted">{l.sub}</span>
                </span>
                <ChevronRight aria-hidden="true" size={18} className="text-muted" />
              </Link>
            </li>
          ))}
        </ul>
      </Card>

      <section className="mt-4" aria-label="System status">
        <SystemStatusCard />
      </section>
    </div>
  );
}
```

- [x] **Step 7: Run tests to verify they pass**

Run: `cd web && npx vitest run`
Expected: PASS, including the moved `app/trades/page.test.tsx` and `app/research/page.test.tsx`.

- [x] **Step 8: Gate and commit**

```bash
cd web && npx vitest run && npx tsc --noEmit && npm run lint
cd .. && git add -A web/app web/components web/lib web/next.config.ts web/next.config.test.ts
git commit -m "feat(web): Trades/Activity/Research/More routes with redirects from the old URLs"
```

---

### Task 6: The shell — rail, phone tab bar, bot card and sheet, halted banner

**Files:**
- Create: `web/lib/nav.ts`, `web/lib/nav.test.ts`
- Rewrite: `web/components/shell/Rail.tsx`, `web/components/shell/Rail.test.tsx`
- Delete: `web/components/shell/RailSection.tsx` (and its test if one exists)
- Create: `web/components/shell/TabBar.tsx`, `BotCard.tsx`, `BotSheet.tsx`, `HaltedBanner.tsx`,
  `web/components/shell/shell.test.tsx`
- Modify: `web/components/options/ControlsStrip.tsx` (remove its halted banner) and
  `ControlsStrip.test.tsx` (move the banner assertions to `shell.test.tsx`)
- Modify: `web/app/layout.tsx`

**Interfaces:**
- Consumes: `Sheet`, `StatusWord` (Tasks 2–3); `HaltControl`, `AutonomyControl`,
  `ControlsResponse`, `ApprovalListResponse` (existing, `components/options/`); `formatDateTime`.
- Produces: `NAV: NavItem[]`, `activeKey(pathname: string): string | null`; `Rail`, `TabBar`,
  `BotCard`, `BotSheet`, `HaltedBanner`. Query keys reused: `["options","controls"]`,
  `["options","approvals","pending"]`.

- [x] **Step 1: Write the failing tests**

`web/lib/nav.test.ts`:

```ts
import { describe, expect, it } from "vitest";
import { NAV, activeKey } from "./nav";

describe("activeKey", () => {
  it("matches Home only exactly", () => {
    expect(activeKey("/")).toBe("home");
    expect(activeKey("/unknown")).toBeNull();
  });
  it("matches a section and its children", () => {
    expect(activeKey("/trades")).toBe("trades");
    expect(activeKey("/trades/41")).toBe("trades");
    expect(activeKey("/ledger/trades")).toBe("activity");
    expect(activeKey("/stock/AAPL")).toBe("research");
    expect(activeKey("/explain")).toBe("more");
  });
  it("does not match a prefix that is not a path segment", () => {
    expect(activeKey("/tradesman")).toBeNull();
  });
});

describe("NAV", () => {
  it("puts exactly five destinations on the phone tab bar", () => {
    expect(NAV.filter((n) => n.phone).map((n) => n.key)).toEqual([
      "home",
      "trades",
      "portfolio",
      "activity",
      "more",
    ]);
  });
});
```

`web/components/shell/Rail.test.tsx` (replace the file):

```tsx
import { screen } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";
import { renderWithQuery } from "@/lib/test-query";

vi.mock("next/navigation", () => ({ usePathname: () => "/trades/41" }));

import { Rail } from "./Rail";

const controls = {
  as_of: new Date().toISOString(),
  autonomy: { level: "approve", label: "Approve each trade" },
  rungs: [],
  halted: false,
  halt_reason: null,
  halted_at: null,
  mode: "paper",
  drain_healthy: true,
  drain_last_seen: null,
  pending_commands: 0,
};

function approvals(n: number) {
  return {
    as_of: new Date().toISOString(),
    approvals: Array.from({ length: n }, (_, i) => ({ id: i + 1, status: "pending" })),
  };
}

describe("Rail", () => {
  it("lists every destination and marks the current one", () => {
    renderWithQuery(<Rail />, { "/options/controls": controls, "/options/approvals": approvals(0) });
    for (const name of ["Home", "Portfolio", "Activity", "Research", "News", "More"]) {
      expect(screen.getByRole("link", { name: new RegExp(`^${name}`) })).toBeInTheDocument();
    }
    expect(screen.getByRole("link", { name: /^Trades/ })).toHaveAttribute("aria-current", "page");
    expect(screen.getByRole("link", { name: /^Home/ })).not.toHaveAttribute("aria-current");
  });
  it("shows the pending count on Trades in words for screen readers", async () => {
    renderWithQuery(<Rail />, { "/options/controls": controls, "/options/approvals": approvals(2) });
    expect(await screen.findByText("2")).toBeInTheDocument();
    expect(screen.getByRole("link", { name: "Trades, 2 waiting" })).toBeInTheDocument();
  });
  it("shows no badge when nothing is waiting", async () => {
    renderWithQuery(<Rail />, { "/options/controls": controls, "/options/approvals": approvals(0) });
    expect(await screen.findByRole("link", { name: "Trades" })).toBeInTheDocument();
  });
});
```

`web/components/shell/shell.test.tsx`:

```tsx
import { fireEvent, screen } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";
import { renderWithQuery } from "@/lib/test-query";

vi.mock("next/navigation", () => ({ usePathname: () => "/" }));

import { BotCard } from "./BotCard";
import { HaltedBanner } from "./HaltedBanner";
import { TabBar } from "./TabBar";

function controls(over: Record<string, unknown> = {}) {
  return {
    as_of: new Date().toISOString(),
    autonomy: { level: "approve", label: "Approve each trade" },
    rungs: [{ level: "approve", label: "Approve each trade" }],
    halted: false,
    halt_reason: null,
    halted_at: null,
    mode: "paper",
    drain_healthy: true,
    drain_last_seen: null,
    pending_commands: 0,
    ...over,
  };
}

describe("TabBar", () => {
  it("has the five phone destinations with Home current", () => {
    renderWithQuery(<TabBar />, {});
    const nav = screen.getByRole("navigation", { name: "Primary" });
    expect(nav).toBeInTheDocument();
    expect(screen.getAllByRole("link")).toHaveLength(5);
    expect(screen.getByRole("link", { name: "Home" })).toHaveAttribute("aria-current", "page");
  });
});

describe("BotCard", () => {
  it("states running, mode and rung in words", async () => {
    renderWithQuery(<BotCard />, { "/options/controls": controls() });
    expect(await screen.findByText("Bot running · paper")).toBeInTheDocument();
    expect(screen.getByText("Approve each trade")).toBeInTheDocument();
  });
  it("states halted in words", async () => {
    renderWithQuery(<BotCard />, { "/options/controls": controls({ halted: true }) });
    expect(await screen.findByText("Halted · paper")).toBeInTheDocument();
  });
  it("says so when the trading service is not draining commands", async () => {
    renderWithQuery(<BotCard />, { "/options/controls": controls({ drain_healthy: false }) });
    expect(await screen.findByText("The trading service is not draining commands")).toBeInTheDocument();
  });
  it("opens the bot sheet with the halt control", async () => {
    renderWithQuery(<BotCard />, { "/options/controls": controls() });
    fireEvent.click(await screen.findByRole("button", { name: /Bot running/ }));
    expect(screen.getByRole("dialog", { name: "Bot controls" })).toBeInTheDocument();
    expect(screen.getByRole("button", { name: /Halt/ })).toBeInTheDocument();
  });
  it("says the status is unavailable when the controls fetch fails", async () => {
    renderWithQuery(<BotCard />, {});
    expect(await screen.findByText("Bot status unavailable")).toBeInTheDocument();
  });
});

describe("HaltedBanner", () => {
  it("renders nothing while trading runs", async () => {
    const { container } = renderWithQuery(<HaltedBanner />, { "/options/controls": controls() });
    await screen.findByTestId("halted-banner-probe");
    expect(container.querySelector('[role="alert"]')).toBeNull();
  });
  it("states the halt, its reason and its time as text", async () => {
    renderWithQuery(<HaltedBanner />, {
      "/options/controls": controls({
        halted: true,
        halt_reason: "daily loss limit",
        halted_at: "2026-10-13T14:05:00Z",
      }),
    });
    const alert = await screen.findByRole("alert");
    expect(alert).toHaveTextContent("Trading is halted");
    expect(alert).toHaveTextContent("daily loss limit");
    expect(alert).toHaveTextContent("Oct 13, 2026");
  });
  it("omits the time for a breaker halt with no command row", async () => {
    renderWithQuery(<HaltedBanner />, {
      "/options/controls": controls({ halted: true, halt_reason: "breaker", halted_at: null }),
    });
    const alert = await screen.findByRole("alert");
    expect(alert).not.toHaveTextContent(/since/);
  });
});
```

Before Step 2, read `web/components/options/ControlsStrip.test.tsx` and copy any assertion about
the halted banner's wording that the three HaltedBanner tests above do not already cover into
`shell.test.tsx` under `describe("HaltedBanner")`, adapted to render `<HaltedBanner />`.

- [x] **Step 2: Run to verify failure**

Run: `cd web && npx vitest run lib/nav.test.ts components/shell`
Expected: FAIL (modules not found; Rail still renders from `/nav`).

- [x] **Step 3: Implement `web/lib/nav.ts`**

```ts
import type { LucideIcon } from "lucide-react";
import { ArrowLeftRight, Ellipsis, Home, Newspaper, PieChart, Receipt, Search } from "lucide-react";

export type NavItem = {
  key: string;
  label: string;
  href: string;
  /** Path prefixes this destination owns; "/" matches only exactly. */
  match: string[];
  icon: LucideIcon;
  /** On the phone tab bar (the rest live under More). */
  phone: boolean;
};

export const NAV: NavItem[] = [
  { key: "home", label: "Home", href: "/", match: ["/"], icon: Home, phone: true },
  { key: "trades", label: "Trades", href: "/trades", match: ["/trades"], icon: ArrowLeftRight, phone: true },
  { key: "portfolio", label: "Portfolio", href: "/portfolio", match: ["/portfolio"], icon: PieChart, phone: true },
  { key: "activity", label: "Activity", href: "/activity", match: ["/activity", "/ledger"], icon: Receipt, phone: true },
  { key: "research", label: "Research", href: "/research", match: ["/research", "/stock"], icon: Search, phone: false },
  { key: "news", label: "News", href: "/news", match: ["/news"], icon: Newspaper, phone: false },
  { key: "more", label: "More", href: "/more", match: ["/more", "/explain"], icon: Ellipsis, phone: true },
];

export function activeKey(pathname: string): string | null {
  let best: { key: string; len: number } | null = null;
  for (const item of NAV) {
    for (const m of item.match) {
      const hit = m === "/" ? pathname === "/" : pathname === m || pathname.startsWith(`${m}/`);
      if (hit && (best === null || m.length > best.len)) best = { key: item.key, len: m.length };
    }
  }
  return best?.key ?? null;
}
```

- [x] **Step 4: Implement the shell components**

`web/components/shell/Rail.tsx`:

```tsx
"use client";

import clsx from "clsx";
import Link from "next/link";
import { usePathname } from "next/navigation";
import { useQuery } from "@tanstack/react-query";
import { apiFetch } from "@/lib/api";
import { NAV, activeKey } from "@/lib/nav";
import type { ApprovalListResponse } from "@/components/options/types";
import { BotCard } from "./BotCard";

export function usePendingCount(): number | null {
  // Same key and URL as <ApprovalsList status="pending"/>, so react-query dedupes.
  const { data } = useQuery({
    queryKey: ["options", "approvals", "pending"],
    queryFn: () => apiFetch<ApprovalListResponse>("/options/approvals?status=pending"),
    refetchInterval: 30_000,
  });
  return data ? data.approvals.length : null;
}

export function Rail() {
  const pathname = usePathname();
  const current = activeKey(pathname);
  const pending = usePendingCount();

  return (
    <nav aria-label="Sections" className="hidden w-[200px] shrink-0 flex-col bg-surface px-3 py-[18px] md:flex">
      <div className="px-2.5 pb-4 text-[0.9375rem] font-extrabold">IBKR Income</div>
      <ul className="flex flex-1 flex-col gap-0.5 overflow-y-auto">
        {NAV.map((item) => {
          const on = item.key === current;
          const badge = item.key === "trades" && pending !== null && pending > 0 ? pending : null;
          const Icon = item.icon;
          return (
            <li key={item.key}>
              <Link
                href={item.href}
                aria-current={on ? "page" : undefined}
                aria-label={badge !== null ? `${item.label}, ${badge} waiting` : item.label}
                className={clsx(
                  "flex items-center gap-2.5 rounded-[10px] px-2.5 py-2 text-sm",
                  on ? "bg-sunk font-semibold text-content" : "text-muted hover:text-content",
                )}
              >
                <Icon aria-hidden="true" size={17} strokeWidth={2} />
                <span className="flex-1">{item.label}</span>
                {badge !== null && (
                  <span aria-hidden="true" className="rounded-full bg-primary px-[7px] text-[11px] font-bold text-on-primary">
                    {badge}
                  </span>
                )}
              </Link>
            </li>
          );
        })}
      </ul>
      <BotCard />
    </nav>
  );
}
```

`web/components/shell/TabBar.tsx`:

```tsx
"use client";

import clsx from "clsx";
import Link from "next/link";
import { usePathname } from "next/navigation";
import { NAV, activeKey } from "@/lib/nav";

export function TabBar() {
  const current = activeKey(usePathname());
  return (
    <nav
      aria-label="Primary"
      className="fixed inset-x-0 bottom-0 z-40 flex justify-around border-t border-border bg-surface px-1.5 pt-2 pb-[max(env(safe-area-inset-bottom),12px)] md:hidden"
    >
      {NAV.filter((n) => n.phone).map((item) => {
        const on = item.key === current;
        const Icon = item.icon;
        return (
          <Link
            key={item.key}
            href={item.href}
            aria-current={on ? "page" : undefined}
            className={clsx(
              "flex min-h-11 min-w-14 flex-col items-center justify-center gap-0.5 text-[11px]",
              on ? "font-bold text-content" : "text-muted",
            )}
          >
            <Icon aria-hidden="true" size={20} strokeWidth={on ? 2.4 : 2} />
            {item.label}
          </Link>
        );
      })}
    </nav>
  );
}
```

`web/components/shell/BotSheet.tsx`:

```tsx
"use client";

import { AutonomyControl } from "@/components/options/AutonomyControl";
import { HaltControl } from "@/components/options/HaltControl";
import type { ControlsResponse } from "@/components/options/types";
import { Sheet } from "@/components/ui/Sheet";

/** Halt is one tap, resume needs RESUME, rung changes confirm: all unchanged, only relocated. */
export function BotSheet({
  open,
  onClose,
  controls,
}: {
  open: boolean;
  onClose: () => void;
  controls: ControlsResponse;
}) {
  return (
    <Sheet open={open} onClose={onClose} title="Bot controls">
      <p className="text-sm text-muted">
        Mode: <span className="font-semibold text-content">{controls.mode}</span>
      </p>
      <div className="mt-4 grid gap-5">
        <HaltControl
          halted={controls.halted}
          haltReason={controls.halt_reason}
          haltedAt={controls.halted_at}
          drainHealthy={controls.drain_healthy}
        />
        <AutonomyControl autonomy={controls.autonomy} rungs={controls.rungs} drainHealthy={controls.drain_healthy} />
      </div>
    </Sheet>
  );
}
```

`web/components/shell/BotCard.tsx`:

```tsx
"use client";

import { useQuery } from "@tanstack/react-query";
import { useState } from "react";
import { apiFetch } from "@/lib/api";
import type { ControlsResponse } from "@/components/options/types";
import { BotSheet } from "./BotSheet";

export function useControls() {
  // Same key as ControlsStrip / ApprovalsList: one request for the whole page.
  return useQuery({
    queryKey: ["options", "controls"],
    queryFn: () => apiFetch<ControlsResponse>("/options/controls"),
    refetchInterval: 30_000,
  });
}

export function BotCard() {
  const { data, isError } = useControls();
  const [open, setOpen] = useState(false);

  if (isError && !data) {
    return <p className="rounded-xl bg-sunk p-2.5 text-[0.8125rem] text-muted">Bot status unavailable</p>;
  }
  if (!data) return null;

  const state = `${data.halted ? "Halted" : "Bot running"} · ${data.mode}`;
  return (
    <>
      <button
        type="button"
        onClick={() => setOpen(true)}
        className="w-full rounded-xl bg-sunk p-2.5 text-left text-[0.8125rem] hover:bg-sunk-deep"
      >
        <span className="block font-bold text-content">{state}</span>
        <span className="block text-muted">{data.autonomy.label}</span>
        {!data.drain_healthy && (
          <span className="mt-1 block font-semibold text-on-flag">The trading service is not draining commands</span>
        )}
      </button>
      <BotSheet open={open} onClose={() => setOpen(false)} controls={data} />
    </>
  );
}
```

Note: `text-on-flag` on a `bg-sunk` button is the amber ink at 7.6:1 against flag, but here it
sits on sunk; check it reaches 4.5:1 with `python3 ~/.claude/skills/da-vinci/scripts/contrast.py
"#6b4500" "#e6eadf"` and `"#f5cf7a" "#232723"`; if either fails, wrap the line in
`<StatusWord tone="flag">` instead and record the ruling.

`web/components/shell/HaltedBanner.tsx`:

```tsx
"use client";

import { formatDateTime } from "@/lib/format";
import { useControls } from "./BotCard";

/** Global: a halted system is unmissable on every page, in words, not colour. */
export function HaltedBanner() {
  const { data } = useControls();
  if (!data?.halted) return <span data-testid="halted-banner-probe" hidden />;
  return (
    <div role="alert" className="bg-flag px-4 py-2.5 text-sm text-on-flag md:px-7">
      <span className="font-bold">Trading is halted</span>
      {data.halt_reason && <span>: {data.halt_reason}</span>}
      {data.halted_at && <span> (since {formatDateTime(data.halted_at)})</span>}
      <span>. Open Bot controls to resume.</span>
    </div>
  );
}
```

`web/app/layout.tsx` — replace the `<Providers>` body with:

```tsx
        <Providers>
          <div className="flex h-dvh overflow-hidden">
            <Rail />
            <div className="flex min-w-0 flex-1 flex-col">
              <HaltedBanner />
              <main className="flex-1 overflow-y-auto overflow-x-hidden pb-24 md:pb-0">{children}</main>
            </div>
            <TabBar />
          </div>
        </Providers>
```

and add the imports `import { HaltedBanner } from "@/components/shell/HaltedBanner";` and
`import { TabBar } from "@/components/shell/TabBar";`.

Then:
- On a phone the rail is hidden, so the bot card must live on More too. In
  `web/app/more/page.tsx`, import `BotCard` from `@/components/shell/BotCard` and render
  `<section className="mt-6" aria-label="Bot"><BotCard /></section>` directly under the `<h1>`
  (before the Theme card). Add `"/options/controls": controls` (the fixture from `shell.test.tsx`)
  to both `renderWithQuery` maps in `web/app/more/page.test.tsx`, and add this test there:

  ```tsx
  it("reaches the bot controls on a phone, where the rail is hidden", async () => {
    renderWithQuery(<MorePage />, { "/system/status": status, "/options/controls": controls });
    expect(await screen.findByRole("button", { name: /Bot running/ })).toBeInTheDocument();
  });
  ```

  (define `controls` at the top of `page.test.tsx` with the same body as in `shell.test.tsx`).
- Delete `web/components/shell/RailSection.tsx` (`git rm`), plus its test if present.
- In `web/components/options/ControlsStrip.tsx`, delete the JSX block that renders the halted
  banner (the element shown when `data.halted` is true, above the strip). Keep the strip's halted
  pill. Delete the matching banner assertions from `ControlsStrip.test.tsx` (now covered in
  `shell.test.tsx`).

- [x] **Step 5: Run tests to verify they pass**

Run: `cd web && npx vitest run`
Expected: PASS.

- [x] **Step 6: Gate and commit**

```bash
cd web && npx vitest run && npx tsc --noEmit && npm run lint
cd .. && git add -A web/lib/nav.ts web/lib/nav.test.ts web/components/shell web/components/options/ControlsStrip.tsx web/components/options/ControlsStrip.test.tsx web/app/layout.tsx web/app/more
git commit -m "feat(web): new shell - rail, phone tab bar, bot card and sheet, global halted banner"
```

---

## Section C — Read-only APIs (Tasks 7–9) · model: opus

Three read-only routes and two `src/reporting/` builders, one config key and three schemas. The API
still writes exactly one table; nothing new is reachable from engine, execution or strategies.

**Entry checks (run before Task 7):**

- [x] **C1. Section B landed.** `git log --oneline main..HEAD` shows six commits; Tasks 5–6 are ticked.
- [x] **C2. Web gate and production build green.**
  `cd web && npx vitest run && npx tsc --noEmit && npm run lint && npm run build`. This is the first
  `next build` since routes moved; a build failure here is Section B's to fix.
- [x] **C3. The safety controls survived the move.** These pass unchanged from baseline:
  `cd web && npx vitest run components/options/HaltControl components/options/AutonomyControl components/options/DecideControls components/options/ConfirmAction`.
- [x] **C4. Python gate green, fences green, OpenAPI current.**

  ```bash
  python -m pytest -q && ruff check . && mypy src
  python -m pytest -q tests/test_web_fence.py tests/test_spreads_fence.py tests/test_news_fence.py \
    tests/test_eval_skills.py tests/test_openapi_current.py
  ```

  The pytest count equals the A2 baseline (Sections A–B touched no Python).
- [x] **C5. The fixtures this section relies on exist.** `grep -nE "^def (db|api_db|client|seed_leg|seed_journal_day|seed_portfolio_snapshot)\b|^def _account_dict" tests/conftest.py`
  lists all seven names. A missing one means the task's tests must be adapted first: record the
  ruling.

**Section exit:** three more commits; `docs/web/openapi.json` regenerated and
`tests/test_openapi_current.py` green; `config/examples/settings.yaml` carries
`web.monthly_income_target_pct: null`.

---

### Task 7: Account value series — `GET /portfolio/value`

**Files:**
- Modify: `src/common/schemas.py` (append after `EquityCurve`)
- Create: `src/reporting/account_value.py`
- Modify: `src/api/models/portfolio.py`, `src/api/routers/portfolio.py`
- Create: `tests/test_reporting_account_value.py`, `tests/test_api_portfolio_value.py`

**Interfaces:**
- Produces:
  - `AccountValuePoint(at: datetime, value: float)`
  - `AccountValueSeries(range: Literal["1d","1w","1m","3m","ytd","all"], points, latest, latest_at, previous_close, change_today, change_today_pct)`
  - `account_value_series(session, range_key, *, now: datetime) -> AccountValueSeries`
  - `month_start_value(session, first_day: date) -> float | None`
  - `GET /portfolio/value?range=1m` → `AccountValueResponse(as_of, series)`

- [x] **Step 1: Write the failing builder tests** — `tests/test_reporting_account_value.py`

```python
"""Account value over time: daily from the journal, intraday from portfolio snapshots."""

from __future__ import annotations

from datetime import UTC, date, datetime, timedelta

from src.reporting.account_value import account_value_series, month_start_value
from tests.conftest import _account_dict

NOW = datetime(2026, 10, 13, 18, 0, tzinfo=UTC)  # 14:00 ET, a Tuesday


def _journal(db, day: date, net_liq: float) -> None:
    from src.storage.models import JournalRow

    with db() as s:
        s.add(
            JournalRow(
                entry_date=day,
                realized_pnl=0.0,
                unrealized_pnl=0.0,
                payload={"fills": [], "eod_summary": {"account": _account_dict(net_liq, 80_000.0)}},
            )
        )


def _snap(db, at: datetime, net_liq: float) -> None:
    from src.storage.models import PortfolioSnapshotRow

    with db() as s:
        s.add(
            PortfolioSnapshotRow(
                captured_at=at, source="monitor", account=_account_dict(net_liq, 80_000.0), positions=[]
            )
        )


def test_empty_history_is_empty_not_zero(db) -> None:
    series = account_value_series(db, "1m", now=NOW)
    assert series.points == []
    assert series.latest is None
    assert series.change_today is None


def test_daily_ranges_read_the_journal_and_end_at_the_latest_snapshot(db) -> None:
    _journal(db, date(2026, 10, 9), 100_000.0)
    _journal(db, date(2026, 10, 12), 101_000.0)
    _snap(db, NOW - timedelta(minutes=5), 101_500.0)

    series = account_value_series(db, "1m", now=NOW)
    assert [p.value for p in series.points] == [100_000.0, 101_000.0, 101_500.0]
    assert series.latest == 101_500.0
    assert series.previous_close == 101_000.0
    assert series.change_today == 500.0
    assert round(series.change_today_pct or 0, 4) == round(500 / 101_000 * 100, 4)


def test_one_month_drops_older_journal_days(db) -> None:
    _journal(db, date(2026, 8, 1), 90_000.0)
    _journal(db, date(2026, 10, 12), 101_000.0)
    series = account_value_series(db, "1m", now=NOW)
    assert [p.value for p in series.points] == [101_000.0]


def test_intraday_ranges_read_snapshots(db) -> None:
    _snap(db, NOW - timedelta(days=2), 99_000.0)
    _snap(db, NOW - timedelta(hours=3), 100_000.0)
    _snap(db, NOW - timedelta(minutes=5), 100_200.0)
    assert [p.value for p in account_value_series(db, "1d", now=NOW).points] == [100_000.0, 100_200.0]
    assert len(account_value_series(db, "1w", now=NOW).points) == 3


def test_an_unreadable_payload_is_skipped_not_zeroed(db) -> None:
    from src.storage.models import JournalRow

    with db() as s:
        s.add(JournalRow(entry_date=date(2026, 10, 12), realized_pnl=0.0, unrealized_pnl=0.0, payload={"x": 1}))
    _journal(db, date(2026, 10, 9), 100_000.0)
    series = account_value_series(db, "1m", now=NOW)
    assert [p.value for p in series.points] == [100_000.0]


def test_month_start_value_is_the_last_close_before_the_month(db) -> None:
    _journal(db, date(2026, 9, 29), 98_000.0)
    _journal(db, date(2026, 9, 30), 99_000.0)
    _journal(db, date(2026, 10, 1), 99_500.0)
    assert month_start_value(db, date(2026, 10, 1)) == 99_000.0
    assert month_start_value(db, date(2026, 9, 1)) is None
```

Check `tests/conftest.py`'s `db` fixture yields a session factory usable as `with db() as s:` and
that `_account_dict` is importable (it is a module-level function at line 121). If the `db`
fixture's name or shape differs, adapt the two helpers above to it and record the ruling.

- [x] **Step 2: Run to verify failure**

Run: `python -m pytest tests/test_reporting_account_value.py -q`
Expected: FAIL (`ModuleNotFoundError: src.reporting.account_value`).

- [x] **Step 3: Add the schemas** — append to `src/common/schemas.py` after `class EquityCurve`

```python
AccountValueRange = Literal["1d", "1w", "1m", "3m", "ytd", "all"]


class AccountValuePoint(BaseModel):
    at: datetime
    value: float


class AccountValueSeries(BaseModel):
    """Account value (net liquidation) over a range, for the Home hero chart.

    Daily ranges read the EOD journal and end with the newest intraday snapshot; 1d/1w read
    intraday portfolio snapshots (retention: `storage.portfolio_snapshot_retention_days`).
    Every figure is None when unknown - never 0.0.
    """

    range: AccountValueRange
    points: list[AccountValuePoint] = Field(default_factory=list)
    latest: float | None = None
    latest_at: datetime | None = None
    previous_close: float | None = None
    change_today: float | None = None
    change_today_pct: float | None = None
```

(`Literal`, `datetime`, `BaseModel`, `Field` are already imported in `schemas.py`; confirm.)

- [x] **Step 4: Implement `src/reporting/account_value.py`**

```python
"""Account value over time — read-only, like the rest of src/reporting/.

Two sources, one shape: the EOD journal (one net-liquidation point per trading day) and the
intraday `portfolio_snapshots` table (every ~15 minutes, 30-day retention). Imports nothing
from src.claude or src.api (tests/test_web_fence.py).
"""

from __future__ import annotations

from collections.abc import Callable
from contextlib import AbstractContextManager
from datetime import UTC, date, datetime, time, timedelta
from zoneinfo import ZoneInfo

from sqlalchemy import select
from sqlalchemy.orm import Session

from src.common.schemas import (
    AccountSnapshot,
    AccountValuePoint,
    AccountValueRange,
    AccountValueSeries,
)
from src.reporting.pnl import _net_liquidation_from_payload
from src.storage.models import JournalRow, PortfolioSnapshotRow

_ET = ZoneInfo("America/New_York")
_SessionFactory = Callable[[], AbstractContextManager[Session]]
_INTRADAY_DAYS = {"1d": 1, "1w": 7}
_DAILY_DAYS = {"1m": 31, "3m": 92}


def _as_utc(dt: datetime) -> datetime:
    return dt.replace(tzinfo=UTC) if dt.tzinfo is None else dt.astimezone(UTC)


def _naive_utc(dt: datetime) -> datetime:
    return _as_utc(dt).replace(tzinfo=None)


def _snap_value(row: PortfolioSnapshotRow) -> float | None:
    try:
        return AccountSnapshot.model_validate(row.account).net_liquidation
    except Exception:
        return None


def _close_at(day: date) -> datetime:
    """A journal day plotted at that day's 16:00 ET close."""
    return datetime.combine(day, time(16, 0), tzinfo=_ET).astimezone(UTC)


def account_value_series(
    session: _SessionFactory, range_key: AccountValueRange, *, now: datetime
) -> AccountValueSeries:
    today_et = _as_utc(now).astimezone(_ET).date()
    with session() as sess:
        journal = sess.execute(select(JournalRow).order_by(JournalRow.entry_date.asc())).scalars().all()
        latest_row = sess.execute(
            select(PortfolioSnapshotRow)
            .order_by(PortfolioSnapshotRow.captured_at.desc(), PortfolioSnapshotRow.id.desc())
            .limit(1)
        ).scalar_one_or_none()
        snaps: list[PortfolioSnapshotRow] = []
        if range_key in _INTRADAY_DAYS:
            start = _naive_utc(now - timedelta(days=_INTRADAY_DAYS[range_key]))
            snaps = list(
                sess.execute(
                    select(PortfolioSnapshotRow)
                    .where(PortfolioSnapshotRow.captured_at >= start)
                    .order_by(PortfolioSnapshotRow.captured_at.asc(), PortfolioSnapshotRow.id.asc())
                ).scalars()
            )

    daily = [(r.entry_date, _net_liquidation_from_payload(r.payload)) for r in journal]
    daily_known = [(d, v) for d, v in daily if v is not None]

    latest: float | None = None
    latest_at: datetime | None = None
    if latest_row is not None and (v := _snap_value(latest_row)) is not None:
        latest, latest_at = v, _as_utc(latest_row.captured_at)
    elif daily_known:
        latest, latest_at = daily_known[-1][1], _close_at(daily_known[-1][0])

    points: list[AccountValuePoint] = []
    if range_key in _INTRADAY_DAYS:
        for row in snaps:
            if (v := _snap_value(row)) is not None:
                points.append(AccountValuePoint(at=_as_utc(row.captured_at), value=v))
    else:
        if range_key == "ytd":
            start_day: date | None = date(today_et.year, 1, 1)
        elif range_key == "all":
            start_day = None
        else:
            start_day = today_et - timedelta(days=_DAILY_DAYS[range_key])
        for d, v in daily_known:
            if start_day is None or d >= start_day:
                points.append(AccountValuePoint(at=_close_at(d), value=v))
        if latest is not None and latest_at is not None and (not points or latest_at > points[-1].at):
            points.append(AccountValuePoint(at=latest_at, value=latest))

    before_today = [v for d, v in daily_known if d < today_et]
    previous_close = before_today[-1] if before_today else None
    change = latest - previous_close if latest is not None and previous_close is not None else None
    change_pct = change / previous_close * 100 if change is not None and previous_close else None

    return AccountValueSeries(
        range=range_key,
        points=points,
        latest=latest,
        latest_at=latest_at,
        previous_close=previous_close,
        change_today=change,
        change_today_pct=change_pct,
    )


def month_start_value(session: _SessionFactory, first_day: date) -> float | None:
    """Net liquidation at the last journal close before `first_day`; None when there is none."""
    with session() as sess:
        rows = sess.execute(
            select(JournalRow).where(JournalRow.entry_date < first_day).order_by(JournalRow.entry_date.desc())
        ).scalars()
        for r in rows:
            v = _net_liquidation_from_payload(r.payload)
            if v is not None:
                return v
    return None
```

- [x] **Step 5: Run the builder tests**

Run: `python -m pytest tests/test_reporting_account_value.py -q`
Expected: PASS (6 tests).

- [x] **Step 6: Write the failing route test** — `tests/test_api_portfolio_value.py`

```python
"""GET /portfolio/value — the Home hero's series. Empty is empty, never zero."""

from __future__ import annotations

from datetime import UTC, date, datetime, timedelta

import pytest

from tests.conftest import OWNER


@pytest.fixture()
def db(api_db):
    return api_db


def test_empty_is_200_with_no_points(client) -> None:
    r = client.get("/portfolio/value?range=1m", headers=OWNER)
    assert r.status_code == 200
    s = r.json()["series"]
    assert s["points"] == [] and s["latest"] is None and s["change_today"] is None


def test_one_month_series_carries_today_change(client, db, seed_journal_day, seed_portfolio_snapshot) -> None:
    yesterday = date.today() - timedelta(days=1)
    seed_journal_day(yesterday, net_liq=100_000.0)
    seed_portfolio_snapshot(captured_at=datetime.now(UTC) - timedelta(minutes=2), net_liq=100_400.0)
    s = client.get("/portfolio/value?range=1m", headers=OWNER).json()["series"]
    assert s["range"] == "1m"
    assert s["latest"] == 100_400.0
    assert s["points"][-1]["value"] == 100_400.0


def test_an_unknown_range_is_422(client) -> None:
    assert client.get("/portfolio/value?range=2y", headers=OWNER).status_code == 422


def test_it_requires_the_owner(client) -> None:
    assert client.get("/portfolio/value").status_code in (401, 403)
```

(`yesterday` may fall on a weekend or be "today" in ET near midnight; the assertions above do not
depend on `previous_close`, so they hold either way.)

- [x] **Step 7: Run to verify failure**

Run: `python -m pytest tests/test_api_portfolio_value.py -q`
Expected: FAIL (404 on `/portfolio/value`).

- [x] **Step 8: Add the model and route**

`src/api/models/portfolio.py` — append:

```python
class AccountValueResponse(Envelope):
    series: AccountValueSeries
```

and import `AccountValueSeries` from `src.common.schemas` at the top of that file.

`src/api/routers/portfolio.py` — add imports `from collections.abc import Iterator`,
`from contextlib import contextmanager`, `from src.common.schemas import AccountValueRange`,
`from src.reporting.account_value import account_value_series`, and `AccountValueResponse` to the
`src.api.models.portfolio` import list; then append:

```python
# ---------------------------------------------------------------------------
# Web overhaul Part 1, Task 7 — GET /portfolio/value
# ---------------------------------------------------------------------------


def _session_factory(db: TradingDb):
    """`src/reporting` takes a session factory; yield the request's read-only session."""

    @contextmanager
    def _factory() -> Iterator[TradingDb]:
        yield db

    return _factory


@router.get("/value", response_model=AccountValueResponse)
def portfolio_value(
    user: OwnerUser,  # noqa: ARG001
    db: TradingDb,
    range_: AccountValueRange = Query("1m", alias="range"),
) -> AccountValueResponse:
    """Account value over `range` for the Home hero. Computes nothing itself: a thin render
    of `account_value_series`. No history is a 200 with no points, never zeros."""
    now = datetime.now(UTC)
    return AccountValueResponse(
        as_of=now,
        series=account_value_series(_session_factory(db), range_, now=now),
    )
```

- [x] **Step 9: Run tests, regenerate OpenAPI, gate, commit**

```bash
python -m pytest tests/test_reporting_account_value.py tests/test_api_portfolio_value.py -q
python -c "import json; from src.api.main import create_app; print(json.dumps(create_app().openapi(), indent=2))" > docs/web/openapi.json
python -m pytest -q && ruff check . && mypy src
git add src/common/schemas.py src/reporting/account_value.py src/api/models/portfolio.py src/api/routers/portfolio.py tests/test_reporting_account_value.py tests/test_api_portfolio_value.py docs/web/openapi.json
git commit -m "feat(api): GET /portfolio/value - account value series for the Home hero"
```

Expected: full suite PASS (including `test_openapi_current` after regeneration and every
`test_web_fence.py` test: the new module writes nothing and imports no `src.claude`).

---

### Task 8: Spreads read surface — `GET /spreads/positions`

**Files:**
- Create: `src/api/spreads_db.py`, `src/api/models/spreads.py`, `src/api/routers/spreads.py`
- Modify: `src/api/main.py`
- Create: `tests/test_api_spreads.py`
- Modify: `tests/test_web_fence.py` (one new test)

**Interfaces:**
- Produces:
  - `spreads_read_session() -> ContextManager[Session | None]` (None when the file is missing or
    unreadable)
  - `SpreadPositionOut` (fields below), `SpreadPositionsResponse(as_of, available: bool,
    underlying: str, mode: str, positions: list[SpreadPositionOut])`
  - `GET /spreads/positions?status=open|closed|all&mode=paper|shadow|baseline&limit=50`
  - `read_spread_rows(session, *, mode: str, status: str, limit: int) -> list[dict]` (used again
    by Task 9)

- [x] **Step 1: Write the failing tests** — `tests/test_api_spreads.py`

```python
"""GET /spreads/positions — a read-only window onto data/spreads.db.

The API may not import src.spreads (tests/test_spreads_fence.py::NOT_SPREADS); it reads the
file through its own mode=ro engine with plain SQL. The tests may import the spreads models
to build a real schema - test files are not fenced.
"""

from __future__ import annotations

from datetime import date, datetime

import pytest
from sqlalchemy import create_engine
from sqlalchemy.exc import OperationalError
from sqlalchemy.orm import Session

from tests.conftest import OWNER


@pytest.fixture()
def spreads_file(tmp_path, monkeypatch):
    import src.api.spreads_db as sdb

    path = tmp_path / "spreads.db"
    monkeypatch.setattr(sdb, "_resolve_path", lambda: str(path))
    sdb.reset_engine()
    yield path
    sdb.reset_engine()


def _make_db(path, rows: list[dict]) -> None:
    from src.spreads.store import SpreadPositionRow, SpreadsBase

    eng = create_engine(f"sqlite:///{path}")
    SpreadsBase.metadata.create_all(eng)
    with Session(eng) as s:
        for r in rows:
            s.add(SpreadPositionRow(**r))
        s.commit()
    eng.dispose()


def _row(**over) -> dict:
    base = dict(
        spread_id="s1",
        mode="paper",
        side="put",
        expiry=date(2026, 10, 13),
        short_strike=580.0,
        long_strike=575.0,
        width=5.0,
        contracts_opened=1,
        contracts=1,
        entry_credit=0.42,
        entry_commission=1.3,
        opened_at=datetime(2026, 10, 13, 14, 0),
        status="open",
    )
    base.update(over)
    return base


def test_no_file_is_unavailable_not_an_error(client, spreads_file) -> None:
    r = client.get("/spreads/positions", headers=OWNER)
    assert r.status_code == 200
    assert r.json()["available"] is False
    assert r.json()["positions"] == []


def test_open_paper_positions_are_listed(client, spreads_file) -> None:
    _make_db(spreads_file, [_row(), _row(spread_id="s2", mode="shadow")])
    body = client.get("/spreads/positions?status=open", headers=OWNER).json()
    assert body["available"] is True
    assert body["mode"] == "paper"
    assert [p["spread_id"] for p in body["positions"]] == ["s1"]
    p = body["positions"][0]
    assert p["side"] == "put" and p["short_strike"] == 580.0 and p["entry_credit"] == 0.42
    assert p["exit_debit"] is None


def test_closed_filter_excludes_open(client, spreads_file) -> None:
    _make_db(spreads_file, [_row(), _row(spread_id="s3", status="closed", contracts=0, exit_debit=0.1)])
    body = client.get("/spreads/positions?status=closed", headers=OWNER).json()
    assert [p["spread_id"] for p in body["positions"]] == ["s3"]


def test_the_engine_cannot_write(spreads_file) -> None:
    import src.api.spreads_db as sdb
    from sqlalchemy import text

    _make_db(spreads_file, [_row()])
    with sdb.spreads_read_session() as s:
        assert s is not None
        with pytest.raises(OperationalError):
            s.execute(text("DELETE FROM spread_positions"))
            s.commit()
```

Append to `tests/test_web_fence.py`:

```python
def test_only_spreads_db_opens_the_spreads_file_in_the_api() -> None:
    """The API reaches data/spreads.db through one read-only module (web overhaul Task 8)."""
    api = ROOT / "src" / "api"
    users = [p.name for p in api.rglob("*.py") if "spreads_db_url_abs" in p.read_text()]
    assert users == ["spreads_db.py"]
    assert "mode=ro" in (api / "spreads_db.py").read_text()
```

(Use the module-level `ROOT` constant `tests/test_web_fence.py` already defines; if it is named
differently there, use that name.)

- [x] **Step 2: Run to verify failure**

Run: `python -m pytest tests/test_api_spreads.py tests/test_web_fence.py -q`
Expected: FAIL (`src.api.spreads_db` missing; fence test finds no `spreads_db.py`).

- [x] **Step 3: Implement `src/api/spreads_db.py`**

```python
"""Read-only access to data/spreads.db for the web API (web overhaul Part 1, Task 8).

The spreads fence forbids src/api from importing src.spreads, so this module opens the file
itself with SQLite mode=ro and reads it with plain SQL. It yields None when the file does not
exist yet or cannot be opened, so a route answers `available: false` instead of a 500.
"""

from __future__ import annotations

import logging
from collections.abc import Iterator
from contextlib import contextmanager
from pathlib import Path
from typing import Any

from sqlalchemy import create_engine, text
from sqlalchemy.engine import Engine
from sqlalchemy.orm import Session, sessionmaker

from src.common.config import get_config

log = logging.getLogger(__name__)

_engine: Engine | None = None
_SessionLocal: sessionmaker[Session] | None = None

_COLUMNS = (
    "spread_id, mode, side, expiry, short_strike, long_strike, width, contracts_opened, "
    "contracts, entry_credit, entry_commission, opened_at, status, exit_debit, "
    "exit_commission, exit_reason, closed_at, realized_pnl_usd"
)


def _resolve_path() -> str:
    """Filesystem path of data/spreads.db. Patched in tests."""
    url = get_config().spreads_db_url_abs()
    return url[len("sqlite:///") :] if url.startswith("sqlite:///") else url


def reset_engine() -> None:
    global _engine, _SessionLocal
    if _engine is not None:
        _engine.dispose()
    _engine = None
    _SessionLocal = None


@contextmanager
def spreads_read_session() -> Iterator[Session | None]:
    global _engine, _SessionLocal
    path = _resolve_path()
    if not Path(path).exists():
        yield None
        return
    try:
        if _engine is None:
            _engine = create_engine(
                f"sqlite:///file:{path}?mode=ro&uri=true",
                future=True,
                connect_args={"timeout": 5},
            )
            _SessionLocal = sessionmaker(bind=_engine, future=True, expire_on_commit=False)
        assert _SessionLocal is not None
        s = _SessionLocal()
        s.execute(text("SELECT 1"))
    except Exception as exc:  # noqa: BLE001 - a /spreads route degrades, never 500s
        log.debug("api spreads_db: cannot open %s: %s", path, exc)
        yield None
        return
    try:
        yield s
    finally:
        s.close()


def read_spread_rows(session: Session, *, mode: str, status: str, limit: int) -> list[dict[str, Any]]:
    """spread_positions rows as dicts, newest first. `status` is open|closed|all; "open"
    includes "expiring" (still held, settling today)."""
    where = "mode = :mode"
    if status == "open":
        where += " AND status IN ('open', 'expiring')"
    elif status == "closed":
        where += " AND status = 'closed'"
    sql = text(f"SELECT {_COLUMNS} FROM spread_positions WHERE {where} ORDER BY opened_at DESC LIMIT :limit")
    try:
        result = session.execute(sql, {"mode": mode, "limit": limit})
    except Exception as exc:  # noqa: BLE001 - a missing table on an old file reads as empty
        log.debug("api spreads_db: read failed: %s", exc)
        return []
    return [dict(r._mapping) for r in result]
```

(`where` is built only from the fixed literals above, never from request text; `mode`, `limit` are
bound parameters.)

- [x] **Step 4: Models and router**

`src/api/models/spreads.py`:

```python
"""Response models for the read-only spreads routes (web overhaul Part 1, Task 8)."""

from __future__ import annotations

from datetime import date, datetime
from typing import Literal

from pydantic import Field

from src.api.models.common import Envelope


class SpreadPositionOut(Envelope):
    spread_id: str
    mode: str
    side: Literal["put", "call"]
    expiry: date
    short_strike: float
    long_strike: float
    width: float
    contracts_opened: int
    contracts: int  # still open
    entry_credit: float  # per share
    entry_commission: float
    opened_at: datetime
    status: str  # open | expiring | closed
    exit_debit: float | None = None  # per share, qty-weighted; None while open
    exit_commission: float | None = None
    exit_reason: str | None = None
    closed_at: datetime | None = None
    realized_pnl_usd: float | None = None  # None while open, never 0.0


class SpreadPositionsResponse(Envelope):
    available: bool  # False when data/spreads.db does not exist or cannot be read
    underlying: str
    mode: str
    positions: list[SpreadPositionOut] = Field(default_factory=list)
```

`src/api/routers/spreads.py`:

```python
"""GET /spreads/positions — read-only, through src/api/spreads_db.py (never src.spreads)."""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Literal

from fastapi import APIRouter, Query

from src.api.deps import OwnerUser
from src.api.models.common import as_utc, as_utc_opt
from src.api.models.spreads import SpreadPositionOut, SpreadPositionsResponse
from src.api.spreads_db import read_spread_rows, spreads_read_session
from src.common.config import get_config

router = APIRouter(prefix="/spreads", tags=["spreads"])


@router.get("/positions", response_model=SpreadPositionsResponse)
def spread_positions(
    user: OwnerUser,  # noqa: ARG001
    status: Literal["open", "closed", "all"] = "open",
    mode: Literal["paper", "shadow", "baseline"] = "paper",
    limit: int = Query(50, ge=1, le=500),
) -> SpreadPositionsResponse:
    now = datetime.now(UTC)
    underlying = get_config().spreads.underlying
    with spreads_read_session() as s:
        if s is None:
            return SpreadPositionsResponse(as_of=now, available=False, underlying=underlying, mode=mode)
        rows = read_spread_rows(s, mode=mode, status=status, limit=limit)
    positions = [
        SpreadPositionOut(
            as_of=now,
            **{
                **r,
                "opened_at": as_utc(r["opened_at"]) if isinstance(r["opened_at"], datetime) else r["opened_at"],
                "closed_at": as_utc_opt(r["closed_at"]) if isinstance(r["closed_at"], datetime) else r["closed_at"],
                "realized_pnl_usd": r["realized_pnl_usd"] if r["status"] == "closed" else None,
            },
        )
        for r in rows
    ]
    return SpreadPositionsResponse(
        as_of=now, available=True, underlying=underlying, mode=mode, positions=positions
    )
```

Raw SQLite returns dates and datetimes as ISO strings through `text()`; Pydantic parses them.
`as_utc`/`as_utc_opt` exist in `src/api/models/common.py` (used by `pnl.py`); confirm their names.

`src/api/main.py`: add `spreads` to the routers import and `app.include_router(spreads.router)`
after `app.include_router(news.router)`.

- [x] **Step 5: Run tests, regenerate OpenAPI, gate, commit**

```bash
python -m pytest tests/test_api_spreads.py tests/test_web_fence.py tests/test_spreads_fence.py -q
python -c "import json; from src.api.main import create_app; print(json.dumps(create_app().openapi(), indent=2))" > docs/web/openapi.json
python -m pytest -q && ruff check . && mypy src
git add src/api/spreads_db.py src/api/models/spreads.py src/api/routers/spreads.py src/api/main.py tests/test_api_spreads.py tests/test_web_fence.py docs/web/openapi.json
git commit -m "feat(api): read-only GET /spreads/positions over data/spreads.db"
```

---

### Task 9: Monthly pay — `GET /pnl/month` and the income target setting

**Files:**
- Modify: `src/common/config.py` (WebCfg + `Config.web` + loader line)
- Modify: `config/examples/settings.yaml` (append `web:` section)
- Modify: `src/common/schemas.py` (append `MonthPay`)
- Create: `src/reporting/pay.py`, `tests/test_reporting_pay.py`
- Modify: `src/api/models/pnl.py`, `src/api/routers/pnl.py`
- Create: `tests/test_api_pnl_month.py`

**Interfaces:**
- Consumes: `build_legs`/`_filtered_legs` (pnl router), `month_start_value` (Task 7),
  `spreads_read_session`, `read_spread_rows` (Task 8).
- Produces:
  - `WebCfg.monthly_income_target_pct: float | None` (percent per month, 0 < x ≤ 20)
  - `MonthPay` (fields below)
  - `SpreadPayInput` dataclass; `build_month_pay(legs, spreads, *, month, strategy, month_start_value, target_pct, today) -> MonthPay`
  - `GET /pnl/month?month=YYYY-MM&strategy=all|csp|cc|spread&book=paper|live` → `MonthPayResponse(as_of, book, pay)`

- [x] **Step 1: Write the failing builder tests** — `tests/test_reporting_pay.py`

```python
"""The month's pay stub: premium in, buybacks and commissions out, net, against a target."""

from __future__ import annotations

from datetime import UTC, date, datetime

import pytest

from src.common.schemas import PnlLeg
from src.reporting.pay import SpreadPayInput, build_month_pay

OCT = date(2026, 10, 1)
TODAY = date(2026, 10, 13)


def leg(**over) -> PnlLeg:
    base = dict(
        candidate_id="c1",
        symbol="AAPL",
        underlying="AAPL",
        strategy="cash_secured_put",
        right="P",
        strike=180.0,
        expiry=date(2026, 11, 21),
        contracts=1,
        opened_at=datetime(2026, 10, 2, 15, 0),
        credit=235.0,
        debit=0.0,
        commissions=1.3,
        commissions_complete=True,
        days_held=0,
        outcome="still_open",
        is_live=False,
    )
    base.update(over)
    return PnlLeg(**base)


def pay(legs=(), spreads=(), **kw):
    args = dict(month=OCT, strategy="all", month_start_value=None, target_pct=None, today=TODAY)
    args.update(kw)
    return build_month_pay(list(legs), list(spreads), **args)


def test_an_empty_month_is_zero_income_with_no_target() -> None:
    p = pay()
    assert (p.premium_collected, p.bought_back, p.commissions, p.net) == (0.0, 0.0, 0.0, 0.0)
    assert p.target is None and p.progress_pct is None
    assert p.days_left == 18


def test_premium_counts_in_the_month_it_was_sold_and_buybacks_in_the_month_bought() -> None:
    sold_sep_bought_oct = leg(
        candidate_id="c2",
        opened_at=datetime(2026, 9, 20, 15, 0),
        closed_at=datetime(2026, 10, 5, 15, 0),
        credit=300.0,
        debit=120.0,
        commissions=2.6,
        outcome="closed_early",
    )
    p = pay([leg(), sold_sep_bought_oct])
    assert p.premium_collected == 235.0
    assert p.bought_back == 120.0
    assert p.commissions == pytest.approx(3.9)
    assert p.net == pytest.approx(235.0 - 120.0 - 3.9)
    assert (p.n_opened, p.n_closed) == (1, 1)


def test_month_is_new_york_time() -> None:
    # 2026-11-01 02:00 UTC is 2026-10-31 22:00 ET: October's pay.
    late = leg(opened_at=datetime(2026, 11, 1, 2, 0, tzinfo=UTC))
    assert pay([late]).premium_collected == 235.0
    assert pay([late], month=date(2026, 11, 1), today=date(2026, 11, 2)).premium_collected == 0.0


def test_strategy_filter_and_rolls_follow_their_side() -> None:
    cc = leg(candidate_id="cc1", strategy="covered_call", right="C", credit=64.0)
    put_roll = leg(candidate_id="r1", strategy="roll", right="P", credit=50.0)
    assert pay([leg(), cc, put_roll], strategy="csp").premium_collected == 285.0
    assert pay([leg(), cc, put_roll], strategy="cc").premium_collected == 64.0
    assert pay([leg(), cc], strategy="spread").premium_collected == 0.0


def test_spreads_count_in_all_and_spread_only() -> None:
    s = SpreadPayInput(
        opened_at=datetime(2026, 10, 13, 14, 0),
        closed_at=datetime(2026, 10, 13, 19, 0),
        entry_credit=0.42,
        exit_debit=0.10,
        contracts_opened=2,
        contracts_open=0,
        entry_commission=2.6,
        exit_commission=2.6,
    )
    p = pay(spreads=[s], strategy="spread")
    assert p.premium_collected == pytest.approx(84.0)
    assert p.bought_back == pytest.approx(20.0)
    assert p.commissions == pytest.approx(5.2)
    assert pay(spreads=[s], strategy="csp").premium_collected == 0.0
    assert pay(spreads=[s]).premium_collected == pytest.approx(84.0)


def test_target_is_a_percent_of_month_start_value() -> None:
    p = pay([leg()], month_start_value=200_000.0, target_pct=1.0)
    assert p.target == 2_000.0
    assert p.progress_pct == pytest.approx((235.0 - 1.3) / 2_000.0 * 100)


def test_no_month_start_value_means_no_target_not_zero() -> None:
    p = pay([leg()], month_start_value=None, target_pct=1.0)
    assert p.target is None and p.progress_pct is None
    assert p.target_pct == 1.0


def test_incomplete_commissions_are_flagged() -> None:
    assert pay([leg(commissions_complete=False)]).commissions_complete is False


def test_a_past_month_has_no_days_left() -> None:
    assert pay(month=date(2026, 9, 1)).days_left == 0
```

- [x] **Step 2: Run to verify failure**

Run: `python -m pytest tests/test_reporting_pay.py -q`
Expected: FAIL (`ModuleNotFoundError: src.reporting.pay`).

- [x] **Step 3: Schema, config, builder**

Append to `src/common/schemas.py` (after `AccountValueSeries`):

```python
class MonthPay(BaseModel):
    """One month's options income as a pay stub (web Home, DESIGN.md "October pay").

    `premium_collected` counts credit on legs SOLD in the month; `bought_back` counts debit on
    legs BOUGHT BACK in the month; a leg touching the month contributes all its commissions
    once. Months are New York calendar months. `target` is None - never 0.0 - when there is no
    target percentage or no month-start account value.
    """

    month: date  # first day of the month
    strategy: Literal["all", "csp", "cc", "spread"]
    premium_collected: float
    bought_back: float
    commissions: float
    commissions_complete: bool
    net: float
    n_opened: int
    n_closed: int
    month_start_value: float | None = None
    target_pct: float | None = None
    target: float | None = None
    progress_pct: float | None = None
    days_left: int
```

`src/common/config.py` — add before `class Config`:

```python
class WebCfg(BaseModel):
    """Display settings for the web console (web/). Nothing here reaches the trading path."""

    # Monthly income target as a percent of the month-start net liquidation value
    # (1.0 = 1% a month). None = no target; the pay card then says "No target set".
    monthly_income_target_pct: float | None = None

    @field_validator("monthly_income_target_pct")
    @classmethod
    def _sane_pct(cls, v: float | None) -> float | None:
        if v is not None and not (0 < v <= 20):
            raise ValueError("web.monthly_income_target_pct must be > 0 and <= 20 (percent per month)")
        return v
```

(Import `field_validator` from pydantic if `config.py` does not already.) Add to `class Config`
after `news: NewsCfg = ...`:

```python
    web: WebCfg = Field(default_factory=WebCfg)
```

and in `get_config()` after the `news=` line:

```python
        web=WebCfg(**(settings.get("web") or {})),
```

Append to `config/examples/settings.yaml`:

```yaml

# Web console (web/). Display-only: nothing here reaches the trading path.
web:
  # Monthly income target, as a percent of the account's month-start net liquidation value
  # (1.0 = 1% a month). null = no target: Home's pay card says "No target set".
  monthly_income_target_pct: null
```

Copy the same block into the private `config/settings.yaml` only if the operator asks; never
`git add` it (git-ignored).

`src/reporting/pay.py`:

```python
"""The month's pay stub — read-only, from the same PnlLeg list every P&L surface uses.

Imports nothing from src.claude or src.api. Spread positions arrive as plain
`SpreadPayInput` values the API builds from data/spreads.db, so this module never touches
src.spreads either.
"""

from __future__ import annotations

import calendar
from collections.abc import Iterable
from dataclasses import dataclass
from datetime import UTC, date, datetime
from typing import Literal
from zoneinfo import ZoneInfo

from src.common.schemas import MonthPay, PnlLeg

_ET = ZoneInfo("America/New_York")
OPTION_MULTIPLIER = 100

PayStrategy = Literal["all", "csp", "cc", "spread"]


@dataclass(frozen=True)
class SpreadPayInput:
    opened_at: datetime
    closed_at: datetime | None
    entry_credit: float  # per share
    exit_debit: float | None  # per share, qty-weighted
    contracts_opened: int
    contracts_open: int
    entry_commission: float
    exit_commission: float


def leg_kind(leg: PnlLeg) -> Literal["csp", "cc"] | None:
    s, r = str(leg.strategy), str(leg.right)
    if s == "cash_secured_put" or (s == "roll" and r == "P"):
        return "csp"
    if s == "covered_call" or (s == "roll" and r == "C"):
        return "cc"
    return None


def _et_date(dt: datetime | None) -> date | None:
    if dt is None:
        return None
    aware = dt.replace(tzinfo=UTC) if dt.tzinfo is None else dt
    return aware.astimezone(_ET).date()


def build_month_pay(
    legs: Iterable[PnlLeg],
    spreads: Iterable[SpreadPayInput],
    *,
    month: date,
    strategy: PayStrategy,
    month_start_value: float | None,
    target_pct: float | None,
    today: date,
) -> MonthPay:
    first = month.replace(day=1)
    last = first.replace(day=calendar.monthrange(first.year, first.month)[1])

    def in_month(dt: datetime | None) -> bool:
        d = _et_date(dt)
        return d is not None and first <= d <= last

    premium = bought = commissions = 0.0
    complete = True
    n_opened = n_closed = 0

    if strategy != "spread":
        for leg in legs:
            kind = leg_kind(leg)
            if kind is None or (strategy != "all" and kind != strategy):
                continue
            opened, closed = in_month(leg.opened_at), in_month(leg.closed_at)
            if opened:
                premium += leg.credit
                n_opened += 1
            if closed:
                bought += leg.debit
                n_closed += 1
            if opened or closed:
                commissions += leg.commissions
                complete = complete and leg.commissions_complete

    if strategy in ("all", "spread"):
        for s in spreads:
            if in_month(s.opened_at):
                premium += s.entry_credit * OPTION_MULTIPLIER * s.contracts_opened
                commissions += s.entry_commission
                n_opened += 1
            if in_month(s.closed_at):
                closed_qty = s.contracts_opened - s.contracts_open
                bought += (s.exit_debit or 0.0) * OPTION_MULTIPLIER * closed_qty
                commissions += s.exit_commission
                n_closed += 1

    net = premium - bought - commissions
    target = (
        month_start_value * target_pct / 100
        if month_start_value is not None and month_start_value > 0 and target_pct is not None
        else None
    )
    return MonthPay(
        month=first,
        strategy=strategy,
        premium_collected=premium,
        bought_back=bought,
        commissions=commissions,
        commissions_complete=complete,
        net=net,
        n_opened=n_opened,
        n_closed=n_closed,
        month_start_value=month_start_value,
        target_pct=target_pct,
        target=target,
        progress_pct=(net / target * 100) if target else None,
        days_left=(last - today).days if first <= today <= last else 0,
    )
```

- [x] **Step 4: Run the builder tests**

Run: `python -m pytest tests/test_reporting_pay.py -q`
Expected: PASS (9 tests). If `PnlLeg` rejects a field in the `leg()` helper (e.g. it has more
required fields than listed), add the missing required fields with neutral values and record it.

- [x] **Step 5: Write the failing route tests** — `tests/test_api_pnl_month.py`

```python
"""GET /pnl/month — a thin render of build_month_pay."""

from __future__ import annotations

from datetime import datetime
from zoneinfo import ZoneInfo

import pytest

from tests.conftest import OWNER

ET = ZoneInfo("America/New_York")


@pytest.fixture()
def db(api_db):
    return api_db


def this_month() -> str:
    return datetime.now(ET).strftime("%Y-%m")


def test_an_empty_month_is_zero_income_and_no_target(client) -> None:
    r = client.get(f"/pnl/month?month={this_month()}", headers=OWNER)
    assert r.status_code == 200
    pay = r.json()["pay"]
    assert pay["premium_collected"] == 0.0
    assert pay["target"] is None
    assert r.json()["book"] == "paper"


def test_a_put_sold_today_counts(client, db, seed_leg) -> None:
    seed_leg(candidate_id="c1", sold=(1, 2.35, 1.3), days_held=0)
    pay = client.get(f"/pnl/month?month={this_month()}&strategy=csp", headers=OWNER).json()["pay"]
    assert pay["premium_collected"] == pytest.approx(235.0)
    assert pay["commissions"] == pytest.approx(1.3)
    assert pay["strategy"] == "csp"


def test_a_bad_month_is_422(client) -> None:
    assert client.get("/pnl/month?month=2026-13", headers=OWNER).status_code == 422
    assert client.get("/pnl/month?strategy=iron_condor", headers=OWNER).status_code == 422


def test_spreads_unavailable_still_answers(client, monkeypatch, tmp_path) -> None:
    import src.api.spreads_db as sdb

    monkeypatch.setattr(sdb, "_resolve_path", lambda: str(tmp_path / "absent.db"))
    sdb.reset_engine()
    r = client.get(f"/pnl/month?month={this_month()}&strategy=spread", headers=OWNER)
    assert r.status_code == 200
    assert r.json()["pay"]["premium_collected"] == 0.0
```

- [x] **Step 6: Run to verify failure**

Run: `python -m pytest tests/test_api_pnl_month.py -q`
Expected: FAIL (404).

- [x] **Step 7: Model and route**

`src/api/models/pnl.py` — import `MonthPay` from `src.common.schemas` and append:

```python
class MonthPayResponse(Envelope):
    book: Literal["paper", "live"]
    pay: MonthPay
```

`src/api/routers/pnl.py` — add imports:

```python
from zoneinfo import ZoneInfo

from src.api.models.pnl import MonthPayResponse
from src.api.spreads_db import read_spread_rows, spreads_read_session
from src.common.config import get_config
from src.reporting.account_value import month_start_value
from src.reporting.pay import SpreadPayInput, build_month_pay
```

(merge `MonthPayResponse` into the existing `src.api.models.pnl` import list), then append:

```python
_ET = ZoneInfo("America/New_York")


def _spread_inputs(book: str) -> list[SpreadPayInput]:
    """Spread positions of the running book as plain inputs; [] when spreads.db is absent."""
    with spreads_read_session() as s:
        if s is None:
            return []
        rows = read_spread_rows(s, mode=book, status="all", limit=5000)

    def dt(v: object) -> datetime | None:
        if v is None:
            return None
        return v if isinstance(v, datetime) else datetime.fromisoformat(str(v))

    return [
        SpreadPayInput(
            opened_at=dt(r["opened_at"]) or datetime.now(UTC),
            closed_at=dt(r["closed_at"]),
            entry_credit=float(r["entry_credit"]),
            exit_debit=None if r["exit_debit"] is None else float(r["exit_debit"]),
            contracts_opened=int(r["contracts_opened"]),
            contracts_open=int(r["contracts"]),
            entry_commission=float(r["entry_commission"] or 0.0),
            exit_commission=float(r["exit_commission"] or 0.0),
        )
        for r in rows
    ]


@router.get("/month", response_model=MonthPayResponse)
def pnl_month(
    user: OwnerUser,  # noqa: ARG001
    db: TradingDb,
    month: str | None = Query(default=None, pattern=r"^\d{4}-(0[1-9]|1[0-2])$"),
    strategy: Literal["all", "csp", "cc", "spread"] = "all",
    book: Literal["paper", "live"] | None = None,
) -> MonthPayResponse:
    """The month's pay stub. `book` defaults to the running mode: a pay figure across paper
    and live is not a number that means anything (same rule as /pnl/summary). Spreads count
    only positions whose mode equals the book; shadow and baseline are simulations."""
    now = datetime.now(UTC)
    today = now.astimezone(_ET).date()
    first = (
        date(int(month[:4]), int(month[5:7]), 1) if month else today.replace(day=1)
    )
    chosen: Literal["paper", "live"] = book or ("live" if get_config().is_live else "paper")
    filters = _filter_params(None, None, None, None, None, chosen)
    legs = _filtered_legs(db, filters)
    pay = build_month_pay(
        legs,
        _spread_inputs(chosen) if strategy in ("all", "spread") else [],
        month=first,
        strategy=strategy,
        month_start_value=month_start_value(_session_factory(db), first),
        target_pct=get_config().web.monthly_income_target_pct,
        today=today,
    )
    return MonthPayResponse(as_of=now, book=chosen, pay=pay)
```

- [x] **Step 8: Run tests, regenerate OpenAPI, gate, commit**

```bash
python -m pytest tests/test_reporting_pay.py tests/test_api_pnl_month.py -q
python -c "import json; from src.api.main import create_app; print(json.dumps(create_app().openapi(), indent=2))" > docs/web/openapi.json
python -m pytest -q && ruff check . && mypy src
git add src/common/config.py src/common/schemas.py src/reporting/pay.py src/api/models/pnl.py src/api/routers/pnl.py config/examples/settings.yaml tests/test_reporting_pay.py tests/test_api_pnl_month.py docs/web/openapi.json
git commit -m "feat(api): GET /pnl/month pay stub with a % of account value income target"
```

---

## Section D — Home page (Tasks 10–13) · model: sonnet

The Home pieces in `web/features/home/`: hero, pay card, positions card, proposal cards and the
review sheet. Each consumes Section A primitives and Section C routes; none is mounted at `/` until
Task 14.

**Entry checks (run before Task 10):**

- [ ] **D1. Section C landed.** `git log --oneline main..HEAD` shows nine commits; Tasks 7–9 are ticked.
- [ ] **D2. Both gates green.** `python -m pytest -q && ruff check . && mypy src` and
  `cd web && npx vitest run && npx tsc --noEmit && npm run lint`.
- [ ] **D3. The routes answer.** `python -m pytest -q tests/test_api_portfolio_value.py tests/test_api_spreads.py tests/test_api_pnl_month.py tests/test_reporting_account_value.py tests/test_reporting_pay.py`
  passes.
- [ ] **D4. The hand-written client types will match the contract.** This prints the field names
  Task 10's `web/features/home/types.ts` must use; compare them with Task 10 Step 1 and fix the
  types there (not the API) if any differ, recording the ruling:

  ```bash
  python - <<'EOF'
  import json
  s = json.load(open("docs/web/openapi.json"))["components"]["schemas"]
  for name in ("AccountValueSeries", "AccountValuePoint", "MonthPay", "MonthPayResponse",
               "SpreadPositionOut", "SpreadPositionsResponse"):
      print(name, sorted(s[name]["properties"]))
  EOF
  ```

- [ ] **D5. The existing types Section D imports exist.** `grep -nE "export type (ApprovalSummary|ApprovalListResponse|ControlsResponse|ClaudeReviewPayload)\b" web/components/options/types.ts`
  lists four lines, and `grep -nE "export type (PositionsResponse|PositionGroup)\b" web/components/portfolio/types.ts`
  lists two. Different names → use the real ones in Tasks 12–13 and record the ruling.

**Section exit:** four more commits; every `web/features/home/*.test.*` green.

---

### Task 10: Home hero — account value, scrubbable chart, range chips

**Files:**
- Create: `web/features/home/types.ts`
- Create: `web/features/home/hero.ts`, `web/features/home/hero.test.ts`
- Create: `web/features/home/HeroChart.tsx`, `web/features/home/AccountHero.tsx`,
  `web/features/home/AccountHero.test.tsx`

**Interfaces:**
- Consumes: `SegmentedControl` (Task 2), `GET /portfolio/value` (Task 7), `--chart-line` token.
- Produces:
  - `types.ts`: `AccountValueResponse`, `MonthPayResponse`, `SpreadPositionsResponse`,
    `SpreadPosition`, `RangeKey`
  - `heroFigures(series, hoverIndex: number | null): { value: number | null; delta: number | null; deltaPct: number | null; caption: string }`
  - `HeroChart({ points, onHover })`, `AccountHero()`

- [ ] **Step 1: Types** — `web/features/home/types.ts`

```ts
/** Mirrors src/api/models (portfolio.py AccountValueResponse, pnl.py MonthPayResponse,
 *  spreads.py SpreadPositionsResponse). Hand-written like components/<domain>/types.ts. */

export type RangeKey = "1d" | "1w" | "1m" | "3m" | "ytd" | "all";

export type AccountValuePoint = { at: string; value: number };

export type AccountValueSeries = {
  range: RangeKey;
  points: AccountValuePoint[];
  latest: number | null;
  latest_at: string | null;
  previous_close: number | null;
  change_today: number | null;
  change_today_pct: number | null;
};

export type AccountValueResponse = { as_of: string; series: AccountValueSeries };

export type MonthPay = {
  month: string;
  strategy: "all" | "csp" | "cc" | "spread";
  premium_collected: number;
  bought_back: number;
  commissions: number;
  commissions_complete: boolean;
  net: number;
  n_opened: number;
  n_closed: number;
  month_start_value: number | null;
  target_pct: number | null;
  target: number | null;
  progress_pct: number | null;
  days_left: number;
};

export type MonthPayResponse = {
  as_of: string;
  book: "paper" | "live";
  pay: MonthPay;
  /** False when a spreads book is in scope but data/spreads.db could not be read. */
  spreads_available: boolean;
};

export type SpreadPosition = {
  spread_id: string;
  mode: string;
  side: "put" | "call";
  expiry: string;
  short_strike: number;
  long_strike: number;
  width: number;
  contracts_opened: number;
  contracts: number;
  entry_credit: number;
  entry_commission: number;
  opened_at: string;
  status: string;
  exit_debit: number | null;
  realized_pnl_usd: number | null;
};

export type SpreadPositionsResponse = {
  as_of: string;
  available: boolean;
  underlying: string;
  mode: string;
  positions: SpreadPosition[];
};
```

- [ ] **Step 2: Write the failing tests**

`web/features/home/hero.test.ts`:

```ts
import { describe, expect, it } from "vitest";
import { heroFigures } from "./hero";
import type { AccountValueSeries } from "./types";

const series: AccountValueSeries = {
  range: "1m",
  points: [
    { at: "2026-10-01T20:00:00Z", value: 100_000 },
    { at: "2026-10-12T20:00:00Z", value: 101_000 },
    { at: "2026-10-13T18:00:00Z", value: 101_500 },
  ],
  latest: 101_500,
  latest_at: "2026-10-13T18:00:00Z",
  previous_close: 101_000,
  change_today: 500,
  change_today_pct: 0.495,
};

describe("heroFigures", () => {
  it("shows the latest value and today's change when not scrubbing", () => {
    expect(heroFigures(series, null)).toEqual({ value: 101_500, delta: 500, deltaPct: 0.495, caption: "today" });
  });
  it("shows the scrubbed point and its change since the range start", () => {
    const f = heroFigures(series, 1);
    expect(f.value).toBe(101_000);
    expect(f.delta).toBe(1_000);
    expect(f.deltaPct).toBeCloseTo(1);
    expect(f.caption).toBe("Oct 12, 2026");
  });
  it("keeps unknowns unknown", () => {
    const empty = { ...series, points: [], latest: null, change_today: null, change_today_pct: null };
    expect(heroFigures(empty, null)).toEqual({ value: null, delta: null, deltaPct: null, caption: "today" });
  });
});
```

`web/features/home/AccountHero.test.tsx`:

```tsx
import { act, fireEvent, screen } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";
import { renderWithQuery, apiFetchMock } from "@/lib/test-query";

const chart = vi.hoisted(() => ({ handlers: [] as Array<(p: { time?: number }) => void> }));

vi.mock("lightweight-charts", () => ({
  ColorType: { Solid: "solid" },
  CrosshairMode: { Magnet: 1 },
  LineType: { Simple: 0 },
  createChart: () => ({
    addLineSeries: () => ({ setData: vi.fn(), applyOptions: vi.fn() }),
    subscribeCrosshairMove: (h: (p: { time?: number }) => void) => chart.handlers.push(h),
    unsubscribeCrosshairMove: vi.fn(),
    timeScale: () => ({ fitContent: vi.fn() }),
    applyOptions: vi.fn(),
    remove: vi.fn(),
  }),
}));

import { AccountHero } from "./AccountHero";

const body = (range: string) => ({
  as_of: new Date().toISOString(),
  series: {
    range,
    points: [
      { at: "2026-10-12T20:00:00Z", value: 101_000 },
      { at: "2026-10-13T18:00:00Z", value: 101_500 },
    ],
    latest: 101_500,
    latest_at: "2026-10-13T18:00:00Z",
    previous_close: 101_000,
    change_today: 500,
    change_today_pct: 0.495,
  },
});

describe("AccountHero", () => {
  it("shows the account value and today's signed change in words", async () => {
    renderWithQuery(<AccountHero />, { "/portfolio/value": body("1m") });
    expect(await screen.findByText("$101,500.00")).toBeInTheDocument();
    expect(screen.getByText("+$500.00 (0.50%) today")).toBeInTheDocument();
  });
  it("rewrites the number while scrubbing and restores it after", async () => {
    renderWithQuery(<AccountHero />, { "/portfolio/value": body("1m") });
    await screen.findByText("$101,500.00");
    const t = Math.floor(Date.parse("2026-10-12T20:00:00Z") / 1000);
    act(() => chart.handlers.at(-1)!({ time: t }));
    expect(screen.getByText("$101,000.00")).toBeInTheDocument();
    act(() => chart.handlers.at(-1)!({}));
    expect(screen.getByText("$101,500.00")).toBeInTheDocument();
  });
  it("refetches for a new range", async () => {
    renderWithQuery(<AccountHero />, { "/portfolio/value": body("1m") });
    await screen.findByText("$101,500.00");
    fireEvent.click(screen.getByRole("button", { name: "3M" }));
    expect(apiFetchMock.mock.calls.some((c) => c[0] === "/portfolio/value?range=3m")).toBe(true);
  });
  it("says there is no history yet instead of drawing an empty frame", async () => {
    const empty = body("1m");
    empty.series = { ...empty.series, points: [], latest: null, change_today: null, change_today_pct: null };
    renderWithQuery(<AccountHero />, { "/portfolio/value": empty });
    expect(await screen.findByText("No account history yet.")).toBeInTheDocument();
    expect(screen.getByText("n/a")).toBeInTheDocument();
  });
});
```

- [ ] **Step 3: Run to verify failure**

Run: `cd web && npx vitest run features/home`
Expected: FAIL (modules not found).

- [ ] **Step 4: Implement**

`web/features/home/hero.ts`:

```ts
import { formatDateTime } from "@/lib/format";
import type { AccountValueSeries } from "./types";

const DATE_ONLY = new Intl.DateTimeFormat("en-US", {
  month: "short",
  day: "numeric",
  year: "numeric",
  timeZone: "America/New_York",
});

export function heroFigures(
  series: AccountValueSeries,
  hoverIndex: number | null,
): { value: number | null; delta: number | null; deltaPct: number | null; caption: string } {
  if (hoverIndex === null || !series.points[hoverIndex]) {
    return {
      value: series.latest,
      delta: series.change_today,
      deltaPct: series.change_today_pct,
      caption: "today",
    };
  }
  const p = series.points[hoverIndex];
  const base = series.points[0].value;
  const delta = p.value - base;
  const intraday = series.range === "1d" || series.range === "1w";
  return {
    value: p.value,
    delta,
    deltaPct: base ? (delta / base) * 100 : null,
    caption: intraday ? formatDateTime(p.at) : DATE_ONLY.format(new Date(p.at)),
  };
}
```

`web/features/home/HeroChart.tsx`:

```tsx
"use client";

import { useEffect, useRef } from "react";
import { ColorType, CrosshairMode, createChart, type IChartApi, type UTCTimestamp } from "lightweight-charts";
import type { AccountValuePoint } from "./types";

function cssVar(name: string): string {
  if (typeof window === "undefined") return "";
  return getComputedStyle(document.documentElement).getPropertyValue(name).trim();
}

const toTime = (iso: string) => Math.floor(Date.parse(iso) / 1000) as UTCTimestamp;

/**
 * One ink line, no grid, no axes: the hero number above is the label. Scrubbing reports the
 * hovered point's index; leaving reports null. Colours are read from tokens at mount and
 * again whenever <html data-theme> changes. Data never animates in (lightweight-charts draws
 * it in place).
 */
export function HeroChart({
  points,
  onHover,
}: {
  points: AccountValuePoint[];
  onHover: (index: number | null) => void;
}) {
  const ref = useRef<HTMLDivElement>(null);
  const onHoverRef = useRef(onHover);
  onHoverRef.current = onHover;

  useEffect(() => {
    const el = ref.current;
    if (!el) return;
    const chart: IChartApi = createChart(el, {
      autoSize: true,
      height: 160,
      layout: { background: { type: ColorType.Solid, color: "transparent" }, textColor: cssVar("--text-muted") },
      grid: { vertLines: { visible: false }, horzLines: { visible: false } },
      rightPriceScale: { visible: false },
      timeScale: { visible: false, borderVisible: false },
      crosshair: { mode: CrosshairMode.Magnet, horzLine: { visible: false, labelVisible: false } },
      handleScale: false,
      handleScroll: false,
    });
    const series = chart.addLineSeries({
      color: cssVar("--chart-line"),
      lineWidth: 2,
      priceLineVisible: false,
      lastValueVisible: false,
      crosshairMarkerRadius: 4,
    });
    const times = points.map((p) => toTime(p.at));
    series.setData(points.map((p, i) => ({ time: times[i], value: p.value })));
    chart.timeScale().fitContent();

    chart.subscribeCrosshairMove((param: { time?: unknown }) => {
      if (param.time === undefined) return onHoverRef.current(null);
      const i = times.indexOf(param.time as UTCTimestamp);
      onHoverRef.current(i >= 0 ? i : null);
    });

    const observer = new MutationObserver(() => {
      series.applyOptions({ color: cssVar("--chart-line") });
      chart.applyOptions({ layout: { textColor: cssVar("--text-muted") } });
    });
    observer.observe(document.documentElement, { attributes: true, attributeFilter: ["data-theme"] });

    return () => {
      observer.disconnect();
      chart.remove();
    };
  }, [points]);

  return <div ref={ref} className="mt-3 h-[160px] w-full" aria-hidden="true" />;
}
```

`web/features/home/AccountHero.tsx`:

```tsx
"use client";

import clsx from "clsx";
import { useQuery } from "@tanstack/react-query";
import { useState } from "react";
import { SegmentedControl } from "@/components/ui/SegmentedControl";
import { apiFetch } from "@/lib/api";
import { UNKNOWN } from "@/lib/format";
import { formatMoneyCell } from "@/lib/money";
import { HeroChart } from "./HeroChart";
import { heroFigures } from "./hero";
import type { AccountValueResponse, RangeKey } from "./types";

const RANGES: { value: RangeKey; label: string }[] = [
  { value: "1d", label: "1D" },
  { value: "1w", label: "1W" },
  { value: "1m", label: "1M" },
  { value: "3m", label: "3M" },
  { value: "ytd", label: "YTD" },
  { value: "all", label: "All" },
];

const MINUS = "−";

function signedMoney(v: number): string {
  if (v === 0) return "$0";
  return `${v > 0 ? "+" : MINUS}${formatMoneyCell(Math.abs(v))}`;
}

export function AccountHero() {
  const [range, setRange] = useState<RangeKey>("1m");
  const [hover, setHover] = useState<number | null>(null);
  const { data, isError } = useQuery({
    queryKey: ["portfolio", "value", range],
    queryFn: () => apiFetch<AccountValueResponse>(`/portfolio/value?range=${range}`),
    refetchInterval: 60_000,
  });

  if (isError && !data) {
    return <p className="text-sm text-muted">Account value unavailable right now.</p>;
  }
  if (!data) return <div className="h-[260px]" aria-busy="true" />;

  const series = data.series;
  const f = heroFigures(series, hover);
  return (
    <section aria-label="Account value">
      <div className="text-[0.8125rem] text-muted">Account value</div>
      <div
        className={clsx(
          "tabular mt-0.5 text-[2.375rem] font-extrabold leading-[1.05] tracking-[-0.025em] md:text-[2.875rem]",
          f.value === null && "hatch text-unknown",
        )}
      >
        {f.value === null ? UNKNOWN : formatMoneyCell(f.value)}
      </div>
      <div
        className={clsx(
          "tabular mt-1 text-sm font-semibold",
          f.delta === null ? "text-muted" : f.delta < 0 ? "text-loss" : "text-gain",
        )}
      >
        {f.delta === null
          ? `${UNKNOWN} ${f.caption}`
          : `${signedMoney(f.delta)} (${f.deltaPct === null ? UNKNOWN : `${Math.abs(f.deltaPct).toFixed(2)}%`}) ${f.caption}`}
      </div>
      {series.points.length === 0 ? (
        <p className="mt-6 text-sm text-muted">No account history yet.</p>
      ) : (
        <HeroChart points={series.points} onHover={setHover} />
      )}
      <SegmentedControl
        label="Chart range"
        appearance="quiet"
        options={RANGES}
        value={range}
        onChange={(r) => {
          setHover(null);
          setRange(r);
        }}
        className="mt-2"
      />
    </section>
  );
}
```

- [ ] **Step 5: Run tests to verify they pass**

Run: `cd web && npx vitest run features/home`
Expected: PASS (7 tests). If the `+$500.00 (0.50%) today` assertion fails on rounding
(0.495 → "0.50" vs "0.49"), `toFixed(2)` of 0.495 is "0.49" in V8 (binary float). Change the
fixture's `change_today_pct` to `0.496`, keep the expected "0.50%", and record the ruling.

- [ ] **Step 6: Gate and commit**

```bash
cd web && npx vitest run && npx tsc --noEmit && npm run lint
cd .. && git add web/features/home
git commit -m "feat(web): Home hero - account value with a scrubbable chart and range chips"
```

---

### Task 11: The pay card

**Files:**
- Create: `web/features/home/PayCard.tsx`, `web/features/home/PayCard.test.tsx`

**Interfaces:**
- Consumes: `Card`, `Disclosure`, `Meter`, `Stub` (Tasks 2–3); `GET /pnl/month` (Task 9);
  `StrategyFilter` (Task 4); `MonthPayResponse` (Task 10 types).
- Produces: `PayCard({ strategy: StrategyFilter })`, `payStubLines(pay: MonthPay): StubLineData[]`

- [ ] **Step 1: Write the failing tests** — `web/features/home/PayCard.test.tsx`

```tsx
import { fireEvent, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";
import { apiFetchMock, renderWithQuery } from "@/lib/test-query";
import { PayCard } from "./PayCard";

function pay(over: Record<string, unknown> = {}) {
  return {
    as_of: new Date().toISOString(),
    book: "paper",
    spreads_available: true,
    pay: {
      month: "2026-10-01",
      strategy: "all",
      premium_collected: 1642,
      bought_back: 210,
      commissions: 18.4,
      commissions_complete: true,
      net: 1413.6,
      n_opened: 9,
      n_closed: 3,
      month_start_value: 200000,
      target_pct: 1,
      target: 2000,
      progress_pct: 70.68,
      days_left: 18,
      ...over,
    },
  };
}

describe("PayCard", () => {
  it("is collapsed by default and shows net, target and pace on one line", async () => {
    renderWithQuery(<PayCard strategy="all" />, { "/pnl/month": pay() });
    const toggle = await screen.findByRole("button", { name: /October pay/ });
    expect(toggle).toHaveAttribute("aria-expanded", "false");
    expect(screen.getByText("+$1,413.60")).toBeInTheDocument();
    expect(screen.getByText("of $2,000.00")).toBeInTheDocument();
    expect(screen.getByText("71% of target · 18 days left")).toBeInTheDocument();
    expect(screen.getByRole("progressbar", { name: "October target" })).toHaveAttribute("aria-valuenow", "71");
  });
  it("opens to the month's stub", async () => {
    renderWithQuery(<PayCard strategy="all" />, { "/pnl/month": pay() });
    fireEvent.click(await screen.findByRole("button", { name: /October pay/ }));
    expect(screen.getByRole("group", { name: "October pay stub" })).toBeInTheDocument();
    expect(screen.getByText("+$1,642.00")).toBeInTheDocument();
    expect(screen.getByText("−$210.00")).toBeInTheDocument();
    expect(screen.getByText("−$18.40")).toBeInTheDocument();
  });
  it("says No target set rather than a zero target", async () => {
    renderWithQuery(<PayCard strategy="all" />, {
      "/pnl/month": pay({ target: null, target_pct: null, progress_pct: null }),
    });
    expect(await screen.findByText("No target set · 18 days left")).toBeInTheDocument();
    expect(screen.queryByText(/of \$0/)).toBeNull();
  });
  it("marks commissions gross when some are missing", async () => {
    renderWithQuery(<PayCard strategy="all" />, { "/pnl/month": pay({ commissions_complete: false }) });
    fireEvent.click(await screen.findByRole("button", { name: /October pay/ }));
    expect(screen.getByText("Commissions (incomplete)")).toBeInTheDocument();
  });
  it("asks for the selected strategy", async () => {
    renderWithQuery(<PayCard strategy="csp" />, { "/pnl/month": pay({ strategy: "csp" }) });
    await screen.findByRole("button", { name: /October pay/ });
    expect(apiFetchMock.mock.calls.some((c) => c[0] === "/pnl/month?strategy=csp")).toBe(true);
  });
  it("says so in a sentence when the fetch fails", async () => {
    renderWithQuery(<PayCard strategy="all" />, {});
    expect(await screen.findByText("Could not load this month's pay.")).toBeInTheDocument();
  });
});
```

- [ ] **Step 2: Run to verify failure**

Run: `cd web && npx vitest run features/home/PayCard.test.tsx`
Expected: FAIL.

- [ ] **Step 3: Implement** — `web/features/home/PayCard.tsx`

```tsx
"use client";

import { useQuery } from "@tanstack/react-query";
import { Card } from "@/components/ui/Card";
import { Disclosure } from "@/components/ui/Disclosure";
import { Meter } from "@/components/ui/Meter";
import { Stub, formatStubValue, type StubLineData } from "@/components/ui/Stub";
import { apiFetch } from "@/lib/api";
import { formatMoneyCell } from "@/lib/money";
import type { StrategyFilter } from "@/lib/strategy";
import type { MonthPay, MonthPayResponse } from "./types";

const MONTH = new Intl.DateTimeFormat("en-US", { month: "long", timeZone: "UTC" });

export function payStubLines(pay: MonthPay): StubLineData[] {
  return [
    {
      label: "Premium collected",
      value: pay.premium_collected,
      format: "signed-money",
      explain: `Credit from ${pay.n_opened} position${pay.n_opened === 1 ? "" : "s"} sold this month.`,
    },
    {
      label: "Bought back",
      value: -pay.bought_back,
      format: "signed-money",
      explain: `What it cost to close ${pay.n_closed} position${pay.n_closed === 1 ? "" : "s"} this month.`,
    },
    {
      label: pay.commissions_complete ? "Commissions" : "Commissions (incomplete)",
      value: -pay.commissions,
      format: "signed-money",
      explain: pay.commissions_complete
        ? "IBKR commissions on every fill that touched this month."
        : "Some fills have no commission recorded yet, so this is a lower bound.",
    },
    { label: "Net so far", value: pay.net, format: "signed-money", total: true },
  ];
}

export function PayCard({ strategy }: { strategy: StrategyFilter }) {
  const { data, isError } = useQuery({
    queryKey: ["pnl", "month", strategy],
    queryFn: () => apiFetch<MonthPayResponse>(`/pnl/month?strategy=${strategy}`),
    refetchInterval: 60_000,
  });

  if (isError && !data) {
    return (
      <Card className="mt-4">
        <p className="text-sm text-muted">Could not load this month's pay.</p>
      </Card>
    );
  }
  if (!data) return <Card className="mt-4 h-[104px]" aria-busy="true" />;

  const pay = data.pay;
  const month = MONTH.format(new Date(pay.month));
  const pace =
    pay.target === null
      ? `No target set · ${pay.days_left} days left`
      : `${Math.round(Math.max(0, pay.progress_pct ?? 0))}% of target · ${pay.days_left} days left`;

  return (
    <Card className="mt-4">
      <Disclosure
        tone="plain"
        summary={
          <span className="block">
            <span className="flex items-baseline justify-between gap-2.5">
              <span className="text-base font-bold">{month} pay</span>
              <span className="tabular font-mono font-semibold">
                {formatStubValue(pay.net, "signed-money")}
                {pay.target !== null && (
                  <span className="ml-1 font-normal text-muted">of {formatMoneyCell(pay.target)}</span>
                )}
              </span>
            </span>
            <span className="mt-2.5 block">
              <Meter value={pay.net} max={pay.target} label={`${month} target`} />
            </span>
            <span className="mt-1.5 block text-[0.8125rem] text-muted">{pace}</span>
          </span>
        }
      >
        <Stub label={`${month} pay stub`} lines={payStubLines(pay)} />
      </Disclosure>
    </Card>
  );
}
```

Note: the `of $2,000.00` text sits inside the net span; the test finds it with `getByText("of
$2,000.00")` because it is its own `<span>`.

Spread income unavailable (Section C review I2): when `data.spreads_available` is `false` and the
strategy includes spreads (`all` or `spread`), the card says in a sentence that spread income is
unavailable (data/spreads.db could not be read) rather than showing `$0` for it or presenting the
wheel total as the whole month; add a test for it.

- [ ] **Step 4: Run tests to verify they pass**

Run: `cd web && npx vitest run features/home/PayCard.test.tsx`
Expected: PASS (6 tests).

- [ ] **Step 5: Gate and commit**

```bash
cd web && npx vitest run && npx tsc --noEmit && npm run lint
cd .. && git add web/features/home/PayCard.tsx web/features/home/PayCard.test.tsx
git commit -m "feat(web): collapsible monthly pay card with target meter and stub"
```

---

### Task 12: The positions card

**Files:**
- Create: `web/features/home/positions.ts`, `web/features/home/positions.test.ts`
- Create: `web/features/home/PositionsCard.tsx`, `web/features/home/PositionsCard.test.tsx`

**Interfaces:**
- Consumes: `Card`, `SegmentedControl`, `StatusWord` (Task 2); `PositionsResponse`/`PositionGroup`
  types (existing `web/components/portfolio/types.ts`); `SpreadPositionsResponse` (Task 10);
  `StrategyFilter`, `STRATEGY_LABEL` (Task 4).
- Produces:
  - `type PositionsFilter = StrategyFilter | "shares"`
  - `type PositionRow = { key; kind: "csp" | "cc" | "spread" | "shares" | "other"; title; status: { word: string; tone: StatusTone } | null; sub: string; value: number | null; valueLabel: string; sortKey: string }`
  - `buildPositionRows(groups, spreads, todayIso: string): PositionRow[]`
  - `PositionsCard({ strategy: StrategyFilter })`

- [ ] **Step 1: Write the failing tests**

Open `web/components/portfolio/types.ts` and confirm the exported names for the positions
response (`PositionsResponse`, `PositionGroup`, `OptionLeg`, `StockLeg`); use those names below
if they differ.

`web/features/home/positions.test.ts`:

```ts
import { describe, expect, it } from "vitest";
import { buildPositionRows } from "./positions";

const TODAY = "2026-10-13";

const optionLeg = (over: Record<string, unknown> = {}) => ({
  as_of: "",
  symbol: "AMD 261024P00150000",
  right: "P",
  strike: 150,
  expiry: "2026-10-24",
  dte: 11,
  contracts: 1,
  short: true,
  delta: -0.4,
  delta_source: "ibkr",
  market_price: 3.1,
  market_value: -310,
  unrealized_pnl: -212,
  moneyness: "itm",
  assignment_risk: true,
  ...over,
});

const group = (underlying: string, options: unknown[], stock: unknown = null) => ({
  as_of: "",
  underlying,
  stock,
  options,
});

describe("buildPositionRows", () => {
  it("names a short put a CSP and flags assignment risk in words", () => {
    const [row] = buildPositionRows([group("AMD", [optionLeg()])] as never, [], TODAY);
    expect(row.kind).toBe("csp");
    expect(row.title).toBe("AMD $150 put");
    expect(row.status).toEqual({ word: "Assignment likely", tone: "flag" });
    expect(row.value).toBe(-212);
    expect(row.valueLabel).toBe("open P&L");
  });
  it("says Expires today on expiry day, ahead of any other status", () => {
    const [row] = buildPositionRows(
      [group("MSFT", [optionLeg({ right: "C", strike: 430, dte: 0, expiry: TODAY, assignment_risk: true })])] as never,
      [],
      TODAY,
    );
    expect(row.kind).toBe("cc");
    expect(row.status).toEqual({ word: "Expires today", tone: "today" });
  });
  it("states moneyness only when it is known", () => {
    const rows = buildPositionRows(
      [
        group("KO", [optionLeg({ moneyness: "otm", assignment_risk: false })]),
        group("PEP", [optionLeg({ moneyness: null, assignment_risk: false })]),
      ] as never,
      [],
      TODAY,
    );
    expect(rows.find((r) => r.title.startsWith("KO"))!.status).toEqual({ word: "Out of the money", tone: "neutral" });
    expect(rows.find((r) => r.title.startsWith("PEP"))!.status).toBeNull();
  });
  it("notes a covered call's cover only when the shares are really held", () => {
    const stock = { as_of: "", shares: 100, avg_cost: 60, adjusted_cost_basis: null, market_price: 70, market_value: 7000, unrealized_pnl: 1000, unrealized_pnl_adjusted: null };
    const rows = buildPositionRows([group("KO", [optionLeg({ right: "C", strike: 72 })], stock)] as never, [], TODAY);
    expect(rows.find((r) => r.kind === "cc")!.sub).toContain("covered by 100 shares");
    expect(rows.find((r) => r.kind === "shares")!.title).toBe("KO · 100 shares");
  });
  it("keeps an unknown P&L unknown", () => {
    const [row] = buildPositionRows([group("AMD", [optionLeg({ unrealized_pnl: null })])] as never, [], TODAY);
    expect(row.value).toBeNull();
  });
  it("adds spreads with what they were sold for", () => {
    const rows = buildPositionRows([], [
      { spread_id: "s1", mode: "paper", side: "put", expiry: TODAY, short_strike: 580, long_strike: 575, width: 5, contracts_opened: 1, contracts: 1, entry_credit: 0.42, entry_commission: 1.3, opened_at: "", status: "open", exit_debit: null, realized_pnl_usd: null },
    ] as never, TODAY, "SPY");
    expect(rows[0]).toMatchObject({ kind: "spread", title: "SPY 580/575 put spread", value: 42, valueLabel: "sold for" });
    expect(rows[0].status).toEqual({ word: "Expires today", tone: "today" });
  });
  it("sorts by expiry, shares last", () => {
    const stock = { as_of: "", shares: 100, avg_cost: 60, adjusted_cost_basis: null, market_price: 70, market_value: 7000, unrealized_pnl: 1000, unrealized_pnl_adjusted: null };
    const rows = buildPositionRows(
      [group("A", [optionLeg({ expiry: "2026-11-21" })], stock), group("B", [optionLeg({ expiry: "2026-10-24" })])] as never,
      [],
      TODAY,
    );
    expect(rows.map((r) => r.kind)).toEqual(["csp", "csp", "shares"]);
    expect(rows[0].title.startsWith("B")).toBe(true);
  });
});
```

(`buildPositionRows` takes an optional 4th argument `underlying` for spreads, default "SPY", which
the card passes from the spreads response.)

`web/features/home/PositionsCard.test.tsx`:

```tsx
import { fireEvent, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";
import { renderWithQuery } from "@/lib/test-query";
import { PositionsCard } from "./PositionsCard";

const positions = {
  as_of: new Date().toISOString(),
  source: "monitor",
  degraded: false,
  groups: [
    {
      as_of: "",
      underlying: "AMD",
      stock: null,
      options: [
        { as_of: "", symbol: "x", right: "P", strike: 150, expiry: "2099-10-24", dte: 11, contracts: 1, short: true, delta: null, delta_source: null, market_price: null, market_value: null, unrealized_pnl: -212, moneyness: "itm", assignment_risk: true },
      ],
    },
    {
      as_of: "",
      underlying: "KO",
      stock: null,
      options: [
        { as_of: "", symbol: "y", right: "C", strike: 72, expiry: "2099-11-14", dte: 32, contracts: 1, short: true, delta: null, delta_source: null, market_price: null, market_value: null, unrealized_pnl: 30, moneyness: "otm", assignment_risk: false },
      ],
    },
  ],
};

const spreadsOff = { as_of: "", available: false, underlying: "SPY", mode: "paper", positions: [] };

describe("PositionsCard", () => {
  it("lists rows and counts per strategy chip", async () => {
    renderWithQuery(<PositionsCard strategy="all" />, { "/portfolio/positions": positions, "/spreads/positions": spreadsOff });
    expect(await screen.findByText("AMD $150 put")).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "All 2" })).toHaveAttribute("aria-pressed", "true");
    expect(screen.getByRole("button", { name: "CSPs 1" })).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "CCs 1" })).toBeInTheDocument();
  });
  it("follows the page's strategy switcher, and its own chips narrow further", async () => {
    const { rerender } = renderWithQuery(<PositionsCard strategy="cc" />, {
      "/portfolio/positions": positions,
      "/spreads/positions": spreadsOff,
    });
    expect(await screen.findByText("KO $72 call")).toBeInTheDocument();
    expect(screen.queryByText("AMD $150 put")).toBeNull();
    fireEvent.click(screen.getByRole("button", { name: "All 2" }));
    expect(screen.getByText("AMD $150 put")).toBeInTheDocument();
    rerender(<PositionsCard strategy="csp" />);
    expect(screen.queryByText("KO $72 call")).toBeNull();
  });
  it("renders option rows when spreads are unavailable", async () => {
    renderWithQuery(<PositionsCard strategy="all" />, { "/portfolio/positions": positions });
    expect(await screen.findByText("AMD $150 put")).toBeInTheDocument();
  });
  it("says nothing is open for an empty filter, in words", async () => {
    renderWithQuery(<PositionsCard strategy="spread" />, { "/portfolio/positions": positions, "/spreads/positions": spreadsOff });
    expect(await screen.findByText("No credit spreads open.")).toBeInTheDocument();
  });
  it("tells no snapshot apart from no positions", async () => {
    renderWithQuery(<PositionsCard strategy="all" />, {
      "/portfolio/positions": { ...positions, source: "none", groups: [] },
      "/spreads/positions": spreadsOff,
    });
    expect(await screen.findByText("No positions captured yet.")).toBeInTheDocument();
  });
});
```

`renderWithQuery` returns RTL's `render` result, so `rerender` is available; it re-renders inside
the same provider because RTL keeps the wrapper element tree: if `rerender` drops the provider
(RTL `rerender` replaces only `ui`, and `renderWithQuery` passed the provider as part of `ui`),
wrap the new element the same way: change the call to
`rerender(<QueryClientProvider client={...}>…)` is not available here, so instead re-render through
a small harness component that takes `strategy` as state. If needed, replace that test's body with:

```tsx
function Harness() {
  const [s, setS] = useState<StrategyFilter>("cc");
  return (<><button onClick={() => setS("csp")}>to csp</button><PositionsCard strategy={s} /></>);
}
```

and click "to csp" instead of calling `rerender`. Record which form was used.

- [ ] **Step 2: Run to verify failure**

Run: `cd web && npx vitest run features/home/positions.test.ts features/home/PositionsCard.test.tsx`
Expected: FAIL.

- [ ] **Step 3: Implement**

`web/features/home/positions.ts`:

```ts
import type { StatusTone } from "@/components/ui/StatusWord";
import type { PositionGroup } from "@/components/portfolio/types";
import type { SpreadPosition } from "./types";

export type PositionKind = "csp" | "cc" | "spread" | "shares" | "other";

export type PositionRow = {
  key: string;
  kind: PositionKind;
  title: string;
  status: { word: string; tone: StatusTone } | null;
  sub: string;
  value: number | null;
  valueLabel: string;
  /** ISO expiry, or "~" so expiry-less rows (shares) sort last. */
  sortKey: string;
};

const DAY = new Intl.DateTimeFormat("en-US", { weekday: "short", day: "numeric", month: "short", timeZone: "UTC" });

function expiryLabel(iso: string | null, dte: number | null): string {
  if (!iso) return "expiry n/a";
  const d = DAY.format(new Date(`${iso}T00:00:00Z`));
  return dte === null ? d : `${d} · ${dte}d`;
}

const money = (v: number) => `$${v.toLocaleString("en-US", { maximumFractionDigits: 2 })}`;

export function buildPositionRows(
  groups: PositionGroup[],
  spreads: SpreadPosition[],
  todayIso: string,
  underlying = "SPY",
): PositionRow[] {
  const rows: PositionRow[] = [];
  for (const g of groups) {
    const shares = g.stock?.shares ?? 0;
    for (const o of g.options) {
      const kind: PositionKind = !o.short ? "other" : o.right === "P" ? "csp" : o.right === "C" ? "cc" : "other";
      const word = o.right === "P" ? "put" : o.right === "C" ? "call" : "option";
      const strike = o.strike === null ? "strike n/a" : money(o.strike);
      let status: PositionRow["status"] = null;
      if (o.expiry === todayIso || o.dte === 0) status = { word: "Expires today", tone: "today" };
      else if (o.assignment_risk) status = { word: "Assignment likely", tone: "flag" };
      else if (o.moneyness === "itm") status = { word: "In the money", tone: "flag" };
      else if (o.moneyness === "atm") status = { word: "At the money", tone: "neutral" };
      else if (o.moneyness === "otm") status = { word: "Out of the money", tone: "neutral" };
      const parts = [expiryLabel(o.expiry, o.dte)];
      if (kind === "cc" && shares >= 100 * o.contracts) parts.push(`covered by ${100 * o.contracts} shares`);
      if (o.contracts > 1) parts.push(`${o.contracts} contracts`);
      rows.push({
        key: `${g.underlying}:${o.symbol}`,
        kind,
        title: `${o.short ? "" : "Long "}${g.underlying} ${strike} ${word}`,
        status,
        sub: parts.join(" · "),
        value: o.unrealized_pnl,
        valueLabel: "open P&L",
        sortKey: o.expiry ?? "~",
      });
    }
    if (g.stock) {
      const s = g.stock;
      const basis = s.adjusted_cost_basis !== null ? ` · adjusted ${money(s.adjusted_cost_basis)}` : "";
      rows.push({
        key: `${g.underlying}:stock`,
        kind: "shares",
        title: `${g.underlying} · ${s.shares} shares`,
        status: null,
        sub: `avg ${money(s.avg_cost)}${basis}`,
        value: s.unrealized_pnl_adjusted ?? s.unrealized_pnl,
        valueLabel: "open P&L",
        sortKey: "~",
      });
    }
  }
  for (const p of spreads) {
    rows.push({
      key: `spread:${p.spread_id}`,
      kind: "spread",
      title: `${underlying} ${p.short_strike}/${p.long_strike} ${p.side} spread`,
      status:
        p.expiry === todayIso
          ? { word: "Expires today", tone: "today" }
          : p.status === "expiring"
            ? { word: "Expiring", tone: "neutral" }
            : { word: "Open", tone: "neutral" },
      sub: `${expiryLabel(p.expiry, null)} · daily spreads book · ${p.mode}`,
      value: p.entry_credit * 100 * p.contracts,
      valueLabel: "sold for",
      sortKey: p.expiry,
    });
  }
  return rows.sort((a, b) => (a.sortKey < b.sortKey ? -1 : a.sortKey > b.sortKey ? 1 : a.title.localeCompare(b.title)));
}
```

`web/features/home/PositionsCard.tsx`:

```tsx
"use client";

import clsx from "clsx";
import { useQuery } from "@tanstack/react-query";
import { useEffect, useState } from "react";
import { Card } from "@/components/ui/Card";
import { SegmentedControl } from "@/components/ui/SegmentedControl";
import { StatusWord } from "@/components/ui/StatusWord";
import type { PositionsResponse } from "@/components/portfolio/types";
import { apiFetch } from "@/lib/api";
import { UNKNOWN } from "@/lib/format";
import { formatMoneyCell } from "@/lib/money";
import { STRATEGY_LABEL, type StrategyFilter } from "@/lib/strategy";
import { buildPositionRows, type PositionRow } from "./positions";
import type { SpreadPositionsResponse } from "./types";

type PositionsFilter = StrategyFilter | "shares";

const FILTERS: PositionsFilter[] = ["all", "csp", "cc", "spread", "shares"];
const LABEL: Record<PositionsFilter, string> = { ...STRATEGY_LABEL, shares: "Shares" };

function matches(row: PositionRow, f: PositionsFilter): boolean {
  return f === "all" || row.kind === f;
}

function todayNewYork(): string {
  return new Intl.DateTimeFormat("en-CA", { timeZone: "America/New_York" }).format(new Date());
}

export function PositionsCard({ strategy }: { strategy: StrategyFilter }) {
  const [filter, setFilter] = useState<PositionsFilter>(strategy);
  useEffect(() => setFilter(strategy), [strategy]);

  // Same key as <PositionsPanel/> on /portfolio: one request when both are mounted.
  const positions = useQuery({
    queryKey: ["portfolio", "positions"],
    queryFn: () => apiFetch<PositionsResponse>("/portfolio/positions"),
    refetchInterval: 60_000,
  });
  const spreads = useQuery({
    queryKey: ["spreads", "positions", "open"],
    queryFn: () => apiFetch<SpreadPositionsResponse>("/spreads/positions?status=open"),
    refetchInterval: 60_000,
  });

  const spreadRows = spreads.data?.available ? spreads.data.positions : [];
  const rows = positions.data
    ? buildPositionRows(positions.data.groups, spreadRows, todayNewYork(), spreads.data?.underlying)
    : [];
  const visible = rows.filter((r) => matches(r, filter));
  const options = FILTERS.map((f) => ({
    value: f,
    label: LABEL[f],
    count: positions.data ? rows.filter((r) => matches(r, f)).length : null,
  }));

  let empty: string | null = null;
  if (positions.isError && !positions.data) empty = "Positions unavailable right now.";
  else if (positions.data?.source === "none") empty = "No positions captured yet.";
  else if (positions.data && visible.length === 0)
    empty = filter === "all" ? "No open positions." : `No ${LABEL[filter].toLowerCase()} open.`;

  return (
    <Card className="mt-4" aria-labelledby="positions-title">
      <div className="flex items-baseline justify-between">
        <h2 id="positions-title" className="text-base font-bold">
          Positions
        </h2>
        <span className="text-[0.8125rem] text-muted">Sorted by expiry</span>
      </div>
      <SegmentedControl
        label="Position type"
        appearance="chips"
        options={options}
        value={filter}
        onChange={setFilter}
        className="mb-1 mt-2"
      />
      {empty !== null ? (
        <p className="py-3 text-sm text-muted">{empty}</p>
      ) : (
        <ul>
          {visible.map((r) => (
            <li key={r.key} className="grid grid-cols-[1fr_auto] gap-x-2.5 border-t border-border py-[11px] text-sm first:border-t-0">
              <div className="min-w-0">
                <span className="font-bold">{r.title}</span>
                {r.status && (
                  <span className="ml-1.5 align-[1px]">
                    <StatusWord tone={r.status.tone}>{r.status.word}</StatusWord>
                  </span>
                )}
                <div className="text-[0.8125rem] text-muted">{r.sub}</div>
              </div>
              <div className="tabular text-right font-semibold">
                <span
                  className={clsx(
                    r.value === null
                      ? "hatch text-unknown"
                      : r.valueLabel === "open P&L" && r.value < 0
                        ? "text-loss"
                        : r.valueLabel === "open P&L" && r.value > 0
                          ? "text-gain"
                          : "",
                  )}
                >
                  {r.value === null
                    ? UNKNOWN
                    : r.valueLabel === "open P&L" && r.value > 0
                      ? `+${formatMoneyCell(r.value)}`
                      : formatMoneyCell(r.value)}
                </span>
                <div className="text-[0.8125rem] font-normal text-muted">{r.valueLabel}</div>
              </div>
            </li>
          ))}
        </ul>
      )}
    </Card>
  );
}
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `cd web && npx vitest run features/home/positions.test.ts features/home/PositionsCard.test.tsx`
Expected: PASS (12 tests).

- [ ] **Step 5: Gate and commit**

```bash
cd web && npx vitest run && npx tsc --noEmit && npm run lint
cd .. && git add web/features/home/positions.ts web/features/home/positions.test.ts web/features/home/PositionsCard.tsx web/features/home/PositionsCard.test.tsx
git commit -m "feat(web): positions card with strategy chips and status words"
```

---

### Task 13: Proposal cards, the Why disclosure and the review sheet

**Files:**
- Create: `web/features/home/proposal.ts`, `web/features/home/proposal.test.ts`
- Create: `web/features/home/WhyDisclosure.tsx`, `ProposalCard.tsx`, `ReviewSheet.tsx`,
  `NeedsYou.tsx`, `ProposalsBanner.tsx`, and `web/features/home/proposals.test.tsx`

**Interfaces:**
- Consumes: `Card`, `Button`, `Disclosure`, `Stub`, `Sheet` (Tasks 2–3); `kindOf`,
  `matchesFilter`, `STRATEGY_EYEBROW` (Task 4); existing `DecideControls`, `ApprovalSummary`,
  `ApprovalListResponse`, `ControlsResponse`, `ClaudeReviewPayload`; `useControls` (Task 6).
- Produces:
  - `proposalStub(a, today: Date): StubLineData[]`, `proposalSentence(a): string`,
    `daysToExpiry(expiry: string | null, today: Date): number | null`
  - `WhyDisclosure({ review })`, `ProposalCard({ approval, onReview })`,
    `ReviewSheet({ approval, open, onClose })`, `NeedsYou({ strategy })`,
    `ProposalsBanner({ strategy })`

- [ ] **Step 1: Write the failing tests**

`web/features/home/proposal.test.ts`:

```ts
import { describe, expect, it } from "vitest";
import { daysToExpiry, proposalSentence, proposalStub } from "./proposal";

const TODAY = new Date("2026-10-13T12:00:00Z");
const csp = { underlying: "AAPL", strategy: "cash_secured_put", right: "P", strike: 180, contracts: 1, premium: 2.35, expiry: "2026-11-21" };

describe("daysToExpiry", () => {
  it("counts calendar days", () => {
    expect(daysToExpiry("2026-11-21", TODAY)).toBe(39);
    expect(daysToExpiry(null, TODAY)).toBeNull();
  });
});

describe("proposalSentence", () => {
  it("states a put's consequence first", () => {
    expect(proposalSentence(csp)).toBe(
      "You collect $235.00. If AAPL closes under $180 on Nov 21, you buy 100 shares at $180.",
    );
  });
  it("states a call's consequence first", () => {
    expect(proposalSentence({ ...csp, strategy: "covered_call", right: "C", strike: 72, premium: 0.64, underlying: "KO", expiry: "2026-11-14" })).toBe(
      "You collect $64.00. If KO closes over $72 on Nov 14, your 100 shares are sold at $72.",
    );
  });
  it("never invents a premium", () => {
    expect(proposalSentence({ ...csp, premium: null })).toBe(
      "Premium not known yet. If AAPL closes under $180 on Nov 21, you buy 100 shares at $180.",
    );
  });
});

describe("proposalStub", () => {
  it("shows the put's math line by line", () => {
    const lines = proposalStub(csp, TODAY);
    expect(lines.map((l) => [l.label, l.value])).toEqual([
      ["Premium", 235],
      ["Cash held aside", 18000],
      ["Return in 39 days", (235 / 18000) * 100],
      ["A year", (235 / 18000) * 100 * (365 / 39)],
    ]);
    expect(lines[3].total).toBe(true);
  });
  it("uses the strike value for a call", () => {
    const lines = proposalStub({ ...csp, strategy: "covered_call", right: "C", strike: 72, premium: 0.64 }, TODAY);
    expect(lines[1]).toMatchObject({ label: "If called, you sell for", value: 7200 });
  });
  it("turns every derived line to n/a when the premium is unknown", () => {
    const lines = proposalStub({ ...csp, premium: null }, TODAY);
    expect(lines.map((l) => l.value)).toEqual([null, 18000, null, null]);
  });
  it("has no annual figure on expiry day", () => {
    const lines = proposalStub({ ...csp, expiry: "2026-10-13" }, TODAY);
    expect(lines[3].value).toBeNull();
  });
});
```

`web/features/home/proposals.test.tsx`:

```tsx
import { fireEvent, screen, within } from "@testing-library/react";
import { describe, expect, it } from "vitest";
import { renderWithQuery } from "@/lib/test-query";
import { NeedsYou } from "./NeedsYou";
import { ProposalsBanner } from "./ProposalsBanner";

const review = {
  why_attractive: "IV rank 62, premium 18% above fair value.",
  risks: "Earnings Oct 30 sits inside the window.",
  tradeoffs: "",
  assignment_considerations: "",
  rolling_considerations: "Roll down and out, or take the shares at $177.65 net.",
  summary: "",
};

function approval(id: number, over: Record<string, unknown> = {}) {
  return {
    as_of: "",
    id,
    candidate_id: `c${id}`,
    status: "pending",
    underlying: "AAPL",
    strategy: "cash_secured_put",
    right: "P",
    strike: 180,
    expiry: "2099-11-21",
    contracts: 1,
    premium: 2.35,
    blended_score: 0.7,
    created_at: "2026-10-13T13:00:00Z",
    expires_at: null,
    decided_at: null,
    order_state: null,
    source: "scan",
    review,
    rationale_tags: [],
    ...over,
  };
}

const controls = {
  as_of: "",
  autonomy: { level: "approve", label: "Approve each trade" },
  rungs: [],
  halted: false,
  halt_reason: null,
  halted_at: null,
  mode: "paper",
  drain_healthy: true,
  drain_last_seen: null,
  pending_commands: 0,
};

const list = (...a: unknown[]) => ({ as_of: "", approvals: a });

describe("NeedsYou", () => {
  it("shows Claude's review collapsed, above the stub", async () => {
    renderWithQuery(<NeedsYou strategy="all" />, {
      "/options/approvals": list(approval(1)),
      "/options/controls": controls,
    });
    const card = await screen.findByRole("article", { name: "AAPL · Sell $180 put" });
    const why = within(card).getByRole("button", { name: /Why this trade/ });
    expect(why).toHaveAttribute("aria-expanded", "false");
    const stub = within(card).getByRole("group", { name: "AAPL put math" });
    expect(why.compareDocumentPosition(stub) & Node.DOCUMENT_POSITION_FOLLOWING).toBeTruthy();
    fireEvent.click(why);
    expect(within(card).getByText("IV rank 62, premium 18% above fair value.")).toBeVisible();
    expect(within(card).getByText(/Claude's review/)).toBeInTheDocument();
  });
  it("leaves out the Why section when there is no review", async () => {
    renderWithQuery(<NeedsYou strategy="all" />, {
      "/options/approvals": list(approval(1, { review: null })),
      "/options/controls": controls,
    });
    const card = await screen.findByRole("article", { name: "AAPL · Sell $180 put" });
    expect(within(card).queryByRole("button", { name: /Why this trade/ })).toBeNull();
  });
  it("filters by strategy", async () => {
    renderWithQuery(<NeedsYou strategy="cc" />, {
      "/options/approvals": list(approval(1), approval(2, { strategy: "covered_call", right: "C", underlying: "KO", strike: 72 })),
      "/options/controls": controls,
    });
    expect(await screen.findByRole("article", { name: "KO · Sell $72 call" })).toBeInTheDocument();
    expect(screen.queryByRole("article", { name: "AAPL · Sell $180 put" })).toBeNull();
  });
  it("says spreads need nothing from you", async () => {
    renderWithQuery(<NeedsYou strategy="spread" />, {
      "/options/approvals": list(approval(1)),
      "/options/controls": controls,
    });
    expect(await screen.findByText("Credit spreads trade on their own in paper. Nothing here needs you.")).toBeInTheDocument();
  });
  it("says so when nothing is waiting", async () => {
    renderWithQuery(<NeedsYou strategy="all" />, { "/options/approvals": list(), "/options/controls": controls });
    expect(await screen.findByText("Nothing needs you right now.")).toBeInTheDocument();
  });
  it("Review opens the sheet with the decide controls; the card itself decides nothing", async () => {
    renderWithQuery(<NeedsYou strategy="all" />, {
      "/options/approvals": list(approval(1)),
      "/options/controls": controls,
    });
    const card = await screen.findByRole("article", { name: "AAPL · Sell $180 put" });
    expect(within(card).queryByRole("button", { name: /Approve/ })).toBeNull();
    fireEvent.click(within(card).getByRole("button", { name: "Review" }));
    const sheet = screen.getByRole("dialog", { name: "Review trade" });
    expect(within(sheet).getByRole("button", { name: /Approve/ })).toBeInTheDocument();
    expect(within(card).getByRole("link", { name: "Details" })).toHaveAttribute("href", "/trades/1");
  });
});

describe("ProposalsBanner", () => {
  it("counts and names what is waiting and links to Trades", async () => {
    renderWithQuery(<ProposalsBanner strategy="all" />, {
      "/options/approvals": list(approval(1), approval(2, { strategy: "covered_call", right: "C", underlying: "KO", strike: 72 })),
    });
    expect(await screen.findByText("2 proposals need you")).toBeInTheDocument();
    expect(screen.getByText("AAPL put · KO call")).toBeInTheDocument();
    expect(screen.getByRole("link", { name: /Open/ })).toHaveAttribute("href", "/trades");
  });
  it("renders nothing when nothing is waiting", async () => {
    const { container } = renderWithQuery(<ProposalsBanner strategy="all" />, { "/options/approvals": list() });
    await new Promise((r) => setTimeout(r, 0));
    expect(container.textContent).toBe("");
  });
});
```

Before Step 2, open `web/components/options/DecideControls.test.tsx` and confirm the Approve
button's accessible name (e.g. "Approve" vs "Approve trade"); adjust the `/Approve/` matchers above
only if it differs.

- [ ] **Step 2: Run to verify failure**

Run: `cd web && npx vitest run features/home/proposal.test.ts features/home/proposals.test.tsx`
Expected: FAIL.

- [ ] **Step 3: Implement**

`web/features/home/proposal.ts`:

```ts
import type { StubLineData } from "@/components/ui/Stub";
import { formatMoneyCell } from "@/lib/money";
import { kindOf } from "@/lib/strategy";

export type ProposalFields = {
  underlying: string;
  strategy: string;
  right: string;
  strike: number;
  contracts: number;
  premium: number | null; // per share
  expiry: string | null;
};

const SHORT_DATE = new Intl.DateTimeFormat("en-US", { month: "short", day: "numeric", timeZone: "UTC" });

const dollars = (v: number) => `$${v.toLocaleString("en-US", { maximumFractionDigits: 2 })}`;

export function daysToExpiry(expiry: string | null, today: Date): number | null {
  if (!expiry) return null;
  const end = Date.parse(`${expiry}T00:00:00Z`);
  const start = Date.UTC(today.getUTCFullYear(), today.getUTCMonth(), today.getUTCDate());
  return Math.round((end - start) / 86_400_000);
}

export function proposalSentence(a: ProposalFields): string {
  const shares = 100 * a.contracts;
  const when = a.expiry ? SHORT_DATE.format(new Date(`${a.expiry}T00:00:00Z`)) : "expiry";
  const collect =
    a.premium === null ? "Premium not known yet." : `You collect ${formatMoneyCell(a.premium * 100 * a.contracts)}.`;
  const k = kindOf(a.strategy, a.right);
  if (k === "cc") {
    return `${collect} If ${a.underlying} closes over ${dollars(a.strike)} on ${when}, your ${shares} shares are sold at ${dollars(a.strike)}.`;
  }
  return `${collect} If ${a.underlying} closes under ${dollars(a.strike)} on ${when}, you buy ${shares} shares at ${dollars(a.strike)}.`;
}

export function proposalStub(a: ProposalFields, today: Date): StubLineData[] {
  const premium = a.premium === null ? null : a.premium * 100 * a.contracts;
  const basis = a.strike * 100 * a.contracts;
  const dte = daysToExpiry(a.expiry, today);
  const ret = premium === null || basis <= 0 ? null : (premium / basis) * 100;
  const annual = ret === null || dte === null || dte <= 0 ? null : ret * (365 / dte);
  const isCall = kindOf(a.strategy, a.right) === "cc";
  return [
    {
      label: "Premium",
      value: premium,
      format: "signed-money",
      explain:
        a.premium === null
          ? "No premium has been quoted for this contract yet."
          : `${a.contracts} contract${a.contracts === 1 ? "" : "s"} × $${a.premium.toFixed(2)} per share × 100 shares.`,
    },
    isCall
      ? {
          label: "If called, you sell for",
          value: basis,
          explain: "The strike × 100 shares per contract: what you receive if the shares are called away.",
        }
      : {
          label: "Cash held aside",
          value: basis,
          explain: "What IBKR sets aside: the strike × 100 shares, so you can buy them if assigned.",
        },
    {
      label: dte === null ? "Return" : `Return in ${dte} days`,
      value: ret,
      format: "percent",
      explain: isCall ? "Premium ÷ the strike value." : "Premium ÷ cash held aside.",
    },
    {
      label: "A year",
      value: annual,
      format: "percent",
      total: true,
      explain: "The return scaled to 365 days. A yardstick, not a forecast.",
    },
  ];
}
```

`web/features/home/WhyDisclosure.tsx`:

```tsx
import { Disclosure } from "@/components/ui/Disclosure";
import type { ClaudeReviewPayload } from "@/components/options/types";

/** Claude's view, collapsed, labelled as Claude's. Renders nothing for an empty review. */
export function WhyDisclosure({ review }: { review: ClaudeReviewPayload | null }) {
  if (!review) return null;
  const items = [
    { label: "In short", text: review.summary ?? "" },
    { label: "For", text: review.why_attractive },
    { label: "Against", text: review.risks },
    { label: "If challenged", text: review.rolling_considerations || review.assignment_considerations },
  ].filter((i) => i.text.trim() !== "");
  if (items.length === 0) return null;
  return (
    <div className="mt-3">
      <Disclosure
        summary={
          <span className="text-[0.8125rem] font-bold">
            Why this trade <span className="font-medium text-muted">· Claude's review</span>
          </span>
        }
      >
        <ul className="list-disc space-y-1 pl-[18px] text-[0.8125rem]">
          {items.map((i) => (
            <li key={i.label}>
              <span className="font-bold">{i.label}:</span> {i.text}
            </li>
          ))}
        </ul>
      </Disclosure>
    </div>
  );
}
```

`web/features/home/ProposalCard.tsx`:

```tsx
"use client";

import Link from "next/link";
import { useId } from "react";
import { Button } from "@/components/ui/Button";
import { Card } from "@/components/ui/Card";
import { Stub } from "@/components/ui/Stub";
import type { ApprovalSummary } from "@/components/options/types";
import { STRATEGY_EYEBROW, kindOf } from "@/lib/strategy";
import { daysToExpiry, proposalSentence, proposalStub } from "./proposal";
import { WhyDisclosure } from "./WhyDisclosure";

const DAY = new Intl.DateTimeFormat("en-US", { weekday: "short", day: "numeric", month: "short", timeZone: "UTC" });

export function proposalTitle(a: ApprovalSummary): string {
  if (a.source === "roll") return `${a.underlying} · Roll`;
  const word = a.right === "P" ? "put" : a.right === "C" ? "call" : "option";
  return `${a.underlying} · Sell $${a.strike} ${word}`;
}

export function ProposalBody({ approval }: { approval: ApprovalSummary }) {
  const isRoll = approval.source === "roll";
  return (
    <>
      <p className="mt-2 text-sm">
        {isRoll ? "This rolls a position you already hold. Open Details for both legs." : proposalSentence(approval)}
      </p>
      <WhyDisclosure review={approval.review} />
      {!isRoll && <Stub label={`${approval.underlying} ${approval.right === "C" ? "call" : "put"} math`} lines={proposalStub(approval, new Date())} />}
    </>
  );
}

export function ProposalCard({
  approval,
  onReview,
}: {
  approval: ApprovalSummary;
  onReview: (a: ApprovalSummary) => void;
}) {
  const titleId = useId();
  const kind = kindOf(approval.strategy, approval.right);
  const dte = daysToExpiry(approval.expiry, new Date());
  const eyebrow = approval.source === "roll" ? "Roll" : kind ? STRATEGY_EYEBROW[kind] : approval.strategy;
  return (
    <Card as="article" aria-labelledby={titleId}>
      <div className="flex items-baseline justify-between gap-2">
        <span className="text-xs font-bold uppercase tracking-[0.04em] text-muted">{eyebrow}</span>
        <span className="text-[0.8125rem] text-muted">
          {approval.expiry ? DAY.format(new Date(`${approval.expiry}T00:00:00Z`)) : "expiry n/a"}
          {dte !== null && ` · ${dte}d`}
        </span>
      </div>
      <h3 id={titleId} className="mt-1 text-[1.0625rem] font-extrabold tracking-[-0.01em]">
        {proposalTitle(approval)}
      </h3>
      <ProposalBody approval={approval} />
      <div className="mt-3.5 flex gap-2">
        <Button variant="primary" block onClick={() => onReview(approval)}>
          Review
        </Button>
        <Link
          href={`/trades/${approval.id}`}
          className="inline-flex min-h-11 w-full items-center justify-center rounded-full bg-sunk px-[18px] text-[0.9375rem] font-bold text-content hover:bg-sunk-deep"
        >
          Details
        </Link>
      </div>
    </Card>
  );
}
```

`web/features/home/ReviewSheet.tsx`:

```tsx
"use client";

import { DecideControls } from "@/components/options/DecideControls";
import type { ApprovalSummary } from "@/components/options/types";
import { useControls } from "@/components/shell/BotCard";
import { Sheet } from "@/components/ui/Sheet";
import { ProposalBody, proposalTitle } from "./ProposalCard";

/**
 * Step 1 of the decide flow: the trade, its Why and its stub. Approve/Reject are the existing
 * DecideControls, so step 2 (ConfirmAction) and step 3 (the LIVE confirmation) and the receipt
 * are exactly the flows the options console already ships.
 */
export function ReviewSheet({
  approval,
  open,
  onClose,
}: {
  approval: ApprovalSummary | null;
  open: boolean;
  onClose: () => void;
}) {
  const controls = useControls();
  if (!approval) return null;
  return (
    <Sheet open={open} onClose={onClose} title="Review trade">
      <h3 className="text-[1.0625rem] font-extrabold">{proposalTitle(approval)}</h3>
      <ProposalBody approval={approval} />
      <div className="mt-5">
        <DecideControls approval={approval} drainHealthy={controls.data?.drain_healthy ?? true} />
      </div>
    </Sheet>
  );
}
```

`web/features/home/NeedsYou.tsx`:

```tsx
"use client";

import { useQuery } from "@tanstack/react-query";
import { useState } from "react";
import type { ApprovalListResponse, ApprovalSummary } from "@/components/options/types";
import { apiFetch } from "@/lib/api";
import { type StrategyFilter, kindOf, matchesFilter } from "@/lib/strategy";
import { ProposalCard } from "./ProposalCard";
import { ReviewSheet } from "./ReviewSheet";

export function usePendingApprovals(strategy: StrategyFilter) {
  const q = useQuery({
    queryKey: ["options", "approvals", "pending"],
    queryFn: () => apiFetch<ApprovalListResponse>("/options/approvals?status=pending"),
    refetchInterval: 30_000,
  });
  const visible = (q.data?.approvals ?? []).filter(
    (a) => a.status === "pending" && matchesFilter(kindOf(a.strategy, a.right), strategy),
  );
  return { ...q, visible };
}

export function NeedsYou({ strategy }: { strategy: StrategyFilter }) {
  const { data, isError, visible } = usePendingApprovals(strategy);
  const [reviewing, setReviewing] = useState<ApprovalSummary | null>(null);

  let body: React.ReactNode;
  if (strategy === "spread") {
    body = <p className="text-sm text-muted">Credit spreads trade on their own in paper. Nothing here needs you.</p>;
  } else if (isError && !data) {
    body = <p className="text-sm text-muted">Proposals unavailable right now.</p>;
  } else if (!data) {
    body = <div className="h-24" aria-busy="true" />;
  } else if (visible.length === 0) {
    body = <p className="text-sm text-muted">Nothing needs you right now.</p>;
  } else {
    body = (
      <div className="grid gap-3">
        {visible.map((a) => (
          <ProposalCard key={a.id} approval={a} onReview={setReviewing} />
        ))}
      </div>
    );
  }

  return (
    <section aria-labelledby="needs-you-title">
      <h2 id="needs-you-title" className="mb-2.5 text-[0.8125rem] font-semibold text-muted">
        Needs you{strategy !== "spread" && data ? ` · ${visible.length} proposal${visible.length === 1 ? "" : "s"}` : ""}
      </h2>
      {body}
      <ReviewSheet approval={reviewing} open={reviewing !== null} onClose={() => setReviewing(null)} />
    </section>
  );
}
```

`web/features/home/ProposalsBanner.tsx`:

```tsx
"use client";

import Link from "next/link";
import { Card } from "@/components/ui/Card";
import type { StrategyFilter } from "@/lib/strategy";
import { usePendingApprovals } from "./NeedsYou";

/** Below 1024px the needs-you column becomes this one line (DESIGN.md Layout). */
export function ProposalsBanner({ strategy }: { strategy: StrategyFilter }) {
  const { visible } = usePendingApprovals(strategy);
  if (strategy === "spread" || visible.length === 0) return null;
  const names = visible
    .slice(0, 3)
    .map((a) => `${a.underlying} ${a.right === "C" ? "call" : "put"}`)
    .join(" · ");
  return (
    <Card as="div" className="mt-4 flex items-center justify-between gap-3">
      <div>
        <div className="font-bold">
          {visible.length} proposal{visible.length === 1 ? "" : "s"} need{visible.length === 1 ? "s" : ""} you
        </div>
        <div className="text-[0.8125rem] text-muted">{names}</div>
      </div>
      <Link
        href="/trades"
        className="inline-flex min-h-11 flex-none items-center rounded-full bg-primary px-[18px] font-bold text-on-primary hover:bg-primary-deep"
      >
        Open
      </Link>
    </Card>
  );
}
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `cd web && npx vitest run features/home`
Expected: PASS.

- [ ] **Step 5: Gate and commit**

```bash
cd web && npx vitest run && npx tsc --noEmit && npm run lint
cd .. && git add web/features/home
git commit -m "feat(web): proposal cards with Claude's review above the stub, and the review sheet"
```

---

## Section E — Assembly, docs and finish (Task 14) · model: opus

Mounts Home at `/`, regenerates the client types, looks at the result in a browser, sweeps the
docs and ratifies `web/DESIGN.md`.

**Entry checks (run before Task 14):**

- [ ] **E1. Section D landed.** `git log --oneline main..HEAD` shows thirteen commits; Tasks 10–13
  are ticked.
- [ ] **E2. Both gates and the build green.** `python -m pytest -q && ruff check . && mypy src` and
  `cd web && npx vitest run && npx tsc --noEmit && npm run lint && npm run build`.
- [ ] **E3. Home's parts exist.** This prints nothing:

  ```bash
  cd web/features/home && for f in AccountHero HeroChart PayCard PositionsCard ProposalCard ReviewSheet NeedsYou ProposalsBanner WhyDisclosure; do
    [ -f "$f.tsx" ] || echo "MISSING $f.tsx"; done
  ```

- [ ] **E4. Nothing decides in one tap.** `grep -rn "submitCommand\|confirmCommand" web/features`
  prints nothing: Home reaches orders only through `DecideControls`.
- [ ] **E5. A browser is available for the visual check.** The Playwright or Chrome tools load, or the
  operator agrees to take the four screenshots in Task 14 Step 5 by hand.

**Section exit (plan done):** fourteen task commits plus the Progress-log commit; DESIGN.md
`status=ratified`; then superpowers:finishing-a-development-branch.

---

### Task 14: Home assembly, docs and the design finish

**Files:**
- Create: `web/features/home/HomePage.tsx`, `web/features/home/HomePage.test.tsx`
- Modify: `web/app/page.tsx` (Home replaces the research re-export)
- Modify: `web/lib/api-types.ts` (regenerated), `web/CLAUDE.md` (Layout section),
  `docs/web/api.md`, `ARCHITECTURE.md`, `STATUS.md`, `CLAUDE.md` (root), `web/DESIGN.md`

**Interfaces:**
- Consumes: everything above.
- Produces: the `/` route.

- [ ] **Step 1: Write the failing test** — `web/features/home/HomePage.test.tsx`

```tsx
import { fireEvent, screen } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";
import { renderWithQuery } from "@/lib/test-query";

const nav = vi.hoisted(() => ({ replace: vi.fn(), params: new URLSearchParams() }));
vi.mock("next/navigation", () => ({
  useRouter: () => ({ replace: nav.replace }),
  useSearchParams: () => nav.params,
  usePathname: () => "/",
}));
vi.mock("./HeroChart", () => ({ HeroChart: () => <div data-testid="chart" /> }));

import { HomePage } from "./HomePage";

const responses = {
  "/portfolio/value": {
    as_of: "",
    series: { range: "1m", points: [], latest: 248310.42, latest_at: null, previous_close: null, change_today: null, change_today_pct: null },
  },
  "/pnl/month": {
    as_of: "",
    book: "paper",
    spreads_available: true,
    pay: { month: "2026-10-01", strategy: "all", premium_collected: 0, bought_back: 0, commissions: 0, commissions_complete: true, net: 0, n_opened: 0, n_closed: 0, month_start_value: null, target_pct: null, target: null, progress_pct: null, days_left: 18 },
  },
  "/portfolio/positions": { as_of: "", source: "none", degraded: true, groups: [] },
  "/spreads/positions": { as_of: "", available: false, underlying: "SPY", mode: "paper", positions: [] },
  "/options/approvals": { as_of: "", approvals: [] },
  "/options/controls": { as_of: "", autonomy: { level: "a", label: "A" }, rungs: [], halted: false, halt_reason: null, halted_at: null, mode: "paper", drain_healthy: true, drain_last_seen: null, pending_commands: 0 },
};

describe("HomePage", () => {
  it("puts the strategy switcher first, then the hero, pay and positions", async () => {
    renderWithQuery(<HomePage />, responses);
    const switcher = await screen.findByRole("group", { name: "Strategy" });
    const hero = await screen.findByRole("region", { name: "Account value" });
    const pay = await screen.findByRole("button", { name: /October pay/ });
    const positions = await screen.findByRole("heading", { name: "Positions" });
    const order = [switcher, hero, pay, positions];
    for (let i = 1; i < order.length; i++) {
      expect(order[i - 1].compareDocumentPosition(order[i]) & Node.DOCUMENT_POSITION_FOLLOWING).toBeTruthy();
    }
  });
  it("writes the strategy into the URL", async () => {
    renderWithQuery(<HomePage />, responses);
    fireEvent.click(await screen.findByRole("button", { name: "CSPs" }));
    expect(nav.replace).toHaveBeenCalledWith("/?strategy=csp", { scroll: false });
  });
});
```

(`<section aria-label="Account value">` has the implicit role `region` because it is labelled.)

- [ ] **Step 2: Run to verify failure**

Run: `cd web && npx vitest run features/home/HomePage.test.tsx`
Expected: FAIL.

- [ ] **Step 3: Implement**

`web/features/home/HomePage.tsx`:

```tsx
"use client";

import { SegmentedControl } from "@/components/ui/SegmentedControl";
import { STRATEGY_FILTERS, STRATEGY_LABEL, kindOf } from "@/lib/strategy";
import { useStrategyFilter } from "@/lib/useStrategyFilter";
import { AccountHero } from "./AccountHero";
import { NeedsYou, usePendingApprovals } from "./NeedsYou";
import { PayCard } from "./PayCard";
import { PositionsCard } from "./PositionsCard";
import { ProposalsBanner } from "./ProposalsBanner";

export function HomePage() {
  const [strategy, setStrategy] = useStrategyFilter();
  const { data } = usePendingApprovals("all");
  // Counts on the switcher are pending proposals per kind: what each tab has waiting.
  const pending = data?.approvals.filter((a) => a.status === "pending") ?? null;
  const options = STRATEGY_FILTERS.map((f) => ({
    value: f,
    label: STRATEGY_LABEL[f],
    count:
      pending === null || f === "all" || f === "spread"
        ? null
        : pending.filter((a) => kindOf(a.strategy, a.right) === f).length || null,
  }));

  return (
    <div className="mx-auto max-w-[1200px] px-4 py-5 md:px-7 md:py-6">
      <SegmentedControl label="Strategy" options={options} value={strategy} onChange={setStrategy} />
      <div className="mt-5 grid items-start gap-6 lg:grid-cols-[minmax(0,1fr)_340px]">
        <div className="min-w-0">
          <AccountHero />
          <div className="lg:hidden">
            <ProposalsBanner strategy={strategy} />
          </div>
          <PayCard strategy={strategy} />
          <PositionsCard strategy={strategy} />
        </div>
        <aside className="hidden lg:block">
          <NeedsYou strategy={strategy} />
        </aside>
      </div>
    </div>
  );
}
```

(Counts: a kind with zero pending shows no count rather than "0", because the switcher's count
means "waiting for you", and the test above clicks a button named exactly "CSPs".)

`web/app/page.tsx`:

```tsx
import { Suspense } from "react";
import { HomePage } from "@/features/home/HomePage";

// useSearchParams (the strategy switcher) needs a Suspense boundary under the App Router.
export default function Page() {
  return (
    <Suspense>
      <HomePage />
    </Suspense>
  );
}
```

- [ ] **Step 4: Run tests, regenerate client types, full gate**

```bash
cd web && npx vitest run features/home/HomePage.test.tsx
npx openapi-typescript ../docs/web/openapi.json -o lib/api-types.ts
npx vitest run && npx tsc --noEmit && npm run lint && npm run build
cd .. && python -m pytest -q && ruff check . && mypy src
```

Expected: everything PASS; `next build` succeeds (no "useSearchParams should be wrapped in a
suspense boundary" error).

- [ ] **Step 5: Look at it**

Start the API and `cd web && npm run dev -- -p 3001` (port 3001 so the operator's running 3000 is
untouched), then screenshot `/` at 1440×900 and 390×844 in light and dark (Bot sheet open once,
one proposal's Why open once). Compare against `web/DESIGN.md` § Surfaces → Home's FIRST VIEWPORT.
Fix any drift before continuing; record each fix as a ruling.

- [ ] **Step 5a: da-vinci critique and audit of every surface built without it**

Sections A and B (and their review fix passes) built UI without invoking da-vinci. Invoke the
`da-vinci` skill (Skill tool; `web/DESIGN.md` is `draft`, so no interview) and run `critique`, then
`audit` (`reference/audit-and-critique.md`), over:

- `components/ui/*` (Button, Card, SegmentedControl, StatusWord, Meter, Disclosure, Stub, Sheet),
  `lib/theme.ts` and the tokens in `app/globals.css`, in light and dark;
- `components/shell/*` (Rail, TabBar, BotCard, BotSheet, HaltedBanner, ThemeToggle), `lib/nav.ts`;
- `app/more/page.tsx` and the moved route pages (`/trades`, `/activity`, `/research`,
  `/research/universe`) as they now look under the new tokens;
- Home as screenshotted in Step 5 (built with da-vinci in Section D; a light pass only).

Fix what the review finds through da-vinci's `polish` mode, inside `web/DESIGN.md`. A fix that
would change the design system (a colour, font, radius or elevation rule) is not made: list it in
the report for the operator. The deferred visual minors from the Section A and B reviews fold into
this step (the ledger's `Section A: minor (deferred)` and `Section B: minor (deferred)` lines): the
sheet shadow literal (`--shadow-sheet` token), lime text selection, the flattened focus accent on
legacy pages, button press scale under reduced motion, the Button / StatusWord / Stub type drift
from DESIGN.md and the 180ms sheet exit, the 44px theme-toggle targets, the missing phone tab
state for `/research` and `/news`, and `aria-haspopup` on the bot card. Record each fix and each
declined item as a ruling; re-run the web gate after the fixes.

- [ ] **Step 6: Documentation (mandatory doc-update table, root CLAUDE.md)**

- `ARCHITECTURE.md`:
  - `web/` folder guide: the new structure (`components/ui/` primitives, `components/shell/` rail /
    tab bar / bot card / halted banner, `features/home/`, `lib/theme.ts`, `lib/nav.ts`,
    `lib/strategy.ts`), the route map (`/`, `/trades`, `/activity`, `/research`,
    `/research/universe`, `/more`) and the redirects.
  - `src/reporting/` section: `account_value.py` and `pay.py` (read-only; same tier rules).
  - `src/api/` section: `spreads_db.py` (read-only mode=ro engine over `data/spreads.db`; the API
    still imports nothing from `src.spreads`) and the three new routes.
  - `src/common/` + data-flow sections: `AccountValuePoint`, `AccountValueSeries`, `MonthPay`.
  - `config/` section: `web.monthly_income_target_pct`.
- `docs/web/api.md`: `GET /portfolio/value`, `GET /pnl/month`, `GET /spreads/positions`, each with
  parameters, the "unknown is null, never 0" rule, and `/pnl/month`'s attribution rule (premium in
  the month sold, buybacks in the month bought, a leg's commissions once per month it touches).
- `STATUS.md`: web overhaul Part 1 built; Parts 2–4 deferred (list them); `GET /nav` no longer read
  by the web (removed in Part 4).
- Root `CLAUDE.md`, "The third, read-only tier — `src/reporting/`": add `account_value.py` and
  `pay.py` to the module list with one line each. "The spreads fence": add one bullet — the web API
  reads `data/spreads.db` only through `src/api/spreads_db.py` (mode=ro, plain SQL), asserted by
  `tests/test_web_fence.py::test_only_spreads_db_opens_the_spreads_file_in_the_api`.
- `SETUP.md`: in the settings walkthrough, one line on `web.monthly_income_target_pct`.
- `web/CLAUDE.md` `## Layout`: replace the `app/page.tsx` entry with the Home description, add
  `trades/`, `activity/`, `research/`, `more/`, `features/home/`, `components/ui/`, the new
  `components/shell/` members, and mark `options/`, `pnl/`, `universe/` as moved.

- [ ] **Step 7: da-vinci finish**

Run `/da-vinci` (it loads `reference/finish.md`): reconcile `web/DESIGN.md`'s tokens and
component prose to what was built, show the diff, and on the operator's approval set the marker
to `status=ratified` with a Decision Log entry. Re-run
`python3 ~/.claude/skills/da-vinci/scripts/design_md_check.py web/DESIGN.md` (exit 0).

- [ ] **Step 8: Commit and update the Progress log**

```bash
git add -A web docs ARCHITECTURE.md STATUS.md CLAUDE.md SETUP.md
git commit -m "feat(web): the payslip Home - strategy switcher, hero, pay, positions, proposals"
```

Tick every step in this plan, fill in every Progress log row (status, commits, gate, date,
rulings) and commit that with the task, per root `CLAUDE.md` § Change workflow 4.
