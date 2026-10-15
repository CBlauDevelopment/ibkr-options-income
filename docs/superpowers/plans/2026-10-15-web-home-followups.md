# Web Home follow-ups (2026-10-15)

Five changes the operator asked for after Web overhaul Part 1 shipped. Visual authority is
`web/DESIGN.md` (ratified); every UI task invokes **da-vinci** first. Branch
`feat/web-home-followups`, worktree `.claude/worktrees/home-followups`.

The operator's words, numbered as they were:

1. Home "Needs you" is empty most days. Show the day's **executed trades** in the same card style
   as the AAPL / KO proposal cards, with filter pills **Opened / Closed / Rolled**, each carrying
   its contract. Closed and Rolled must say **why**, and the stub must show the **full P&L**.
2. "October pay" has nowhere to set the target. Put it under **More**: a fixed amount, a % of
   account value, or a % of a fixed amount.
3. Each position is pressable. The page shows the **initial full trade** (premium collected, %ROC
   and so on), the **underlying's chart at the very top**, and **headlines** below the chart.
4. A **search** to filter positions (AMZN, NVDA).
5. At the chart's bottom right, replace "Chart by TradingView" with a **calendar** showing the
   **daily realised P&L**, as brokerages do.

## Progress log

| Task | Status | Commits | Gate | Date | Rulings / notes |
|---|---|---|---|---|---|
| 0 Worktree and baseline | done | n/a | pytest `test_api_pnl_month` + `test_command_schemas` 43 passed; vitest `features/home` 113 passed | 2026-10-15 | venv and `web/node_modules` symlinked, `init_db()` run |
| 1 Income target: setting, command, API | done | (this commit) | pytest 3669 passed + 1 skip, ruff/mypy clean, OpenAPI + `api-types.ts` regenerated, fences green | 2026-10-15 | `IncomeTarget` lives in `schemas.py` (the command payload subclasses it, so the stored and the posted shape cannot differ); `src/common/income_target.py` holds the stored form, the resolution order and the arithmetic so the API can read the row through its own read-only session; `MonthPay.target_pct` kept, `target_mode` / `target_amount` / `target_base` added. **Fix outside the brief:** `POST /commands` answered 500 when a validator raised `ValueError` (the error's `ctx` held the exception object); it now serialises through `exc.json()`, which also fixes the latent ledger-upload-limit path. `ruff format src tests` also touched `routers/portfolio.py`, `routers/system.py` and `tests/test_config_keys.py` (pre-existing drift); reverted, not mine |
| 2 Income target: More card, pay card copy | done | (this commit) | vitest `features` + `app/more` 137 passed (+18 new), tsc 0, `next lint` clean, da-vinci lint exit 0 | 2026-10-15 | `features/more/target.ts` holds the form rules (text in, payload out) apart from the card; the pay card's "No target set" now keys on `target_mode === "off"` (a fixed target has no percent), and the link to More sits below the disclosure because a link inside the disclosure's button would nest interactive elements. The field's focus ring is on its wrapper via `has-[input:focus-visible]` (the linter's OUTLINE_NONE rule found `outline-none` on the bare input; a real fix, not an exception). Visual inspection is batched into Task 10 with the other surfaces |
| 3 Day trades API (`GET /pnl/day`) | done | (this commit) | pytest 3708 passed + 1 skip (+39 new), ruff/mypy clean, OpenAPI + types regenerated, fences green; builders also run against a read-only copy of the operator's real trading DB (34 legs; reasons read correctly; no rolls on record yet) | 2026-10-15 | `src/reporting/day.py` (+ `DayTrade`, `DayFact`, `DayReview`, `DayRolledTo` in `schemas.py`). **A roll pairs on the shared combo `order_id`** (the buy-back and the new SELL fill share it), not on the time heuristic the plan assumed; the logged decision matches on the roll approval id, else the newest decision for the contract. `pay.py`'s `et_date` / `close_day` became public so the day and the pay stub use one rule. A loss says "the buy-back cost N% more than the premium collected", not "-109% kept". Opened cards carry Claude's stored review; the web labels it Claude's |
| 4 Day trades on Home | done | (this commit) | vitest `features` 144 passed (+28 new), tsc 0, `next lint` clean, da-vinci lint exit 0; rendered once at 1440 in Chrome against a synthetic mock API (full inspection in Task 10) | 2026-10-15 | `trades.ts` (title, sentence, stub, time), `TradeCard`, `TodayTrades`. **One grid, one copy of each card** instead of the aside + hidden-below-1024 pair: from 1024px the left column spans three rows and the right stacks Needs you over Done today, below it DOM order puts Done today after Positions. Closed and rolled cards show the API's reason as the always-visible sentence and the facts behind a "Why it closed / was rolled" disclosure ("the system's rules", plus "and Claude's view" when a Claude line is present, which is labelled as Claude's). **Fix to Task 3:** the API model `CalendarResponse` clashed with the portfolio one in OpenAPI (generated types broke `components/portfolio`); renamed `RealisedCalendarResponse` |
| 5 Realised calendar API (`GET /pnl/calendar`) | done | (same commit as Task 3) | as Task 3 | 2026-10-15 | Built beside Task 3 because it shares the close-day rule and the spread inputs; `build_month_calendar` in `day.py`. A day nothing closed is absent (not a flat day). Net after commissions; `complete` false when a close that day has no commission recorded |
| 6 Calendar sheet, TradingView credit moved | todo | | | | |
| 7 Positions search and row links | todo | | | | |
| 8 Position detail API | todo | | | | |
| 9 Position detail page | todo | | | | |
| 10 Docs, da-vinci finish, full gate | todo | | | | |

## Rulings made up front (the operator may overturn any of them)

- **One data source for pay, the feed and the calendar.** All three read the same `PnlLeg` list
  (`build_legs`) plus the book's spreads rows (`spreads_db.py`) that `GET /pnl/month` already
  uses, so a card, the calendar and the pay stub can never disagree. Share sales and manual trades
  are not in it (they live in the ledger); the calendar says "options and credit spreads".
- **Feed = today, New York day.** `GET /pnl/day?date=` takes any date so the calendar can reuse it
  for a tapped day. Expiries and assignments that land on the day appear under Closed (an expiry is
  not an execution, but the position leaves the book and would otherwise vanish without a trace).
- **A roll is one card.** The buy-back leg (`close_reason=roll`) and the new leg it opened are
  paired (same underlying and right, the new leg opened within 10 minutes of the buy-back) and shown
  once under Rolled; the new leg is not repeated under Opened. An unpaired roll buy-back still shows
  as Rolled, saying the new leg is not on record.
- **Reasoning is deterministic text from stored facts.** Closed: the `CloseReason` plus the numbers
  (kept %, days left). Rolled: the stored roll alert's trigger label and detail, and Claude's stored
  recommendation labelled as Claude's. Opened: Claude's stored review, as on a proposal. Nothing is
  generated at read time; no LLM is called.
- **Target storage.** `system_settings` key `income_target` (JSON), written only by a drained
  `set_income_target` command, like `set_roll_mode`. Absent row falls back to the legacy
  `web.monthly_income_target_pct` (so the shipped config keeps working); an explicit `off` row means
  no target. It is display-only: nothing in the trading path reads it.
- **Position URL.** `/positions/{underlying}/{slug}` with slug `2026-11-21_P180` (option),
  `shares`, or `spread-{id}`. Chart first, then the initial trade, then headlines on a phone; on
  desktop the chart and headlines stack in the left column (headlines directly below the chart, as
  asked) and the trade sits in a 340px right column, mirroring Home.
- **Headlines.** A light `GET /research/{symbol}/headlines` over the existing `recent_news` loader,
  not the full analysis route (which can start an SEC fundamentals ingest).
- **TradingView credit.** The chart library's licence needs a link somewhere users can reach. It
  leaves the chart and goes to the foot of More, under "Credits". Removing it outright would breach
  the licence.
- **Pinned beats roll.** The operator fixed the position page's composition (chart on top, news
  below it), so da-vinci's three-structure workshop is skipped; the contract goes in
  `web/DESIGN.md` `## Surfaces` before code.
- **Finish reviewer runs in-thread.** The session may not spawn agents unprompted, so da-vinci's
  fresh reviewer is run in-thread and disclosed as such.

## Task 1 - Income target: setting, command, API

Files: `src/common/schemas.py` (`IncomeTarget`, `MonthPay` target fields), `src/storage/system_settings.py`
(`get_income_target`, `set_income_target`), `src/api/models/commands.py` (`SET_INCOME_TARGET`,
`SetIncomeTargetPayload`), `src/notify/command_drain.py` (`set_income_target` handler),
`src/reporting/pay.py` (`target` replaces `target_pct`), `src/api/routers/pnl.py` (`GET /pnl/target`,
`/pnl/month` reads the resolved target), `docs/web/commands.md`, `docs/web/api.md`,
`docs/web/openapi.json`, tests.

- [x] Failing tests: payload validation per mode; setting round-trip; resolution order (web row,
      `off`, config fallback, nothing); `build_month_pay` for each mode; `/pnl/target`; drain handler.
- [x] Implement; keep `target_pct` on `MonthPay` (existing clients) and add `target_mode`,
      `target_amount`, `target_base`.
- [x] Regenerate `docs/web/openapi.json` and `web/lib/api-types.ts`; fence tests green.

## Task 2 - Income target: More card and pay card copy

Files: `web/features/more/TargetCard.tsx` (+ test), `web/app/more/page.tsx`,
`web/features/home/PayCard.tsx`, `web/features/home/types.ts`.

- [x] da-vinci loaded. Card on More: segmented control (Fixed amount, % of account, % of an amount),
      labelled inputs, a plain-English preview of what it means this month, Save, receipt.
- [x] Pay card: "No target set" gains a link to More; copy per mode.

## Task 3 - Day trades API

Files: `src/common/schemas.py` (`DayTrade`), `src/reporting/day.py`, `src/api/routers/pnl.py`
(`GET /pnl/day`), `src/api/models/pnl.py`, tests.

- [x] Failing tests per action (opened, closed with each `CloseReason`, rolled paired and unpaired,
      expired, assigned, spread open and close), strategy scoping, unknown stays `null`.
- [x] Implement over `build_legs` + spreads rows + `ClaudeReviewRow` / `RollAlertRow` reads.

## Task 4 - Day trades on Home

Files: `web/features/home/TodayTrades.tsx`, `TradeCard.tsx`, `trades.ts` (+ tests), `NeedsYou.tsx`,
`HomePage.tsx`.

- [x] da-vinci loaded. Right column: Needs you, then "Done today" with pills All / Opened / Closed
      / Rolled (counts). Phone: the same section after Positions.
- [x] Card = proposal card anatomy: eyebrow, title, one sentence, Why disclosure, stub, a Details link when an approval exists, no lime.

## Task 5 - Realised calendar API

Files: `src/reporting/day.py` (`build_month_calendar`), `src/api/routers/pnl.py`
(`GET /pnl/calendar?month=`), models, tests.

## Task 6 - Calendar sheet

Files: `web/features/home/RealisedCalendar.tsx`, `AccountHero.tsx`, `web/app/more/page.tsx`
(Credits), tests.

- [ ] Calendar icon button at the chart row's end; opens a Sheet with a month grid, month total,
      prev / next month, a tapped day listing what closed that day.

## Task 7 - Positions search and row links

Files: `web/features/home/PositionsCard.tsx`, `positions.ts` (+ tests).

## Task 8 - Position detail API

Files: `src/api/routers/portfolio.py` (`GET /portfolio/position`), `src/api/routers/research.py`
(`GET /research/{symbol}/headlines`), models, tests.

## Task 9 - Position detail page

Files: `web/app/positions/[underlying]/[slug]/page.tsx`, `web/features/position/*`, `web/DESIGN.md`
(`## Surfaces` contract first).

## Task 10 - Docs, finish, full gate

- [ ] `web/DESIGN.md` (components, Decision Log), `web/CLAUDE.md`, `ARCHITECTURE.md`, `SETUP.md`,
      `STATUS.md`, `docs/web/*`, README only if a command or top-level dir changed (none expected).
- [ ] da-vinci finish: lint, 1440 / 390 inspection in both themes, in-thread review.
- [ ] `pytest -q`, `ruff check .`, `mypy src`, `npm test`, `tsc`, `npm run lint`, a scratch build.
