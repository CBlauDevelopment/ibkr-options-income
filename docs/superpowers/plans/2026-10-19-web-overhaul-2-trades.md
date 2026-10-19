# Web Overhaul, Part 2: Trades — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task (native execution, chosen by the operator 2026-10-19). The plan is split into four sections; every section opens with **entry checks** that must all pass before its first task starts. Each section carries a **model label** so an orchestrator that delegates a section knows which model to spawn. **Every task that touches UI starts by invoking the `da-vinci` skill** (operator, 2026-10-19), and so does any subagent given one of those tasks (say so in its prompt). Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Recompose `/trades` on the payslip design system for how the account actually runs.
On FULL autonomy the system approves and sends nearly every trade itself, so the page leads with
what happened, not with an empty queue: the strategy switcher; three wheel views (Proposals,
History, Assessed) and one spreads view, kept in the URL; a smart default (Proposals when
something waits on you, History otherwise); History as one New York day at a time (what is in
flight, what traded, what was proposed and did not trade), with **who approved each trade
recorded and shown**; rolls that say what they roll on every surface; the spreads view
trade-first, with the menu Claude saw as the reason, over a new `GET /spreads/picks`; the approval
detail page restyled; and "Propose a roll" moved from the Shorts table onto the short option's own
page.

**Architecture:** Two backend tasks. Task 1 adds one read-only route (`GET /spreads/picks`) that
reads `data/spreads.db` through the existing `src/api/spreads_db.py` engine and parses each stored
menu with the shared `SpreadMenuItem` schema. Task 2 adds the one schema change: a nullable
`approvals.decided_by` (`system` | `web` | `telegram`). It is written where an approval is
decided: the entry auto-queue and the roll pipeline on FULL autonomy, and `_process_button` for a
tap, with the drain's existing indirection naming the web. The API exposes it on
`ApprovalSummary`, beside the roll's buy-back leg (from the frozen snapshot) and the order's fill
price, and on `/pnl/day`'s trade cards, which also gain `previous_day` / `next_day`. No engine,
gate, strategy or sizing code reads the new column: it is a record for the page, and a test says
so. The page is `web/features/trades/TradesPage.tsx`, with each view in its own component in
`web/features/trades/`. They reuse Home's `ProposalCard`, `ReviewSheet`, `usePendingApprovals` and
`TradeCard`; `ReviewSheet` only gains two optional callbacks. Legacy `components/options/*`
components that stay mounted (assessed and the detail page) are restyled in place under their
existing tests. The roll-proposal flow is lifted out of `ShortsRow` into a hook so the position
page can use it without a second copy of the logic. Every order intent still goes through the
unchanged `DecideControls` → `ConfirmAction`.

**Tech Stack:** Next.js 15 App Router, React 19, Tailwind CSS v4, @tanstack/react-query,
lucide-react, Vitest + Testing Library; FastAPI, SQLAlchemy (plain SQL over a `mode=ro` SQLite
engine for spreads; the ORM over the trading DB), Pydantic, pytest.

**Spec:** `web/DESIGN.md` (ratified 2026-10-14; § Surfaces → Trades, § Components → Proposal card,
Review sheet, Strategy switcher, Trade card; the authority for every visual value) and the roadmap
in `docs/superpowers/plans/2026-10-13-web-overhaul-1-foundation-home.md` § "Roadmap (this plan is
Part 1 of 4)", Part 2, as revised by the operator on 2026-10-19 (the rulings below). The Trades
surface contract is written into `web/DESIGN.md` in Task 3 before any Trades code.

## Execution model

| Section | Tasks | Model | Why this model |
|---|---|---|---|
| **A — The API and the decision record** | 1–2 | **opus** | Task 1 is one route over an existing read-only engine. Task 2 changes code the trading service runs: a column migration on the live trading DB, plus writes in `approval_service`, the drain's indirection, the entry auto-queue and the roll pipeline. Every line of code and every test is given, but this section gets the most capable model because a slip here reaches the trading process. |
| **B — The views** | 3–7 | **sonnet** | New components in `web/features/trades/` against interfaces that Part 1 and Section A pinned; the legacy components being restyled get full replacement code under their existing tests. |
| **C — Assembly, detail page, roll** | 8–10 | **sonnet** | The page assembly, the detail-page restyle and a behaviour-preserving extraction (`useRollProposal`) are given in full; `ShortsTable.test.tsx` passing unmodified is the proof the extraction changed nothing. |
| **D — Docs and finish** | 11 | **sonnet**, then an **opus** whole-branch review | The doc sweep and the da-vinci finish are checklists; the whole-branch review at the end (superpowers:executing-plans' final review, or superpowers:requesting-code-review) runs on the most capable model. |

**How a section runs (native):**

1. Run that section's **entry checks** (below each section heading), in order.
2. **Any check fails → stop.** Report what failed with its output, and do not start the section's
   first task. A failure that belongs to the previous section is fixed there (reopen its last
   task, record the ruling) before re-running the checks.
3. **All checks pass →** record a row for them in the Progress log ("Section X entry", gate
   result, date) and start the first task. No operator confirmation is needed between green
   sections.
4. An orchestrator delegating instead of running natively spawns one subagent per section on
   the labelled model, hands it this plan plus `web/DESIGN.md`, tells it to invoke `da-vinci`
   before any UI code, and runs the next section's entry checks itself before spawning the next.

**Commit counts.** Each task is one commit (Task 1's also adds this plan file). A review fix pass
adds one commit; record it in the Progress log and add one to every later entry check's count.

## Progress log

| Section / task | Status | Commits | Gate | Date | Rulings |
|---|---|---|---|---|---|
| **Plan revised** (operator review) | done | (plan file only) | n/a | 2026-10-19 | Operator rulings of 2026-10-19 written in (see "Rulings made up front"): smart default; Working and Decided merged into History, one New York day at a time; who approved recorded in `approvals.decided_by`; rolls show both legs on the card, rows and detail page; Spreads only under Credit spreads, trade-first; Cancel moved to a new Part 5; Activity keeps the raw fills and orders ledger (Part 3). Tasks renumbered 1–11. |
| **A entry checks** (baseline) | done | (none) | A1–A5 pass. pytest 3836 passed, 1 skipped; vitest 817 passed (94 files); ruff, mypy, tsc, lint clean | 2026-10-19 | Ruling: executed inline in a git worktree (`.claude/worktrees/web-overhaul-2`, branch renamed to `feat/web-overhaul-2`), no subagents and no per-task review, at the operator's request to save tokens. Entry checks ran in the worktree at 13ce361 (identical to `main`). |
| 1 Spreads picks API | done | 1c635b8 | pytest 3848 (baseline + 12); ruff, mypy, vitest 817, tsc, lint clean | 2026-10-19 | none |
| 2 Who decided, the roll's leg, the fill, History's days | done | 36c2f4d | pytest 3867 (Task 1 + 19); ruff, mypy, vitest 817, tsc, lint clean | 2026-10-19 | Ruling: `DayTradesResponse` annotates `previous_day`/`next_day` as `dt.date` (`import datetime as dt`), because its own `date` field shadows the type inside the class body and mypy rejects `date \| None` there. Ruling: `reporting/day.py` types the decider as `DecidedBy = Literal["system","web","telegram"]` and narrows with one `cast`, because `in (...)` does not narrow a `str` for mypy. Ruling: ran `ruff format` on the four files this task wrote or extended (`spreads_db.py`, `day.py`, the two new test files); other pre-existing format drift left alone. |
| **B entry checks** | done | (none) | B1-B5 pass | 2026-10-19 | none |
| 3 Trades contract, views, Proposals | done | ad32f5c | vitest 846 (98 files, baseline + 29); tsc, lint clean; da-vinci lint exit 0; DESIGN.md check exit 0 | 2026-10-19 | none. `ReviewSheet.tsx`'s `DecideControls` line was one line in the file (the plan showed it already split), so the edit split it. |
| 4 Rolls say what they roll | done | 2f3dbf4 | vitest 856 (98 files, Task 3 + 10); tsc, lint clean | 2026-10-19 | none. 9 of the 10 new tests failed first; "says nothing about who approved it when that was not recorded" passes before the code exists, as a guard. The existing roll card test (no `roll_from`) passed unchanged: the new no-legs sentence still contains "This rolls a position you already hold". |
| 5 History | done | a642822 | vitest 879 (101 files, Task 4 + 23: 10 logic, 12 HistoryView, 1 calendar); tsc, lint clean; da-vinci lint exit 0 | 2026-10-19 | Ruling: `timeET` strips both U+202F and U+00A0 (`/[  ]/g`) instead of the plan's single literal character, because a literal narrow no-break space is invisible in a diff and easy to lose; same behaviour, one more character class. |
| 6 Assessed | done | 7911958 | vitest 881 (101 files, Task 5 + 2); tsc, lint clean; da-vinci lint exit 0 | 2026-10-19 | none. Both new tests failed first; every existing Assessed, AssessedRow and ApprovalDetail test passed unchanged. |
| 7 Spreads view | done | 2636741 | vitest 906 (103 files, Task 6 + 25: 16 logic, 9 view); tsc, lint clean; da-vinci lint exit 0. Section B exit met: every `web/features/trades/*.test.*` and `web/features/home/*.test.*` green. Protected files byte-identical to `main` | 2026-10-19 | none. Observation, not a Task 7 change: `grep -rn "submitCommand\|confirmCommand" web/features` is not empty, because `web/features/more/TargetCard.tsx` (Part 1 / Home follow-ups, on `main`) calls `submitCommand` directly; Global Constraints says it should print nothing. Nothing under `features/trades` matches. Left for the finish review. |
| **C entry checks** | done | (none) | C1-C5 pass, orchestrator-run (C2 included a production build in a scratch copy) | 2026-10-19 | Ruling: C4 (and the same grep repeated as an `Expected: prints nothing` check in Tasks 10 and 11) is read as "no file this plan creates or changes under `web/features` calls `submitCommand`/`confirmCommand`". The only allowed hits are `web/features/more/TargetCard.tsx` and `web/features/more/TargetCard.test.tsx`, which were on `main` before this plan (Home follow-ups, the income-target form) and are not touched. Cost if wrong: the operator decides TargetCard should go through a `components/options` flow, which is a separate change. |
| 8 Trades page assembly | done | this commit (`git log --oneline` for the hash) | vitest 899 (102 files: Task 7's 906 + 10 TradesPage tests - 17 removed with the legacy page test and TickerPillBar's test; HomePage's 5 tests unchanged after `useHydrated` moved); tsc, lint clean; da-vinci lint exit 0. Protected files byte-identical to `main` | 2026-10-19 | Ruling: in `TradesPage.test.tsx` the `@/lib/test-query` import comes before `@/lib/commands`, with a comment saying why. The plan listed them the other way round; `test-query` registers the `@/lib/api` mock when it is evaluated, so `lib/commands` (which imports `@/lib/api`) loaded first kept the real `apiFetch` and "approving in the sheet moves the card to History at once" never reached `POST /commands`. Cost if wrong: none, test-only. Also ticked the unticked step boxes of Tasks 1 and 2 and the A and C entry checks. |
| 9 Approval detail page | | | | | |
| 10 Roll moves to the position page | | | | | |
| **D entry checks** | | | | | |
| 11 Docs, da-vinci finish, full gate | | | | | |

## Roadmap (this plan is Part 2 of 5)

- **Part 1 — Foundation, shell and Home.** Done (merged ab7339c), plus the Home follow-ups
  (merged bb34b58).
- **Part 2 — Trades.** This plan.
- **Part 3 — Portfolio and Activity.** As planned, plus: Activity → "Fills and orders" becomes
  the raw, broker-truth list for auditing, covering every fill and every order (Working, All,
  Rejected) in every book. The legacy `OrdersTable` and `FillsTable`, which Part 2 unmounts
  without restyling, are restyled and mounted there. Trades → History tells each trade's story
  (proposal, decision, order, fill); one sentence on each page links to the other.
- **Part 4 — Research, News, More and cleanup.** As planned, plus: delete the legacy
  `components/options` files this part leaves unmounted (`ApprovalsList`, `ApprovalCard`,
  `ShortsTable`, `ShortsRow`, and the `ControlsStrip` component itself after moving
  `DrainWarning` out), **after** porting `ApprovalCard.test.tsx`'s DecideControls cases to a
  `DecideControls.test.tsx` (those tests are DecideControls' only coverage today).
- **Part 5 — Order control (added 2026-10-19 by the operator).** Cancel a working order from
  Trades → History's in-flight rows. This needs a `cancel_order` command kind, its drain handler
  (cancel at IBKR through the execution connection, then reconcile the `OrderRow`), a Cancel
  button behind `ConfirmAction` and the second LIVE confirmation, and the receipt. It reaches the
  execution path, so it starts with its own spec (superpowers:brainstorming) and its own reviewed
  plan, never as a rider on a UI part. Until it ships, History says in words that a working order
  is cancelled in IBKR.

## Rulings made up front (the operator may overturn any of them)

The evidence behind rulings 1–5 (2026-10-19, read from `data/income_system.db`):
`autonomy_level` is `full`. All 72 approved approvals were approved within a millisecond of
being raised (for example, #114 was raised at 19:03:40.3028 and decided at 19:03:40.3019), none
was rejected, and 42 expired. Since Oct 1 there were 43 CSP, 11 CC and 10 roll approvals.

1. **The views follow how the account runs.** Wheel strategies (All, CSPs, CCs) get
   **Proposals · History · Assessed**. Credit spreads gets **Spreads** only, and Spreads is *not*
   a chip under All: the switcher picks the system, and the chips are the wheel's lifecycle.
   Under All, History says in one line that credit spreads are under Credit spreads. The old tabs
   map like this: Approvals → Proposals; Submitted, Orders (Working) and Decided → History; Orders
   (All, Rejected) and Fills → Activity in Part 3; Assessed → Assessed; Shorts → the short
   option's own page (ruling 7).
2. **A smart default.** With no `?view=`, the page opens on Proposals when a proposal in the
   current strategy waits on you, and on History otherwise. The default is decided **once per
   visit**, when the pending count first loads, so approving the last proposal never moves the
   page under you. An explicit `?view=` always wins, and choosing a view always writes it into
   the URL.
3. **History is one New York day at a time** (`?day=YYYY-MM-DD`, default today), built from
   existing routes plus Task 2's fields:
   - **In flight** (today only): approvals whose Approve this browser sent, with their receipts,
     and working orders (queued, submitted, partial) in the strategy.
   - **Traded:** Home's `TradeCard` for each wheel trade opened, closed or rolled that day, from
     `GET /pnl/day?date=&strategy=`, with who approved it.
   - **Not traded:** approvals raised that day that ended without a fill (expired, rejected, or
     approved but their order was cancelled or rejected). Each is a row that opens its detail
     page, with the outcome and who decided it in words.

   Previous and next jump to the nearest day with wheel activity (`previous_day` / `next_day` on
   `/pnl/day`); Today returns. The realised calendar's day panel (Home's chart) links "Open this
   day in History".
4. **Who approved is recorded, never guessed.** A new nullable `approvals.decided_by` holds:
   - `system`: the entry auto-queue on WHITELIST or FULL, and the roll pipeline's auto-approve
     on FULL;
   - `web`: the drain's approve or reject;
   - `telegram`: a tap.

   The drain still calls `_process_button` through its existing indirection, and the call site
   is unchanged. Only the indirection passes `decided_by="web"`, so
   `test_the_handler_calls_process_button_rather_than_reimplementing_it` passes unmodified. Rows
   decided before the column existed carry null and read only "Approved" (or "Rejected"), never
   a guess from timestamps. An expiry leaves it null. It is display-only: nothing in
   `src/engine/`, `src/strategies/` or the execution gate reads it, and Task 2 pins that.
5. **Rolls say what they roll.** `ApprovalSummary.roll_from` comes from the frozen snapshot: the
   leg being bought back (strike, expiry, right, contracts) and the mids the roll was priced at.
   The title reads "NVDA · Roll $250 put Oct 23 → Oct 28" (or "$250 → $245 put Oct 23 → Nov 20"
   when the strike moves) on the card, the History rows and the detail page. The card and the
   detail page sum it in a stub (Buy back, Sell, Net credit or Net debit) at those mids, labelled
   as the quote it was priced at, never as a fill. A snapshot from before the 2026-10-11 redesign
   has no `roll_from` and keeps the old sentence. `source` is `roll` whenever the snapshot's
   strategy is `roll`, so a roll whose candidate was pruned (the 14-day purge) never reads as a
   scan.
6. **The controls strip leaves Trades.** Part 1 made the bot card (rail foot; More on a phone)
   the place for Halt, Resume, the autonomy rung and roll mode, and Home has no strip either.
   Trades keeps the one line that matters when deciding: the "not draining commands" warning
   (`DrainWarning`, unchanged words) above the view. The global halted banner is unchanged.
7. **"Propose a roll" moves to the position page, not onto the rows.** Every Positions row is
   now a link to its page (Home follow-ups), and a button inside a link nests interactive
   elements. The short option's page gains a Roll card: the alerts the monitor fired on that
   contract, Claude's stored view labelled as Claude's, and Propose a roll, through the exact
   confirm-then-receipt flow `ShortsRow` runs today (lifted into `useRollProposal`, not copied).
   Home's position rows gain a flag word "Roll alert", so the at-a-glance signal the Shorts table
   gave is not lost.
8. **Spreads is read-only and trade-first**, over a new `GET /spreads/picks?day=`. The day's
   spreads lead: the paper book and the baseline book (always the deterministic pick) are shown
   side by side from 1024px, which is the comparison the baseline book exists for. Each paper
   spread carries "The menu Claude saw" collapsed under it: the lettered menu, Claude's pick and
   what was sent, and Claude's reason labelled as Claude's view. Every other pick of the day (a
   skip, a fallback with nothing sent, a send refusal, or a pick whose spread is not on record)
   follows under "Other picks" as a short card, with its menu collapsed. The shadow book follows
   when it has rows. Day navigation jumps to the nearest day
   with activity. Only paper-book spreads link to a position page
   (`GET /portfolio/positions/SPY/spread-<id>` reads the running book only).
9. **Proposal cards are Home's** (`ProposalCard`, `ReviewSheet`, `usePendingApprovals`), one
   column below 1024px and two from 1024px. Ticker chips (from two tickers up) replace
   `TickerPillBar`, which is deleted with its test.
10. **Legacy files left unmounted stay put.** `ApprovalsList`, `ApprovalCard`, `ShortsTable` and
    `ShortsRow` stay until Part 4, because their tests are the only coverage of a protected
    component or of a flow this part reuses. `OrdersTable` and `FillsTable` stay unmounted and
    unrestyled until Part 3 mounts them on Activity. None of them is restyled here.
11. **Protected files are byte-identical to `main`:** `web/components/options/{DecideControls,
    ConfirmAction,CommandReceipt,HaltControl,AutonomyControl,RollModeControl}.tsx` and
    `web/lib/{commands,receipt}.ts`. Their look inside the sheet stays the recorded DESIGN.md
    exception.
12. **Strategy scoping uses only what the API returns.** An order carries a strategy name but no
    option right, so an in-flight roll order shows only under All. `/pnl/day` scopes trade cards
    on the server.
13. **The finish review runs in-thread** unless the operator allows a subagent; disclose which.
14. **The ideal zone stops mixing units** (Task 9). The legacy bar drew a strike band (a share
    price) and the premium and its floor (an option price per share) on one axis. The detail page
    now says the two things separately: the strike against the strike zone, and the premium
    against the least credit worth taking.

## Global Constraints

- Every colour comes from a semantic token; never a raw palette class (`bg-white`, `bg-gray-800`)
  or a hex literal in a component.
- Fonts: Hanken Grotesk for everything; Red Hat Mono (`font-mono`) for stub, ledger and price
  figures. Apply `.tabular` to every numeric column.
- Lime (`bg-primary`) only on primary actions (Review), the pending-count badge, the pay meter
  and the "Expires today" status word. Nothing on History, the Spreads view or the Roll card is
  lime.
- Unknown values render `n/a` with the `.hatch` texture and `text-unknown`, never `$0`, `0%` or a
  blank. A genuine zero renders `$0`.
- No state by colour alone: signed money carries `+`/`−`, flags carry a word, selected carries an
  ink fill (never lime or green).
- Charts never animate their data in. Only touched things move (chevron 180ms, sheet 240ms in,
  press scale 0.98), all removed under `prefers-reduced-motion`.
- No shadow anywhere except the review sheet and the confirm dialog.
- Zero em dashes in UI copy; banned words: "seamless", "robust", "unlock", "elevate".
- Claude's text is always labelled as Claude's ("Claude's review", "Claude's view") and never sits
  on a button. Who approved a trade is said in words from `decided_by` only; an unrecorded decider
  is never inferred.
- Safety friction unchanged: every order intent goes through `DecideControls` → `ConfirmAction`;
  promote and propose-a-roll go through `ConfirmAction` first; the second LIVE confirmation stays;
  halt stays one tap in the bot sheet; resume still needs the typed word RESUME.
- `grep -rn "submitCommand\|confirmCommand" web/features` prints nothing: features reach commands
  only through `components/options` flows.
- Old URLs keep working: `/options` → `/trades`, `/options/:id` → `/trades/:id` (307);
  `/trades/:id` stays. Retired view names (`?view=working`, `?view=decided`) open History.
- Backend: the API writes nothing new (still exactly one table, `app_commands`); nothing under
  `src/api/` imports `src.spreads`; `data/spreads.db` is opened only by `src/api/spreads_db.py`.
  The one schema change is the nullable `approvals.decided_by`, added through `_ADDED_COLUMNS`
  with no backfill. No engine, gate, strategy or sizing code changes or reads it.
- Quality gate after every task: `cd web && npx vitest run && npx tsc --noEmit && npm run lint`;
  for Tasks 1 and 2 also `python -m pytest -q && ruff check . && mypy src` from the repo root.
- Never run `next build` inside `web/` (the operator's `next dev` shares `web/.next`): build in a
  scratch copy (command in Section C's entry checks).
- da-vinci never changes the design system (colour, font, radius, elevation, a new token)
  without the operator; a new token is proposed in the Progress log and waits.

## Review Focus

1. **A stored spreads menu that no longer parses** (schema drift, a damaged row). That pick says
   "This menu could not be read." and every other pick on the day still renders; the route never
   500s → Task 1 test `test_an_unreadable_menu_is_flagged_and_the_other_picks_still_render`,
   Task 7 test "says an unreadable menu could not be read and still shows the other picks".
2. **An older or absent spreads file.** No `data/spreads.db` answers `available: false`; a file
   without the `spread_picks` table (the picker never ran) answers `available: true` with no
   picks; a `spread_positions` table without `pick_id` still lists the day's spreads → Task 1
   tests `test_no_file_is_unavailable_not_an_error`,
   `test_an_old_file_without_the_picks_table_is_available_with_no_picks`,
   `test_an_older_positions_table_without_pick_id_still_reads`; Task 7 tests for the unavailable
   and picker-off sentences.
3. **Who decided is recorded, never guessed, and never read by the trading path.** Each of the
   three writers stamps its value; the drain's indirection names the web while the drain's own
   call stays `(approval_id, action)`; a second decision never overwrites the first; an old null
   row reads only "Approved"; nothing in `src/engine/`, `src/strategies/` or `src/execution/`
   reads it → Task 2 `tests/test_approval_decided_by.py` (all eight), Task 5 test "an approval
   decided before the record existed says only Approved".
4. **Approve from the sheet on Trades.** The card leaves Proposals the instant Approve is
   confirmed and appears in History → In flight with its receipt; a failed or expired command
   hands it back; a reload mid-command keeps it in flight → Task 3 test "hands the card on
   through onSubmitted", Task 5 test "a failed command hands the card back", Task 8 tests
   "approving in the sheet moves the card to History at once" and "a reload mid-command keeps
   the card in flight".
5. **The default view and URL combinations.** No `?view=` with a proposal waiting → Proposals;
   with none → History; the default does not flip when the last proposal is approved;
   `?view=foo` → the default; `?view=working` or `?view=decided` → History;
   `?strategy=spread&view=history` → Spreads; `?view=spreads` under All → the default →
   Task 3 `views.test.ts` and `useTradesView.test.tsx`, Task 8 tests.
6. **Rolls.** A roll with `roll_from` shows both legs and the net at the quoted mids, labelled as
   the quote; a roll without it keeps the old sentence; a pruned roll candidate still reads as a
   roll → Task 2 `test_a_roll_carries_the_leg_it_buys_back`,
   `test_a_roll_is_a_roll_even_when_its_candidate_was_pruned`; Task 4 tests; Task 9 test "a roll
   shows both legs and the net it was priced at".
7. **Propose a roll only where a roll exists.** A held short option with a known strike and
   right gets the Roll card; a long option, a contract no longer held, shares and spreads get no
   roll control → Task 10 PositionPage tests.

---

## File structure

```
src/
  storage/models.py                 MODIFY  ApprovalRow.decided_by
  storage/db.py                     MODIFY  _ADDED_COLUMNS["approvals"]["decided_by"]
  notify/approval_service.py        MODIFY  _process_button(..., decided_by="telegram")
  notify/command_drain.py           MODIFY  the indirection passes decided_by="web"
  notify/sender.py                  MODIFY  the entry auto-queue stamps decided_by="system"
  execution/roll_pipeline.py        MODIFY  an auto-approved roll stamps decided_by="system"
  common/schemas.py                 MODIFY  DayTrade.decided_by
  reporting/day.py                  MODIFY  decided_by on opened and rolled cards; activity_days
  api/spreads_db.py                 MODIFY  try_read_pick_rows, try_read_spread_rows_opened,
                                            read_activity_days (+ _json_list, _columns_of, _stamp)
  api/models/spreads.py             MODIFY  SpreadMenuItemOut, SpreadPickOut, SpreadPicksResponse
  api/routers/spreads.py            MODIFY  GET /spreads/picks (+ _now, _new_york_day_bounds,
                                            _menu_item_out, _pick_out)
  api/models/options.py             MODIFY  ApprovalRollFrom; ApprovalSummary.decided_by,
                                            roll_from, fill_price
  api/routers/options.py            MODIFY  _roll_from, _decider, _build_summary, list + detail joins
  api/models/pnl.py                 MODIFY  DayTradesResponse.previous_day, next_day
  api/routers/pnl.py                MODIFY  pnl_day fills them
tests/test_api_spread_picks.py      CREATE
tests/test_approval_decided_by.py   CREATE
tests/test_api_approvals.py         MODIFY  +6
tests/test_reporting_day.py         MODIFY  +4
tests/test_api_pnl_day.py           MODIFY  +1
docs/web/openapi.json               MODIFY  regenerated
web/
  lib/api-types.ts                  MODIFY  regenerated (offline)
  lib/useHydrated.ts                CREATE  (moved out of features/home/HomePage.tsx)
  components/options/types.ts       MODIFY  ApprovalSummary: decided_by?, roll_from?, fill_price?
  features/home/types.ts            MODIFY  DayTrade.decided_by?; DayTradesResponse previous_day?, next_day?
  features/home/proposal.ts         MODIFY  rollTitle, rollSentence, rollStub, decisionWords
  features/home/ProposalCard.tsx    MODIFY  a roll's title, sentence and stub
  features/home/TradeCard.tsx       MODIFY  who approved it, in words
  features/home/RealisedCalendar.tsx MODIFY "Open this day in History" in the day panel
  features/home/ReviewSheet.tsx     MODIFY  optional onSubmitted / onSettled
  features/home/HomePage.tsx        MODIFY  imports useHydrated
  features/home/positions.ts        MODIFY  Roll alert flag
  features/home/PositionsCard.tsx   MODIFY  reads /options/shorts for the flag
  features/trades/                  CREATE  views.ts, useTradesView.ts, useSubmittedApprovals.ts,
                                            ProposalsView.tsx, history.ts, HistoryView.tsx,
                                            SpreadsView.tsx, spreads.ts, types.ts, TradesPage.tsx
                                            (+ tests)
  features/position/RollCard.tsx    CREATE  (+ test)
  features/position/PositionPage.tsx MODIFY mounts RollCard
  app/trades/page.tsx               MODIFY  <Suspense><TradesPage/></Suspense>
  app/trades/page.test.tsx          DELETE  (cases ported to TradesPage.test.tsx)
  app/trades/[approvalId]/page.tsx  MODIFY  payslip shell, loading and not-found
  components/options/
    ControlsStrip.tsx               MODIFY  DrainWarning classes only
    AssessedBrowser.tsx             MODIFY  restyle, strategy prop
    AssessedRow.tsx                 MODIFY  markup only (flow untouched)
    StageBadge.tsx                  MODIFY  StatusWord, STAGE_LABEL export
    ApprovalDetail.tsx              MODIFY  payslip layout, a roll's legs, who decided
                                            (DecideControls untouched)
    ReviewPanel.tsx, IdealZoneBar.tsx, AlternativesTable.tsx, RationaleTags.tsx  MODIFY restyle
    RollProposal.tsx                CREATE  useRollProposal, RollReceipt, RollDialogs
    ShortsRow.tsx                   MODIFY  thin over RollProposal (markup of the row unchanged)
    TickerPillBar.tsx (+ test)      DELETE
    OrdersTable.tsx, FillsTable.tsx UNCHANGED  (unmounted; Part 3 restyles and mounts them)
  DESIGN.md, CLAUDE.md              MODIFY
ARCHITECTURE.md, STATUS.md, SETUP.md, CLAUDE.md, docs/web/api.md   MODIFY (Task 11)
```

---

## Section A — The API and the decision record (Tasks 1–2) · model: opus

Task 1 adds one read-only route. Task 2 adds the decision record to the trading DB and exposes it.
Nothing here touches the web app except the regenerated `api-types.ts` and two hand-written type
files that gain optional fields.

**Entry checks (the baseline; run from the repo root on `main` before Task 1 Step 1):**

- [x] **A1. Clean starting point.** `git status --short` shows nothing except this plan file
  (untracked) and, optionally, `web/design-preview.html`. `git branch --show-current` prints
  `main`.
- [x] **A2. Baseline is green.** All of these pass; record the pytest and vitest counts in the
  Progress log row, because every later gate compares against them:

  ```bash
  python -m pytest -q && ruff check . && mypy src
  cd web && npx vitest run && npx tsc --noEmit && npm run lint && cd ..
  ```

  A red baseline is not this plan's to fix: stop and report it.
- [x] **A3. The spec is valid.** `python3 ~/.claude/skills/da-vinci/scripts/design_md_check.py web/DESIGN.md`
  exits 0.
- [x] **A4. The pieces Task 1 builds on exist.** Each command prints at least one line:

  ```bash
  grep -n "def spreads_read_session\|def try_read_spread_rows\|^_COLUMNS" src/api/spreads_db.py
  grep -n "def spread_position_out" src/api/spread_inputs.py
  grep -n "class SpreadMenuItem\b\|class SpreadCandidate\b" src/common/schemas.py
  grep -n "class SpreadPickRow\|pick_id" src/spreads/store.py
  grep -n "class SpreadsAiCfg\|    ai: SpreadsAiCfg" src/common/config.py
  ```

- [x] **A5. The pieces Task 2 changes are where this plan says.** Each command prints exactly the
  line(s) named; anything else means the code moved, so stop and re-read it before editing:

  ```bash
  grep -n "^def _process_button(approval_id: int, action: str)" src/notify/approval_service.py src/notify/command_drain.py   # two lines
  grep -n "    return real(approval_id, action)" src/notify/command_drain.py                                                # one line
  grep -n "approval.decided_at = datetime.now(UTC)" src/notify/approval_service.py                                     # one line
  grep -n "decided_at=datetime.now(UTC)," src/notify/sender.py                                                         # one line
  grep -n "decided_at=now if auto_approve else None," src/execution/roll_pipeline.py                                   # one line
  grep -n '"snapshot": "JSON",' src/storage/db.py                                                                      # the approvals entry, and orders'
  grep -n "approval_by_candidate: dict\[str, int\]" src/reporting/day.py                                               # one line
  grep -n "def pnl_day" src/api/routers/pnl.py                                                                         # one line
  grep -rn "decided_by" src tests web/features web/components | head                                                   # prints nothing
  ```

**Section exit:** two commits on `feat/web-overhaul-2`; Tasks 1 and 2 ticked in the Progress log.

---

### Task 1: `GET /spreads/picks` — the day's menus, Claude's choice, what was sent

**Files:**
- Modify: `src/api/spreads_db.py`, `src/api/models/spreads.py`, `src/api/routers/spreads.py`
- Create: `tests/test_api_spread_picks.py`
- Modify: `docs/web/openapi.json`, `web/lib/api-types.ts` (both regenerated)
- Add: this plan file (first commit of the branch)

**Interfaces:**
- Consumes: `spreads_read_session()`, `_COLUMNS` (spreads_db.py), `spread_position_out(row, now)`
  (spread_inputs.py), `SpreadMenuItem` (src/common/schemas.py), `get_config().spreads`
  (`underlying`, `mode`, `ai.enabled`), `as_utc` (src/api/models/common.py).
- Produces:
  - `try_read_pick_rows(session, *, day: date) -> list[dict] | None` (newest first; `menu` and
    `send_reasons` parsed, `menu` None when it is not a JSON list; the three flags as bool)
  - `try_read_spread_rows_opened(session, *, start: datetime, end: datetime) -> list[dict] | None`
    (every mode; each row also has `pick_id`, None on a file without that column)
  - `read_activity_days(session) -> set[date]`
  - `GET /spreads/picks?day=YYYY-MM-DD` → `SpreadPicksResponse`:
    `as_of, available, underlying, mode, ai_enabled, day, previous_day, next_day, picks: list[SpreadPickOut], positions: list[SpreadPositionOut]`
  - `SpreadPickOut`: `pick_id, created_at, book_mode, choice, reason, fallback_reason, executed_letter, send_rejected, send_reasons, filled, model, regime, side, plan_bias, event_flag, menu_readable, menu: list[SpreadMenuItemOut], spread_id`
  - `SpreadMenuItemOut`: `letter, position, side, short_strike, long_strike, width, contracts, credit_mid, credit_after_costs, max_loss_per_contract_usd, short_delta, spot, dist_spot_pts, dist_em_multiple, be_nominal_exits`

- [x] **Step 1: Branch**

```bash
git switch -c feat/web-overhaul-2
```

If executing in a separate worktree (superpowers:using-git-worktrees), symlink the main `.venv`
and `web/node_modules` into it and run `python -c "from src.storage.db import init_db; init_db()"`
(a fresh worktree otherwise fails four monitor tests with "no such table: fills").

- [x] **Step 2: Write the failing tests** — `tests/test_api_spread_picks.py`

```python
"""GET /spreads/picks - one New York day of the spreads picker (web overhaul Part 2, Task 1).

Read-only over data/spreads.db through src/api/spreads_db.py (the API may not import
src.spreads). The tests may import the spreads models to build a real schema: test files are
not fenced.
"""

from __future__ import annotations

import sqlite3
from datetime import UTC, date, datetime

import pytest
from sqlalchemy import create_engine
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


@pytest.fixture()
def frozen_now(monkeypatch):
    """The route's clock: 2026-10-15 15:00 UTC, 11:00 in New York."""
    import src.api.routers.spreads as routes

    now = datetime(2026, 10, 15, 15, 0, tzinfo=UTC)
    monkeypatch.setattr(routes, "_now", lambda: now)
    return now


def _menu_item(letter: str, position: str, short: float, long: float, contracts: int = 2) -> dict:
    from src.common.schemas import SpreadCandidate, SpreadMenuItem

    candidate = SpreadCandidate(
        spread_id=f"20261015-P{short:g}-{long:g}",
        side="put",
        expiry=date(2026, 10, 15),
        short_strike=short,
        long_strike=long,
        width=short - long,
        credit_mid=0.25,
        credit_natural=0.24,
        short_delta=-0.14,
        spot=767.29,
        quote_time=datetime(2026, 10, 15, 14, 17, tzinfo=UTC),
    )
    return SpreadMenuItem(
        letter=letter,
        position=position,
        candidate=candidate,
        contracts=contracts,
        credit_after_costs=0.144,
        cost_pct_of_credit=0.424,
        max_loss_per_contract_usd=475.0,
        dist_spot_pts=5.29,
        dist_em_multiple=1.49,
        beyond_wall_pts=2.73,
        be_full_loss=0.9712,
        be_nominal_exits=0.9493,
    ).model_dump(mode="json")


def _pick(**over) -> dict:
    base = dict(
        created_at=datetime(2026, 10, 15, 14, 17, 30),  # naive UTC, as the service writes it
        day=date(2026, 10, 15),
        episode_key="2026-10-15:put:765.25",
        book_mode="paper",
        menu=[_menu_item("A", "inside", 763.0, 758.0), _menu_item("B", "baseline", 762.0, 757.0)],
        choice="B",
        reason="B sits past the put wall.",
        executed_letter="B",
        model="claude-sonnet-5-5",
        effort="low",
        snapshot={"regime": "negative", "side": "put"},
        market={},
        regime="negative",
        side="put",
    )
    base.update(over)
    return base


def _position(**over) -> dict:
    base = dict(
        spread_id="20261015-P762-757-101726",
        mode="paper",
        side="put",
        expiry=date(2026, 10, 15),
        short_strike=762.0,
        long_strike=757.0,
        width=5.0,
        contracts_opened=2,
        contracts=2,
        entry_credit=0.25,
        entry_commission=2.6,
        opened_at=datetime(2026, 10, 15, 14, 18),
        status="open",
    )
    base.update(over)
    return base


def _make_db(path, *, picks=(), positions=(), with_picks_table: bool = True) -> None:
    from src.spreads.store import SpreadPickRow, SpreadPositionRow, SpreadsBase

    eng = create_engine(f"sqlite:///{path}")
    if with_picks_table:
        SpreadsBase.metadata.create_all(eng)
    else:
        SpreadPositionRow.__table__.create(eng)
    with Session(eng) as s:
        for p in picks:
            s.add(SpreadPickRow(**p))
        for p in positions:
            s.add(SpreadPositionRow(**p))
        s.commit()
    eng.dispose()


def test_no_file_is_unavailable_not_an_error(client, spreads_file, frozen_now) -> None:
    r = client.get("/spreads/picks", headers=OWNER)
    assert r.status_code == 200
    body = r.json()
    assert body["available"] is False
    assert body["picks"] == [] and body["positions"] == []
    assert body["day"] == "2026-10-15"
    assert isinstance(body["ai_enabled"], bool)


def test_the_default_day_is_today_in_new_york(client, spreads_file, monkeypatch) -> None:
    import src.api.routers.spreads as routes

    # 02:00 UTC on the 16th is still the evening of the 15th in New York.
    monkeypatch.setattr(routes, "_now", lambda: datetime(2026, 10, 16, 2, 0, tzinfo=UTC))
    _make_db(spreads_file, picks=[_pick()])
    body = client.get("/spreads/picks", headers=OWNER).json()
    assert body["day"] == "2026-10-15"
    assert len(body["picks"]) == 1


def test_a_pick_carries_its_menu_choice_and_outcome(client, spreads_file, frozen_now) -> None:
    _make_db(spreads_file, picks=[_pick(filled=True)])
    body = client.get("/spreads/picks?day=2026-10-15", headers=OWNER).json()
    assert body["available"] is True
    (p,) = body["picks"]
    assert (p["choice"], p["executed_letter"], p["filled"]) == ("B", "B", True)
    assert p["reason"] == "B sits past the put wall."
    assert p["menu_readable"] is True
    assert [i["letter"] for i in p["menu"]] == ["A", "B"]
    b = p["menu"][1]
    assert b["position"] == "baseline"
    assert (b["side"], b["short_strike"], b["long_strike"], b["contracts"]) == ("put", 762.0, 757.0, 2)
    assert (b["credit_mid"], b["credit_after_costs"], b["be_nominal_exits"]) == (0.25, 0.144, 0.9493)
    # Stored naive UTC leaves the API with an offset, so a browser never reads it as local time.
    assert p["created_at"].endswith(("Z", "+00:00"))


def test_send_reasons_and_flags_read_back(client, spreads_file, frozen_now) -> None:
    _make_db(spreads_file, picks=[_pick(send_rejected=True, send_reasons=["stale_pick"])])
    (p,) = client.get("/spreads/picks", headers=OWNER).json()["picks"]
    assert p["send_rejected"] is True and p["filled"] is False
    assert p["send_reasons"] == ["stale_pick"]


def test_an_unreadable_menu_is_flagged_and_the_other_picks_still_render(
    client, spreads_file, frozen_now
) -> None:
    bad = _pick(menu=[{"letter": "A"}], choice="A", executed_letter="A")
    good = _pick(created_at=datetime(2026, 10, 15, 15, 0), episode_key="2026-10-15:call:770")
    _make_db(spreads_file, picks=[bad, good])
    picks = client.get("/spreads/picks", headers=OWNER).json()["picks"]
    # Newest first: the good pick (15:00) leads.
    assert [p["menu_readable"] for p in picks] == [True, False]
    assert len(picks[0]["menu"]) == 2
    assert picks[1]["menu"] == []


def test_a_pick_names_the_spread_it_opened(client, spreads_file, frozen_now) -> None:
    _make_db(spreads_file, picks=[_pick(filled=True)], positions=[_position(pick_id=1)])
    body = client.get("/spreads/picks", headers=OWNER).json()
    assert body["picks"][0]["spread_id"] == "20261015-P762-757-101726"


def test_the_day_lists_every_book_opened_that_new_york_day(client, spreads_file, frozen_now) -> None:
    _make_db(
        spreads_file,
        positions=[
            _position(),
            _position(spread_id="base-1", mode="baseline"),
            _position(spread_id="yesterday", opened_at=datetime(2026, 10, 14, 15, 0)),
        ],
    )
    body = client.get("/spreads/picks?day=2026-10-15", headers=OWNER).json()
    assert sorted((p["spread_id"], p["mode"]) for p in body["positions"]) == [
        ("20261015-P762-757-101726", "paper"),
        ("base-1", "baseline"),
    ]


def test_previous_and_next_skip_days_with_nothing(client, spreads_file, frozen_now) -> None:
    _make_db(
        spreads_file,
        picks=[_pick(day=date(2026, 10, 9), created_at=datetime(2026, 10, 9, 14, 0), episode_key="a")],
        positions=[_position(spread_id="later", opened_at=datetime(2026, 10, 20, 14, 0))],
    )
    body = client.get("/spreads/picks?day=2026-10-15", headers=OWNER).json()
    assert body["previous_day"] == "2026-10-09"
    assert body["next_day"] == "2026-10-20"
    assert body["picks"] == [] and body["positions"] == []


def test_an_old_file_without_the_picks_table_is_available_with_no_picks(
    client, spreads_file, frozen_now
) -> None:
    _make_db(spreads_file, positions=[_position()], with_picks_table=False)
    body = client.get("/spreads/picks", headers=OWNER).json()
    assert body["available"] is True
    assert body["picks"] == []
    assert len(body["positions"]) == 1


def test_an_older_positions_table_without_pick_id_still_reads(client, spreads_file, frozen_now) -> None:
    con = sqlite3.connect(spreads_file)
    con.execute(
        "CREATE TABLE spread_positions (id INTEGER PRIMARY KEY, spread_id TEXT, mode TEXT, "
        "side TEXT, expiry DATE, short_strike FLOAT, long_strike FLOAT, width FLOAT, "
        "contracts_opened INTEGER, contracts INTEGER, entry_credit FLOAT, entry_commission FLOAT, "
        "opened_at DATETIME, status TEXT, exit_debit FLOAT, exit_commission FLOAT, "
        "exit_reason TEXT, closed_at DATETIME, realized_pnl_usd FLOAT)"
    )
    con.execute(
        "INSERT INTO spread_positions (spread_id, mode, side, expiry, short_strike, long_strike, "
        "width, contracts_opened, contracts, entry_credit, entry_commission, opened_at, status, "
        "exit_commission, realized_pnl_usd) VALUES ('s1', 'paper', 'put', '2026-10-15', 762, 757, "
        "5, 2, 2, 0.25, 2.6, '2026-10-15 14:18:00.000000', 'open', 0, 0)"
    )
    con.commit()
    con.close()
    body = client.get("/spreads/picks", headers=OWNER).json()
    assert body["available"] is True
    assert body["picks"] == []
    assert [p["spread_id"] for p in body["positions"]] == ["s1"]


def test_a_bad_day_is_a_422(client, spreads_file) -> None:
    assert client.get("/spreads/picks?day=2026-13-01", headers=OWNER).status_code == 422


def test_it_needs_the_owner(client, spreads_file) -> None:
    assert client.get("/spreads/picks").status_code in (401, 403)
```

- [x] **Step 3: Run them to verify they fail**

Run: `python -m pytest tests/test_api_spread_picks.py -q`
Expected: FAIL (every test answers 404: no `/spreads/picks` route; `routes._now` does not exist).

- [x] **Step 4: Add the reads** — append to `src/api/spreads_db.py`

Add these imports at the top (keep the existing ones; `date`, `datetime` and `UTC` come from
`datetime`, `ZoneInfo` from `zoneinfo`, `json` is stdlib):

```python
import json
from datetime import UTC, date, datetime
from zoneinfo import ZoneInfo
```

Then append at the end of the file:

```python
_PICK_COLUMNS = (
    "id, created_at, day, book_mode, menu, choice, reason, fallback_reason, executed_letter, "
    "send_rejected, send_reasons, filled, model, regime, side, plan_bias, event_flag"
)
_NEW_YORK = ZoneInfo("America/New_York")


def _json_list(raw: Any) -> list[Any] | None:
    """A JSON column read through plain SQL comes back as text. None when it is not a list."""
    if isinstance(raw, list):
        return raw
    if isinstance(raw, str):
        try:
            value = json.loads(raw)
        except ValueError:
            return None
        return value if isinstance(value, list) else None
    return None


def _columns_of(session: Session, table: str) -> set[str]:
    """Column names of a table; empty when the table does not exist (an older file)."""
    try:
        return {str(r[1]) for r in session.execute(text(f"PRAGMA table_info({table})"))}
    except Exception:  # noqa: BLE001 - an unreadable schema reads as no columns
        session.rollback()
        return set()


def _stamp(dt: datetime) -> str:
    """A naive-UTC datetime in the text form SQLAlchemy stores in SQLite, for plain-SQL ranges."""
    return dt.strftime("%Y-%m-%d %H:%M:%S.%f")


def try_read_pick_rows(session: Session, *, day: date) -> list[dict[str, Any]] | None:
    """spread_picks rows for one New York day (the service stamps `day` in New York), newest
    first, or None when the read failed (an older file without the table: the picker never ran).
    `menu` and `send_reasons` come back parsed; a `menu` that is not a JSON list is None."""
    sql = text(
        f"SELECT {_PICK_COLUMNS} FROM spread_picks WHERE day = :day "
        "ORDER BY created_at DESC, id DESC"
    ).columns(day=Date, created_at=DateTime)
    try:
        result = session.execute(sql, {"day": day.isoformat()})
    except Exception as exc:  # noqa: BLE001 - the caller decides what unreadable means
        log.debug("api spreads_db: pick read failed: %s", exc)
        session.rollback()  # the next read on this session starts clean
        return None
    rows: list[dict[str, Any]] = []
    for r in result:
        row = dict(r._mapping)
        row["menu"] = _json_list(row["menu"])
        row["send_reasons"] = _json_list(row["send_reasons"]) or []
        for flag in ("send_rejected", "filled", "event_flag"):
            row[flag] = bool(row[flag])
        rows.append(row)
    return rows


def try_read_spread_rows_opened(
    session: Session, *, start: datetime, end: datetime
) -> list[dict[str, Any]] | None:
    """spread_positions rows of every mode opened in [start, end) (naive UTC, as stored), oldest
    first, each with `pick_id` (None on an older file that has no such column), or None when the
    read failed."""
    pick = "pick_id" if "pick_id" in _columns_of(session, "spread_positions") else "NULL AS pick_id"
    sql = text(
        f"SELECT {_COLUMNS}, {pick} FROM spread_positions "
        "WHERE opened_at >= :start AND opened_at < :end ORDER BY opened_at"
    ).columns(expiry=Date, opened_at=DateTime, closed_at=DateTime)
    try:
        result = session.execute(sql, {"start": _stamp(start), "end": _stamp(end)})
    except Exception as exc:  # noqa: BLE001 - the caller decides what unreadable means
        log.debug("api spreads_db: opened read failed: %s", exc)
        session.rollback()
        return None
    return [dict(r._mapping) for r in result]


def read_activity_days(session: Session) -> set[date]:
    """New York days with a pick or an opened spread, for the day navigation. A table an older
    file lacks contributes nothing."""
    days: set[date] = set()
    try:
        for (d,) in session.execute(text("SELECT DISTINCT day FROM spread_picks").columns(day=Date)):
            if d is not None:
                days.add(d)
    except Exception:  # noqa: BLE001 - no picks table: the picker never ran
        session.rollback()
    try:
        opened = text("SELECT opened_at FROM spread_positions").columns(opened_at=DateTime)
        for (at,) in session.execute(opened):
            if at is not None:
                days.add(at.replace(tzinfo=UTC).astimezone(_NEW_YORK).date())
    except Exception:  # noqa: BLE001
        session.rollback()
    return days
```

- [x] **Step 5: Add the response models** — append to `src/api/models/spreads.py`

Add `from pydantic import BaseModel` beside the existing `Field` import, then append:

```python
class SpreadMenuItemOut(BaseModel):
    """One lettered spread on a pick menu, flattened from the stored SpreadMenuItem. Credits are
    per share; every figure was computed by src/spreads/menu.py when the menu was built."""

    letter: str
    position: Literal["inside", "baseline", "outer"]
    side: Literal["put", "call"]
    short_strike: float
    long_strike: float
    width: float
    contracts: int  # set by the spreads gate, never by Claude
    credit_mid: float
    credit_after_costs: float
    max_loss_per_contract_usd: float
    short_delta: float | None
    spot: float
    dist_spot_pts: float  # short strike's distance from spot (positive = out of the money)
    dist_em_multiple: float | None  # the same in expected moves
    be_nominal_exits: float | None  # break-even win rate (0-1) under the configured exits


class SpreadPickOut(BaseModel):
    """One menu Claude was shown, its choice, and what the service did with it."""

    pick_id: int
    created_at: datetime
    book_mode: str
    choice: str  # a menu letter, or "skip"
    reason: str  # Claude's reason; "" when it gave none
    fallback_reason: str | None  # set when Claude's answer could not be used
    executed_letter: str | None  # the item the service tried to send; None when nothing
    send_rejected: bool  # True when it did not trade (refused at send time, or not filled)
    send_reasons: list[str]
    filled: bool
    model: str
    regime: str
    side: str | None
    plan_bias: str | None
    event_flag: bool
    menu_readable: bool  # False when the stored menu no longer parses; `menu` is then empty
    menu: list[SpreadMenuItemOut] = Field(default_factory=list)
    spread_id: str | None = None  # the position this pick opened, when one did


class SpreadPicksResponse(Envelope):
    available: bool  # False when data/spreads.db does not exist or cannot be read
    underlying: str
    mode: str  # the spreads service's configured book mode (shadow | paper)
    ai_enabled: bool  # config spreads.ai.enabled: whether menus are offered at all
    day: date  # the New York day shown
    previous_day: date | None = None  # nearest earlier day with a pick or an opened spread
    next_day: date | None = None
    picks: list[SpreadPickOut] = Field(default_factory=list)  # newest first
    positions: list[SpreadPositionOut] = Field(default_factory=list)  # every mode, oldest first
```

- [x] **Step 6: Add the route** — `src/api/routers/spreads.py`

Replace the module docstring and imports with:

```python
"""GET /spreads/positions and GET /spreads/picks — read-only, through src/api/spreads_db.py
(never src.spreads)."""

from __future__ import annotations

from datetime import UTC, date, datetime, time, timedelta
from typing import Any, Literal
from zoneinfo import ZoneInfo

from fastapi import APIRouter, Query
from pydantic import ValidationError

from src.api.deps import OwnerUser
from src.api.models.common import as_utc
from src.api.models.spreads import (
    SpreadMenuItemOut,
    SpreadPickOut,
    SpreadPicksResponse,
    SpreadPositionsResponse,
)
from src.api.spread_inputs import spread_position_out
from src.api.spreads_db import (
    read_activity_days,
    read_spread_rows,
    spreads_read_session,
    try_read_pick_rows,
    try_read_spread_rows_opened,
)
from src.common.config import get_config
from src.common.schemas import SpreadMenuItem

router = APIRouter(prefix="/spreads", tags=["spreads"])

NEW_YORK = ZoneInfo("America/New_York")
```

Keep `spread_positions` exactly as it is. Append below it:

```python
def _now() -> datetime:
    """The picks route's clock. Patched in tests."""
    return datetime.now(UTC)


def _new_york_day_bounds(day: date) -> tuple[datetime, datetime]:
    """[start, end) of a New York calendar day as naive UTC, the form spreads.db stores."""
    start = datetime.combine(day, time.min, NEW_YORK).astimezone(UTC)
    end = datetime.combine(day + timedelta(days=1), time.min, NEW_YORK).astimezone(UTC)
    return start.replace(tzinfo=None), end.replace(tzinfo=None)


def _menu_item_out(item: SpreadMenuItem) -> SpreadMenuItemOut:
    c = item.candidate
    return SpreadMenuItemOut(
        letter=item.letter,
        position=item.position,
        side=c.side,
        short_strike=c.short_strike,
        long_strike=c.long_strike,
        width=c.width,
        contracts=item.contracts,
        credit_mid=c.credit_mid,
        credit_after_costs=item.credit_after_costs,
        max_loss_per_contract_usd=item.max_loss_per_contract_usd,
        short_delta=c.short_delta,
        spot=c.spot,
        dist_spot_pts=item.dist_spot_pts,
        dist_em_multiple=item.dist_em_multiple,
        be_nominal_exits=item.be_nominal_exits,
    )


def _pick_out(row: dict[str, Any], spread_id: str | None) -> SpreadPickOut:
    """One spread_picks row. A menu that no longer parses (an older or damaged row) is said to
    be unreadable rather than guessed at, and never takes the other picks down with it."""
    menu: list[SpreadMenuItemOut] = []
    readable = row["menu"] is not None
    if readable:
        try:
            menu = [_menu_item_out(SpreadMenuItem.model_validate(m)) for m in row["menu"]]
        except ValidationError:
            readable, menu = False, []
    return SpreadPickOut(
        pick_id=row["id"],
        created_at=as_utc(row["created_at"]),
        book_mode=row["book_mode"],
        choice=row["choice"],
        reason=row["reason"] or "",
        fallback_reason=row["fallback_reason"],
        executed_letter=row["executed_letter"],
        send_rejected=row["send_rejected"],
        send_reasons=[str(r) for r in row["send_reasons"]],
        filled=row["filled"],
        model=row["model"],
        regime=row["regime"],
        side=row["side"] or None,
        plan_bias=row["plan_bias"],
        event_flag=row["event_flag"],
        menu_readable=readable,
        menu=menu,
        spread_id=spread_id,
    )


@router.get("/picks", response_model=SpreadPicksResponse)
def spread_picks(
    user: OwnerUser,  # noqa: ARG001
    day: date | None = None,
) -> SpreadPicksResponse:
    """One New York day of the spreads picker: each menu Claude was shown, its choice, what was
    sent, and every spread any book opened that day. `day` defaults to today in New York."""
    now = _now()
    cfg = get_config().spreads
    the_day = day or now.astimezone(NEW_YORK).date()
    unavailable = SpreadPicksResponse(
        as_of=now,
        available=False,
        underlying=cfg.underlying,
        mode=cfg.mode,
        ai_enabled=cfg.ai.enabled,
        day=the_day,
    )
    with spreads_read_session() as s:
        if s is None:
            return unavailable
        start, end = _new_york_day_bounds(the_day)
        opened = try_read_spread_rows_opened(s, start=start, end=end)
        if opened is None:
            return unavailable
        pick_rows = try_read_pick_rows(s, day=the_day) or []
        days = read_activity_days(s)
    by_pick = {r["pick_id"]: r["spread_id"] for r in opened if r.get("pick_id") is not None}
    return unavailable.model_copy(
        update={
            "available": True,
            "previous_day": max((d for d in days if d < the_day), default=None),
            "next_day": min((d for d in days if d > the_day), default=None),
            "picks": [_pick_out(p, by_pick.get(p["id"])) for p in pick_rows],
            "positions": [
                spread_position_out({k: v for k, v in r.items() if k != "pick_id"}, now)
                for r in opened
            ],
        }
    )
```

`Literal` and `Query` stay imported for `spread_positions`.

- [x] **Step 7: Run the tests to verify they pass**

Run: `python -m pytest tests/test_api_spread_picks.py tests/test_api_spreads.py tests/test_web_fence.py tests/test_spreads_fence.py -q`
Expected: PASS. If `test_web_fence.py` or `test_spreads_fence.py` fails, the route or the reads
broke a fence (an `src.spreads` import, or a second module opening the spreads file): fix the
code, never the fence test.

- [x] **Step 8: Regenerate the contract and the client types**

```bash
python -c "import json; from src.api.main import create_app; print(json.dumps(create_app().openapi(), indent=2))" > docs/web/openapi.json
cd web && npx openapi-typescript ../docs/web/openapi.json -o lib/api-types.ts && cd ..
python -m pytest tests/test_openapi_current.py -q
```

Expected: PASS; `git diff --stat docs/web/openapi.json web/lib/api-types.ts` shows only additions
for the three new schemas and the new path.

- [x] **Step 9: Full gate**

```bash
python -m pytest -q && ruff check . && mypy src
cd web && npx vitest run && npx tsc --noEmit && npm run lint && cd ..
```

Expected: pytest = baseline + 12, every other gate as at the baseline.

- [x] **Step 10: Commit**

```bash
git add src/api/spreads_db.py src/api/models/spreads.py src/api/routers/spreads.py \
  tests/test_api_spread_picks.py docs/web/openapi.json web/lib/api-types.ts \
  docs/superpowers/plans/2026-10-19-web-overhaul-2-trades.md
git commit -m "feat(api): GET /spreads/picks - the day's pick menus, Claude's choice and what was sent"
```

Then fill the Task 1 row of the Progress log (status, commit, gate, date, rulings) and amend
nothing: the log row is committed with the next task.

---

### Task 2: Who decided, what a roll moves, what filled, and History's neighbouring days

**Files:**
- Modify: `src/storage/models.py` (`ApprovalRow.decided_by`), `src/storage/db.py` (`_ADDED_COLUMNS`)
- Modify: `src/notify/approval_service.py` (`_process_button` gains `decided_by`),
  `src/notify/command_drain.py` (the indirection passes `"web"`), `src/notify/sender.py` (the
  entry auto-queue stamps `"system"`), `src/execution/roll_pipeline.py` (an auto-approved roll
  stamps `"system"`)
- Modify: `src/api/models/options.py`, `src/api/routers/options.py`
- Modify: `src/common/schemas.py` (`DayTrade.decided_by`), `src/reporting/day.py`,
  `src/api/models/pnl.py`, `src/api/routers/pnl.py`
- Create: `tests/test_approval_decided_by.py`
- Modify: `tests/test_api_approvals.py` (+6), `tests/test_reporting_day.py` (+4),
  `tests/test_api_pnl_day.py` (+1)
- Modify: `docs/web/openapi.json`, `web/lib/api-types.ts` (both regenerated),
  `web/components/options/types.ts`, `web/features/home/types.ts` (optional fields only)

**Interfaces:**
- Consumes: `_process_button(approval_id, action)` (approval_service.py; the drain's indirection
  of the same name), `_auto_queue_candidates` (sender.py), `queue_roll_candidate(..., auto_approve)`
  (roll_pipeline.py), `RollOrigin` (schemas.py), `_build_summary` (options router),
  `build_day_trades`, `_Lookups`, `leg_kind`, `et_date`, `close_day`, `_kind_in_scope` (reporting).
- Produces:
  - `ApprovalRow.decided_by: str | None` (`"system" | "web" | "telegram"`; null = not recorded)
  - `_process_button(approval_id: int, action: str, decided_by: str = "telegram")`
  - `ApprovalRollFrom` (`strike, expiry, right, contracts, old_mid, new_mid`); on
    `ApprovalSummary` (and so `ApprovalDetail`): `decided_by: Literal["system","web","telegram"] | None`,
    `roll_from: ApprovalRollFrom | None`, `fill_price: float | None`
  - `DayTrade.decided_by` (opened: the entry's approval; rolled: the roll's own approval; closed:
    always None, because a close is never the opening approval's decision)
  - `activity_days(session, legs, *, strategy) -> set[date]` (reporting/day.py);
    `DayTradesResponse.previous_day`, `.next_day`
  - web: `ApprovalRollFrom` and the three optional `ApprovalSummary` fields
    (`components/options/types.ts`); `DayTrade.decided_by?`, `DayTradesResponse.previous_day?`,
    `.next_day?` (`features/home/types.ts`)

**Why the drain's call site does not change.** CLAUDE.md: "the drain's approve/reject handlers
call `_process_button` unchanged, never reimplement it", and
`test_the_handler_calls_process_button_rather_than_reimplementing_it` monkeypatches the drain's
indirection with a two-argument lambda. So `_apply_approval_decision` keeps calling
`_process_button(payload.approval_id, action)`; only the indirection's body becomes
`real(approval_id, action, decided_by="web")`. That test passes unmodified (its lambda replaces
the indirection, so in that test the row records `telegram`, which the test does not read).

- [x] **Step 1: Write the failing tests** — `tests/test_approval_decided_by.py`

```python
"""approvals.decided_by - who decided each approval (web overhaul Part 2, Task 2).

A record for the console, never an input: written where an approval is decided, read by the
API, and by nothing on the trading path.
"""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from pathlib import Path
from types import SimpleNamespace

from src.common.schemas import Strategy
from src.storage.models import ApprovalRow
from tests.test_roll_pipeline import _cand as _roll_cand

ROOT = Path(__file__).resolve().parents[1]


def _pending(db, candidate_id: str = "c1") -> int:
    with db() as s:
        row = ApprovalRow(
            candidate_id=candidate_id,
            status="pending",
            chat_id="9",
            expires_at=datetime.now(UTC) + timedelta(hours=1),
        )
        s.add(row)
        s.flush()
        return row.id


def _decided_by(db, approval_id: int) -> str | None:
    with db() as s:
        return s.get(ApprovalRow, approval_id).decided_by


def test_a_tap_in_telegram_is_recorded_as_telegram(db) -> None:
    from src.notify.approval_service import _process_button

    approve, reject = _pending(db, "a"), _pending(db, "b")
    _process_button(approve, "approve")
    _process_button(reject, "reject")
    assert _decided_by(db, approve) == "telegram"
    assert _decided_by(db, reject) == "telegram"


def test_the_drain_names_the_web(db) -> None:
    # The drain's handler calls this indirection with (approval_id, action) exactly as before;
    # only the indirection adds who decided.
    from src.notify.command_drain import _process_button as via_drain

    approval_id = _pending(db)
    found, _text, _short = via_drain(approval_id, "approve")
    assert found
    assert _decided_by(db, approval_id) == "web"


def test_a_second_decision_never_overwrites_the_first(db) -> None:
    from src.notify.approval_service import _process_button
    from src.notify.command_drain import _process_button as via_drain

    approval_id = _pending(db)
    _process_button(approval_id, "approve")
    _found, text, _short = via_drain(approval_id, "approve")
    assert text.startswith("Already")
    assert _decided_by(db, approval_id) == "telegram"


def test_an_auto_approved_roll_is_recorded_as_the_system(db) -> None:
    from src.execution.roll_pipeline import queue_roll_candidate

    approval_id = queue_roll_candidate(_roll_cand(), chat_id="9", ttl_minutes=120, auto_approve=True)
    assert approval_id is not None
    assert _decided_by(db, approval_id) == "system"


def test_a_roll_waiting_for_a_tap_has_no_decider_yet(db) -> None:
    from src.execution.roll_pipeline import queue_roll_candidate

    approval_id = queue_roll_candidate(_roll_cand(), chat_id="9", ttl_minutes=120)
    assert approval_id is not None
    assert _decided_by(db, approval_id) is None


async def test_the_entry_auto_queue_is_recorded_as_the_system(db, monkeypatch) -> None:
    import src.notify.sender as sender

    class _Bot:
        def __init__(self, token: str) -> None:
            self.token = token

        async def __aenter__(self) -> _Bot:
            return self

        async def __aexit__(self, *exc: object) -> bool:
            return False

        async def send_message(self, **_: object) -> None:
            return None

    monkeypatch.setattr(sender, "is_halted", lambda: False)
    monkeypatch.setattr(sender, "Bot", _Bot)
    monkeypatch.setattr(sender, "format_auto_trade_notification", lambda queued: "queued")
    cand = _roll_cand().model_copy(
        update={"candidate_id": "csp-aapl-195", "strategy": Strategy.CASH_SECURED_PUT, "roll_from": None}
    )
    cfg = SimpleNamespace(approval=SimpleNamespace(ttl_minutes=60), is_live=False)

    assert await sender._auto_queue_candidates([cand], cfg, "token", "chat", None) is True
    with db() as s:
        row = s.query(ApprovalRow).filter_by(candidate_id="csp-aapl-195").one()
        assert (row.status, row.decided_by) == ("approved", "system")


def test_an_expiry_leaves_it_unset(db) -> None:
    from src.storage.approvals import expire_stale_approvals

    approval_id = _pending(db)
    expire_stale_approvals(force=True)
    with db() as s:
        row = s.get(ApprovalRow, approval_id)
        assert (row.status, row.decided_by) == ("expired", None)


def test_the_trading_path_never_reads_who_decided() -> None:
    """decided_by is a record for the console. The engine and the strategies never mention it;
    execution only writes it, once, where the roll pipeline auto-approves."""
    hits = []
    for pkg in ("engine", "strategies", "execution"):
        for path in sorted((ROOT / "src" / pkg).rglob("*.py")):
            for line in path.read_text().splitlines():
                if "decided_by" in line:
                    hits.append((path.relative_to(ROOT).as_posix(), line.strip()))
    assert hits == [
        ("src/execution/roll_pipeline.py", 'decided_by="system" if auto_approve else None,'),
    ]
```

Append to `tests/test_api_approvals.py`:

```python
# --- web overhaul Part 2, Task 2: who decided, a roll's leg, the fill --------------------------


def _roll_snapshot(*, with_leg: bool = True) -> dict:
    snap = _snapshot(underlying="AAPL", strategy="roll", strike=250.0, premium=1.175)
    if with_leg:
        snap["roll_from"] = {
            "con_id": 8, "candidate_id": "c0", "strike": 250.0, "expiry": "2026-10-23",
            "right": "P", "contracts": 1, "chain_id": "c0", "seq": 1,
            "original_expiry": "2026-10-23", "old_mid": 2.1, "new_mid": 3.275, "allow_debit": False,
        }  # fmt: skip
    return snap


def _all_by_cid(client) -> dict:
    r = client.get("/options/approvals?status=all", headers=AUTH)
    assert r.status_code == 200
    return {a["candidate_id"]: a for a in r.json()["approvals"]}


def test_who_decided_is_reported_and_an_unrecorded_one_is_null(client) -> None:
    with session_scope() as s:
        row = _seed_approval(s, candidate_id="auto", status="approved", decided_at=datetime.now(UTC))
        row.decided_by = "system"
    by_cid = _all_by_cid(client)
    assert by_cid["auto"]["decided_by"] == "system"
    assert by_cid["c1"]["decided_by"] is None


def test_an_unrecognised_decider_reads_as_null_never_an_error(client) -> None:
    with session_scope() as s:
        row = _seed_approval(s, candidate_id="odd", status="approved")
        row.decided_by = "cron"
    assert _all_by_cid(client)["odd"]["decided_by"] is None


def test_a_roll_carries_the_leg_it_buys_back(client) -> None:
    with session_scope() as s:
        _seed_candidate(s, candidate_id="r1", run_id="roll-1", underlying="AAPL", strategy="roll", strike=250.0)
        _seed_approval(s, candidate_id="r1", snapshot=_roll_snapshot())
    by_cid = _all_by_cid(client)
    leg = by_cid["r1"]["roll_from"]
    assert (leg["strike"], leg["expiry"], leg["right"], leg["contracts"]) == (250.0, "2026-10-23", "P", 1)
    assert (leg["old_mid"], leg["new_mid"]) == (2.1, 3.275)
    assert by_cid["r1"]["premium"] == 1.175  # the net, per share
    assert by_cid["c1"]["roll_from"] is None  # an entry has no leg to buy back


def test_a_roll_from_before_the_redesign_has_no_leg(client) -> None:
    with session_scope() as s:
        _seed_approval(s, candidate_id="old-roll", snapshot=_roll_snapshot(with_leg=False))
    a = _all_by_cid(client)["old-roll"]
    assert a["roll_from"] is None and a["source"] == "roll"


def test_a_roll_is_a_roll_even_when_its_candidate_was_pruned(client) -> None:
    with session_scope() as s:
        _seed_approval(s, candidate_id="pruned-roll", snapshot=_roll_snapshot())
    assert _all_by_cid(client)["pruned-roll"]["source"] == "roll"


def test_the_fill_price_comes_from_the_order_and_is_null_until_it_fills(client) -> None:
    with session_scope() as s:
        ap = s.query(ApprovalRow).first()
        s.add(
            OrderRow(candidate_id=ap.candidate_id, approval_id=ap.id, state="filled",
                     limit_price=3.25, avg_fill_price=3.2, snapshot=_snapshot())
        )  # fmt: skip
        _seed_approval(s, candidate_id="working")
        s.flush()
        working = s.query(ApprovalRow).filter_by(candidate_id="working").one()
        s.add(
            OrderRow(candidate_id="working", approval_id=working.id, state="submitted",
                     limit_price=3.0, snapshot=_snapshot())
        )  # fmt: skip
    by_cid = _all_by_cid(client)
    assert (by_cid["c1"]["order_state"], by_cid["c1"]["fill_price"]) == ("filled", 3.2)
    assert by_cid["working"]["fill_price"] is None
    detail = client.get(f"/options/approvals/{by_cid['c1']['id']}", headers=AUTH).json()
    assert (detail["fill_price"], detail["decided_by"], detail["roll_from"]) == (3.2, None, None)
```

Append to `tests/test_reporting_day.py`:

```python
# --- who approved it (web overhaul Part 2, Task 2) ------------------------------------------


def test_an_opened_card_says_who_approved_it(db) -> None:
    put_leg(db, "c1")
    with db() as s:
        s.add(ApprovalRow(candidate_id="c1", status="approved", decided_by="system"))
    [t] = day_trades(db)
    assert t.decided_by == "system"


def test_an_unrecorded_decider_stays_unknown(db) -> None:
    put_leg(db, "c1")
    with db() as s:
        s.add(ApprovalRow(candidate_id="c1", status="approved"))
    [t] = day_trades(db)
    assert t.decided_by is None


def test_a_closed_card_never_borrows_the_opening_decision(db) -> None:
    put_leg(db, "c1", sold=(2.35, at(14), 1.3), bought=(0.5, at(17), 1.3, "profit_take"))
    with db() as s:
        s.add(ApprovalRow(candidate_id="c1", status="approved", decided_by="web"))
    trades = day_trades(db)
    assert by_key(trades, "c1:opened").decided_by == "web"
    assert by_key(trades, "c1:closed").decided_by is None


def test_a_rolled_card_says_who_approved_the_roll(db) -> None:
    seed_roll(db)
    with db() as s:
        s.query(ApprovalRow).filter_by(candidate_id="new").update({"decided_by": "system"})
    [t] = day_trades(db)
    assert t.decided_by == "system"
```

Append to `tests/test_api_pnl_day.py` (and add `ApprovalRow` to its `src.storage.models` import):

```python
def test_previous_and_next_skip_days_with_no_wheel_activity(client, db) -> None:
    seed(db, "early", sold_at=datetime(2026, 10, 5, 14))
    seed(db, "late", sold_at=datetime(2026, 10, 14, 14), bought_at=datetime(2026, 10, 16, 15), reason="profit_take")
    with db() as s:
        # A call proposal raised on the 7th that never traded still makes the 7th a History day.
        s.add(
            ApprovalRow(candidate_id="x", status="expired", created_at=datetime(2026, 10, 7, 15),
                        snapshot={"strategy": "covered_call", "right": "C"})
        )  # fmt: skip
    body = client.get("/pnl/day?date=2026-10-09", headers=OWNER).json()
    assert (body["previous_day"], body["next_day"]) == ("2026-10-07", "2026-10-14")
    puts = client.get("/pnl/day?date=2026-10-09&strategy=csp", headers=OWNER).json()
    assert puts["previous_day"] == "2026-10-05"  # the call proposal is outside the puts' scope
    last = client.get("/pnl/day?date=2026-10-16", headers=OWNER).json()
    assert (last["previous_day"], last["next_day"]) == ("2026-10-14", None)
```

- [x] **Step 2: Run them to verify they fail**

Run: `python -m pytest tests/test_approval_decided_by.py tests/test_api_approvals.py tests/test_reporting_day.py tests/test_api_pnl_day.py -q`
Expected: FAIL (`ApprovalRow` has no `decided_by`; the API has no `decided_by`, `roll_from`,
`fill_price`, `previous_day` or `next_day`). The fence test fails too, because it finds no hit at
all yet.

- [x] **Step 3: The column** — `src/storage/models.py`, in `ApprovalRow` directly under
  `decided_at`:

```python
    # Who decided it (web overhaul Part 2, 2026-10-19): "system" (auto-approved on WHITELIST or
    # FULL autonomy, entries and rolls), "web" (the console, through the command drain) or
    # "telegram" (a tap). Null on a row decided before the column existed, and on an expiry.
    # A record for the console only: nothing on the trading path reads it.
    decided_by: Mapped[str | None] = mapped_column(String(12), nullable=True)
```

`src/storage/db.py`, in `_ADDED_COLUMNS`:

```python
    "approvals": {
        "snapshot": "JSON",
        "decided_by": "VARCHAR(12)",  # who decided it (web overhaul Part 2, 2026-10-19)
    },
```

- [x] **Step 4: The three writers**

`src/notify/approval_service.py`: change the signature and add one line beside `decided_at`:

```python
def _process_button(
    approval_id: int, action: str, decided_by: str = "telegram"
) -> tuple[bool, str, str]:
    """Synchronous DB work: update approval status, optionally enqueue an order.

    Returns (found, decision_text, candidate_id_short).
    decision_text is plain text (no parse_mode) suitable for edit_message_text.
    ``decided_by`` records who decided ("telegram" for a tap; the command drain's indirection
    passes "web"). It is written once, with the decision, and never read back by the trading path.
    """
```

```python
            approval.decided_at = datetime.now(UTC)
            approval.decided_by = decided_by
```

The idempotency guard above it returns before either line for an already-decided approval, so a
second decision never overwrites the first.

`src/notify/command_drain.py`: the indirection only (its callers are unchanged):

```python
def _process_button(approval_id: int, action: str) -> tuple[bool, str, str]:
    """Indirection to ``src.notify.approval_service._process_button``.

    Deferred so ``approval_service`` (which imports this module at import time
    for ``drain_once``) is not a circular import. Tests monkeypatch THIS name to
    assert the handler delegates rather than reimplementing. The one thing it adds is who
    decided: a decision drained from the console is recorded as "web".
    """
    from src.notify.approval_service import _process_button as real

    return real(approval_id, action, decided_by="web")
```

`src/notify/sender.py`, in `_auto_queue_candidates`' `ApprovalRow(...)`:

```python
                        decided_at=datetime.now(UTC),
                        decided_by="system",  # auto-approved: shown on the web, never read back
```

`src/execution/roll_pipeline.py`, in `queue_roll_candidate`'s `ApprovalRow(...)` (the comment goes
on the line above and must not contain the column's name, which the fence test counts):

```python
                decided_at=now if auto_approve else None,
                # Who decided: the system on FULL autonomy. Shown on the web, never read back.
                decided_by="system" if auto_approve else None,
```

Run: `python -m pytest tests/test_approval_decided_by.py tests/test_drain_approve_reject.py tests/test_roll_pipeline.py tests/test_execution.py -q`
Expected: PASS, with `test_the_handler_calls_process_button_rather_than_reimplementing_it`
unmodified.

- [x] **Step 5: The approval API** — `src/api/models/options.py`

Above `ApprovalSummary`:

```python
DecidedByLit = Literal["system", "web", "telegram"]


class ApprovalRollFrom(BaseModel):
    """The short a roll buys back, from the frozen snapshot's ``roll_from`` (2026-10-11 roll
    redesign). The mids are what the roll was priced at when it was proposed, per share: a quote,
    never a fill."""

    strike: float
    expiry: date
    right: str  # "C" | "P"
    contracts: int
    old_mid: float | None = None  # to buy the old leg back
    new_mid: float | None = None  # the new leg's price
```

In `ApprovalSummary`, after `rationale_tags`:

```python
    # Web overhaul Part 2 (2026-10-19). Who decided: None before the record existed, or on an
    # expiry, never inferred.
    decided_by: DecidedByLit | None = None
    roll_from: ApprovalRollFrom | None = None  # a roll's buy-back leg; None for an entry
    fill_price: float | None = None  # the order's average fill per share; None until it fills
```

`src/api/routers/options.py`: add `ApprovalRollFrom` to the `src.api.models.options` import and
`from pydantic import ValidationError` to the imports, then add above `_build_summary`:

```python
_DECIDERS = ("system", "web", "telegram")


def _roll_from(snap: dict[str, Any]) -> ApprovalRollFrom | None:
    """A roll's buy-back leg from its snapshot. None for an entry, or for a roll frozen before
    the 2026-10-11 redesign (no ``roll_from``), or for one that no longer parses."""
    raw = snap.get("roll_from")
    if not isinstance(raw, dict):
        return None
    try:
        return ApprovalRollFrom.model_validate(raw)
    except ValidationError:
        return None


def _decider(raw: Any) -> Any:
    """The recorded decider, or None for anything unrecorded or unrecognised (never a 500)."""
    return raw if raw in _DECIDERS else None
```

Change `_build_summary`'s signature to add `fill_price: float | None = None` after `review`, and
in its body replace the `source=_source_from_run_id(run_id),` argument and add three fields:

```python
        # The snapshot says roll even when the 14-day purge has removed the candidate row.
        source="roll" if snap_fields.get("strategy") == "roll" else _source_from_run_id(run_id),
        review=review,
        rationale_tags=rationale_tags,
        decided_by=_decider(getattr(approval, "decided_by", None)),
        roll_from=_roll_from(snap),
        fill_price=fill_price,
    )
```

In the list route, replace the `order_map` block and the `summaries` comprehension with:

```python
    order_map: dict[int, tuple[str, float | None]] = {}
    if approval_ids:
        orders = db.execute(
            select(OrderRow.approval_id, OrderRow.state, OrderRow.avg_fill_price).where(
                OrderRow.approval_id.in_(approval_ids)
            )
        ).all()
        order_map = {row[0]: (row[1], row[2]) for row in orders if row[0] is not None}

    review_map = _latest_reviews_by_candidate(db, candidate_ids)

    summaries = []
    for a in approvals:
        state, fill_price = order_map.get(a.id, (None, None))
        summaries.append(
            _build_summary(
                a, cand_map.get(a.candidate_id), state, review_map.get(a.candidate_id), fill_price
            )
        )
```

In the detail route: declare `fill_price: float | None = None` beside `order_id`, select
`OrderRow.id, OrderRow.state, OrderRow.avg_fill_price`, unpack
`order_id, order_state, fill_price = order_row`, call
`_build_summary(approval, cand, order_state, fill_price=fill_price)`, and add to the
`ApprovalDetail(...)` arguments, after `rationale_tags=summary.rationale_tags,`:

```python
        decided_by=summary.decided_by,
        roll_from=summary.roll_from,
        fill_price=summary.fill_price,
```

Run: `python -m pytest tests/test_api_approvals.py -q`
Expected: PASS (every existing test plus the 6 new).

- [x] **Step 6: The day's cards and History's neighbouring days**

`src/common/schemas.py`, in `DayTrade` after `approval_id`:

```python
    # Who approved the trade this card is about (web overhaul Part 2): an opened card's entry
    # approval, a rolled card's roll approval. A closed card has none (a close is not the
    # opening approval's decision). None when not recorded; never inferred.
    decided_by: Literal["system", "web", "telegram"] | None = None
```

`src/reporting/day.py`:

1. `_Lookups` gains a last field, `decided_by: dict[int, str]  # approval id -> who decided it`.
2. In `_lookups`, beside `approvals: dict[str, int] = {}` add `decided: dict[int, str] = {}`; in
   the approvals loop, after `approvals[a.candidate_id] = a.id`, add
   `if a.decided_by in ("system", "web", "telegram"): decided[a.id] = a.decided_by`; and return
   `_Lookups(approvals, reviews, roll_close, new_ids, decisions, views, decided)`.
3. Add below `_lookups`:

```python
def _decider(look: _Lookups, candidate_id: str | None) -> str | None:
    """Who approved the trade a candidate opened; None when unrecorded or there is no approval."""
    approval_id = look.approval_by_candidate.get(candidate_id or "")
    return look.decided_by.get(approval_id) if approval_id is not None else None
```

4. In the rolled card's `base = {**base, ...}`, add `"decided_by": _decider(look, new_cid),`
   (only the roll's own approval; never the old leg's, which `approval_id` falls back to).
5. In the opened `DayTrade(...)`, add `decided_by=_decider(look, leg.candidate_id),` after
   `approval_id=...`.
6. Append at the end of the wheel section:

```python
def _approval_kind(snapshot: Any) -> Literal["csp", "cc"] | None:
    """The side of the book a proposal's snapshot is on, as leg_kind does for a leg."""
    if not isinstance(snapshot, dict):
        return None
    s, r = snapshot.get("strategy"), snapshot.get("right")
    if s == "cash_secured_put" or (s == "roll" and r == "P"):
        return "csp"
    if s == "covered_call" or (s == "roll" and r == "C"):
        return "cc"
    return None


def activity_days(
    session: _SessionFactory, legs: Iterable[PnlLeg], *, strategy: PayStrategy
) -> set[date]:
    """New York days with a wheel trade (opened, closed, rolled) or a wheel proposal raised, in
    the strategy's scope: History's previous and next day. Spreads are not counted; the spreads
    view navigates over GET /spreads/picks."""
    days: set[date] = set()
    for leg in legs:
        if not _kind_in_scope(leg_kind(leg), strategy):
            continue
        for d in (et_date(leg.opened_at), close_day(leg)):
            if d is not None:
                days.add(d)
    with session() as sess:
        for created_at, snapshot in sess.execute(select(ApprovalRow.created_at, ApprovalRow.snapshot)):
            d = et_date(created_at)
            if d is not None and _kind_in_scope(_approval_kind(snapshot), strategy):
                days.add(d)
    return days
```

`src/api/models/pnl.py`, in `DayTradesResponse`:

```python
    # Web overhaul Part 2: the nearest New York days with wheel activity (a trade or a proposal)
    # in this scope, for History's day navigation; None at either end.
    previous_day: date | None = None
    next_day: date | None = None
```

`src/api/routers/pnl.py`: import `activity_days` beside `build_day_trades`, and in `pnl_day`
before the `return`:

```python
    days = activity_days(_session_factory(db), legs, strategy=strategy)
```

then add to `DayTradesResponse(...)`:

```python
        previous_day=max((d for d in days if d < the_day), default=None),
        next_day=min((d for d in days if d > the_day), default=None),
```

Run: `python -m pytest tests/test_reporting_day.py tests/test_api_pnl_day.py tests/test_web_fence.py -q`
Expected: PASS (4 + 1 new). `test_reporting_never_writes_anything` still passes: `activity_days`
only selects.

- [x] **Step 7: Regenerate the contract and the client types; add the hand-written fields**

```bash
python -c "import json; from src.api.main import create_app; print(json.dumps(create_app().openapi(), indent=2))" > docs/web/openapi.json
cd web && npx openapi-typescript ../docs/web/openapi.json -o lib/api-types.ts && cd ..
python -m pytest tests/test_openapi_current.py -q
```

`web/components/options/types.ts`: add above `ApprovalSummary`

```ts
/** A roll's buy-back leg and the mids it was priced at (per share; a quote, never a fill). */
export type ApprovalRollFrom = {
  strike: number;
  expiry: string;
  right: string;
  contracts: number;
  old_mid: number | null;
  new_mid: number | null;
};
```

and inside `ApprovalSummary`, after `rationale_tags`:

```ts
  /** Who decided: the system (auto-approved), you on the web, or you in Telegram. Null when not
   *  recorded (decided before 2026-10-19, or expired); never inferred. Optional so fixtures
   *  written before the field still type-check. */
  decided_by?: "system" | "web" | "telegram" | null;
  /** A roll's buy-back leg; null for an entry or a roll frozen before the 2026-10-11 redesign. */
  roll_from?: ApprovalRollFrom | null;
  /** The order's average fill per share; null until it fills. */
  fill_price?: number | null;
```

`web/features/home/types.ts`: in `DayTrade` add
`decided_by?: "system" | "web" | "telegram" | null;` and in `DayTradesResponse` add
`previous_day?: string | null;` and `next_day?: string | null;`.

- [x] **Step 8: Full gate**

```bash
python -m pytest -q && ruff check . && mypy src
cd web && npx vitest run && npx tsc --noEmit && npm run lint && cd ..
```

Expected: pytest = Task 1's count + 19, every other gate as at the baseline.

- [x] **Step 9: Commit** (with the Progress log row for Task 1 filled in)

```bash
git add src/storage/models.py src/storage/db.py src/notify/approval_service.py src/notify/command_drain.py \
  src/notify/sender.py src/execution/roll_pipeline.py src/api/models/options.py src/api/routers/options.py \
  src/common/schemas.py src/reporting/day.py src/api/models/pnl.py src/api/routers/pnl.py \
  tests/test_approval_decided_by.py tests/test_api_approvals.py tests/test_reporting_day.py tests/test_api_pnl_day.py \
  docs/web/openapi.json web/lib/api-types.ts web/components/options/types.ts web/features/home/types.ts \
  docs/superpowers/plans/2026-10-19-web-overhaul-2-trades.md
git commit -m "feat: record who decided each approval; expose it with a roll's leg, the fill and History's days"
```

The running trading service writes the column only after `./ibkr restart`; until then new rows
carry null and read "Approved". Say so in the hand-off (Task 11 Step 7).

---

## Section B — The views (Tasks 3–7) · model: sonnet

Each view is its own component in `web/features/trades/`, tested on its own. None is mounted at
`/trades` until Task 8, so the legacy page keeps working throughout this section. Task 4 also
changes Home's proposal and trade cards (rolls and who approved), which Home shows at once.

**Entry checks (run before Task 3):**

- [x] **B1. Section A landed.** `git log --oneline main..HEAD` shows two commits; Tasks 1 and 2
  are ticked.
- [x] **B2. Both gates green.** `python -m pytest -q && ruff check . && mypy src` and
  `cd web && npx vitest run && npx tsc --noEmit && npm run lint`.
- [x] **B3. The routes answer.** `python -m pytest -q tests/test_api_spread_picks.py tests/test_approval_decided_by.py tests/test_api_pnl_day.py`
  passes.
- [x] **B4. The hand-written client types will match the contract.** This prints the field names
  that Task 7's `web/features/trades/types.ts` and Task 2's optional fields must use. Compare them
  with Task 7 Step 3 and Task 2 Step 7. If any differ, fix the types there (not the API) and
  record the ruling:

  ```bash
  python - <<'EOF'
  import json
  s = json.load(open("docs/web/openapi.json"))["components"]["schemas"]
  for name in ("SpreadPicksResponse", "SpreadPickOut", "SpreadMenuItemOut", "ApprovalRollFrom"):
      print(name, sorted(s[name]["properties"]))
  for name, keys in (("ApprovalSummary", ("decided_by", "roll_from", "fill_price")),
                     ("DayTrade", ("decided_by",)), ("DayTradesResponse", ("previous_day", "next_day"))):
      print(name, [k for k in keys if k in s[name]["properties"]])
  EOF
  ```

- [x] **B5. The pieces Section B reuses exist under these names.** Each line prints a match:

  ```bash
  cd web
  grep -n "export function usePendingApprovals" features/home/NeedsYou.tsx
  grep -n "export function ProposalCard\|export function proposalTitle\|export function ProposalBody" features/home/ProposalCard.tsx
  grep -n "export function ReviewSheet" features/home/ReviewSheet.tsx
  grep -n "export function TradeCard" features/home/TradeCard.tsx
  grep -n "export function useControls" components/shell/BotCard.tsx
  grep -n "export function DrainWarning" components/options/ControlsStrip.tsx
  grep -n "export function kindOf\|export function matchesFilter\|export const STRATEGY_EYEBROW" lib/strategy.ts
  grep -n "export function loadAllPersistedCommands\|export function savePersistedCommand\|export type CommandStatus" lib/commands.ts
  grep -n "export function renderWithQuery\|export const apiFetchMock" lib/test-query.tsx
  grep -n "onApprovalSubmitted?: (id: number, command: CommandStatus) => void\|onApprovalSettled?: (id: number) => void" components/options/DecideControls.tsx
  grep -n "queryKey: \[\"options\", \"orders\", filter\]" components/options/OrdersTable.tsx
  cd ..
  ```

  A different name or signature → use the real one in Tasks 3–7 and record the ruling.

**Section exit:** five more commits; every `web/features/trades/*.test.*` and
`web/features/home/*.test.*` green.

---

### Task 3: The Trades contract, view state, and the Proposals view

**Files:**
- Modify: `web/DESIGN.md` (§ Surfaces → Trades)
- Create: `web/features/trades/views.ts`, `web/features/trades/views.test.ts`
- Create: `web/features/trades/useTradesView.ts`, `web/features/trades/useTradesView.test.tsx`
- Create: `web/features/trades/useSubmittedApprovals.ts`, `web/features/trades/useSubmittedApprovals.test.tsx`
- Modify: `web/features/home/ReviewSheet.tsx` (two optional props)
- Create: `web/features/trades/ProposalsView.tsx`, `web/features/trades/ProposalsView.test.tsx`

**Interfaces:**
- Consumes: `usePendingApprovals(strategy)` → `{ data, isError, visible }` (NeedsYou.tsx);
  `ProposalCard({ approval, onReview })`; `ReviewSheet`; `SegmentedControl`; `StrategyFilter`;
  `loadAllPersistedCommands(): Map<number, CommandStatus>`.
- Produces:
  - `views.ts`: `type TradesView = "proposals" | "history" | "assessed" | "spreads"`,
    `VIEW_LABEL: Record<TradesView, string>`, `viewsFor(strategy): TradesView[]`,
    `explicitView(raw, strategy): TradesView | null` (the URL's view when this strategy has it;
    the retired `working` and `decided` read as `history`),
    `defaultView(strategy, pending: number | null): TradesView | null` (ruling 2),
    `type TickerCount = { ticker: string; count: number }`, `tickerCounts(items: { underlying: string }[]): TickerCount[]`
  - `useTradesView(strategy, pending): [TradesView | null, (v: TradesView) => void]` (the `?view=`
    URL state; null only while the default is still unknown), `useTradesDay(): [string | null,
    (day: string | null) => void]` (the `?day=` URL state; null is today)
  - `useSubmittedApprovals(): { submitted: Map<number, CommandStatus>; markSubmitted(id, command): void; clearSubmitted(id): void }`
    (both callbacks stable across renders)
  - `ReviewSheet` gains `onSubmitted?: (id: number, command: CommandStatus) => void` and
    `onSettled?: (id: number) => void`, passed to `DecideControls` as `onApprovalSubmitted` /
    `onApprovalSettled`
  - `ProposalsView({ strategy, submitted, onSubmitted, onSettled })`

- [x] **Step 1: Load da-vinci.** Invoke the `da-vinci` skill. It reads `web/DESIGN.md` (ratified)
  instead of interviewing. The Trades composition below is fixed by the roadmap and DESIGN.md
  (pinned beats roll), so skip the structure workshop; da-vinci's job in this task is the craft
  floor of `ProposalsView` and the contract's wording.

- [x] **Step 2: Write the Trades contract into `web/DESIGN.md`.** Replace the three-line
  `### Trades` block under `## Surfaces` (it starts "Operate. Proposals, Working, Decided,
  Assessed and Spreads segments.") with:

```markdown
### Trades
Operate. Dials as the project default. Built in web overhaul Part 2
(docs/superpowers/plans/2026-10-19-web-overhaul-2-trades.md).
- **THESIS:** what the wheel did and why, a day at a time, and the few things that wait on you.
  The account runs on full autonomy, so the page leads with what happened, not with an empty
  queue. Refuses the order-management grid: a proposal is a card you judge, a trade is the card
  Home shows, an order or a passed-over proposal is a sentence with a state word, and a spreads
  menu is the menu Claude saw, kept as the reason under the spread it opened.
- **OWN-WORLD:** the payslip. Proposal and trade cards exactly as on Home (lime only on Review);
  in-flight orders and not-traded proposals as rows without table chrome; who approved a trade
  in words ("Approved by the system"), from the record only; the spreads menu as a lettered list
  under a perforation, its figures in the stub face. Nothing on History or Spreads is an action
  apart from the unchanged decide flow inside a sent card's receipt.
- **STORY:** what needs me (Proposals), what the wheel did today or on any day (History: in
  flight, traded, not traded), what the scan passed over and why (Assessed), and, under Credit
  spreads, what each book traded and the menu behind it (Spreads).
- **FIRST VIEWPORT:** the title, the strategy switcher (All, CSPs, CCs, Credit spreads, with
  pending counts), the view chips (Proposals, History, Assessed; Proposals carries the pending
  count, History the in-flight count), a flag line when the trading service is not draining
  commands, then the view. With no view in the URL the page opens on Proposals when something
  waits on you and on History otherwise, decided once per visit. Proposals: ticker chips (from
  two tickers up), then proposal cards, one column below 1024px and two from 1024px. History: the
  day with previous, next and Today, then In flight (today only), Traded, Not traded. Credit
  spreads has one view, so its chips are hidden and Spreads shows.
- **FORM:** one page; the view and the day live in the URL (`?view=history&day=2026-10-09`)
  beside the strategy (`?strategy=csp`), so a link or a reload keeps all three. Review opens the
  review sheet exactly as on Home; approving moves the card to History's In flight at once, and
  a failed command hands it back.
- **FINISH:** unreviewed and undocumented is unfinished.
```

Run: `python3 ~/.claude/skills/da-vinci/scripts/design_md_check.py web/DESIGN.md`
Expected: exit 0.

- [x] **Step 3: Write the failing tests for the view rules** — `web/features/trades/views.test.ts`

```ts
import { describe, expect, it } from "vitest";
import { defaultView, explicitView, tickerCounts, viewsFor } from "./views";

describe("viewsFor", () => {
  it("gives the wheel three views, under All too", () => {
    expect(viewsFor("all")).toEqual(["proposals", "history", "assessed"]);
    expect(viewsFor("csp")).toEqual(["proposals", "history", "assessed"]);
    expect(viewsFor("cc")).toEqual(["proposals", "history", "assessed"]);
  });
  it("offers only Spreads for credit spreads, which trade on their own", () => {
    expect(viewsFor("spread")).toEqual(["spreads"]);
  });
});

describe("explicitView", () => {
  it("keeps a view the strategy has", () => {
    expect(explicitView("assessed", "cc")).toBe("assessed");
    expect(explicitView("history", "all")).toBe("history");
  });
  it("opens History for the retired Working and Decided, so old links still land", () => {
    expect(explicitView("working", "all")).toBe("history");
    expect(explicitView("decided", "csp")).toBe("history");
  });
  it("is null for a junk or missing view, or one the strategy lacks", () => {
    expect(explicitView("foo", "all")).toBeNull();
    expect(explicitView(null, "all")).toBeNull();
    expect(explicitView(undefined, "csp")).toBeNull();
    expect(explicitView("spreads", "all")).toBeNull();
    expect(explicitView("history", "spread")).toBeNull();
  });
});

describe("defaultView", () => {
  it("opens Proposals when something waits on you, History when nothing does", () => {
    expect(defaultView("all", 2)).toBe("proposals");
    expect(defaultView("csp", 0)).toBe("history");
  });
  it("is unknown until the pending count is, except for credit spreads", () => {
    expect(defaultView("all", null)).toBeNull();
    expect(defaultView("spread", null)).toBe("spreads");
  });
});

describe("tickerCounts", () => {
  it("counts each underlying once, alphabetically", () => {
    expect(tickerCounts([{ underlying: "NVDA" }, { underlying: "AAPL" }, { underlying: "NVDA" }])).toEqual([
      { ticker: "AAPL", count: 1 },
      { ticker: "NVDA", count: 2 },
    ]);
  });
  it("is empty for no proposals", () => {
    expect(tickerCounts([])).toEqual([]);
  });
});
```

`web/features/trades/useTradesView.test.tsx`:

```tsx
import { act, renderHook } from "@testing-library/react";
import { beforeEach, describe, expect, it, vi } from "vitest";

const nav = vi.hoisted(() => ({ replace: vi.fn(), params: new URLSearchParams() }));
vi.mock("next/navigation", () => ({
  useRouter: () => ({ replace: nav.replace }),
  useSearchParams: () => nav.params,
  usePathname: () => "/trades",
}));

import { useTradesDay, useTradesView } from "./useTradesView";

beforeEach(() => {
  nav.replace.mockReset();
  nav.params = new URLSearchParams();
});

describe("useTradesView", () => {
  it("reads ?view=", () => {
    nav.params = new URLSearchParams("view=assessed");
    const { result } = renderHook(() => useTradesView("all", 3));
    expect(result.current[0]).toBe("assessed");
  });
  it("opens History for a retired view name", () => {
    nav.params = new URLSearchParams("view=decided");
    const { result } = renderHook(() => useTradesView("all", 3));
    expect(result.current[0]).toBe("history");
  });
  it("opens Proposals when something waits on you, History when nothing does, nothing while unknown", () => {
    expect(renderHook(() => useTradesView("all", 2)).result.current[0]).toBe("proposals");
    expect(renderHook(() => useTradesView("all", 0)).result.current[0]).toBe("history");
    expect(renderHook(() => useTradesView("all", null)).result.current[0]).toBeNull();
  });
  it("keeps the default it chose when the last proposal is approved", () => {
    const { result, rerender } = renderHook(({ n }: { n: number | null }) => useTradesView("all", n), {
      initialProps: { n: 1 },
    });
    expect(result.current[0]).toBe("proposals");
    rerender({ n: 0 });
    expect(result.current[0]).toBe("proposals");
  });
  it("writes a view into the URL and keeps the strategy", () => {
    nav.params = new URLSearchParams("strategy=csp");
    const { result } = renderHook(() => useTradesView("csp", 0));
    act(() => result.current[1]("history"));
    expect(nav.replace).toHaveBeenCalledWith("/trades?strategy=csp&view=history", { scroll: false });
  });
  it("shows Spreads for credit spreads whatever the URL says", () => {
    nav.params = new URLSearchParams("strategy=spread&view=history");
    const { result } = renderHook(() => useTradesView("spread", null));
    expect(result.current[0]).toBe("spreads");
  });
});

describe("useTradesDay", () => {
  it("reads a well-formed ?day= and ignores anything else", () => {
    nav.params = new URLSearchParams("day=2026-10-09");
    expect(renderHook(() => useTradesDay()).result.current[0]).toBe("2026-10-09");
    nav.params = new URLSearchParams("day=yesterday");
    expect(renderHook(() => useTradesDay()).result.current[0]).toBeNull();
  });
  it("writes and clears the day, keeping the rest of the URL", () => {
    nav.params = new URLSearchParams("view=history");
    const { result } = renderHook(() => useTradesDay());
    act(() => result.current[1]("2026-10-09"));
    expect(nav.replace).toHaveBeenLastCalledWith("/trades?view=history&day=2026-10-09", { scroll: false });
    nav.params = new URLSearchParams("view=history&day=2026-10-09");
    const again = renderHook(() => useTradesDay());
    act(() => again.result.current[1](null));
    expect(nav.replace).toHaveBeenLastCalledWith("/trades?view=history", { scroll: false });
  });
});
```

`web/features/trades/useSubmittedApprovals.test.tsx`:

```tsx
import { act, renderHook } from "@testing-library/react";
import { beforeEach, describe, expect, it } from "vitest";
import { savePersistedCommand, type CommandStatus } from "@/lib/commands";
import { useSubmittedApprovals } from "./useSubmittedApprovals";

const command = {
  id: 7, kind: "approve", status: "pending", result: null, needs_confirmation: false,
  confirm_token: null, created_at: "", applied_at: null, as_of: "",
} as CommandStatus;

beforeEach(() => localStorage.clear());

describe("useSubmittedApprovals", () => {
  it("marks and clears an approval", () => {
    const { result } = renderHook(() => useSubmittedApprovals());
    act(() => result.current.markSubmitted(1, command));
    expect(result.current.submitted.get(1)).toEqual(command);
    act(() => result.current.clearSubmitted(1));
    expect(result.current.submitted.size).toBe(0);
  });
  it("clearing an id it does not hold keeps the same map, so nothing re-renders", () => {
    const { result } = renderHook(() => useSubmittedApprovals());
    const before = result.current.submitted;
    act(() => result.current.clearSubmitted(99));
    expect(result.current.submitted).toBe(before);
  });
  it("keeps its callbacks stable across renders", () => {
    const { result, rerender } = renderHook(() => useSubmittedApprovals());
    const { markSubmitted, clearSubmitted } = result.current;
    rerender();
    expect(result.current.markSubmitted).toBe(markSubmitted);
    expect(result.current.clearSubmitted).toBe(clearSubmitted);
  });
  it("is seeded after mount from a command persisted before a reload", () => {
    savePersistedCommand(1, command);
    const { result } = renderHook(() => useSubmittedApprovals());
    expect(result.current.submitted.has(1)).toBe(true);
  });
});
```

- [x] **Step 4: Run them to verify they fail**

Run: `cd web && npx vitest run features/trades`
Expected: FAIL (modules not found).

- [x] **Step 5: Write the three modules**

`web/features/trades/views.ts`:

```ts
import type { StrategyFilter } from "@/lib/strategy";

/** The Trades page's views (web/DESIGN.md Surfaces → Trades). */
export type TradesView = "proposals" | "history" | "assessed" | "spreads";

export const VIEW_LABEL: Record<TradesView, string> = {
  proposals: "Proposals",
  history: "History",
  assessed: "Assessed",
  spreads: "Spreads",
};

/** Views retired in the 2026-10-19 revision. Old links open History, where their rows now live. */
const RETIRED: Record<string, TradesView> = { working: "history", decided: "history" };

/** Which views a strategy has. Credit spreads trade on their own: nothing to approve or assess. */
export function viewsFor(strategy: StrategyFilter): TradesView[] {
  return strategy === "spread" ? ["spreads"] : ["proposals", "history", "assessed"];
}

/** The view the URL asks for, when this strategy has it; null when it asks for none or one it lacks. */
export function explicitView(raw: string | null | undefined, strategy: StrategyFilter): TradesView | null {
  const name = raw ? (RETIRED[raw] ?? raw) : null;
  return name !== null && (viewsFor(strategy) as string[]).includes(name) ? (name as TradesView) : null;
}

/**
 * With no view asked for: Proposals when something waits on you, History otherwise (the account
 * runs on full autonomy, so most visits have nothing to approve). Null until the count is known.
 */
export function defaultView(strategy: StrategyFilter, pending: number | null): TradesView | null {
  if (strategy === "spread") return "spreads";
  if (pending === null) return null;
  return pending > 0 ? "proposals" : "history";
}

export type TickerCount = { ticker: string; count: number };

/** One chip per underlying, alphabetical, with how many proposals each has. */
export function tickerCounts(items: { underlying: string }[]): TickerCount[] {
  const counts = new Map<string, number>();
  for (const i of items) counts.set(i.underlying, (counts.get(i.underlying) ?? 0) + 1);
  return [...counts]
    .map(([ticker, count]) => ({ ticker, count }))
    .sort((a, b) => a.ticker.localeCompare(b.ticker));
}
```

`web/features/trades/useTradesView.ts`:

```ts
"use client";

import { usePathname, useRouter, useSearchParams } from "next/navigation";
import { useCallback, useEffect, useState } from "react";
import type { StrategyFilter } from "@/lib/strategy";
import { type TradesView, defaultView, explicitView } from "./views";

/**
 * The Trades view, kept in `?view=` beside `?strategy=` so a reload or a shared link keeps both.
 * With no view in the URL the default (ruling 2) is decided once per visit and strategy, when the
 * pending count first loads, so approving the last proposal never moves the page under you.
 * Null only while that count is still loading. A page using this must render inside <Suspense>
 * (Next's useSearchParams rule).
 */
export function useTradesView(
  strategy: StrategyFilter,
  pending: number | null,
): [TradesView | null, (v: TradesView) => void] {
  const params = useSearchParams();
  const router = useRouter();
  const pathname = usePathname();
  const explicit = explicitView(params.get("view"), strategy);
  const fresh = defaultView(strategy, pending);
  const [decided, setDecided] = useState<Partial<Record<StrategyFilter, TradesView>>>({});

  useEffect(() => {
    if (fresh === null) return;
    setDecided((d) => (d[strategy] === undefined ? { ...d, [strategy]: fresh } : d));
  }, [fresh, strategy]);

  const set = useCallback(
    (v: TradesView) => {
      const next = new URLSearchParams(params.toString());
      next.set("view", v);
      router.replace(`${pathname}?${next.toString()}`, { scroll: false });
    },
    [params, router, pathname],
  );

  return [explicit ?? decided[strategy] ?? fresh, set];
}

const DAY = /^\d{4}-\d{2}-\d{2}$/;

/** History's day in `?day=YYYY-MM-DD`; null (the parameter left out) is today in New York. */
export function useTradesDay(): [string | null, (day: string | null) => void] {
  const params = useSearchParams();
  const router = useRouter();
  const pathname = usePathname();
  const raw = params.get("day");
  const value = raw !== null && DAY.test(raw) ? raw : null;

  const set = useCallback(
    (day: string | null) => {
      const next = new URLSearchParams(params.toString());
      if (day === null) next.delete("day");
      else next.set("day", day);
      const qs = next.toString();
      router.replace(qs ? `${pathname}?${qs}` : pathname, { scroll: false });
    },
    [params, router, pathname],
  );

  return [value, set];
}
```

`web/features/trades/useSubmittedApprovals.ts`:

```ts
"use client";

import { useCallback, useEffect, useState } from "react";
import { loadAllPersistedCommands, type CommandStatus } from "@/lib/commands";

export type SubmittedApprovals = {
  /** Approval id -> the Approve command in flight for it. */
  submitted: Map<number, CommandStatus>;
  markSubmitted: (id: number, command: CommandStatus) => void;
  clearSubmitted: (id: number) => void;
};

/**
 * Approvals whose Approve command is in flight. An approval's own status stays "pending" until
 * the trading service applies the command, so this client-side map is what moves a card from
 * Proposals to History's In flight the instant Approve is confirmed. Seeded from localStorage after mount
 * (never in a useState initializer, which runs during SSR and would break hydration), so a
 * reload mid-command keeps the card in flight.
 *
 * Both callbacks are stable: DecideControls lists onApprovalSettled in an effect's dependencies,
 * and a new function every render would re-run that effect on every render.
 */
export function useSubmittedApprovals(): SubmittedApprovals {
  const [submitted, setSubmitted] = useState<Map<number, CommandStatus>>(() => new Map());

  useEffect(() => {
    const persisted = loadAllPersistedCommands();
    if (persisted.size > 0) setSubmitted(persisted);
  }, []);

  const markSubmitted = useCallback(
    (id: number, command: CommandStatus) => setSubmitted((prev) => new Map(prev).set(id, command)),
    [],
  );
  const clearSubmitted = useCallback(
    (id: number) =>
      setSubmitted((prev) => {
        if (!prev.has(id)) return prev;
        const next = new Map(prev);
        next.delete(id);
        return next;
      }),
    [],
  );

  return { submitted, markSubmitted, clearSubmitted };
}
```

- [x] **Step 6: Run them to verify they pass**

Run: `cd web && npx vitest run features/trades`
Expected: PASS (21 tests).

- [x] **Step 7: Give `ReviewSheet` the two callbacks** — `web/features/home/ReviewSheet.tsx`

Add `import type { CommandStatus } from "@/lib/commands";` to the imports. Change the
`ReviewSheet` signature and its `ReviewBody` call to:

```tsx
export function ReviewSheet({
  approval,
  open,
  onClose,
  onSubmitted,
  onSettled,
}: {
  approval: ApprovalSummary | null;
  open: boolean;
  onClose: () => void;
  /** Passed to DecideControls: fired the instant Approve is confirmed (Trades moves the card to History's In flight). */
  onSubmitted?: (id: number, command: CommandStatus) => void;
  /** Passed to DecideControls: fired when that command fails or expires (the card goes back). */
  onSettled?: (id: number) => void;
}) {
  if (!approval) return null;
  return (
    <Sheet open={open} onClose={onClose} title="Review trade">
      <ReviewBody approval={approval} onSubmitted={onSubmitted} onSettled={onSettled} />
    </Sheet>
  );
}
```

Change `ReviewBody`'s signature to
`function ReviewBody({ approval, onSubmitted, onSettled }: { approval: ApprovalSummary; onSubmitted?: (id: number, command: CommandStatus) => void; onSettled?: (id: number) => void })`
and its `DecideControls` line to:

```tsx
        <DecideControls
          approval={{ ...approval, status }}
          drainHealthy={controls.data?.drain_healthy ?? true}
          onApprovalSubmitted={onSubmitted}
          onApprovalSettled={onSettled}
        />
```

Nothing else in the file changes. Home passes neither prop, so Home is unchanged.

Run: `cd web && npx vitest run features/home`
Expected: PASS (every existing Home test, including `ReviewSheet.test.tsx`).

- [x] **Step 8: Write the failing Proposals view tests** — `web/features/trades/ProposalsView.test.tsx`

```tsx
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { fireEvent, render, screen, waitFor, within } from "@testing-library/react";
import { beforeEach, describe, expect, it, vi } from "vitest";
import type { CommandStatus } from "@/lib/commands";
import { apiFetchMock } from "@/lib/test-query";
import { ProposalsView } from "./ProposalsView";

function approval(id: number, underlying: string, over: Record<string, unknown> = {}) {
  return {
    as_of: "", id, candidate_id: `c${id}`, status: "pending", underlying,
    strategy: "cash_secured_put", right: "P", strike: 180, expiry: "2099-11-21", contracts: 1,
    premium: 2.35, blended_score: 0.7, created_at: "2026-10-13T13:00:00Z", expires_at: null,
    decided_at: null, order_state: null, source: "scan", review: null, rationale_tags: [],
    ...over,
  };
}

const controls = {
  as_of: "", autonomy: { level: "approve", label: "Approve each trade" }, rungs: [], halted: false,
  halt_reason: null, halted_at: null, mode: "paper", drain_healthy: true, drain_last_seen: null,
  pending_commands: 0,
};

const command = {
  id: 7, kind: "approve", status: "pending", result: null, needs_confirmation: false,
  confirm_token: null, created_at: "", applied_at: null, as_of: "", created: true,
};

type Approval = ReturnType<typeof approval>;

function mount(approvals: Approval[] | Error, props: { strategy?: "all" | "csp" | "cc"; submitted?: Map<number, CommandStatus> } = {}) {
  apiFetchMock.mockImplementation(async (path: string) => {
    if (path.startsWith("/options/approvals?")) {
      if (approvals instanceof Error) throw approvals;
      return { as_of: "", approvals };
    }
    if (path.startsWith("/options/approvals/")) {
      const id = Number(path.split("/").pop());
      return (approvals as Approval[]).find((a) => a.id === id);
    }
    if (path === "/options/controls") return controls;
    if (path === "/commands" || path.startsWith("/commands/")) return command;
    throw new Error(`no mocked response for ${path}`);
  });
  const onSubmitted = vi.fn();
  const onSettled = vi.fn();
  const qc = new QueryClient({ defaultOptions: { queries: { retry: false } } });
  render(
    <QueryClientProvider client={qc}>
      <ProposalsView
        strategy={props.strategy ?? "all"}
        submitted={props.submitted ?? new Map()}
        onSubmitted={onSubmitted}
        onSettled={onSettled}
      />
    </QueryClientProvider>,
  );
  return { onSubmitted, onSettled };
}

beforeEach(() => {
  (apiFetchMock as unknown as { mockClear: () => void }).mockClear();
  localStorage.clear();
});

describe("ProposalsView", () => {
  it("shows every pending proposal as Home's card, with Review", async () => {
    mount([approval(1, "AAPL"), approval(2, "NVDA", { strike: 190 })]);
    const aapl = await screen.findByRole("article", { name: "AAPL · Sell $180 put" });
    expect(within(aapl).getByRole("button", { name: "Review" })).toBeInTheDocument();
    expect(screen.getByRole("article", { name: "NVDA · Sell $190 put" })).toBeInTheDocument();
  });

  it("leaves out a proposal whose Approve is already in flight", async () => {
    mount([approval(1, "AAPL"), approval(2, "NVDA", { strike: 190 })], {
      submitted: new Map([[1, command as unknown as CommandStatus]]),
    });
    await screen.findByRole("article", { name: "NVDA · Sell $190 put" });
    expect(screen.queryByRole("article", { name: "AAPL · Sell $180 put" })).toBeNull();
  });

  it("filters by ticker and clears back to all", async () => {
    mount([approval(1, "AAPL"), approval(2, "NVDA", { strike: 190 }), approval(3, "NVDA", { strike: 185 })]);
    const chips = await screen.findByRole("group", { name: "Ticker" });
    fireEvent.click(within(chips).getByRole("button", { name: /^NVDA/ }));
    expect(screen.queryByRole("article", { name: "AAPL · Sell $180 put" })).toBeNull();
    expect(screen.getAllByRole("article")).toHaveLength(2);
    fireEvent.click(within(chips).getByRole("button", { name: "All tickers" }));
    expect(screen.getAllByRole("article")).toHaveLength(3);
  });

  it("shows no ticker chips when every proposal is on one ticker", async () => {
    mount([approval(1, "AAPL"), approval(2, "AAPL", { strike: 175 })]);
    await screen.findAllByRole("article");
    expect(screen.queryByRole("group", { name: "Ticker" })).toBeNull();
  });

  it("scopes to the strategy", async () => {
    mount(
      [approval(1, "AAPL"), approval(2, "MSFT", { strategy: "covered_call", right: "C", strike: 420 })],
      { strategy: "cc" },
    );
    expect(await screen.findByRole("article", { name: "MSFT · Sell $420 call" })).toBeInTheDocument();
    expect(screen.queryByRole("article", { name: "AAPL · Sell $180 put" })).toBeNull();
  });

  it("says nothing needs you when the list is empty", async () => {
    mount([]);
    expect(await screen.findByText("Nothing needs you right now.")).toBeInTheDocument();
  });

  it("names the retry when the list cannot be loaded", async () => {
    mount(new Error("down"));
    expect(await screen.findByText(/could not be loaded/)).toBeInTheDocument();
  });

  it("hands the card on through onSubmitted the instant Approve is confirmed", async () => {
    const { onSubmitted } = mount([approval(1, "AAPL")]);
    const card = await screen.findByRole("article", { name: "AAPL · Sell $180 put" });
    fireEvent.click(within(card).getByRole("button", { name: "Review" }));
    const sheet = screen.getByRole("dialog", { name: "Review trade" });
    fireEvent.click(within(sheet).getByRole("button", { name: "Approve" }));
    const confirm = within(sheet).getByRole("dialog", { name: "Approve this contract" });
    const buttons = confirm.querySelectorAll("button");
    fireEvent.click(buttons[buttons.length - 1]);
    await waitFor(() => expect(onSubmitted).toHaveBeenCalledWith(1, expect.objectContaining({ id: 7 })));
  });
});
```

- [x] **Step 9: Run them to verify they fail**

Run: `cd web && npx vitest run features/trades/ProposalsView.test.tsx`
Expected: FAIL (`./ProposalsView` not found).

- [x] **Step 10: Write `web/features/trades/ProposalsView.tsx`**

```tsx
"use client";

import { useState, type ReactNode } from "react";
import type { ApprovalSummary } from "@/components/options/types";
import { SegmentedControl } from "@/components/ui/SegmentedControl";
import { usePendingApprovals } from "@/features/home/NeedsYou";
import { ProposalCard } from "@/features/home/ProposalCard";
import { ReviewSheet } from "@/features/home/ReviewSheet";
import type { CommandStatus } from "@/lib/commands";
import type { StrategyFilter } from "@/lib/strategy";
import { tickerCounts } from "./views";

/**
 * Pending proposals at page width: Home's cards, Home's review sheet. A proposal whose Approve
 * is in flight is in `submitted` and shows under History's In flight instead.
 */
export function ProposalsView({
  strategy,
  submitted,
  onSubmitted,
  onSettled,
}: {
  strategy: StrategyFilter;
  submitted: Map<number, CommandStatus>;
  onSubmitted: (id: number, command: CommandStatus) => void;
  onSettled: (id: number) => void;
}) {
  const { data, isError, visible } = usePendingApprovals(strategy);
  const [ticker, setTicker] = useState("all");
  const [reviewing, setReviewing] = useState<ApprovalSummary | null>(null);

  const waiting = visible.filter((a) => !submitted.has(a.id));
  const tickers = tickerCounts(waiting);
  // A ticker whose last proposal was decided or sent loses its chip; the list then shows them all.
  const active = tickers.some((t) => t.ticker === ticker) ? ticker : "all";
  const shown = active === "all" ? waiting : waiting.filter((a) => a.underlying === active);

  let body: ReactNode;
  if (isError && !data) {
    body = (
      <p className="text-sm text-muted">
        Proposals could not be loaded. They are asked for again every 30 seconds.
      </p>
    );
  } else if (!data) {
    body = (
      <div className="h-40 rounded-[18px] bg-surface" role="status" aria-busy="true" aria-label="Loading proposals" />
    );
  } else if (waiting.length === 0) {
    body = <p className="text-sm text-muted">Nothing needs you right now.</p>;
  } else {
    body = (
      <>
        {tickers.length > 1 && (
          <SegmentedControl
            label="Ticker"
            appearance="quiet"
            className="mb-4"
            options={[
              { value: "all", label: "All tickers" },
              ...tickers.map((t) => ({ value: t.ticker, label: t.ticker, count: t.count })),
            ]}
            value={active}
            onChange={setTicker}
          />
        )}
        <div className="grid items-start gap-4 lg:grid-cols-2">
          {shown.map((a) => (
            <ProposalCard key={a.id} approval={a} onReview={setReviewing} />
          ))}
        </div>
      </>
    );
  }

  return (
    <section aria-labelledby="proposals-title">
      <h2 id="proposals-title" className="sr-only">
        Proposals
      </h2>
      {body}
      <ReviewSheet
        approval={reviewing}
        open={reviewing !== null}
        onClose={() => setReviewing(null)}
        onSubmitted={onSubmitted}
        onSettled={onSettled}
      />
    </section>
  );
}
```

- [x] **Step 11: Run the tests to verify they pass, then the gate**

Run: `cd web && npx vitest run features/trades features/home && npx tsc --noEmit && npm run lint`
Expected: PASS (29 new tests); tsc 0; lint clean.

- [x] **Step 12: da-vinci check.** Run `python3 ~/.claude/skills/da-vinci/scripts/lint.py web/features/trades`
  (exit 0 clean, 1 findings). Fix every finding in the code, not by exception; record anything
  left in the Progress log.

- [x] **Step 13: Commit** (with the Progress log row for Task 2 filled in)

```bash
git add web/DESIGN.md web/features/trades web/features/home/ReviewSheet.tsx docs/superpowers/plans/2026-10-19-web-overhaul-2-trades.md
git commit -m "feat(web): Trades contract, view state in the URL, and the Proposals view"
```

---

### Task 4: Rolls say what they roll, and trades say who approved them

**Files:**
- Modify: `web/DESIGN.md` (§ Components → Proposal card, Trade card: one sentence each)
- Modify: `web/features/home/proposal.ts` (`rollTitle`, `rollSentence`, `rollStub`, `decisionWords`)
- Modify: `web/features/home/proposal.test.ts` (+6)
- Modify: `web/features/home/ProposalCard.tsx` (`proposalTitle`, `ProposalBody`)
- Modify: `web/features/home/proposals.test.tsx` (+2)
- Modify: `web/features/home/TradeCard.tsx` (who approved it, in words)
- Modify: `web/features/home/TodayTrades.test.tsx` (+2)

**Interfaces:**
- Consumes: `ApprovalSummary.roll_from`, `.decided_by` and `DayTrade.decided_by` (Task 2);
  `StubLineData`; `formatMoneyCell`.
- Produces (all in `features/home/proposal.ts`):
  - `type RollFields = { underlying; strike; expiry; right; contracts; premium; roll_from? }`
  - `rollTitle(a): string`: "NVDA · Roll $250 put Oct 23 → Oct 28"; "NVDA · Roll" without a leg
  - `rollSentence(a): string`, `rollStub(a): StubLineData[]` (Buy back, Sell, Net credit or Net debit)
  - `type DecidedBy = "system" | "web" | "telegram"`;
    `decisionWords(status, decidedBy?): string | null`: "Approved by the system", "Rejected by
    you, in Telegram", "Approved" when unrecorded, "Expired unanswered", null while pending.

Home's cards change too: that is the point. A roll on Home's Needs you column now names its legs.

- [x] **Step 1: Load da-vinci** if it is not already loaded, and write the contract first. In
  `web/DESIGN.md` § Components:
  - **Proposal card**: after the sentence that ends "then Review (primary, opens the review sheet)
    and Details (secondary, the full approval page).", add: "A roll's title names both legs
    ("NVDA · Roll $250 put Oct 23 → Oct 28", or "$250 → $245 put" when the strike moves), its
    sentence says what it buys back and what it sells, and its stub sums Buy back, Sell and the
    Net credit (or Net debit) at the quotes it was priced at, which the stub says, so a quote
    never reads as a fill. A roll frozen before the 2026-10-11 redesign carries no legs and says
    so."
  - **Trade card**: after "then the stub, which sums the whole trade (...)", add: "An opened or
    rolled card says who approved it under its sentence ("Approved by the system", "Approved by
    you, on the web", "Approved by you, in Telegram"), from the stored record only; a card whose
    decider was not recorded says nothing rather than guess."

  Run: `python3 ~/.claude/skills/da-vinci/scripts/design_md_check.py web/DESIGN.md` → exit 0.

- [x] **Step 2: Write the failing tests**

In `web/features/home/proposal.test.ts`, change the import to
`import { daysToExpiry, decisionWords, proposalSentence, proposalStub, rollSentence, rollStub, rollTitle } from "./proposal";`
and append:

```ts
const roll = {
  underlying: "NVDA", strike: 250, expiry: "2026-10-28", right: "P", contracts: 1, premium: 1.175,
  roll_from: { strike: 250, expiry: "2026-10-23", right: "P", contracts: 1, old_mid: 2.1, new_mid: 3.275 },
};

describe("rolls", () => {
  it("titles a roll with both legs", () => {
    expect(rollTitle(roll)).toBe("NVDA · Roll $250 put Oct 23 → Oct 28");
    expect(rollTitle({ ...roll, strike: 245, expiry: "2026-11-20" })).toBe("NVDA · Roll $250 → $245 put Oct 23 → Nov 20");
    expect(rollTitle({ ...roll, expiry: "2026-10-23", strike: 255 })).toBe("NVDA · Roll $250 → $255 put Oct 23");
  });
  it("keeps the plain title for a roll frozen before its legs were recorded", () => {
    expect(rollTitle({ ...roll, roll_from: null })).toBe("NVDA · Roll");
  });
  it("says what it buys back and sells, and the net at the quotes it was priced at", () => {
    expect(rollSentence(roll)).toBe(
      "Buys back the $250 put expiring Oct 23 and sells the $250 put expiring Oct 28. At the quotes it was priced at, that is a net credit of $117.50.",
    );
    expect(rollSentence({ ...roll, premium: -0.4 })).toMatch(/a net debit of \$40\.00\.$/);
    expect(rollSentence({ ...roll, premium: null })).toMatch(/The net is not known\.$/);
  });
  it("sums the two legs to the net", () => {
    const lines = rollStub(roll);
    expect(lines.map((l) => l.label)).toEqual(["Buy back $250 put Oct 23", "Sell $250 put Oct 28", "Net credit"]);
    expect(lines[0].value).toBeCloseTo(-210);
    expect(lines[1].value).toBeCloseTo(327.5);
    expect(lines[2].value).toBeCloseTo(117.5);
    expect(lines[2].total).toBe(true);
    expect(rollStub({ ...roll, premium: -0.4 })[2].label).toBe("Net debit");
  });
  it("leaves an unknown leg unknown, never zero", () => {
    expect(rollStub({ ...roll, roll_from: { ...roll.roll_from, old_mid: null } })[0].value).toBeNull();
    expect(rollStub({ ...roll, premium: null })[2].value).toBeNull();
  });
});

describe("decisionWords", () => {
  it("names who decided, from the record only", () => {
    expect(decisionWords("approved", "system")).toBe("Approved by the system");
    expect(decisionWords("approved", "web")).toBe("Approved by you, on the web");
    expect(decisionWords("rejected", "telegram")).toBe("Rejected by you, in Telegram");
    expect(decisionWords("approved", null)).toBe("Approved");
    expect(decisionWords("approved")).toBe("Approved");
    expect(decisionWords("expired", null)).toBe("Expired unanswered");
    expect(decisionWords("pending", null)).toBeNull();
  });
});
```

Append inside `describe("NeedsYou")` in `web/features/home/proposals.test.tsx`:

```tsx
  it("names a roll's two legs and sums them to the net", async () => {
    const leg = { strike: 250, expiry: "2099-10-23", right: "P", contracts: 1, old_mid: 2.1, new_mid: 3.275 };
    renderWithQuery(<NeedsYou strategy="all" />, {
      "/options/approvals": list(
        approval(9, { source: "roll", strategy: "roll", strike: 250, expiry: "2099-10-28", premium: 1.175, roll_from: leg }),
      ),
      "/options/controls": controls,
    });
    const card = await screen.findByRole("article", { name: "AAPL · Roll $250 put Oct 23 → Oct 28" });
    const stub = within(card).getByRole("group", { name: "AAPL roll math" });
    expect(within(stub).getByText("Net credit")).toBeInTheDocument();
    expect(within(card).getByText(/At the quotes it was priced at/)).toBeInTheDocument();
  });

  it("says a roll without recorded legs has none, never inventing them", async () => {
    renderWithQuery(<NeedsYou strategy="all" />, {
      "/options/approvals": list(approval(9, { source: "roll", strategy: "roll", roll_from: null })),
      "/options/controls": controls,
    });
    const card = await screen.findByRole("article", { name: "AAPL · Roll" });
    expect(within(card).getByText(/legs were not recorded/)).toBeInTheDocument();
    expect(within(card).queryByRole("group", { name: /math/ })).toBeNull();
  });
```

Append inside the top-level `describe` in `web/features/home/TodayTrades.test.tsx`:

```tsx
  it("says who approved an opened trade, from the record", async () => {
    renderWithQuery(<TodayTrades strategy="all" />, { "/pnl/day": day([{ ...opened, decided_by: "system" }]) });
    expect(await screen.findByText("Approved by the system")).toBeInTheDocument();
  });

  it("says nothing about who approved it when that was not recorded", async () => {
    renderWithQuery(<TodayTrades strategy="all" />, { "/pnl/day": day([{ ...opened, decided_by: null }]) });
    await screen.findByRole("article");
    expect(screen.queryByText(/^Approved/)).toBeNull();
  });
```

- [x] **Step 3: Run them to verify they fail**

Run: `cd web && npx vitest run features/home`
Expected: FAIL (`rollTitle`, `rollSentence`, `rollStub`, `decisionWords` not exported; the roll
card's title is "AAPL · Roll"; no "Approved by the system").

- [x] **Step 4: Add to `web/features/home/proposal.ts`**

Add `import type { ApprovalRollFrom } from "@/components/options/types";` to the imports, then
append:

```ts
export type RollFields = {
  underlying: string;
  strike: number; // the new leg
  expiry: string | null; // the new leg
  right: string;
  contracts: number;
  premium: number | null; // the net per share: the new leg's mid less the old leg's
  roll_from?: ApprovalRollFrom | null;
};

const md = (iso: string) => SHORT_DATE.format(new Date(`${iso}T00:00:00Z`));
const rightWord = (r: string) => (r === "C" ? "call" : "put");

/** "NVDA · Roll $250 put Oct 23 → Oct 28"; the strike and the date each show a move only when they move. */
export function rollTitle(a: RollFields): string {
  const from = a.roll_from;
  if (!from) return `${a.underlying} · Roll`;
  const strikes = from.strike === a.strike ? `$${from.strike}` : `$${from.strike} → $${a.strike}`;
  const dates = !a.expiry || a.expiry === from.expiry ? md(from.expiry) : `${md(from.expiry)} → ${md(a.expiry)}`;
  return `${a.underlying} · Roll ${strikes} ${rightWord(from.right)} ${dates}`;
}

/** What the roll does, then the net at the quotes it was priced at (never presented as a fill). */
export function rollSentence(a: RollFields): string {
  const from = a.roll_from;
  if (!from) return "This rolls a position you already hold. Its legs were not recorded on this proposal.";
  const sells = a.expiry ? `the $${a.strike} ${rightWord(a.right)} expiring ${md(a.expiry)}` : `the $${a.strike} ${rightWord(a.right)}`;
  const head = `Buys back the $${from.strike} ${rightWord(from.right)} expiring ${md(from.expiry)} and sells ${sells}.`;
  if (a.premium === null) return `${head} The net is not known.`;
  const net = a.premium * 100 * a.contracts;
  return `${head} At the quotes it was priced at, that is a net ${net < 0 ? "debit" : "credit"} of ${formatMoneyCell(Math.abs(net))}.`;
}

/** Buy back, Sell, then the net: the roll's own arithmetic at the quotes it was priced at. */
export function rollStub(a: RollFields): StubLineData[] {
  const from = a.roll_from;
  if (!from) return [];
  const n = a.contracts;
  const leg = (mid: number | null, sign: 1 | -1) => (mid === null ? null : sign * mid * 100 * n);
  const net = a.premium === null ? null : a.premium * 100 * n;
  const per = (mid: number | null, what: string) =>
    mid === null
      ? `No quote was recorded for ${what}.`
      : `${n} contract${n === 1 ? "" : "s"} × $${mid.toFixed(2)} per share × 100 shares, the quote when the roll was proposed.`;
  return [
    {
      label: `Buy back $${from.strike} ${rightWord(from.right)} ${md(from.expiry)}`,
      value: leg(from.old_mid, -1),
      format: "signed-money",
      explain: per(from.old_mid, "the leg bought back"),
    },
    {
      label: `Sell $${a.strike} ${rightWord(a.right)}${a.expiry ? ` ${md(a.expiry)}` : ""}`,
      value: leg(from.new_mid, 1),
      format: "signed-money",
      explain: per(from.new_mid, "the new leg"),
    },
    {
      label: net !== null && net < 0 ? "Net debit" : "Net credit",
      value: net,
      format: "signed-money",
      total: true,
      explain: "What the roll takes in after buying back the old leg, before commissions. The fill can differ from the quote.",
    },
  ];
}

export type DecidedBy = "system" | "web" | "telegram";

const WHO: Record<DecidedBy, string> = {
  system: "by the system",
  web: "by you, on the web",
  telegram: "by you, in Telegram",
};

/** The decision in words, naming who decided only when that was recorded. Null while pending. */
export function decisionWords(status: string, decidedBy?: DecidedBy | null): string | null {
  if (status === "approved" || status === "rejected") {
    const verb = status === "approved" ? "Approved" : "Rejected";
    return decidedBy ? `${verb} ${WHO[decidedBy]}` : verb;
  }
  if (status === "expired") return "Expired unanswered";
  return null;
}
```

- [x] **Step 5: Use them on the cards**

`web/features/home/ProposalCard.tsx`: import `rollSentence, rollStub, rollTitle` from
`./proposal` beside the existing names; in `proposalTitle` replace the roll line with
`if (a.source === "roll") return rollTitle(a);`; and replace `ProposalBody`'s body with:

```tsx
  const isRoll = approval.source === "roll";
  const roll = isRoll ? rollStub(approval) : [];
  return (
    <>
      <p className="mt-2 text-sm">{isRoll ? rollSentence(approval) : proposalSentence(approval)}</p>
      <WhyDisclosure review={approval.review} />
      {!isRoll && (
        <Stub label={`${approval.underlying} ${approval.right === "C" ? "call" : "put"} math`} lines={proposalStub(approval, new Date())} />
      )}
      {roll.length > 0 && <Stub label={`${approval.underlying} roll math`} lines={roll} />}
    </>
  );
```

`web/features/home/TradeCard.tsx`: import `decisionWords` from `./proposal`, and directly under
the sentence `<p className="mt-2 text-sm">{tradeSentence(trade)}</p>` add:

```tsx
      {trade.action !== "closed" && trade.decided_by && (
        <p className="mt-1 text-[0.8125rem] text-muted">{decisionWords("approved", trade.decided_by)}</p>
      )}
```

- [x] **Step 6: Run the tests to verify they pass, then the gate**

Run: `cd web && npx vitest run features/home && npx tsc --noEmit && npm run lint`
Expected: PASS (10 new; every existing Home test unchanged, including the roll card's old
"AAPL · Roll" cases, whose fixtures carry no `roll_from`). If an existing test asserted the old
sentence "Open Details for both legs", replace that assertion with the new "legs were not
recorded" sentence and record the ruling: the old sentence promised legs the detail page did not
show.

- [x] **Step 7: Commit** (with the Progress log row for Task 3 filled in)

```bash
git add web/DESIGN.md web/features/home/proposal.ts web/features/home/proposal.test.ts web/features/home/ProposalCard.tsx \
  web/features/home/proposals.test.tsx web/features/home/TradeCard.tsx web/features/home/TodayTrades.test.tsx \
  docs/superpowers/plans/2026-10-19-web-overhaul-2-trades.md
git commit -m "feat(web): rolls name both legs and sum to the net; trade cards say who approved them"
```

---

### Task 5: History — one New York day: in flight, traded, not traded

**Files:**
- Create: `web/features/trades/time.ts` (+ `time.test.ts`)
- Create: `web/features/trades/history.ts`, `web/features/trades/history.test.ts`
- Create: `web/features/trades/HistoryView.tsx`, `web/features/trades/HistoryView.test.tsx`
- Modify: `web/components/options/ControlsStrip.tsx` (`DrainWarning`'s classes only)
- Modify: `web/features/home/RealisedCalendar.tsx` ("Open this day in History"),
  `web/features/home/RealisedCalendar.test.tsx` (+1)

**Interfaces:**
- Consumes: `usePendingApprovals` (Home), `proposalTitle` (Home, roll-aware since Task 4),
  `decisionWords` (Task 4), `TradeCard` (Home), `DecideControls({ approval, drainHealthy,
  initialCommand, onApprovalSettled })`, `useControls()`, `Card`, `StatusWord`, `Button`, `kindOf`,
  `matchesFilter`, `STRATEGY_EYEBROW`; `GET /pnl/day?date=&strategy=` (with Task 2's
  `previous_day`, `next_day`, `decided_by`); `GET /options/approvals?status=all&since=&until=&limit=200`;
  `GET /options/orders?state=working`.
- Produces:
  - `time.ts`: `timeET(iso): string` ("10:17 AM ET"), `dayLabel(isoDate): string` ("Thu, Oct 15"),
    `newYorkDay(iso): string | null`, `todayInNewYork(now?: Date): string`, `shiftDay(isoDate, n): string`
  - `history.ts`: `type NotTradedRow`, `notTradedRows(approvals, day, strategy): NotTradedRow[]`,
    `orderContract(o): string` ("$190 cash-secured put"), `IN_FLIGHT_STATES`
  - `HistoryView({ strategy, day, today, onDay, submitted, onSettled })`,
    `useWorkingOrders()` (key `["options", "orders", "working"]`, the key the legacy
    `OrdersTable` used, so `DecideControls`' invalidation of `["options", "orders"]` reaches it),
    `useInFlightCount(strategy, submitted): number | null`

**What each section reads, and why the day is New York's.** In flight is today's only: what this
browser sent (still pending on the server, in `submitted`) and every working order in scope.
Traded is `/pnl/day` for the day, wheel cards only. Not traded is the approvals raised that New
York day. The approvals route filters by UTC date, so the view asks for the day either side and
keeps the rows whose `created_at` falls on the New York day (an approval raised at 22:00 New York
time is the next UTC day).

- [x] **Step 1: Load da-vinci** if it is not already loaded. Brief: Home's trade cards at page
  width; in-flight orders and not-traded proposals as rows without table chrome (Position row
  anatomy: the whole row a link where there is somewhere to go, a state word, the value
  right-aligned with its label beneath); who decided in words; nothing lime; empty sections
  omitted, except Traded, which says so.

- [x] **Step 2: Write the failing logic tests**

`web/features/trades/time.test.ts`:

```ts
import { describe, expect, it } from "vitest";
import { dayLabel, newYorkDay, shiftDay, timeET, todayInNewYork } from "./time";

describe("time", () => {
  it("shows a time in New York", () => {
    expect(timeET("2026-10-15T14:17:30Z")).toBe("10:17 AM ET");
    expect(timeET("nope")).toBe("time n/a");
  });
  it("labels a day without shifting it", () => {
    expect(dayLabel("2026-10-15")).toBe("Thu, Oct 15");
  });
  it("puts an instant on its New York day", () => {
    expect(newYorkDay("2026-10-16T02:00:00Z")).toBe("2026-10-15");
    expect(newYorkDay("2026-10-15T14:00:00Z")).toBe("2026-10-15");
    expect(newYorkDay("nope")).toBeNull();
  });
  it("knows today in New York, not in UTC", () => {
    expect(todayInNewYork(new Date("2026-10-16T02:00:00Z"))).toBe("2026-10-15");
  });
  it("shifts a day across a month end", () => {
    expect(shiftDay("2026-10-31", 1)).toBe("2026-11-01");
    expect(shiftDay("2026-11-01", -1)).toBe("2026-10-31");
  });
});
```

`web/features/trades/history.test.ts`:

```ts
import { describe, expect, it } from "vitest";
import type { ApprovalSummary } from "@/components/options/types";
import { notTradedRows, orderContract } from "./history";

const a = (over: Partial<ApprovalSummary>): ApprovalSummary => ({
  as_of: "", id: 1, candidate_id: "c1", status: "expired", underlying: "AAPL", strategy: "cash_secured_put",
  right: "P", strike: 180, expiry: "2026-11-20", contracts: 1, premium: 2.35, blended_score: 70,
  created_at: "2026-10-15T15:00:00Z", expires_at: null, decided_at: null, order_state: null,
  source: "scan", review: null, rationale_tags: [], ...over,
});

describe("notTradedRows", () => {
  it("keeps what ended without a fill: expired, rejected, or an order cancelled or rejected", () => {
    const rows = notTradedRows(
      [
        a({ id: 1, status: "expired" }),
        a({ id: 2, status: "rejected", decided_by: "telegram" }),
        a({ id: 3, status: "approved", order_state: "cancelled", decided_by: "system" }),
        a({ id: 4, status: "approved", order_state: "rejected" }),
        a({ id: 5, status: "approved", order_state: "filled" }),
        a({ id: 6, status: "approved", order_state: "submitted" }),
        a({ id: 7, status: "pending" }),
        a({ id: 8, status: "approved", order_state: null }),
      ],
      "2026-10-15",
      "all",
    );
    expect(rows.map((r) => [r.id, r.word, r.decision])).toEqual([
      [1, "Expired", "Expired unanswered"],
      [2, "Rejected", "Rejected by you, in Telegram"],
      [3, "Order cancelled", "Approved by the system"],
      [4, "Order rejected", "Approved"],
    ]);
  });
  it("keeps only the New York day asked for", () => {
    const rows = notTradedRows(
      [
        a({ id: 1, created_at: "2026-10-16T02:00:00Z" }), // 22:00 on the 15th in New York
        a({ id: 2, created_at: "2026-10-15T03:00:00Z" }), // 23:00 on the 14th in New York
      ],
      "2026-10-15",
      "all",
    );
    expect(rows.map((r) => r.id)).toEqual([1]);
  });
  it("follows the strategy, a roll under the side it rolls", () => {
    const rows = notTradedRows(
      [a({ id: 1 }), a({ id: 2, strategy: "covered_call", right: "C" }), a({ id: 3, strategy: "roll", right: "C", source: "roll" })],
      "2026-10-15",
      "cc",
    );
    expect(rows.map((r) => r.id)).toEqual([2, 3]);
  });
  it("puts the newest first and keeps an unknown premium unknown", () => {
    const rows = notTradedRows(
      [a({ id: 1, created_at: "2026-10-15T14:00:00Z", premium: null }), a({ id: 2, created_at: "2026-10-15T16:00:00Z" })],
      "2026-10-15",
      "all",
    );
    expect(rows.map((r) => r.id)).toEqual([2, 1]);
    expect(rows[1].value).toBeNull();
    expect(rows[0].value).toBeCloseTo(235);
  });
});

describe("orderContract", () => {
  it("names the contract from the strategy, since an order carries no right", () => {
    expect(orderContract({ strategy: "cash_secured_put", strike: 190 })).toBe("$190 cash-secured put");
    expect(orderContract({ strategy: "roll", strike: 250 })).toBe("$250 roll");
  });
});
```

- [x] **Step 3: Run them to verify they fail**

Run: `cd web && npx vitest run features/trades/time.test.ts features/trades/history.test.ts`
Expected: FAIL (modules not found).

- [x] **Step 4: Write `web/features/trades/time.ts`**

```ts
const TIME_ET = new Intl.DateTimeFormat("en-US", { hour: "numeric", minute: "2-digit", timeZone: "America/New_York" });
const DAY = new Intl.DateTimeFormat("en-US", { weekday: "short", month: "short", day: "numeric", timeZone: "UTC" });
/** en-CA formats as YYYY-MM-DD. */
const NEW_YORK_DAY = new Intl.DateTimeFormat("en-CA", { timeZone: "America/New_York" });

export function timeET(iso: string): string {
  const t = Date.parse(iso);
  // Some ICU builds put a narrow no-break space before AM/PM; the label uses a plain one.
  return Number.isNaN(t) ? "time n/a" : `${TIME_ET.format(new Date(t)).replace(/ /g, " ")} ET`;
}

/** "Thu, Oct 15" for a "YYYY-MM-DD" New York day (formatted in UTC so the date never shifts). */
export function dayLabel(isoDate: string): string {
  return DAY.format(new Date(`${isoDate}T00:00:00Z`));
}

/** The New York calendar day an instant falls on, or null for an unreadable one. */
export function newYorkDay(iso: string): string | null {
  const t = Date.parse(iso);
  return Number.isNaN(t) ? null : NEW_YORK_DAY.format(new Date(t));
}

export function todayInNewYork(now: Date = new Date()): string {
  return NEW_YORK_DAY.format(now);
}

export function shiftDay(isoDate: string, n: number): string {
  const d = new Date(`${isoDate}T00:00:00Z`);
  d.setUTCDate(d.getUTCDate() + n);
  return d.toISOString().slice(0, 10);
}
```

- [x] **Step 5: Write `web/features/trades/history.ts`**

```ts
import type { ApprovalSummary } from "@/components/options/types";
import { proposalTitle } from "@/features/home/ProposalCard";
import { decisionWords } from "@/features/home/proposal";
import { STRATEGY_EYEBROW, type StrategyFilter, kindOf, matchesFilter } from "@/lib/strategy";
import { newYorkDay, timeET } from "./time";

/** Order states that are still in flight. Filled, cancelled and rejected orders are history. */
export const IN_FLIGHT_STATES = new Set(["queued", "submitted", "partial"]);

/** "$190 cash-secured put". An order carries the strategy name, not the option right. */
export function orderContract(o: { strategy: string; strike: number }): string {
  const k = kindOf(o.strategy, null);
  const kind = k ? STRATEGY_EYEBROW[k].toLowerCase() : o.strategy.replace(/_/g, " ");
  return `$${o.strike} ${kind}`;
}

export type NotTradedRow = {
  id: number;
  title: string;
  /** The outcome as a status word. */
  word: string;
  /** Who decided, from the record only ("Approved by the system", "Approved", "Expired unanswered"). */
  decision: string;
  raised: string;
  /** The proposal's premium (a roll's net) in dollars; null when unknown, never 0. */
  value: number | null;
  valueLabel: string;
};

function outcome(a: ApprovalSummary): string | null {
  if (a.status === "expired") return "Expired";
  if (a.status === "rejected") return "Rejected";
  if (a.status === "approved" && a.order_state === "cancelled") return "Order cancelled";
  if (a.status === "approved" && a.order_state === "rejected") return "Order rejected";
  return null; // pending, in flight, filled (a Traded card), or approved with no order of its own
}

/** Proposals raised on the New York `day` that ended without a fill, newest first. */
export function notTradedRows(approvals: ApprovalSummary[], day: string, strategy: StrategyFilter): NotTradedRow[] {
  const out: { at: number; row: NotTradedRow }[] = [];
  for (const a of approvals) {
    if (newYorkDay(a.created_at) !== day || !matchesFilter(kindOf(a.strategy, a.right), strategy)) continue;
    const word = outcome(a);
    if (word === null) continue;
    const isRoll = a.source === "roll" || a.strategy === "roll";
    out.push({
      at: Date.parse(a.created_at) || 0,
      row: {
        id: a.id,
        title: proposalTitle(a),
        word,
        decision: decisionWords(a.status, a.decided_by ?? null) ?? word,
        raised: `raised ${timeET(a.created_at)}`,
        value: a.premium === null ? null : a.premium * 100 * a.contracts,
        valueLabel: isRoll ? "net, as priced" : "premium",
      },
    });
  }
  return out.sort((x, y) => y.at - x.at).map((o) => o.row);
}
```

Run: `cd web && npx vitest run features/trades/time.test.ts features/trades/history.test.ts`
Expected: PASS (10 tests).

- [x] **Step 6: Restyle `DrainWarning`** — in `web/components/options/ControlsStrip.tsx`, change
  only the `<p>`'s `className` in `DrainWarning` to
  `"rounded-xl bg-flag px-3 py-2.5 text-[0.8125rem] text-on-flag"`. The words and the
  `data-testid` stay exactly as they are (ControlsStrip and shell tests read them).

- [x] **Step 7: Write the failing view tests** — `web/features/trades/HistoryView.test.tsx`

```tsx
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { fireEvent, render, screen, waitFor, within } from "@testing-library/react";
import { beforeEach, describe, expect, it, vi } from "vitest";
import type { CommandStatus } from "@/lib/commands";
import { apiFetchMock } from "@/lib/test-query";
import type { DayTrade } from "@/features/home/types";
import type { StrategyFilter } from "@/lib/strategy";
import { HistoryView, useInFlightCount } from "./HistoryView";

const DAY = "2026-10-15";

const approval = (over: Record<string, unknown> = {}) => ({
  as_of: "", id: 1, candidate_id: "c1", status: "pending", underlying: "AAPL",
  strategy: "cash_secured_put", right: "P", strike: 180, expiry: "2099-11-21", contracts: 1,
  premium: 2.35, blended_score: 0.7, created_at: "2026-10-15T15:00:00Z", expires_at: null,
  decided_at: null, order_state: null, source: "scan", review: null, rationale_tags: [], ...over,
});

const controls = {
  as_of: "", autonomy: { level: "full", label: "Full" }, rungs: [], halted: false, halt_reason: null,
  halted_at: null, mode: "paper", drain_healthy: true, drain_last_seen: null, pending_commands: 0,
};

const pending = {
  id: 7, kind: "approve", status: "pending", result: null, needs_confirmation: false,
  confirm_token: null, created_at: "", applied_at: null, as_of: "",
} as CommandStatus;

const order = (id: number, underlying: string, strategy: string, over: Record<string, unknown> = {}) => ({
  as_of: "x", id, candidate_id: `o${id}`, approval_id: null, underlying, strategy, strike: 190,
  expiry: null, state: "submitted", limit_price: 3.25, filled_qty: 0, avg_fill_price: null,
  is_live: false, detail: null, created_at: "2026-10-15T14:00:00Z", updated_at: "x", ...over,
});

const trade = (over: Partial<DayTrade> = {}): DayTrade => ({
  key: "c9:opened", action: "opened", how: null, kind: "csp", source: "wheel", underlying: "NVDA",
  right: "P", strike: 165, long_strike: null, expiry: "2099-11-21", contracts: 1,
  at: "2026-10-15T14:42:00Z", is_live: false, premium: 235, bought_back: null, commissions: 1.3,
  commissions_complete: true, net_pnl: null, capital: 16500, roc_pct: 1.4, annualized_pct: 13,
  pct_kept: null, dte_at_open: 39, days_held: null, reason: null, facts: [], approval_id: 9,
  review: null, rolled_to: null, decided_by: "system", ...over,
});

type World = {
  sent?: unknown[];
  range?: unknown[];
  orders?: unknown[];
  trades?: DayTrade[];
  previous?: string | null;
  next?: string | null;
  commandStatus?: string;
};

function serve(w: World = {}) {
  apiFetchMock.mockImplementation(async (path: string) => {
    if (path === "/options/approvals?status=pending") return { as_of: "", approvals: w.sent ?? [] };
    if (path.startsWith("/options/approvals?status=all")) return { as_of: "", approvals: w.range ?? [] };
    if (path === "/options/controls") return controls;
    if (path.startsWith("/options/orders")) return { as_of: "x", orders: w.orders ?? [] };
    if (path.startsWith("/pnl/day")) {
      return {
        as_of: "", date: DAY, book: "paper", strategy: "all", trades: w.trades ?? [], spreads_available: true,
        previous_day: w.previous ?? null, next_day: w.next ?? null,
      };
    }
    if (path.startsWith("/commands/")) return { ...pending, status: w.commandStatus ?? "pending" };
    throw new Error(`no mocked response for ${path}`);
  });
}

function mount(props: { strategy?: StrategyFilter; day?: string; submitted?: Map<number, CommandStatus> } = {}) {
  const onDay = vi.fn();
  const onSettled = vi.fn();
  const qc = new QueryClient({ defaultOptions: { queries: { retry: false } } });
  render(
    <QueryClientProvider client={qc}>
      <HistoryView
        strategy={props.strategy ?? "all"}
        day={props.day ?? DAY}
        today={DAY}
        onDay={onDay}
        submitted={props.submitted ?? new Map()}
        onSettled={onSettled}
      />
    </QueryClientProvider>,
  );
  return { onDay, onSettled };
}

beforeEach(() => {
  (apiFetchMock as unknown as { mockClear: () => void }).mockClear();
  localStorage.clear();
});

describe("HistoryView", () => {
  it("shows today's in-flight work: a sent approval with its receipt, and working orders", async () => {
    serve({ sent: [approval()], orders: [order(4, "MSFT", "covered_call")] });
    mount({ submitted: new Map([[1, pending]]) });
    const flight = await screen.findByRole("region", { name: "In flight" });
    const card = await within(flight).findByRole("article", { name: "AAPL · Sell $180 put" });
    expect(within(card).getByTestId("command-receipt")).toBeInTheDocument();
    const msft = (await within(flight).findByText("MSFT")).closest("li") as HTMLElement;
    expect(within(msft).getByText("Submitted")).toBeInTheDocument();
    expect(within(flight).getByText(/cancelled in IBKR/)).toBeInTheDocument();
  });

  it("a failed command hands the card back to Proposals", async () => {
    serve({ sent: [approval()], commandStatus: "failed" });
    const { onSettled } = mount({ submitted: new Map([[1, pending]]) });
    await waitFor(() => expect(onSettled).toHaveBeenCalledWith(1));
  });

  it("scopes working orders to the strategy; a roll order shows only under All", async () => {
    serve({ orders: [order(1, "NVDA", "cash_secured_put"), order(2, "MSFT", "covered_call"), order(3, "AMD", "roll")] });
    mount({ strategy: "csp" });
    const flight = await screen.findByRole("region", { name: "In flight" });
    expect(await within(flight).findByText("NVDA")).toBeInTheDocument();
    expect(within(flight).queryByText("MSFT")).toBeNull();
    expect(within(flight).queryByText("AMD")).toBeNull();
  });

  it("leaves out In flight on a past day, and when nothing is in flight", async () => {
    serve({ orders: [order(1, "NVDA", "cash_secured_put")], trades: [trade()] });
    mount({ day: "2026-10-09" });
    await screen.findByRole("article", { name: "NVDA · Sold $165 put" });
    expect(screen.queryByRole("region", { name: "In flight" })).toBeNull();
  });

  it("lists the day's trades as Home's cards, saying who approved them", async () => {
    serve({ trades: [trade()] });
    mount();
    const traded = await screen.findByRole("region", { name: "Traded" });
    const card = await within(traded).findByRole("article", { name: "NVDA · Sold $165 put" });
    expect(within(card).getByText("Approved by the system")).toBeInTheDocument();
  });

  it("leaves credit spreads to the Credit spreads switcher", async () => {
    serve({ trades: [trade(), trade({ key: "s1:opened", source: "spreads", kind: "spread", underlying: "SPY", long_strike: 757, strike: 762 })] });
    mount();
    const traded = await screen.findByRole("region", { name: "Traded" });
    await within(traded).findByRole("article", { name: "NVDA · Sold $165 put" });
    expect(within(traded).getAllByRole("article")).toHaveLength(1);
    expect(screen.getByRole("link", { name: /Credit spreads/ })).toHaveAttribute("href", "/trades?strategy=spread");
  });

  it("says so when nothing traded", async () => {
    serve();
    mount({ day: "2026-10-09" });
    expect(await screen.findByText("Nothing traded on Fri, Oct 9.")).toBeInTheDocument();
  });

  it("lists proposals that did not trade, with the outcome and who decided, each opening its page", async () => {
    serve({
      range: [
        approval({ id: 3, status: "approved", order_state: "cancelled", decided_by: "system", underlying: "TSLA", strike: 260 }),
        approval({ id: 4, status: "expired", underlying: "KO", strike: 60, created_at: "2026-10-15T14:00:00Z" }),
      ],
    });
    mount();
    const not = await screen.findByRole("region", { name: "Not traded" });
    const tsla = await within(not).findByRole("link", { name: /TSLA/ });
    expect(tsla).toHaveAttribute("href", "/trades/3");
    expect(within(tsla).getByText("Order cancelled")).toBeInTheDocument();
    expect(within(tsla).getByText(/Approved by the system/)).toBeInTheDocument();
    expect(within(not).getByRole("link", { name: /KO/ })).toHaveTextContent(/Expired unanswered/);
  });

  it("an approval decided before the record existed says only Approved", async () => {
    serve({ range: [approval({ id: 3, status: "approved", order_state: "rejected" })] });
    mount();
    const row = await screen.findByRole("link", { name: /AAPL/ });
    expect(row).toHaveTextContent(/Approved · raised/);
    expect(row).not.toHaveTextContent(/by the system|by you/);
  });

  it("asks for the day either side and keeps the New York day", async () => {
    serve({ range: [approval({ id: 3, status: "expired", created_at: "2026-10-15T03:00:00Z" })] });
    mount();
    await screen.findByRole("region", { name: "Traded" });
    expect(apiFetchMock.mock.calls.some((c) => c[0] === "/options/approvals?status=all&since=2026-10-14&until=2026-10-16&limit=200")).toBe(true);
    // 03:00 UTC on the 15th is the 14th in New York.
    expect(screen.queryByRole("region", { name: "Not traded" })).toBeNull();
  });

  it("steps to the neighbouring days with trades, and back to today", async () => {
    serve({ previous: "2026-10-09", next: null });
    const { onDay } = mount({ day: "2026-10-12" });
    const next = await screen.findByRole("button", { name: "Next day with trades" });
    await waitFor(() => expect(screen.getByRole("button", { name: "Previous day with trades" })).toBeEnabled());
    expect(next).toBeDisabled();
    fireEvent.click(screen.getByRole("button", { name: "Previous day with trades" }));
    expect(onDay).toHaveBeenCalledWith("2026-10-09");
    fireEvent.click(screen.getByRole("button", { name: "Today" }));
    expect(onDay).toHaveBeenCalledWith(null);
  });

  it("counts what is in flight: sent approvals plus working orders in scope", async () => {
    serve({ sent: [approval()], orders: [order(1, "NVDA", "cash_secured_put"), order(2, "MSFT", "covered_call")] });
    function Count() {
      const n = useInFlightCount("all", new Map([[1, pending]]));
      return <p>count {n === null ? "unknown" : n}</p>;
    }
    const qc = new QueryClient({ defaultOptions: { queries: { retry: false } } });
    render(
      <QueryClientProvider client={qc}>
        <Count />
      </QueryClientProvider>,
    );
    expect(await screen.findByText("count 3")).toBeInTheDocument();
  });
});
```

Append inside `describe("RealisedCalendar")` in `web/features/home/RealisedCalendar.test.tsx`
(its `openIt` helper and fixtures serve it):

```tsx
  it("links a tapped day to that day in History", async () => {
    const dialog = await openIt();
    fireEvent.click(await within(dialog).findByRole("button", { name: /Fri, Oct 9/ }));
    const section = await within(dialog).findByRole("region", { name: "What closed on Fri, Oct 9" });
    expect(within(section).getByRole("link", { name: "Open this day in History" })).toHaveAttribute(
      "href",
      "/trades?view=history&day=2026-10-09",
    );
  });
```

- [x] **Step 8: Run them to verify they fail**

Run: `cd web && npx vitest run features/trades/HistoryView.test.tsx features/home/RealisedCalendar.test.tsx`
Expected: FAIL (`./HistoryView` not found; no "Open this day in History" link).

- [x] **Step 9: Write `web/features/trades/HistoryView.tsx`**

```tsx
"use client";

import clsx from "clsx";
import Link from "next/link";
import { useQuery } from "@tanstack/react-query";
import { ChevronLeft, ChevronRight } from "lucide-react";
import { useId, type ReactNode } from "react";
import { DecideControls } from "@/components/options/DecideControls";
import type { ApprovalListResponse, ApprovalSummary, OrderListResponse, OrderSummary } from "@/components/options/types";
import { useControls } from "@/components/shell/BotCard";
import { Button } from "@/components/ui/Button";
import { Card } from "@/components/ui/Card";
import { StatusWord, type StatusTone } from "@/components/ui/StatusWord";
import { usePendingApprovals } from "@/features/home/NeedsYou";
import { proposalTitle } from "@/features/home/ProposalCard";
import { TradeCard } from "@/features/home/TradeCard";
import type { DayTradesResponse } from "@/features/home/types";
import { apiFetch } from "@/lib/api";
import type { CommandStatus } from "@/lib/commands";
import { UNKNOWN } from "@/lib/format";
import { formatMoneyCell } from "@/lib/money";
import { STRATEGY_EYEBROW, type StrategyFilter, kindOf, matchesFilter } from "@/lib/strategy";
import { IN_FLIGHT_STATES, notTradedRows, orderContract } from "./history";
import { dayLabel, shiftDay, timeET } from "./time";

const H2 = "mb-2.5 text-[0.8125rem] font-semibold text-muted";

// State is never colour alone: a word on every row; a flag fill only where it needs attention.
const ORDER_STATE: Record<string, { word: string; tone: StatusTone }> = {
  queued: { word: "Queued", tone: "neutral" },
  submitted: { word: "Submitted", tone: "neutral" },
  partial: { word: "Partial", tone: "flag" },
};

/** Working orders. The key the legacy OrdersTable used, so DecideControls' invalidation reaches it. */
export function useWorkingOrders() {
  return useQuery({
    queryKey: ["options", "orders", "working"],
    queryFn: () => apiFetch<OrderListResponse>("/options/orders?state=working"),
    placeholderData: (prev) => prev,
    refetchInterval: 15_000,
  });
}

function inScope(orders: OrderSummary[], strategy: StrategyFilter): OrderSummary[] {
  // An order carries a strategy name but no right, so a roll order can only be placed under All.
  return orders.filter((o) => IN_FLIGHT_STATES.has(o.state) && matchesFilter(kindOf(o.strategy, null), strategy));
}

/** Approvals still pending on the server whose Approve this browser has sent. */
function useSent(strategy: StrategyFilter, submitted: Map<number, CommandStatus>) {
  const { data, visible } = usePendingApprovals(strategy);
  return { loaded: data !== undefined, sent: visible.filter((a) => submitted.has(a.id)) };
}

/** History's chip count: sent approvals plus working orders in scope; null until both load. */
export function useInFlightCount(strategy: StrategyFilter, submitted: Map<number, CommandStatus>): number | null {
  const { loaded, sent } = useSent(strategy, submitted);
  const orders = useWorkingOrders();
  if (!loaded || !orders.data) return null;
  return sent.length + inScope(orders.data.orders, strategy).length;
}

function SentCard({
  approval,
  command,
  drainHealthy,
  onSettled,
}: {
  approval: ApprovalSummary;
  command: CommandStatus | null;
  drainHealthy: boolean;
  onSettled: (id: number) => void;
}) {
  const titleId = useId();
  const kind = kindOf(approval.strategy, approval.right);
  const eyebrow = approval.source === "roll" ? "Roll" : kind ? STRATEGY_EYEBROW[kind] : approval.strategy;
  return (
    <Card as="article" aria-labelledby={titleId}>
      <span className="text-xs font-bold uppercase tracking-[0.04em] text-muted">{eyebrow} · sent</span>
      <h3 id={titleId} className="mt-1 text-[1.0625rem] font-extrabold tracking-[-0.01em]">
        {proposalTitle(approval)}
      </h3>
      <p className="mt-1 text-sm text-muted">You approved this. The receipt says what the trading service has done with it.</p>
      <div className="mt-3">
        {/* The unchanged decide flow: with a command in flight it shows the receipt, not live buttons. */}
        <DecideControls approval={approval} drainHealthy={drainHealthy} initialCommand={command} onApprovalSettled={onSettled} />
      </div>
      <Link
        href={`/trades/${approval.id}`}
        aria-describedby={titleId}
        className="mt-3 inline-flex min-h-11 w-full items-center justify-center rounded-full bg-sunk px-[18px] text-[1.0625rem] font-bold text-content transition-transform duration-[90ms] hover:bg-sunk-deep motion-safe:active:scale-[0.98]"
      >
        Details
      </Link>
    </Card>
  );
}

function Price({ value }: { value: number | null }) {
  if (value == null) return <span className="hatch text-unknown">{UNKNOWN}</span>;
  return <span>${value.toFixed(2)}</span>;
}

function OrderRow({ o }: { o: OrderSummary }) {
  const state = ORDER_STATE[o.state] ?? { word: o.state, tone: "neutral" as const };
  const body = (
    <>
      <div className="min-w-0">
        <p className="flex flex-wrap items-center gap-x-1.5 gap-y-1">
          <span className="font-bold">{o.underlying}</span>
          <span className="font-bold">{orderContract(o)}</span>
          <StatusWord tone={state.tone}>{state.word}</StatusWord>
        </p>
        <p className="tabular mt-0.5 font-mono text-[0.8125rem] text-muted">
          limit <Price value={o.limit_price} /> · {o.filled_qty.toFixed(0)} filled · since {timeET(o.created_at)} ·{" "}
          {o.is_live ? "live" : "paper"}
        </p>
        {o.detail && <p className="mt-0.5 text-[0.8125rem]">{o.detail}</p>}
      </div>
    </>
  );
  return (
    <li className="border-t border-border first:border-t-0">
      {o.approval_id !== null ? (
        <Link href={`/trades/${o.approval_id}`} className="-mx-2 grid grid-cols-[1fr_16px] items-center gap-x-2.5 rounded-xl px-2 py-[11px] text-sm hover:bg-sunk">
          {body}
          <ChevronRight size={16} aria-hidden="true" className="text-muted" />
        </Link>
      ) : (
        <div className="py-[11px] text-sm">{body}</div>
      )}
    </li>
  );
}

function InFlight({
  strategy,
  submitted,
  onSettled,
}: {
  strategy: StrategyFilter;
  submitted: Map<number, CommandStatus>;
  onSettled: (id: number) => void;
}) {
  const { loaded, sent } = useSent(strategy, submitted);
  const orders = useWorkingOrders();
  const controls = useControls();
  const drainHealthy = controls.data?.drain_healthy ?? true;
  const working = orders.data ? inScope(orders.data.orders, strategy) : [];
  if (!loaded || !orders.data || (sent.length === 0 && working.length === 0)) return null;
  return (
    <section aria-labelledby="flight-title">
      <h2 id="flight-title" className={H2}>
        In flight
      </h2>
      <div className="grid gap-4">
        {sent.length > 0 && (
          <div className="grid items-start gap-4 lg:grid-cols-2">
            {sent.map((a) => (
              <SentCard key={a.id} approval={a} command={submitted.get(a.id) ?? null} drainHealthy={drainHealthy} onSettled={onSettled} />
            ))}
          </div>
        )}
        {working.length > 0 && (
          <Card as="div">
            <ul>
              {working.map((o) => (
                <OrderRow key={o.id} o={o} />
              ))}
            </ul>
            <p className="mt-2 text-[0.8125rem] text-muted">
              A working order is cancelled in IBKR for now. Cancelling it from here is planned.
            </p>
          </Card>
        )}
      </div>
    </section>
  );
}

function NotTraded({ strategy, day }: { strategy: StrategyFilter; day: string }) {
  // The approvals route filters by UTC date; ask for the day either side and keep New York's day.
  const since = shiftDay(day, -1);
  const until = shiftDay(day, 1);
  const q = useQuery({
    queryKey: ["options", "approvals", "range", since, until],
    queryFn: () =>
      apiFetch<ApprovalListResponse>(`/options/approvals?status=all&since=${since}&until=${until}&limit=200`),
    refetchInterval: 60_000,
  });
  if (!q.data) return null;
  const rows = notTradedRows(q.data.approvals, day, strategy);
  if (rows.length === 0) return null;
  return (
    <section aria-labelledby="not-traded-title">
      <h2 id="not-traded-title" className={H2}>
        Not traded
      </h2>
      <Card as="div">
        <ul>
          {rows.map((r) => (
            <li key={r.id} className="border-t border-border first:border-t-0">
              <Link
                href={`/trades/${r.id}`}
                className="-mx-2 grid grid-cols-[1fr_auto_16px] items-center gap-x-2.5 rounded-xl px-2 py-[11px] text-sm hover:bg-sunk"
              >
                <div className="min-w-0">
                  <span className="font-bold">{r.title}</span>
                  <span className="ml-1.5 align-[1px]">
                    <StatusWord>{r.word}</StatusWord>
                  </span>
                  <div className="text-[0.8125rem] text-muted">
                    {r.decision} · {r.raised}
                  </div>
                </div>
                <div className="tabular text-right font-semibold">
                  <span className={clsx(r.value === null && "hatch text-unknown")}>
                    {r.value === null ? UNKNOWN : formatMoneyCell(r.value)}
                  </span>
                  <div className="text-[0.8125rem] font-normal text-muted">{r.valueLabel}</div>
                </div>
                <ChevronRight size={16} aria-hidden="true" className="text-muted" />
              </Link>
            </li>
          ))}
        </ul>
      </Card>
    </section>
  );
}

/**
 * One New York day of the wheel: what is in flight (today only), what traded (Home's trade cards),
 * and what was proposed and did not trade. Read-only, apart from the unchanged decide flow inside
 * a sent card's receipt.
 */
export function HistoryView({
  strategy,
  day,
  today,
  onDay,
  submitted,
  onSettled,
}: {
  strategy: StrategyFilter;
  /** The New York day shown, YYYY-MM-DD. */
  day: string;
  today: string;
  /** null goes back to today. */
  onDay: (day: string | null) => void;
  submitted: Map<number, CommandStatus>;
  onSettled: (id: number) => void;
}) {
  const isToday = day === today;
  const q = useQuery({
    queryKey: ["pnl", "day", strategy, day],
    queryFn: () => apiFetch<DayTradesResponse>(`/pnl/day?date=${day}&strategy=${strategy}`),
    refetchInterval: isToday ? 60_000 : false,
  });
  const trades = (q.data?.trades ?? []).filter((t) => t.source === "wheel");

  let traded: ReactNode;
  if (q.isError && !q.data) {
    traded = <p className="text-sm text-muted">This day's trades could not be loaded. They are asked for again every minute.</p>;
  } else if (!q.data) {
    traded = <div className="h-32 rounded-[18px] bg-surface" role="status" aria-busy="true" aria-label="Loading the day's trades" />;
  } else if (trades.length === 0) {
    traded = <p className="text-sm text-muted">{isToday ? "Nothing has traded yet today." : `Nothing traded on ${dayLabel(day)}.`}</p>;
  } else {
    traded = (
      <div className="grid items-start gap-4 lg:grid-cols-2">
        {trades.map((t) => (
          <TradeCard key={t.key} trade={t} />
        ))}
      </div>
    );
  }

  return (
    <div className="grid gap-6">
      <div className="flex flex-wrap items-center gap-2">
        <h2 className="mr-auto text-[1.0625rem] font-bold">
          {dayLabel(day)}
          {isToday ? " · today" : ""}
        </h2>
        <Button
          variant="quiet"
          aria-label="Previous day with trades"
          disabled={!q.data?.previous_day}
          onClick={() => q.data?.previous_day && onDay(q.data.previous_day)}
        >
          <ChevronLeft size={18} aria-hidden="true" />
        </Button>
        <Button
          variant="quiet"
          aria-label="Next day with trades"
          disabled={!q.data?.next_day}
          onClick={() => q.data?.next_day && onDay(q.data.next_day === today ? null : q.data.next_day)}
        >
          <ChevronRight size={18} aria-hidden="true" />
        </Button>
        {!isToday && (
          <Button variant="secondary" onClick={() => onDay(null)}>
            Today
          </Button>
        )}
      </div>

      {isToday && <InFlight strategy={strategy} submitted={submitted} onSettled={onSettled} />}

      <section aria-labelledby="traded-title">
        <h2 id="traded-title" className={H2}>
          Traded
        </h2>
        {traded}
      </section>

      <NotTraded strategy={strategy} day={day} />

      {strategy === "all" && (
        <p className="text-[0.8125rem] text-muted">
          Credit spreads trade on their own and are not listed here. Their days are under{" "}
          <Link href="/trades?strategy=spread" className="font-semibold text-content underline underline-offset-2">
            Credit spreads
          </Link>
          .
        </p>
      )}
    </div>
  );
}
```

The traded-section heading carries the day heading's level (h2) because the page's h1 is
"Trades" and the day line is the view's own heading.

- [x] **Step 10: The calendar's link** — `web/features/home/RealisedCalendar.tsx`

Add `import Link from "next/link";`. Give `DayCloses` a second prop,
`onLeave: () => void`, and add at the end of its `<section>`, after the list/empty/error branch:

```tsx
      <Link
        href={`/trades?view=history&day=${date}`}
        onClick={onLeave}
        className="mt-2 inline-flex min-h-11 items-center gap-1 text-[0.8125rem] font-semibold underline-offset-2 hover:underline"
      >
        Open this day in History <ChevronRight size={14} aria-hidden="true" />
      </Link>
```

`CalendarBody` gains `onLeave: () => void` and renders `<DayCloses date={selected} onLeave={onLeave} />`;
`RealisedCalendarButton` renders `<CalendarBody now={now} onLeave={() => setOpen(false)} />`, so
following the link closes the sheet on Home and on Trades alike.

- [x] **Step 11: Run the tests to verify they pass, then the gate**

Run: `cd web && npx vitest run features/trades features/home components/options components/shell && npx tsc --noEmit && npm run lint && python3 ~/.claude/skills/da-vinci/scripts/lint.py features/trades`
Expected: PASS: 10 logic tests, 12 HistoryView tests and 1 calendar test new; every existing
`ControlsStrip`, shell and Home test unchanged; tsc 0; lint clean; da-vinci lint exit 0.

- [x] **Step 12: Commit** (with the Progress log row for Task 4 filled in)

```bash
git add web/features/trades/time.ts web/features/trades/time.test.ts web/features/trades/history.ts \
  web/features/trades/history.test.ts web/features/trades/HistoryView.tsx web/features/trades/HistoryView.test.tsx \
  web/components/options/ControlsStrip.tsx web/features/home/RealisedCalendar.tsx web/features/home/RealisedCalendar.test.tsx \
  docs/superpowers/plans/2026-10-19-web-overhaul-2-trades.md
git commit -m "feat(web): History - a New York day of in-flight work, trades and proposals that did not trade"
```

---

### Task 6: Assessed — the scan's contracts, restyled, scoped by strategy

**Files:**
- Modify: `web/components/options/AssessedBrowser.tsx` (whole file)
- Modify: `web/components/options/AssessedRow.tsx` (the returned JSX above the two dialogs, and
  one import; the flow above `return` is untouched)
- Modify: `web/components/options/StageBadge.tsx` (whole file)
- Modify: `web/components/options/AssessedBrowser.test.tsx` (+2 tests)

**Interfaces:**
- Consumes: `AssessedRow({ contract, drainHealthy })` (its promote flow unchanged), `Card`,
  `Button`, `StatusWord`, `kindOf`, `matchesFilter`, `formatDateTime`.
- Produces: `AssessedBrowser({ strategy?: StrategyFilter })`, `stageCounts(contracts): string`
  ("passed: 1 · risk gate: 1"), `STAGE_LABEL` (StageBadge.tsx).

- [x] **Step 1: Load da-vinci** if it is not already loaded. Brief: cards per symbol on paper,
  rows without table chrome, Promote as a secondary button (it proposes, it never trades), the
  stage as a word.

- [x] **Step 2: Write the failing tests** — append inside `describe("AssessedBrowser")` in
  `web/components/options/AssessedBrowser.test.tsx`:

```tsx
  it("scopes the contracts to the strategy and drops a symbol left with none", async () => {
    const { apiFetch } = await import("@/lib/api");
    const c = (id: string, symbol: string, strategy: string) => ({
      as_of: "x", candidate_id: id, symbol, strategy, strike: 190.0, expiry: null, stage: "passed",
      reasons: [], reasons_text: [], blended_score: 72.0, premium: 3.25, ideal: null,
      promotable: false, promote_note: null,
    });
    (apiFetch as any).mockResolvedValue({
      as_of: "x", run_id: "r1", computed_at: null,
      groups: [
        { as_of: "x", symbol: "NVDA", contracts: [c("a", "NVDA", "cash_secured_put")], counts: { passed: 1 } },
        { as_of: "x", symbol: "MSFT", contracts: [c("b", "MSFT", "covered_call")], counts: { passed: 1 } },
      ],
    });
    withClient(<AssessedBrowser strategy="cc" />);
    expect(await screen.findByText("MSFT")).toBeDefined();
    expect(screen.queryByText("NVDA")).toBeNull();
  });

  it("names its two filters with visible labels", async () => {
    const { apiFetch } = await import("@/lib/api");
    (apiFetch as any).mockResolvedValue({ as_of: "x", run_id: "r1", computed_at: null, groups: [] });
    withClient(<AssessedBrowser />);
    await screen.findByText(/No assessed contracts/i);
    expect(screen.getByLabelText("Stage")).toBeDefined();
    expect(screen.getByLabelText("Symbol")).toBeDefined();
  });
```

- [x] **Step 3: Run them to verify they fail**

Run: `cd web && npx vitest run components/options/AssessedBrowser.test.tsx`
Expected: FAIL (`strategy` ignored, so NVDA shows; the legacy labels are not tied to their
controls).

- [x] **Step 4: Rewrite `web/components/options/StageBadge.tsx`**

```tsx
import { StatusWord } from "@/components/ui/StatusWord";

type Stage = "generator" | "risk_gate" | "score_floor" | "dedupe" | "top_n" | "passed";

export const STAGE_LABEL: Record<Stage, string> = {
  generator: "Filtered",
  risk_gate: "Gate rejected",
  score_floor: "Below score floor",
  dedupe: "Lost dedupe",
  top_n: "Capped out",
  passed: "Passed",
};

// A word on every stage, never colour alone; the flag fill only where the Rules Engine said no.
export function StageBadge({ stage }: { stage: Stage }) {
  return <StatusWord tone={stage === "risk_gate" ? "flag" : "neutral"}>{STAGE_LABEL[stage] ?? stage}</StatusWord>;
}
```

- [x] **Step 5: Rewrite `web/components/options/AssessedBrowser.tsx`**

```tsx
"use client";

import clsx from "clsx";
import { useQuery } from "@tanstack/react-query";
import { ChevronDown } from "lucide-react";
import { useId, useState } from "react";
import { Card } from "@/components/ui/Card";
import { apiFetch } from "@/lib/api";
import { formatDateTime } from "@/lib/format";
import { type StrategyFilter, kindOf, matchesFilter } from "@/lib/strategy";
import { AssessedRow } from "./AssessedRow";
import type { AssessedContract, AssessedResponse, AssessedStage, ControlsResponse } from "./types";

const STAGES: AssessedStage[] = ["generator", "risk_gate", "score_floor", "dedupe", "top_n", "passed"];

const FIELD =
  "min-h-11 rounded-xl border border-control bg-surface px-3 text-base text-content focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-focus";

/** "passed: 1 · risk gate: 1", in pipeline order, from the contracts actually shown. */
export function stageCounts(contracts: AssessedContract[]): string {
  const counts = new Map<string, number>();
  for (const c of contracts) counts.set(c.stage, (counts.get(c.stage) ?? 0) + 1);
  return STAGES.filter((s) => counts.has(s))
    .map((s) => `${s.replace(/_/g, " ")}: ${counts.get(s)}`)
    .join(" · ");
}

export function AssessedBrowser({ strategy = "all" }: { strategy?: StrategyFilter } = {}) {
  const [stageFilter, setStageFilter] = useState<AssessedStage | "all">("all");
  const [symbolFilter, setSymbolFilter] = useState("");
  const stageId = useId();
  const symbolId = useId();

  const { data, isLoading, isError } = useQuery({
    queryKey: ["options", "assessed", stageFilter, symbolFilter],
    queryFn: () => {
      const params = new URLSearchParams({ run: "latest" });
      if (stageFilter !== "all") params.set("stage", stageFilter);
      if (symbolFilter.trim()) params.set("symbol", symbolFilter.trim().toUpperCase());
      return apiFetch<AssessedResponse>(`/options/assessed?${params.toString()}`);
    },
    placeholderData: (prev) => prev,
  });

  // The drain's health drives a promoted command's receipt "stalled" state (spec §9.2 rule 3).
  // Defaults to healthy while loading so an unloaded drain never falsely reads as dead.
  const controls = useQuery({
    queryKey: ["options", "controls"],
    queryFn: () => apiFetch<ControlsResponse>("/options/controls"),
    placeholderData: (prev) => prev,
    refetchInterval: 30_000,
  });
  const drainHealthy = controls.data?.drain_healthy ?? true;

  const filters = (
    <div className="flex flex-wrap items-end gap-3">
      <div className="grid gap-1">
        <label htmlFor={stageId} className="text-xs font-semibold tracking-[0.04em] text-muted">
          Stage
        </label>
        <select
          id={stageId}
          value={stageFilter}
          onChange={(e) => setStageFilter(e.target.value as AssessedStage | "all")}
          className={FIELD}
        >
          <option value="all">all stages</option>
          {STAGES.map((s) => (
            <option key={s} value={s}>
              {s.replace(/_/g, " ")}
            </option>
          ))}
        </select>
      </div>
      <div className="grid gap-1">
        <label htmlFor={symbolId} className="text-xs font-semibold tracking-[0.04em] text-muted">
          Symbol
        </label>
        <input
          id={symbolId}
          type="text"
          value={symbolFilter}
          onChange={(e) => setSymbolFilter(e.target.value)}
          placeholder="NVDA"
          autoComplete="off"
          autoCapitalize="characters"
          spellCheck={false}
          className={clsx(FIELD, "w-32 placeholder:text-muted")}
        />
      </div>
    </div>
  );

  if (isLoading) return <p className="text-sm text-muted">Loading assessed contracts</p>;
  if (isError) return <p className="text-sm text-muted">Assessed contracts could not be loaded right now.</p>;

  const groups = (data?.groups ?? [])
    .map((g) => ({
      symbol: g.symbol,
      contracts: g.contracts.filter((c) => matchesFilter(kindOf(c.strategy, null), strategy)),
    }))
    .filter((g) => g.contracts.length > 0);
  const computed = formatDateTime(data?.computed_at);

  return (
    <div className="grid gap-4">
      {filters}
      {data?.run_id && (
        <p className="text-[0.8125rem] text-muted">
          Run {data.run_id}
          {computed ? ` · computed ${computed}` : ""}
        </p>
      )}
      {groups.length === 0 ? (
        <p className="text-sm text-muted">No assessed contracts for this run.</p>
      ) : (
        groups.map((g) => <Group key={g.symbol} symbol={g.symbol} contracts={g.contracts} drainHealthy={drainHealthy} />)
      )}
    </div>
  );
}

function Group({
  symbol,
  contracts,
  drainHealthy,
}: {
  symbol: string;
  contracts: AssessedContract[];
  drainHealthy: boolean;
}) {
  const [open, setOpen] = useState(true);
  const panelId = useId();
  return (
    <Card as="section" aria-label={`${symbol} assessed contracts`}>
      <button
        type="button"
        aria-expanded={open}
        aria-controls={panelId}
        onClick={() => setOpen((o) => !o)}
        className="flex min-h-11 w-full items-center justify-between gap-3 text-left"
      >
        <span className="text-[1.0625rem] font-bold">{symbol}</span>
        <span className="flex items-center gap-2">
          <span className="text-[0.8125rem] text-muted">{stageCounts(contracts)}</span>
          <ChevronDown
            size={16}
            aria-hidden="true"
            className={clsx("text-muted transition-transform duration-[180ms] ease-out motion-reduce:transition-none", open && "rotate-180")}
          />
        </span>
      </button>
      <ul id={panelId} hidden={!open} className="mt-1">
        {contracts.map((c) => (
          <AssessedRow key={c.candidate_id} contract={c} drainHealthy={drainHealthy} />
        ))}
      </ul>
    </Card>
  );
}
```

`formatDateTime` returns `""` for a missing or unparseable time, which the `computed ?` guard
handles.

- [x] **Step 6: Restyle `AssessedRow`'s markup** — in `web/components/options/AssessedRow.tsx`
  add `import { Button } from "@/components/ui/Button";` and replace everything from
  `<li className="px-4 py-2">` down to (not including) `{liveStep && (` with:

```tsx
    <li className="border-t border-border py-3 first:border-t-0">
      <div className="flex items-center justify-between gap-3">
        <p className="flex flex-wrap items-center gap-x-2 gap-y-1">
          <StageBadge stage={contract.stage} />
          <span className="text-sm font-bold">
            {contract.strike != null ? `$${contract.strike}` : "strike n/a"} {contract.strategy.replace(/_/g, " ")}
          </span>
        </p>
        <span className="tabular font-mono text-[0.8125rem] text-muted">
          score{" "}
          {contract.blended_score != null ? (
            contract.blended_score.toFixed(1)
          ) : (
            <span className="hatch text-unknown">n/a</span>
          )}
        </span>
      </div>
      {contract.reasons_text.length > 0 && (
        <p className="mt-1 text-[0.8125rem] text-muted">{contract.reasons_text.join(" · ")}</p>
      )}
      {!canPromote && contract.promote_note && (
        <p className="mt-1 text-[0.8125rem] text-muted">{contract.promote_note}</p>
      )}

      {canPromote && (
        <div className="mt-2">
          {/* Secondary, not lime: promote re-prices and re-gates; it never trades. */}
          <Button variant="secondary" disabled={inFlight} onClick={() => setConfirming(true)}>
            Promote
          </Button>
        </div>
      )}

      {error && (
        <p className="mt-2 text-[0.8125rem] text-loss" data-testid="command-error" role="alert">
          {error}
        </p>
      )}

      {current && <CommandReceipt command={current} order={null} drainHealthy={drainHealthy} />}

      {approvalId != null && (
        <p className="mt-1 text-[0.8125rem]">
          <Link href={`/trades/${approvalId}`} className="font-semibold underline underline-offset-2">
            View approval
          </Link>
        </p>
      )}

```

The two `ConfirmAction` blocks, the closing `</li>`, `describeError` and everything above
`return (` stay exactly as they are.

- [x] **Step 7: Run the tests to verify they pass, then the gate**

Run: `cd web && npx vitest run components/options && npx tsc --noEmit && npm run lint`
Expected: PASS: every existing `AssessedBrowser`, `AssessedRow` and `ApprovalDetail` test
unchanged plus the 2 new ones. An existing promote test that fails means the markup change
touched the flow: restore the flow, never edit that test.

- [x] **Step 8: da-vinci lint**

Run: `python3 ~/.claude/skills/da-vinci/scripts/lint.py web/components/options/AssessedBrowser.tsx web/components/options/AssessedRow.tsx web/components/options/StageBadge.tsx`
Expected: exit 0, or every finding fixed in the code.

- [x] **Step 9: Commit** (with the Progress log row for Task 5 filled in)

```bash
git add web/components/options/AssessedBrowser.tsx web/components/options/AssessedBrowser.test.tsx \
  web/components/options/AssessedRow.tsx web/components/options/StageBadge.tsx docs/superpowers/plans/2026-10-19-web-overhaul-2-trades.md
git commit -m "feat(web): Assessed view - symbol cards, stage words, strategy scope, labelled filters"
```

---

### Task 7: Spreads — what each book traded, with the menu Claude saw as the reason

**Files:**
- Create: `web/features/trades/types.ts`
- Create: `web/features/trades/spreads.ts`, `web/features/trades/spreads.test.ts`
- Create: `web/features/trades/SpreadsView.tsx`, `web/features/trades/SpreadsView.test.tsx`

**The composition (ruling 8): trades first, the menu as the reason.** The day's spreads lead. The
paper book and the baseline book (simulated, always the deterministic pick) sit side by side from
1024px, which is the comparison the baseline book exists for. A paper spread that a pick opened
carries "The menu Claude saw" under it, collapsed: what was sent, Claude's reason labelled as
Claude's view, and the lettered menu with Baseline, Claude's pick and Sent as words. Every other
pick of the day (a skip, a fallback, a refusal, or a pick whose spread is not on record) follows
under "Other picks" as a short card with its menu collapsed the same way. The shadow book
follows when it has rows.

**Interfaces:**
- Consumes: `GET /spreads/picks?day=` (Task 1), `SpreadPosition` (`web/features/home/types.ts`),
  `Card`, `Disclosure`, `StatusWord`, `Button`, `formatStubValue`, `formatMoneyCell`.
- Produces:
  - `types.ts`: `SpreadMenuItem`, `SpreadPick`, `SpreadPicksResponse`
  - `spreads.ts`: `codeWords(code)`, `fallbackWords(code)`, `itemLabel(i)`, `itemDetail(i)`,
    `breakEven(i): string | null`, `pickTitle(p, underlying)`, `pickSentence(p)`,
    `timeET` and `dayLabel` (re-exported from Task 5's `time.ts`), `positionHref(p, underlying): string | null`,
    `bookRow(p, underlying): BookRow`, `BOOK_LABEL`
  - `SpreadsView()`

- [x] **Step 1: Load da-vinci** if it is not already loaded. Brief: the spreads lead, as Position
  rows grouped by book, paper and baseline side by side from 1024px; the menu is a stub-like
  lettered list under a perforation, collapsed under the spread it opened; Claude's reason is
  labelled as Claude's view; nothing on this view is an action, so no lime; an unreadable menu is
  said in words with the hatch.

- [x] **Step 2: Write the failing logic tests** — `web/features/trades/spreads.test.ts`

```ts
import { describe, expect, it } from "vitest";
import type { SpreadPosition } from "@/features/home/types";
import {
  bookRow,
  breakEven,
  codeWords,
  dayLabel,
  fallbackWords,
  itemDetail,
  pickSentence,
  pickTitle,
  positionHref,
  timeET,
} from "./spreads";
import type { SpreadMenuItem, SpreadPick } from "./types";

const item = (over: Partial<SpreadMenuItem> = {}): SpreadMenuItem => ({
  letter: "B", position: "baseline", side: "put", short_strike: 762, long_strike: 757, width: 5,
  contracts: 21, credit_mid: 0.25, credit_after_costs: 0.144, max_loss_per_contract_usd: 475,
  short_delta: -0.14, spot: 767.29, dist_spot_pts: 5.29, dist_em_multiple: 1.49,
  be_nominal_exits: 0.9493, ...over,
});

const pick = (over: Partial<SpreadPick> = {}): SpreadPick => ({
  pick_id: 1, created_at: "2026-10-15T14:17:30Z", book_mode: "paper", choice: "B",
  reason: "B sits past the put wall.", fallback_reason: null, executed_letter: "B",
  send_rejected: false, send_reasons: [], filled: true, model: "claude-sonnet-5-5",
  regime: "negative", side: "put", plan_bias: null, event_flag: false, menu_readable: true,
  menu: [item({ letter: "A", position: "inside", short_strike: 763, long_strike: 758 }), item()],
  spread_id: "s1", ...over,
});

const position = (over: Partial<SpreadPosition> = {}): SpreadPosition => ({
  as_of: "", spread_id: "s1", mode: "paper", side: "put", expiry: "2026-10-15", short_strike: 762,
  long_strike: 757, width: 5, contracts_opened: 21, contracts: 21, entry_credit: 0.25,
  entry_commission: 27.3, opened_at: "2026-10-15T14:18:00Z", status: "open", exit_debit: null,
  exit_commission: null, exit_reason: null, closed_at: null, realized_pnl_usd: null, ...over,
});

describe("codeWords and fallbackWords", () => {
  it("turns a stored code into words", () => {
    expect(codeWords("stale_pick")).toBe("stale pick");
  });
  it("says what each known fallback means, and keeps an unknown code visible", () => {
    expect(fallbackWords("timeout")).toBe("Claude did not answer in time");
    expect(fallbackWords("off_menu")).toBe("Claude named a letter that was not on the menu");
    expect(fallbackWords("nonzero_exit")).toBe("the picker failed (nonzero exit)");
  });
});

describe("pickTitle", () => {
  it("names Claude's pick, a skip, and a pick that could not be used", () => {
    expect(pickTitle(pick(), "SPY")).toBe("SPY · Claude picked B");
    expect(pickTitle(pick({ choice: "skip", executed_letter: null }), "SPY")).toBe("SPY · Claude skipped");
    expect(pickTitle(pick({ choice: "skip", fallback_reason: "timeout" }), "SPY")).toBe("SPY · Claude's pick not used");
  });
});

describe("pickSentence", () => {
  it("a filled pick says what was sent and that it filled", () => {
    expect(pickSentence(pick())).toBe("Sent B, the 762/757 put spread, 21 contracts. It filled.");
  });
  it("a pick that did not trade says why, in words", () => {
    expect(pickSentence(pick({ filled: false, send_rejected: true, send_reasons: ["stale_pick", "halted"] }))).toBe(
      "B did not trade: stale pick, halted.",
    );
    expect(pickSentence(pick({ filled: false, send_rejected: true, send_reasons: [] }))).toBe(
      "B did not trade: no reason recorded.",
    );
  });
  it("a skip says nothing was sent", () => {
    expect(pickSentence(pick({ choice: "skip", executed_letter: null, filled: false }))).toBe(
      "Claude chose not to trade this menu. Nothing was sent.",
    );
  });
  it("a fallback says why Claude's answer was not used and what was taken instead", () => {
    expect(pickSentence(pick({ choice: "skip", fallback_reason: "timeout" }))).toBe(
      "Claude did not answer in time, so the baseline pick B was taken. Sent B, the 762/757 put spread, 21 contracts. It filled.",
    );
    expect(
      pickSentence(pick({ choice: "skip", fallback_reason: "timeout", executed_letter: null, filled: false, send_rejected: true, send_reasons: ["no_baseline_item"] })),
    ).toBe("Claude did not answer in time, so there was no baseline pick to fall back on. Nothing was sent.");
  });
  it("a result the service has not recorded yet is said to be unrecorded, never guessed", () => {
    expect(pickSentence(pick({ filled: false }))).toBe("Sent B, the 762/757 put spread, 21 contracts. No result is recorded yet.");
  });
  it("an executed letter missing from an unreadable menu is named by its letter alone", () => {
    expect(pickSentence(pick({ menu: [], menu_readable: false }))).toBe("Sent B. It filled.");
  });
});

describe("menu figures", () => {
  it("describes an item's size and distance", () => {
    expect(itemDetail(item())).toBe("21 contracts · 5.29 pts from spot (1.49 expected moves) · $0.14 a share after costs");
    expect(itemDetail(item({ contracts: 1, dist_em_multiple: null }))).toBe("1 contract · 5.29 pts from spot · $0.14 a share after costs");
  });
  it("gives the break-even win rate, or null when it is unknown", () => {
    expect(breakEven(item())).toBe("break-even at 94.9% wins");
    expect(breakEven(item({ be_nominal_exits: null }))).toBeNull();
  });
});

describe("times and days", () => {
  it("shows a pick's time in New York", () => {
    expect(timeET("2026-10-15T14:17:30Z")).toBe("10:17 AM ET");
  });
  it("labels a day without shifting it", () => {
    expect(dayLabel("2026-10-15")).toBe("Thu, Oct 15");
  });
});

describe("the book's rows", () => {
  it("an open spread shows the credit taken, unsigned", () => {
    const r = bookRow(position(), "SPY");
    expect(r.title).toBe("SPY 762/757 put spread");
    expect(r.word).toBe("Open");
    expect(r.value).toBeCloseTo(525);
    expect(r.signed).toBe(false);
    expect(r.valueLabel).toBe("credit taken");
  });
  it("a closed spread shows its realised P&L, signed", () => {
    const r = bookRow(position({ status: "closed", realized_pnl_usd: -231.5 }), "SPY");
    expect(r.word).toBe("Closed");
    expect(r.value).toBe(-231.5);
    expect(r.signed).toBe(true);
    expect(r.valueLabel).toBe("realised");
  });
  it("links only the paper book, the one the position page reads", () => {
    expect(positionHref(position(), "SPY")).toBe("/positions/SPY/spread-s1");
    expect(positionHref(position({ mode: "baseline" }), "SPY")).toBeNull();
    expect(positionHref(position({ mode: "shadow" }), "SPY")).toBeNull();
  });
});
```

- [x] **Step 3: Write the types** — `web/features/trades/types.ts`

```ts
import type { SpreadPosition } from "@/features/home/types";

/** Mirrors src/api/models/spreads.py SpreadMenuItemOut, SpreadPickOut and SpreadPicksResponse.
 *  Hand-written like components/<domain>/types.ts. Credits are per share. */

export type SpreadMenuItem = {
  letter: string;
  position: "inside" | "baseline" | "outer";
  side: "put" | "call";
  short_strike: number;
  long_strike: number;
  width: number;
  contracts: number;
  credit_mid: number;
  credit_after_costs: number;
  max_loss_per_contract_usd: number;
  short_delta: number | null;
  spot: number;
  dist_spot_pts: number;
  dist_em_multiple: number | null;
  /** Break-even win rate (0-1) under the configured exits; null when it cannot be computed. */
  be_nominal_exits: number | null;
};

export type SpreadPick = {
  pick_id: number;
  created_at: string;
  book_mode: string;
  /** A menu letter, or "skip". */
  choice: string;
  /** Claude's reason; "" when it gave none. */
  reason: string;
  fallback_reason: string | null;
  executed_letter: string | null;
  /** True when it did not trade: refused at send time, or sent and not filled. */
  send_rejected: boolean;
  send_reasons: string[];
  filled: boolean;
  model: string;
  regime: string;
  side: string | null;
  plan_bias: string | null;
  event_flag: boolean;
  /** False when the stored menu no longer parses; `menu` is then empty. */
  menu_readable: boolean;
  menu: SpreadMenuItem[];
  spread_id: string | null;
};

export type SpreadPicksResponse = {
  as_of: string;
  available: boolean;
  underlying: string;
  mode: string;
  ai_enabled: boolean;
  day: string;
  previous_day: string | null;
  next_day: string | null;
  /** Newest first. */
  picks: SpreadPick[];
  /** Every book's spreads opened that day, oldest first. */
  positions: SpreadPosition[];
};
```

Check the field names against Section B's entry check B4 output; a difference is fixed here.

- [x] **Step 4: Run the logic tests to verify they fail**

Run: `cd web && npx vitest run features/trades/spreads.test.ts`
Expected: FAIL (`./spreads` not found).

- [x] **Step 5: Write `web/features/trades/spreads.ts`**

```ts
import type { SpreadPosition } from "@/features/home/types";
import { dayLabel, timeET } from "./time";
import type { SpreadMenuItem, SpreadPick } from "./types";

// Shared with History; re-exported so this module's callers and tests keep one import.
export { dayLabel, timeET };

const FALLBACK: Record<string, string> = {
  timeout: "Claude did not answer in time",
  off_menu: "Claude named a letter that was not on the menu",
  unparseable: "Claude's answer could not be read",
  picker_error: "the picker failed",
};

/** A stored reason code in words: "stale_pick" becomes "stale pick". */
export function codeWords(code: string): string {
  return code.replace(/_/g, " ");
}

/** Why Claude's answer was not used. An unknown code stays visible rather than being guessed at. */
export function fallbackWords(code: string): string {
  return FALLBACK[code] ?? `the picker failed (${codeWords(code)})`;
}

const capitalise = (s: string) => s.charAt(0).toUpperCase() + s.slice(1);
const plural = (n: number, word: string) => `${n} ${word}${n === 1 ? "" : "s"}`;

export function itemLabel(i: { short_strike: number; long_strike: number; side: string }): string {
  return `${i.short_strike}/${i.long_strike} ${i.side}`;
}

export function itemDetail(i: SpreadMenuItem): string {
  const distance =
    `${i.dist_spot_pts.toFixed(2)} pts from spot` +
    (i.dist_em_multiple === null ? "" : ` (${i.dist_em_multiple.toFixed(2)} expected moves)`);
  return [plural(i.contracts, "contract"), distance, `$${i.credit_after_costs.toFixed(2)} a share after costs`].join(" · ");
}

/** The win rate the item needs to break even under the configured exits; null when unknown. */
export function breakEven(i: SpreadMenuItem): string | null {
  return i.be_nominal_exits === null ? null : `break-even at ${(i.be_nominal_exits * 100).toFixed(1)}% wins`;
}

export function pickTitle(p: SpreadPick, underlying: string): string {
  if (p.fallback_reason !== null) return `${underlying} · Claude's pick not used`;
  if (p.choice === "skip") return `${underlying} · Claude skipped`;
  return `${underlying} · Claude picked ${p.choice}`;
}

/**
 * What happened, from the stored flags only. A result the service has not recorded yet is said
 * to be unrecorded, never guessed as a fill or a refusal. `send_rejected` covers both a refusal
 * before sending and an order that did not fill, so it reads "did not trade".
 */
export function pickSentence(p: SpreadPick): string {
  const letter = p.executed_letter;
  let head = "";
  if (p.fallback_reason !== null) {
    head = `${capitalise(fallbackWords(p.fallback_reason))}, so ${
      letter === null ? "there was no baseline pick to fall back on" : `the baseline pick ${letter} was taken`
    }. `;
  } else if (p.choice === "skip") {
    head = "Claude chose not to trade this menu. ";
  }
  if (letter === null) return `${head}Nothing was sent.`;
  const item = p.menu.find((i) => i.letter === letter);
  const what = item ? `${letter}, the ${itemLabel(item)} spread, ${plural(item.contracts, "contract")}` : letter;
  if (p.filled) return `${head}Sent ${what}. It filled.`;
  if (p.send_rejected) {
    const why = p.send_reasons.length > 0 ? p.send_reasons.map(codeWords).join(", ") : "no reason recorded";
    return `${head}${letter} did not trade: ${why}.`;
  }
  return `${head}Sent ${what}. No result is recorded yet.`;
}

/** The position page reads the running (paper) book only; shadow and baseline spreads have none. */
export function positionHref(p: SpreadPosition, underlying: string): string | null {
  return p.mode === "paper" ? `/positions/${encodeURIComponent(underlying)}/spread-${p.spread_id}` : null;
}

export const BOOK_LABEL: Record<string, string> = {
  paper: "Paper book",
  shadow: "Shadow book · simulated fills",
  baseline: "Baseline book · simulated, always the deterministic pick",
};

export type BookRow = {
  key: string;
  href: string | null;
  title: string;
  word: string;
  sub: string;
  value: number | null;
  signed: boolean;
  valueLabel: string;
};

export function bookRow(p: SpreadPosition, underlying: string): BookRow {
  const closed = p.status === "closed";
  return {
    key: p.spread_id,
    href: positionHref(p, underlying),
    title: `${underlying} ${itemLabel(p)} spread`,
    word: closed ? "Closed" : p.status === "expiring" ? "Expiring" : "Open",
    sub: `${plural(p.contracts_opened, "contract")} · credit $${p.entry_credit.toFixed(2)} a share · opened ${timeET(p.opened_at)}`,
    value: closed ? p.realized_pnl_usd : p.entry_credit * 100 * p.contracts_opened,
    signed: closed,
    valueLabel: closed ? "realised" : "credit taken",
  };
}
```

Run: `cd web && npx vitest run features/trades/spreads.test.ts`
Expected: PASS (16 tests).

- [x] **Step 6: Write the failing view tests** — `web/features/trades/SpreadsView.test.tsx`

```tsx
import { fireEvent, screen, waitFor, within } from "@testing-library/react";
import { describe, expect, it } from "vitest";
import { apiFetchMock, renderWithQuery } from "@/lib/test-query";
import { SpreadsView } from "./SpreadsView";

const item = (letter: string, position: string, short: number, long: number) => ({
  letter, position, side: "put", short_strike: short, long_strike: long, width: 5, contracts: 21,
  credit_mid: 0.25, credit_after_costs: 0.144, max_loss_per_contract_usd: 475, short_delta: -0.14,
  spot: 767.29, dist_spot_pts: 5.29, dist_em_multiple: 1.49, be_nominal_exits: 0.9493,
});

const pick = (over: Record<string, unknown> = {}) => ({
  pick_id: 2, created_at: "2026-10-15T15:00:00Z", book_mode: "paper", choice: "A",
  reason: "A keeps the most room under spot.", fallback_reason: null, executed_letter: "A",
  send_rejected: false, send_reasons: [], filled: true, model: "claude-sonnet-5-5",
  regime: "negative", side: "put", plan_bias: null, event_flag: false, menu_readable: true,
  menu: [item("A", "inside", 763, 758), item("B", "baseline", 762, 757)], spread_id: "s1", ...over,
});

const position = (over: Record<string, unknown> = {}) => ({
  as_of: "", spread_id: "s1", mode: "paper", side: "put", expiry: "2026-10-15", short_strike: 763,
  long_strike: 758, width: 5, contracts_opened: 21, contracts: 0, entry_credit: 0.25,
  entry_commission: 27.3, opened_at: "2026-10-15T15:01:00Z", status: "closed", exit_debit: 0.05,
  exit_commission: 27.3, exit_reason: "profit_take", closed_at: "2026-10-15T17:00:00Z",
  realized_pnl_usd: 365.4, ...over,
});

const baseline = position({ spread_id: "b1", mode: "baseline", short_strike: 762, long_strike: 757, realized_pnl_usd: -120 });

const day = (over: Record<string, unknown> = {}) => ({
  as_of: "", available: true, underlying: "SPY", mode: "paper", ai_enabled: true, day: "2026-10-15",
  previous_day: "2026-10-09", next_day: null, picks: [pick()], positions: [position()], ...over,
});

describe("SpreadsView", () => {
  it("leads with the day's spreads, paper and baseline books side by side, results signed", async () => {
    renderWithQuery(<SpreadsView />, { "/spreads/picks": day({ positions: [position(), baseline] }) });
    const book = await screen.findByRole("region", { name: "Spreads opened this day" });
    const paper = within(book).getByRole("region", { name: "Paper book" });
    const base = within(book).getByRole("region", { name: /Baseline book/ });
    expect(within(paper).getByText("+$365.40")).toBeInTheDocument();
    expect(within(base).getByText("−$120.00")).toBeInTheDocument();
    // The position page reads the paper book only: a baseline spread is not a link.
    expect(within(paper).getByRole("link", { name: /SPY 763\/758 put spread/ })).toHaveAttribute("href", "/positions/SPY/spread-s1");
    expect(within(base).queryByRole("link")).toBeNull();
  });

  it("keeps the menu Claude saw under the spread it opened, collapsed, with the pick marked and the reason labelled", async () => {
    renderWithQuery(<SpreadsView />, { "/spreads/picks": day() });
    const paper = await screen.findByRole("region", { name: "Paper book" });
    const toggle = within(paper).getByRole("button", { name: /The menu Claude saw/ });
    expect(toggle).toHaveAttribute("aria-expanded", "false");
    fireEvent.click(toggle);
    expect(within(paper).getByText("Sent A, the 763/758 put spread, 21 contracts. It filled.")).toBeInTheDocument();
    expect(within(paper).getByText("Claude's view:")).toBeInTheDocument();
    const rows = within(within(paper).getByRole("list", { name: "Menu" })).getAllByRole("listitem");
    expect(rows).toHaveLength(2);
    expect(within(rows[0]).getByText("Claude's pick")).toBeInTheDocument();
    expect(within(rows[0]).getByText("Sent")).toBeInTheDocument();
    expect(within(rows[1]).getByText("Baseline")).toBeInTheDocument();
  });

  it("lists picks without a spread on this page under Other picks", async () => {
    renderWithQuery(<SpreadsView />, {
      "/spreads/picks": day({
        picks: [pick(), pick({ pick_id: 1, choice: "skip", executed_letter: null, filled: false, spread_id: null, reason: "Event risk." })],
      }),
    });
    const other = await screen.findByRole("region", { name: "Other picks" });
    const card = within(other).getByRole("article", { name: "SPY · Claude skipped" });
    expect(within(card).getByText("Claude chose not to trade this menu. Nothing was sent.")).toBeInTheDocument();
    expect(within(other).queryByRole("article", { name: "SPY · Claude picked A" })).toBeNull();
  });

  it("says an unreadable menu could not be read and still shows the other picks", async () => {
    renderWithQuery(<SpreadsView />, {
      "/spreads/picks": day({
        picks: [pick(), pick({ pick_id: 1, menu_readable: false, menu: [], choice: "B", executed_letter: "B", spread_id: null, filled: false, send_rejected: true })],
      }),
    });
    const other = await screen.findByRole("region", { name: "Other picks" });
    const bad = within(other).getByRole("article", { name: "SPY · Claude picked B" });
    expect(within(bad).getByText("This menu could not be read.")).toHaveClass("hatch");
    expect(screen.getByRole("region", { name: "Paper book" })).toBeInTheDocument();
  });

  it("says the book could not be read, rather than showing an empty day", async () => {
    renderWithQuery(<SpreadsView />, { "/spreads/picks": day({ available: false, picks: [], positions: [] }) });
    expect(await screen.findByText("The spreads book could not be read right now.")).toBeInTheDocument();
    expect(screen.queryByText("No spread was opened on this day.")).toBeNull();
  });

  it("says when the picker is off", async () => {
    renderWithQuery(<SpreadsView />, { "/spreads/picks": day({ ai_enabled: false, picks: [] }) });
    expect(await screen.findByText(/Claude's picker is off/)).toBeInTheDocument();
  });

  it("says when nothing was opened and no menu was offered", async () => {
    renderWithQuery(<SpreadsView />, { "/spreads/picks": day({ picks: [], positions: [] }) });
    expect(await screen.findByText("No spread was opened on this day.")).toBeInTheDocument();
    expect(screen.getByText("No menu was offered on this day.")).toBeInTheDocument();
  });

  it("steps to the previous day with activity, and back to today", async () => {
    renderWithQuery(<SpreadsView />, {
      "/spreads/picks?day=2026-10-09": day({ day: "2026-10-09", previous_day: null, next_day: "2026-10-15", picks: [], positions: [] }),
      "/spreads/picks": day(),
    });
    expect(await screen.findByRole("heading", { name: /Thu, Oct 15/ })).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Next day with spreads activity" })).toBeDisabled();
    fireEvent.click(screen.getByRole("button", { name: "Previous day with spreads activity" }));
    expect(await screen.findByRole("heading", { name: /Fri, Oct 9/ })).toBeInTheDocument();
    expect(apiFetchMock.mock.calls.some((c) => c[0] === "/spreads/picks?day=2026-10-09")).toBe(true);
    fireEvent.click(screen.getByRole("button", { name: "Today" }));
    await waitFor(() => expect(screen.getByRole("heading", { name: /Thu, Oct 15/ })).toBeInTheDocument());
  });

  it("sends nothing: no request but reads", async () => {
    renderWithQuery(<SpreadsView />, { "/spreads/picks": day() });
    await screen.findByRole("region", { name: "Spreads opened this day" });
    const writes = apiFetchMock.mock.calls.filter((c) => (c[1] as RequestInit | undefined)?.method);
    expect(writes).toHaveLength(0);
  });
});
```

`renderWithQuery` answers an exact key before a prefix, so `"/spreads/picks?day=2026-10-09"`
wins over `"/spreads/picks"` for that one request.

- [x] **Step 7: Run them to verify they fail**

Run: `cd web && npx vitest run features/trades/SpreadsView.test.tsx`
Expected: FAIL (`./SpreadsView` not found).

- [x] **Step 8: Write `web/features/trades/SpreadsView.tsx`**

```tsx
"use client";

import clsx from "clsx";
import Link from "next/link";
import { useQuery } from "@tanstack/react-query";
import { ChevronLeft, ChevronRight } from "lucide-react";
import { useId, useState, type ReactNode } from "react";
import { Button } from "@/components/ui/Button";
import { Card } from "@/components/ui/Card";
import { Disclosure } from "@/components/ui/Disclosure";
import { StatusWord } from "@/components/ui/StatusWord";
import { formatStubValue } from "@/components/ui/Stub";
import type { SpreadPosition } from "@/features/home/types";
import { apiFetch } from "@/lib/api";
import { UNKNOWN } from "@/lib/format";
import { formatMoneyCell } from "@/lib/money";
import { BOOK_LABEL, bookRow, breakEven, dayLabel, itemDetail, itemLabel, pickSentence, pickTitle, timeET } from "./spreads";
import type { SpreadMenuItem, SpreadPick, SpreadPicksResponse } from "./types";

const H2 = "mb-2.5 text-[0.8125rem] font-semibold text-muted";

/**
 * Read-only: one New York day of the spreads books, trades first. Each paper spread carries the
 * menu Claude saw, collapsed, as its reason; picks with no spread here follow. Nothing here sends anything.
 */
export function SpreadsView() {
  // null is "today", the server's New York day; a past day is a fixed date that does not change.
  const [day, setDay] = useState<string | null>(null);
  const q = useQuery({
    queryKey: ["spreads", "picks", day ?? "today"],
    queryFn: () => apiFetch<SpreadPicksResponse>(day === null ? "/spreads/picks" : `/spreads/picks?day=${day}`),
    refetchInterval: day === null ? 60_000 : false,
  });
  const data = q.data;

  if (q.isError && !data) {
    return <p className="text-sm text-muted">The spreads picks could not be loaded right now.</p>;
  }
  if (!data) {
    return <div className="h-40 rounded-[18px] bg-surface" role="status" aria-busy="true" aria-label="Loading the spreads picks" />;
  }

  // A pick belongs under its spread when that spread is on this page; every other pick is "other".
  const shown = new Set(data.positions.map((p) => p.spread_id));
  const pickFor = new Map(data.picks.filter((p) => p.spread_id && shown.has(p.spread_id)).map((p) => [p.spread_id as string, p]));
  const others = data.picks.filter((p) => !(p.spread_id && shown.has(p.spread_id)));

  return (
    <div className="grid gap-6">
      <div className="flex flex-wrap items-center gap-2">
        <h2 className="mr-auto text-[1.0625rem] font-bold">
          {dayLabel(data.day)}
          {day === null ? " · today" : ""}
        </h2>
        <Button
          variant="quiet"
          aria-label="Previous day with spreads activity"
          disabled={data.previous_day === null}
          onClick={() => setDay(data.previous_day)}
        >
          <ChevronLeft size={18} aria-hidden="true" />
        </Button>
        <Button
          variant="quiet"
          aria-label="Next day with spreads activity"
          disabled={data.next_day === null}
          onClick={() => setDay(data.next_day)}
        >
          <ChevronRight size={18} aria-hidden="true" />
        </Button>
        {day !== null && (
          <Button variant="secondary" onClick={() => setDay(null)}>
            Today
          </Button>
        )}
      </div>

      {!data.available ? (
        <p className="text-sm text-muted">The spreads book could not be read right now.</p>
      ) : (
        <>
          {!data.ai_enabled && (
            <p className="text-sm text-muted">
              Claude&apos;s picker is off, so the spreads service sells its own pick without a menu. Menus appear here when the picker is on.
            </p>
          )}
          <Books positions={data.positions} underlying={data.underlying} pickFor={pickFor} />
          {others.length > 0 && (
            <section aria-labelledby="other-picks-title">
              <h2 id="other-picks-title" className={H2}>
                Other picks
              </h2>
              <div className="grid items-start gap-4 lg:grid-cols-2">
                {others.map((p) => (
                  <PickCard key={p.pick_id} pick={p} underlying={data.underlying} />
                ))}
              </div>
            </section>
          )}
          {data.ai_enabled && data.picks.length === 0 && <p className="text-sm text-muted">No menu was offered on this day.</p>}
        </>
      )}
    </div>
  );
}

function Books({
  positions,
  underlying,
  pickFor,
}: {
  positions: SpreadPosition[];
  underlying: string;
  pickFor: Map<string, SpreadPick>;
}) {
  const of = (mode: string) => positions.filter((p) => p.mode === mode);
  const other = positions.filter((p) => !(p.mode in BOOK_LABEL));
  return (
    <section aria-labelledby="book-title">
      <h2 id="book-title" className={H2}>
        Spreads opened this day
      </h2>
      {positions.length === 0 ? (
        <p className="text-sm text-muted">No spread was opened on this day.</p>
      ) : (
        <div className="grid gap-4">
          {/* Paper beside baseline: Claude's pick against the rules' pick, the baseline book's purpose. */}
          <div className="grid items-start gap-4 lg:grid-cols-2">
            {of("paper").length > 0 && <Book label={BOOK_LABEL.paper} rows={of("paper")} underlying={underlying} pickFor={pickFor} />}
            {of("baseline").length > 0 && <Book label={BOOK_LABEL.baseline} rows={of("baseline")} underlying={underlying} pickFor={pickFor} />}
          </div>
          {of("shadow").length > 0 && <Book label={BOOK_LABEL.shadow} rows={of("shadow")} underlying={underlying} pickFor={pickFor} />}
          {other.length > 0 && <Book label="Other books" rows={other} underlying={underlying} pickFor={pickFor} />}
        </div>
      )}
    </section>
  );
}

function Book({
  label,
  rows,
  underlying,
  pickFor,
}: {
  label: string;
  rows: SpreadPosition[];
  underlying: string;
  pickFor: Map<string, SpreadPick>;
}) {
  const titleId = useId();
  return (
    <Card as="section" aria-labelledby={titleId}>
      <h3 id={titleId} className="text-[1.0625rem] font-bold">
        {label}
      </h3>
      <ul className="mt-1">
        {rows.map((p) => {
          const r = bookRow(p, underlying);
          const pick = p.mode === "paper" ? pickFor.get(p.spread_id) : undefined;
          const body: ReactNode = (
            <>
              <div className="min-w-0">
                <span className="font-bold">{r.title}</span>
                <span className="ml-1.5 align-[1px]">
                  <StatusWord>{r.word}</StatusWord>
                </span>
                <div className="text-[0.8125rem] text-muted">{r.sub}</div>
              </div>
              <div className="tabular text-right font-semibold">
                <span
                  className={clsx(
                    r.value === null && "hatch text-unknown",
                    r.signed && r.value !== null && r.value < 0 && "text-loss",
                    r.signed && r.value !== null && r.value > 0 && "text-gain",
                  )}
                >
                  {r.value === null ? UNKNOWN : r.signed ? formatStubValue(r.value, "signed-money") : formatMoneyCell(r.value)}
                </span>
                <div className="text-[0.8125rem] font-normal text-muted">{r.valueLabel}</div>
              </div>
            </>
          );
          return (
            <li key={r.key} className="border-t border-border first:border-t-0">
              {r.href ? (
                <Link href={r.href} className="-mx-2 grid grid-cols-[1fr_auto_16px] items-center gap-x-2.5 rounded-xl px-2 py-[11px] text-sm hover:bg-sunk">
                  {body}
                  <ChevronRight size={16} aria-hidden="true" className="text-muted" />
                </Link>
              ) : (
                <div className="grid grid-cols-[1fr_auto] items-center gap-x-2.5 py-[11px] text-sm">{body}</div>
              )}
              {pick && (
                <div className="mb-3">
                  <MenuDisclosure pick={pick} />
                </div>
              )}
            </li>
          );
        })}
      </ul>
    </Card>
  );
}

/** The menu Claude saw, collapsed: what was sent, Claude's reason (labelled), the lettered menu. */
function MenuDisclosure({ pick, withSentence = true }: { pick: SpreadPick; withSentence?: boolean }) {
  return (
    <Disclosure
      summary={
        <span className="text-[0.8125rem] font-bold">
          The menu Claude saw{" "}
          <span className="font-medium text-muted">
            · {pick.choice === "skip" ? "Claude skipped" : `Claude picked ${pick.choice}`} at {timeET(pick.created_at)}
          </span>
        </span>
      }
    >
      {withSentence && <p className="text-[0.8125rem]">{pickSentence(pick)}</p>}
      {pick.reason.trim() !== "" && (
        <p className="mt-2 text-[0.8125rem]">
          <span className="font-bold">Claude&apos;s view:</span> {pick.reason}
        </p>
      )}
      {pick.menu_readable ? (
        <ul aria-label="Menu" className="mt-3 border-t-2 border-dashed border-perforation pt-1">
          {pick.menu.map((i) => (
            <MenuRow key={i.letter} item={i} pick={pick} />
          ))}
        </ul>
      ) : (
        <p className="mt-3 border-t-2 border-dashed border-perforation pt-2 text-[0.8125rem]">
          <span className="hatch text-unknown">This menu could not be read.</span>
        </p>
      )}
      <p className="mt-1 text-xs text-muted">
        Asked {pick.model} · gamma {pick.regime}
        {pick.event_flag ? " · event day" : ""}
      </p>
    </Disclosure>
  );
}

function PickCard({ pick, underlying }: { pick: SpreadPick; underlying: string }) {
  const titleId = useId();
  return (
    <Card as="article" aria-labelledby={titleId}>
      <div className="flex items-baseline justify-between gap-2">
        <span className="text-xs font-bold uppercase tracking-[0.04em] text-muted">
          Credit spread · {pick.side ? `${pick.side} side` : "menu"}
        </span>
        <span className="text-[0.8125rem] text-muted">{timeET(pick.created_at)}</span>
      </div>
      <h3 id={titleId} className="mt-1 text-[1.0625rem] font-extrabold tracking-[-0.01em]">
        {pickTitle(pick, underlying)}
      </h3>
      <p className="mt-2 text-sm">{pickSentence(pick)}</p>
      <div className="mt-3">
        {pick.menu_readable ? (
          <MenuDisclosure pick={pick} withSentence={false} />
        ) : (
          <p className="border-t-2 border-dashed border-perforation pt-2 text-[0.8125rem]">
            <span className="hatch text-unknown">This menu could not be read.</span>
          </p>
        )}
      </div>
    </Card>
  );
}

function MenuRow({ item, pick }: { item: SpreadMenuItem; pick: SpreadPick }) {
  const be = breakEven(item);
  return (
    <li className="grid grid-cols-[28px_1fr_auto] items-start gap-x-2.5 border-t border-border py-2.5 first:border-t-0">
      <span aria-hidden="true" className="grid h-7 w-7 place-items-center rounded-full bg-sunk font-mono text-[0.8125rem] font-semibold">
        {item.letter}
      </span>
      <div className="min-w-0">
        <p className="flex flex-wrap items-center gap-x-1.5 gap-y-1 text-sm">
          <span className="font-bold">
            <span className="sr-only">{item.letter}: </span>
            {itemLabel(item)}
          </span>
          {item.position === "baseline" && <StatusWord>Baseline</StatusWord>}
          {pick.choice === item.letter && <StatusWord>Claude&apos;s pick</StatusWord>}
          {pick.executed_letter === item.letter && <StatusWord>Sent</StatusWord>}
        </p>
        <p className="mt-0.5 text-[0.8125rem] text-muted">
          {itemDetail(item)} ·{" "}
          {be === null ? (
            <>
              break-even <span className="hatch text-unknown">{UNKNOWN}</span>
            </>
          ) : (
            be
          )}
        </p>
      </div>
      <div className="text-right">
        <p className="tabular font-mono text-[0.84375rem] font-medium">${item.credit_mid.toFixed(2)}</p>
        <p className="text-xs text-muted">credit a share</p>
      </div>
    </li>
  );
}
```

A paper spread whose pick's menu no longer parses still shows its row; its disclosure says the
menu could not be read, under the outcome sentence (which names the letter that was sent) and the
reason. An unreadable menu on an other pick says so on the card itself, with no disclosure to open.

- [x] **Step 9: Run the tests to verify they pass, then the gate**

Run: `cd web && npx vitest run features/trades && npx tsc --noEmit && npm run lint && python3 ~/.claude/skills/da-vinci/scripts/lint.py features/trades`
Expected: PASS (16 logic + 9 view tests new, and Task 5's `time.test.ts` still green); tsc 0; lint clean; da-vinci lint exit 0.

- [x] **Step 10: Commit** (with the Progress log row for Task 6 filled in)

```bash
git add web/features/trades/types.ts web/features/trades/spreads.ts web/features/trades/spreads.test.ts \
  web/features/trades/SpreadsView.tsx web/features/trades/SpreadsView.test.tsx docs/superpowers/plans/2026-10-19-web-overhaul-2-trades.md
git commit -m "feat(web): Spreads view - the day's books first, the menu Claude saw as the reason"
```

---
## Section C — Assembly, detail page, roll (Tasks 8–10) · model: sonnet

Mounts the new page at `/trades`, restyles the approval detail page, and moves Propose a roll.

**Entry checks (run before Task 8):**

- [x] **C1. Section B landed.** `git log --oneline main..HEAD` shows seven commits; Tasks 3–7 are
  ticked.
- [x] **C2. Gates and a production build green.** `cd web && npx vitest run && npx tsc --noEmit && npm run lint`,
  then the build in a scratch copy (never inside `web/`, whose `.next` the operator's dev server
  shares):

  ```bash
  S="$(mktemp -d)/web" && rsync -a --exclude node_modules --exclude .next web/ "$S/" \
    && ln -s "$PWD/web/node_modules" "$S/node_modules" && (cd "$S" && npm run build)
  ```

- [x] **C3. The views exist.** This prints nothing:

  ```bash
  cd web/features/trades && for f in ProposalsView HistoryView SpreadsView; do
    [ -f "$f.tsx" ] || echo "MISSING $f.tsx"; done; cd -
  ```

- [x] **C4. Nothing in features sends a command itself.** `grep -rn "submitCommand\|confirmCommand" web/features`
  prints nothing.
- [x] **C5. The protected files are untouched.** This prints nothing:

  ```bash
  git diff --stat main -- web/components/options/DecideControls.tsx web/components/options/ConfirmAction.tsx \
    web/components/options/CommandReceipt.tsx web/components/options/HaltControl.tsx \
    web/components/options/AutonomyControl.tsx web/components/options/RollModeControl.tsx \
    web/lib/commands.ts web/lib/receipt.ts
  ```

**Section exit:** three more commits; `/trades` is the new page; the legacy page test is gone and
its cases live in `TradesPage.test.tsx`.

---

### Task 8: The Trades page at `/trades`

**Files:**
- Create: `web/lib/useHydrated.ts`
- Modify: `web/features/home/HomePage.tsx` (imports `useHydrated` instead of defining it)
- Create: `web/features/trades/TradesPage.tsx`, `web/features/trades/TradesPage.test.tsx`
- Modify: `web/app/trades/page.tsx` (whole file)
- Delete: `web/app/trades/page.test.tsx`, `web/components/options/TickerPillBar.tsx`,
  `web/components/options/TickerPillBar.test.tsx`

**Interfaces:**
- Consumes: everything Tasks 3–7 produced (`useTradesView(strategy, pending)`, `useTradesDay()`,
  `useSubmittedApprovals()`, `ProposalsView`, `HistoryView`, `useInFlightCount`, `SpreadsView`,
  `todayInNewYork`); `useStrategyFilter()`, `useControls()`, `DrainWarning({ lastSeen })`,
  `AssessedBrowser({ strategy })`, `usePendingApprovals`.
- Produces: `useHydrated(): boolean` (`lib/useHydrated.ts`); `TradesPage()`; the `/trades` route.

- [x] **Step 1: Load da-vinci** if it is not already loaded. Brief: the page's first viewport per
  the Trades contract written in Task 3; the strategy switcher on its white track, the view chips
  below it as filter chips, never two controls with the same look stacked.

- [x] **Step 2: Move `useHydrated` to `web/lib/useHydrated.ts`**

```ts
import { useSyncExternalStore } from "react";

const noSubscribe = () => () => {};

/**
 * False for the server render and for the hydration pass, true from then on. A page inside a
 * Suspense boundary (useSearchParams) hydrates after the rail; the rail's approvals query shares
 * the page's key and may already have landed, so the page would render from data the server never
 * had and hydration would fail. Rendering the bare page until hydration is over keeps the two
 * passes identical. Home and Trades both need it.
 */
export function useHydrated(): boolean {
  return useSyncExternalStore(
    noSubscribe,
    () => true,
    () => false,
  );
}
```

In `web/features/home/HomePage.tsx` delete the local `noSubscribe` and `useHydrated` (and the
`useSyncExternalStore` import), and add `import { useHydrated } from "@/lib/useHydrated";`.

Run: `cd web && npx vitest run features/home/HomePage.test.tsx`
Expected: PASS (its hydration test included).

- [x] **Step 3: Write the failing page tests** — `web/features/trades/TradesPage.test.tsx`

```tsx
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { act, fireEvent, render, screen, waitFor, within } from "@testing-library/react";
import { hydrateRoot } from "react-dom/client";
import { renderToString } from "react-dom/server";
import { beforeEach, describe, expect, it, vi } from "vitest";
import { savePersistedCommand, type CommandStatus } from "@/lib/commands";
import { apiFetchMock } from "@/lib/test-query";

const nav = vi.hoisted(() => ({ replace: vi.fn(), params: new URLSearchParams() }));
vi.mock("next/navigation", () => ({
  useRouter: () => ({ replace: nav.replace }),
  useSearchParams: () => nav.params,
  usePathname: () => "/trades",
}));

import { TradesPage } from "./TradesPage";

const aapl = {
  as_of: "", id: 1, candidate_id: "c1", status: "pending", underlying: "AAPL",
  strategy: "cash_secured_put", right: "P", strike: 180, expiry: "2099-11-21", contracts: 1,
  premium: 2.35, blended_score: 0.7, created_at: "2026-10-13T13:00:00Z", expires_at: null,
  decided_at: null, order_state: null, source: "scan", review: null, rationale_tags: [],
};

const pendingCommand = {
  id: 7, kind: "approve", status: "pending", result: null, needs_confirmation: false,
  confirm_token: null, created_at: "", applied_at: null, as_of: "",
};

function serve(world: { drainHealthy?: boolean; pending?: unknown[] } = {}) {
  apiFetchMock.mockImplementation(async (path: string) => {
    if (path === "/options/approvals?status=pending") return { as_of: "", approvals: world.pending ?? [aapl] };
    if (path.startsWith("/options/approvals?status=all")) return { as_of: "", approvals: [] };
    if (path === "/options/approvals/1") return aapl;
    if (path === "/options/controls") {
      return {
        as_of: "", autonomy: { level: "full", label: "Full" }, rungs: [], halted: false,
        halt_reason: null, halted_at: null, mode: "paper", drain_healthy: world.drainHealthy ?? true,
        drain_last_seen: null, pending_commands: 0,
      };
    }
    if (path.startsWith("/options/orders")) return { as_of: "", orders: [] };
    if (path.startsWith("/options/assessed")) return { as_of: "", run_id: "r1", computed_at: null, groups: [] };
    if (path.startsWith("/pnl/day")) {
      return {
        as_of: "", date: "2026-10-15", book: "paper", strategy: "all", trades: [], spreads_available: true,
        previous_day: null, next_day: null,
      };
    }
    if (path.startsWith("/spreads/picks")) {
      return {
        as_of: "", available: true, underlying: "SPY", mode: "paper", ai_enabled: true, day: "2026-10-15",
        previous_day: null, next_day: null, picks: [], positions: [],
      };
    }
    if (path === "/commands" || path.startsWith("/commands/")) return { ...pendingCommand, created: true };
    throw new Error(`no mocked response for ${path}`);
  });
}

const tree = (qc: QueryClient) => (
  <QueryClientProvider client={qc}>
    <TradesPage />
  </QueryClientProvider>
);

function mount() {
  const qc = new QueryClient({ defaultOptions: { queries: { retry: false } } });
  const r = render(tree(qc));
  return { rerenderPage: () => r.rerender(tree(qc)) };
}

const viewNames = (group: HTMLElement) =>
  within(group)
    .getAllByRole("button")
    .map((b) => (b.textContent ?? "").replace(/\s*\d+$/, "").trim());

beforeEach(() => {
  nav.replace.mockReset();
  nav.params = new URLSearchParams();
  localStorage.clear();
  (apiFetchMock as unknown as { mockClear: () => void }).mockClear();
  serve();
});

describe("TradesPage", () => {
  it("names the page, then the strategy switcher, then three views; a waiting proposal opens Proposals", async () => {
    mount();
    expect(await screen.findByRole("heading", { level: 1, name: "Trades" })).toBeInTheDocument();
    expect(screen.getByRole("group", { name: "Strategy" })).toBeInTheDocument();
    const views = await screen.findByRole("group", { name: "View" });
    expect(viewNames(views)).toEqual(["Proposals", "History", "Assessed"]);
    expect(await within(views).findByRole("button", { name: /^Proposals/ })).toHaveAttribute("aria-pressed", "true");
    expect(await screen.findByRole("article", { name: "AAPL · Sell $180 put" })).toBeInTheDocument();
  });

  it("opens History when nothing waits on you", async () => {
    serve({ pending: [] });
    mount();
    const views = await screen.findByRole("group", { name: "View" });
    await waitFor(() => expect(within(views).getByRole("button", { name: /^History/ })).toHaveAttribute("aria-pressed", "true"));
    expect(await screen.findByRole("region", { name: "Traded" })).toBeInTheDocument();
  });

  it("gives Credit spreads one view, Spreads, and no view chips", async () => {
    nav.params = new URLSearchParams("strategy=spread");
    mount();
    expect(await screen.findByText(/No spread was opened on this day/)).toBeInTheDocument();
    expect(screen.queryByRole("group", { name: "View" })).toBeNull();
  });

  it("opens the default for a junk ?view=, and History for a retired one", async () => {
    nav.params = new URLSearchParams("view=foo");
    const { rerenderPage } = mount();
    expect(await screen.findByRole("article", { name: "AAPL · Sell $180 put" })).toBeInTheDocument();
    nav.params = new URLSearchParams("view=decided");
    rerenderPage();
    expect(await screen.findByRole("region", { name: "Traded" })).toBeInTheDocument();
  });

  it("passes ?day= to History", async () => {
    nav.params = new URLSearchParams("view=history&day=2026-10-09");
    mount();
    expect(await screen.findByRole("heading", { name: /Fri, Oct 9/ })).toBeInTheDocument();
    expect(apiFetchMock.mock.calls.some((c) => c[0] === "/pnl/day?date=2026-10-09&strategy=all")).toBe(true);
  });

  it("writes the view into the URL", async () => {
    mount();
    const views = await screen.findByRole("group", { name: "View" });
    fireEvent.click(within(views).getByRole("button", { name: /^History/ }));
    expect(nav.replace).toHaveBeenCalledWith("/trades?view=history", { scroll: false });
  });

  it("approving in the sheet moves the card to History at once, and the page stays on Proposals", async () => {
    const { rerenderPage } = mount();
    const card = await screen.findByRole("article", { name: "AAPL · Sell $180 put" });
    fireEvent.click(within(card).getByRole("button", { name: "Review" }));
    const sheet = screen.getByRole("dialog", { name: "Review trade" });
    fireEvent.click(within(sheet).getByRole("button", { name: "Approve" }));
    const confirm = within(sheet).getByRole("dialog", { name: "Approve this contract" });
    const buttons = confirm.querySelectorAll("button");
    fireEvent.click(buttons[buttons.length - 1]);
    await waitFor(() => expect(screen.queryByRole("article", { name: "AAPL · Sell $180 put" })).toBeNull());
    fireEvent.click(within(sheet).getByRole("button", { name: "Close" }));
    const views = screen.getByRole("group", { name: "View" });
    expect(within(views).getByRole("button", { name: /^Proposals/ })).toHaveAttribute("aria-pressed", "true");
    expect(screen.getByText("Nothing needs you right now.")).toBeInTheDocument();
    await waitFor(() => expect(within(views).getByRole("button", { name: /^History/ }).textContent).toMatch(/1$/));

    nav.params = new URLSearchParams("view=history");
    rerenderPage();
    const flight = await screen.findByRole("region", { name: "In flight" });
    const sent = await within(flight).findByRole("article", { name: "AAPL · Sell $180 put" });
    expect(within(sent).getByTestId("command-receipt")).toBeInTheDocument();
  });

  it("a reload mid-command keeps the card in flight, and so opens History", async () => {
    savePersistedCommand(1, pendingCommand as CommandStatus);
    mount();
    const flight = await screen.findByRole("region", { name: "In flight" });
    const sent = await within(flight).findByRole("article", { name: "AAPL · Sell $180 put" });
    expect(within(sent).getByTestId("command-receipt")).toBeInTheDocument();
  });

  it("warns in words when the trading service is not draining commands", async () => {
    serve({ drainHealthy: false });
    mount();
    expect(await screen.findByTestId("drain-dead-warning")).toBeInTheDocument();
  });

  it("hydrates over the server HTML even when the rail has already filled the shared cache", async () => {
    const html = renderToString(tree(new QueryClient()));
    const container = document.createElement("div");
    container.innerHTML = html;
    document.body.appendChild(container);
    const warm = new QueryClient({ defaultOptions: { queries: { retry: false, staleTime: Infinity } } });
    warm.setQueryData(["options", "approvals", "pending"], { as_of: "", approvals: [aapl] });
    const errors: unknown[] = [];
    await act(async () => {
      hydrateRoot(container, tree(warm), { onRecoverableError: (e) => errors.push(e) });
    });
    expect(errors).toEqual([]);
    container.remove();
  });
});
```

The reload test leans on ruling 2: the persisted command takes AAPL out of the pending count, so
nothing waits on you and the default is History, where the card sits in flight.

- [x] **Step 4: Run them to verify they fail**

Run: `cd web && npx vitest run features/trades/TradesPage.test.tsx`
Expected: FAIL (`./TradesPage` not found).

- [x] **Step 5: Write `web/features/trades/TradesPage.tsx`**

```tsx
"use client";

import { AssessedBrowser } from "@/components/options/AssessedBrowser";
import { DrainWarning } from "@/components/options/ControlsStrip";
import { useControls } from "@/components/shell/BotCard";
import { SegmentedControl } from "@/components/ui/SegmentedControl";
import { usePendingApprovals } from "@/features/home/NeedsYou";
import { STRATEGY_FILTERS, STRATEGY_LABEL, kindOf } from "@/lib/strategy";
import { useHydrated } from "@/lib/useHydrated";
import { useStrategyFilter } from "@/lib/useStrategyFilter";
import { HistoryView, useInFlightCount } from "./HistoryView";
import { ProposalsView } from "./ProposalsView";
import { SpreadsView } from "./SpreadsView";
import { todayInNewYork } from "./time";
import { useSubmittedApprovals } from "./useSubmittedApprovals";
import { useTradesDay, useTradesView } from "./useTradesView";
import { VIEW_LABEL, viewsFor } from "./views";

const SHELL = "mx-auto max-w-[1200px] px-4 py-5 md:px-7 md:py-6";

export function TradesPage() {
  const hydrated = useHydrated();
  const [strategy, setStrategy] = useStrategyFilter();
  const { submitted, markSubmitted, clearSubmitted } = useSubmittedApprovals();
  const all = usePendingApprovals("all");
  const scoped = usePendingApprovals(strategy);
  // What waits on you: pending proposals, less any whose Approve is already in flight.
  const pendingCount = scoped.data ? scoped.visible.filter((a) => !submitted.has(a.id)).length : null;
  const [view, setView] = useTradesView(strategy, pendingCount);
  const [dayParam, setDay] = useTradesDay();
  const inFlight = useInFlightCount(strategy, submitted);
  const controls = useControls();
  const today = todayInNewYork();

  const waiting = all.data ? all.visible.filter((a) => !submitted.has(a.id)) : null;
  const strategyOptions = STRATEGY_FILTERS.map((f) => ({
    value: f,
    label: STRATEGY_LABEL[f],
    count:
      waiting === null || f === "all" || f === "spread"
        ? null
        : waiting.filter((a) => kindOf(a.strategy, a.right) === f).length || null,
  }));
  const views = viewsFor(strategy);
  const viewOptions = views.map((v) => ({
    value: v,
    label: VIEW_LABEL[v],
    count: v === "proposals" ? pendingCount : v === "history" ? inFlight || null : null,
  }));

  const heading = <h1 className="text-2xl font-extrabold tracking-[-0.015em]">Trades</h1>;
  if (!hydrated) return <div className={SHELL}>{heading}</div>;

  return (
    <div className={SHELL}>
      {heading}
      <SegmentedControl label="Strategy" options={strategyOptions} value={strategy} onChange={setStrategy} className="mt-4" />
      {views.length > 1 && view !== null && (
        <div className="mt-4">
          <SegmentedControl label="View" appearance="chips" options={viewOptions} value={view} onChange={setView} />
        </div>
      )}
      {controls.data && !controls.data.drain_healthy && view !== "spreads" && (
        <div className="mt-4">
          <DrainWarning lastSeen={controls.data.drain_last_seen} />
        </div>
      )}
      <div className="mt-5">
        {view === null && (
          <div className="h-40 rounded-[18px] bg-surface" role="status" aria-busy="true" aria-label="Loading trades" />
        )}
        {view === "proposals" && (
          <ProposalsView strategy={strategy} submitted={submitted} onSubmitted={markSubmitted} onSettled={clearSubmitted} />
        )}
        {view === "history" && (
          <HistoryView
            strategy={strategy}
            day={dayParam ?? today}
            today={today}
            onDay={setDay}
            submitted={submitted}
            onSettled={clearSubmitted}
          />
        )}
        {view === "assessed" && <AssessedBrowser strategy={strategy} />}
        {view === "spreads" && <SpreadsView />}
      </div>
    </div>
  );
}
```

- [x] **Step 6: Mount it** — replace `web/app/trades/page.tsx` with:

```tsx
import { Suspense } from "react";
import { TradesPage } from "@/features/trades/TradesPage";

// useSearchParams (the strategy switcher, the view and the day) needs a Suspense boundary under the App Router.
export default function Page() {
  return (
    <Suspense>
      <TradesPage />
    </Suspense>
  );
}
```

- [x] **Step 7: Delete what the new page replaced**

```bash
git rm web/app/trades/page.test.tsx web/components/options/TickerPillBar.tsx web/components/options/TickerPillBar.test.tsx
grep -rn "TickerPillBar\|app/trades/page.test" web/app web/components web/features web/lib --include='*.ts' --include='*.tsx'
```

Expected: the grep prints nothing. The legacy page test's cases now live in
`TradesPage.test.tsx` and the views' own tests: Decided → History's "Not traded" (Task 5); the
ticker pills → Task 3's "filters by ticker and clears back to all"; Submitted → "approving in the
sheet moves the card to History at once" and Task 5's "a failed command hands the card back";
reload persistence → "a reload mid-command keeps the card in flight". `OrdersTable` and
`FillsTable` keep their own tests, unmounted until Part 3.

- [x] **Step 8: Run the tests and the gate**

Run: `cd web && npx vitest run && npx tsc --noEmit && npm run lint && python3 ~/.claude/skills/da-vinci/scripts/lint.py features/trades`
Expected: the whole suite PASSES (TradesPage 10 new; the deleted page and pill-bar tests gone);
tsc 0; lint clean; da-vinci lint exit 0.

- [x] **Step 9: Commit** (with the Progress log rows for Task 7 and the C entry checks filled in)

```bash
git add web/lib/useHydrated.ts web/features/home/HomePage.tsx web/features/trades/TradesPage.tsx \
  web/features/trades/TradesPage.test.tsx web/app/trades/page.tsx docs/superpowers/plans/2026-10-19-web-overhaul-2-trades.md
git commit -m "feat(web): /trades - strategy switcher, Proposals / History / Assessed or Spreads, the smart default"
```

---

### Task 9: The approval detail page on the payslip

**Files:**
- Modify (whole file): `web/components/options/ApprovalDetail.tsx`, `web/components/options/ReviewPanel.tsx`,
  `web/components/options/IdealZoneBar.tsx`, `web/components/options/AlternativesTable.tsx`
- Modify: `web/components/options/RationaleTags.tsx` (two class strings)
- Modify: `web/app/trades/[approvalId]/page.tsx` (whole file)
- Modify: `web/components/options/ApprovalDetail.test.tsx` (one assertion, +6 tests)
- Create: `web/components/options/IdealZoneBar.test.tsx`

**Interfaces:**
- Consumes: `proposalTitle` (`features/home/ProposalCard`, roll-aware since Task 4),
  `proposalSentence`, `proposalStub`, `rollSentence`, `rollStub`, `decisionWords`
  (`features/home/proposal`, Task 4); `decided_by`, `roll_from`, `fill_price` (Task 2); `Card`,
  `Stub`, `StatusWord`, `DecideControls` (unchanged).
- Produces: `BackToTrades()`, `ApprovalDetailCard({ detail })` (same name and prop),
  `hasReviewContent(review): boolean` (ReviewPanel.tsx),
  `IdealZoneBar({ ideal, premium, strike })` (gains `strike`), `zoneWords(strike, lo, hi): string | null`,
  `creditWords(premium, minCredit): string | null`.

**A correction this task makes (ruling):** the legacy `IdealZoneBar` drew `lo`/`hi` (a strike
band, in share price) and `min_credit` and `premium` (per-share option prices) on one axis, so
the premium marker sat at a meaningless point. The restyle shows the two as what they are: the
strike against the strike zone, and the premium against the least credit worth taking.

- [ ] **Step 1: Load da-vinci** if it is not already loaded. Brief: the Position page's anatomy
  (back link, the contract as a title with a status word, content left and a 340px column
  right); the decision lives in the right column on desktop and directly after the trade and
  Claude's review on a phone; the protected decide controls keep their recorded look.

- [ ] **Step 2: Write the failing tests**

In `web/components/options/ApprovalDetail.test.tsx`, replace the body of
`it("renders a not-found state with a link back to the list", ...)` with:

```tsx
    withClient(<ApprovalDetailCard detail={base} />);
    expect(screen.getByRole("link", { name: "Back to Trades" })).toHaveAttribute("href", "/trades");
```

and append inside its `describe`:

```tsx
  it("titles the page with the contract and its status in words", () => {
    withClient(<ApprovalDetailCard detail={base} />);
    expect(screen.getByRole("heading", { level: 1, name: "NVDA · Sell $190 put" })).toBeDefined();
    expect(screen.getByText("Pending")).toBeDefined();
  });

  it("sums the trade in a stub and labels the review as Claude's", () => {
    withClient(<ApprovalDetailCard detail={base} />);
    expect(screen.getByRole("group", { name: "NVDA put math" })).toBeDefined();
    expect(screen.getByRole("heading", { name: "Claude's review" })).toBeDefined();
  });

  it("says who decided it, from the record, and what it filled at", () => {
    withClient(
      <ApprovalDetailCard
        detail={{ ...base, status: "approved", decided_at: "2026-10-16T19:03:40Z", decided_by: "system", order_state: "filled", fill_price: 3.2 }}
      />,
    );
    expect(screen.getByText("Approved by the system")).toBeDefined();
    expect(screen.getByText("Filled at")).toBeDefined();
    expect(screen.getByText("$3.20")).toBeDefined();
  });

  it("says only Approved when who decided was not recorded", () => {
    withClient(<ApprovalDetailCard detail={{ ...base, status: "approved", decided_at: "2026-10-01T15:00:00Z" }} />);
    expect(screen.getByText("Approved")).toBeDefined();
    expect(screen.queryByText(/by the system|by you/)).toBeNull();
  });

  it("a roll shows both legs and the net it was priced at", () => {
    const roll = {
      ...base,
      source: "roll" as const,
      strategy: "roll",
      strike: 190,
      expiry: "2026-10-30",
      premium: 1.175,
      roll_from: { strike: 190, expiry: "2026-10-23", right: "P", contracts: 1, old_mid: 2.1, new_mid: 3.275 },
    };
    withClient(<ApprovalDetailCard detail={roll} />);
    expect(screen.getByRole("heading", { level: 1, name: "NVDA · Roll $190 put Oct 23 → Oct 30" })).toBeDefined();
    const stub = screen.getByRole("group", { name: "NVDA roll math" });
    expect(stub.textContent).toMatch(/Buy back \$190 put Oct 23/);
    expect(stub.textContent).toMatch(/Net credit/);
    expect(screen.getByText(/At the quotes it was priced at/)).toBeDefined();
  });

  it("puts the decision after the trade and the review, the phone's order", () => {
    withClient(<ApprovalDetailCard detail={base} />);
    const trade = screen.getByRole("heading", { name: "The trade" });
    const review = screen.getByRole("heading", { name: "Claude's review" });
    const decision = screen.getByRole("heading", { name: "Decision" });
    const follows = (a: Element, b: Element) => (a.compareDocumentPosition(b) & Node.DOCUMENT_POSITION_FOLLOWING) !== 0;
    expect(follows(trade, review)).toBe(true);
    expect(follows(review, decision)).toBe(true);
  });
```

`web/components/options/IdealZoneBar.test.tsx`:

```tsx
import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";
import { IdealZoneBar, creditWords, zoneWords } from "./IdealZoneBar";

describe("zoneWords and creditWords", () => {
  it("places the strike against the zone in words", () => {
    expect(zoneWords(190, 185, 192)).toBe("inside the zone");
    expect(zoneWords(180, 185, 192)).toBe("below the zone");
    expect(zoneWords(195, 185, 192)).toBe("above the zone");
    expect(zoneWords(190, null, 192)).toBeNull();
  });
  it("places the premium against the least credit worth taking", () => {
    expect(creditWords(3.25, 3.1)).toBe("above it");
    expect(creditWords(3.0, 3.1)).toBe("below it");
    expect(creditWords(3.1, 3.1)).toBe("exactly at it");
    expect(creditWords(null, 3.1)).toBeNull();
  });
});

describe("IdealZoneBar", () => {
  it("shows the strike zone and the credit floor as separate lines, never on one axis", () => {
    render(<IdealZoneBar ideal={{ lo: 185, hi: 192, min_credit: 3.1 }} premium={3.25} strike={190} />);
    expect(screen.getByText("$185.00")).toBeDefined();
    expect(screen.getByText("$192.00")).toBeDefined();
    expect(screen.getByText(/inside the zone/)).toBeDefined();
    expect(screen.getByText("$3.10")).toBeDefined();
    expect(screen.getByText(/above it/)).toBeDefined();
  });
  it("renders an unknown floor as n/a with the hatch", () => {
    render(<IdealZoneBar ideal={{ lo: 185, hi: 192, min_credit: null }} premium={3.25} strike={190} />);
    const na = screen.getByText("n/a");
    expect(na.className).toContain("hatch");
  });
  it("says when no zone was derived", () => {
    render(<IdealZoneBar ideal={{ lo: null, hi: null, min_credit: null }} premium={3.25} strike={190} />);
    expect(screen.getByText("No ideal zone derived.")).toBeDefined();
  });
});
```

- [ ] **Step 3: Run them to verify they fail**

Run: `cd web && npx vitest run components/options/ApprovalDetail.test.tsx components/options/IdealZoneBar.test.tsx`
Expected: FAIL (no "Back to Trades" link, no level-1 title, no `zoneWords`).

- [ ] **Step 4: Rewrite `web/components/options/IdealZoneBar.tsx`**

```tsx
import clsx from "clsx";
import { UNKNOWN } from "@/lib/format";
import type { IdealZonePayload } from "./types";

// Two questions, two lines: is the strike where it ought to be (a share price against the strike
// zone), and does the premium clear the least credit worth taking (an option price against the
// floor)? They are different units, so they never share an axis.

export function zoneWords(strike: number | null, lo: number | null, hi: number | null): string | null {
  if (strike == null || lo == null || hi == null) return null;
  if (strike < Math.min(lo, hi)) return "below the zone";
  if (strike > Math.max(lo, hi)) return "above the zone";
  return "inside the zone";
}

export function creditWords(premium: number | null, minCredit: number | null): string | null {
  if (premium == null || minCredit == null) return null;
  if (Math.abs(premium - minCredit) < 0.005) return "exactly at it";
  return premium > minCredit ? "above it" : "below it";
}

function Figure({ value }: { value: number | null }) {
  if (value == null) return <span className="hatch font-mono text-unknown">{UNKNOWN}</span>;
  return <span className="tabular font-mono">${value.toFixed(2)}</span>;
}

function StrikeBand({ lo, hi, strike }: { lo: number; hi: number; strike: number }) {
  const min = Math.min(lo, hi, strike);
  const max = Math.max(lo, hi, strike);
  const range = max - min || 1;
  // 5% to 95%, so a marker at either end stays inside the track.
  const pct = (v: number) => 5 + ((v - min) / range) * 90;
  return (
    <div aria-hidden="true" className="relative mt-2 h-2.5 rounded-full bg-sunk">
      <div
        className="absolute top-0 h-full rounded-full bg-sunk-deep"
        style={{ left: `${pct(Math.min(lo, hi))}%`, width: `${Math.abs(pct(hi) - pct(lo))}%` }}
      />
      <div className="absolute -top-1 h-[18px] w-0.5 -translate-x-1/2 rounded-full bg-content" style={{ left: `${pct(strike)}%` }} />
    </div>
  );
}

export function IdealZoneBar({
  ideal,
  premium,
  strike,
}: {
  ideal: IdealZonePayload;
  premium: number | null;
  strike: number | null;
}) {
  const { lo, hi, min_credit: minCredit } = ideal;
  if (lo == null && hi == null && minCredit == null) {
    return <p className="text-sm text-muted">No ideal zone derived.</p>;
  }
  const zone = zoneWords(strike, lo, hi);
  const credit = creditWords(premium, minCredit);
  return (
    <div className="grid gap-4 text-sm">
      <div>
        <p>
          Strike zone <Figure value={lo} /> to <Figure value={hi} />
          {strike != null && (
            <>
              {" · this strike "}
              <Figure value={strike} />
              {zone && <span className="text-muted">, {zone}</span>}
            </>
          )}
        </p>
        {lo != null && hi != null && strike != null && <StrikeBand lo={lo} hi={hi} strike={strike} />}
      </div>
      <p>
        Least credit worth taking <Figure value={minCredit} /> a share
        {premium != null && (
          <>
            {" · this one pays "}
            <Figure value={premium} />
            {credit && <span className={clsx("text-muted")}>, {credit}</span>}
          </>
        )}
      </p>
    </div>
  );
}
```

The bar is `aria-hidden`: the sentence above it says the same thing in words.

- [ ] **Step 5: Rewrite `web/components/options/ReviewPanel.tsx`**

```tsx
import type { ClaudeReviewPayload } from "./types";

// The five review fields render as five labelled entries, never one paragraph, so the bull case,
// the risk case and the mechanical notes read as distinct ideas. A null review, or one with every
// field empty, renders nothing at all. The plain-English `summary` leads, as the verdict, and the
// `evidence` ids it cites follow.

type Section = { label: string; tag: string; text: string };

function sectionsOf(review: ClaudeReviewPayload): Section[] {
  return [
    { label: "Why attractive", tag: "Bull case", text: review.why_attractive },
    { label: "Risks", tag: "Bear case", text: review.risks },
    { label: "Tradeoffs", tag: "Balance", text: review.tradeoffs },
    { label: "Assignment considerations", tag: "Watch for", text: review.assignment_considerations },
    { label: "Rolling considerations", tag: "If challenged", text: review.rolling_considerations },
  ].filter((s) => s.text);
}

/** Whether ReviewPanel would render anything, so a caller can leave out the card around it. */
export function hasReviewContent(review: ClaudeReviewPayload | null): boolean {
  return review !== null && (sectionsOf(review).length > 0 || Boolean(review.summary));
}

export function ReviewPanel({ review }: { review: ClaudeReviewPayload | null }) {
  if (!review || !hasReviewContent(review)) return null;
  const present = sectionsOf(review);
  const summary = review.summary ?? "";
  const evidence = review.evidence ?? [];
  return (
    <div className="space-y-3">
      {summary && (
        <div className="rounded-xl bg-sunk px-3 py-2.5">
          <p className="text-xs font-semibold tracking-[0.04em] text-muted">
            {review.recommendation ? `Verdict: ${review.recommendation}` : "Verdict"}
          </p>
          <p className="mt-0.5 text-sm font-bold">Summary</p>
          <p className="mt-1 text-sm">{summary}</p>
        </div>
      )}
      {present.length > 0 && (
        <dl className="grid gap-x-6 sm:grid-cols-2">
          {present.map((s) => (
            <div key={s.label} className="border-t border-border py-2.5">
              <dt>
                <span className="block text-xs font-semibold tracking-[0.04em] text-muted">{s.tag}</span>
                <span className="text-sm font-bold">{s.label}</span>
              </dt>
              <dd className="mt-1 text-sm">{s.text}</dd>
            </div>
          ))}
        </dl>
      )}
      {evidence.length > 0 && <EvidenceList ids={evidence} />}
    </div>
  );
}

// The ids the verdict cites. The FACTS and NEWS blocks they point into live only in that scan's
// prompt, not in the stored review, so each id is shown with what kind of source it is rather
// than pretending to link to text the console does not have.
function EvidenceList({ ids }: { ids: string[] }) {
  return (
    <div className="text-xs text-muted">
      <span>Cited: </span>
      <ul className="inline-flex flex-wrap gap-2 align-middle">
        {ids.map((id) => (
          <li key={id} className="rounded-[6px] bg-sunk px-1.5 py-0.5">
            <span className="font-mono text-content">{id}</span> <span>{evidenceKind(id)}</span>
          </li>
        ))}
      </ul>
    </div>
  );
}

export function evidenceKind(id: string): string {
  if (/^F\d+$/.test(id)) return "computed fact";
  if (/^N\d+$/.test(id)) return "news headline";
  return "source";
}
```

Run: `cd web && npx vitest run components/options/ReviewPanel.test.tsx`
Expected: PASS unchanged (it asserts labels, tags, texts, the verdict and the evidence words, all
kept). If `components/explain/FactCard` is now imported by nothing, leave it: the explain pages
use it.

- [ ] **Step 6: Rewrite `web/components/options/AlternativesTable.tsx`**

```tsx
import { UNKNOWN } from "@/lib/format";
import { StageBadge } from "./StageBadge";
import type { AlternativeStrike } from "./types";

const money = (v: number | null) =>
  v == null ? <span className="hatch text-unknown">{UNKNOWN}</span> : <span>${v.toFixed(2)}</span>;

export function AlternativesTable({ alternatives }: { alternatives: AlternativeStrike[] }) {
  if (alternatives.length === 0) return null;
  return (
    <div>
      <h2 className="text-[1.0625rem] font-bold">Other contracts assessed on this run</h2>
      <ul className="mt-1">
        {alternatives.map((a) => (
          <li key={a.candidate_id} className="flex items-center justify-between gap-3 border-t border-border py-2.5 text-sm first:border-t-0">
            <p className="flex flex-wrap items-center gap-x-2 gap-y-1">
              <span className="font-bold">${a.strike}</span>
              {a.expiry && <span className="text-muted">{a.expiry}</span>}
              {a.stage && <StageBadge stage={a.stage as never} />}
            </p>
            <p className="tabular text-right font-mono text-[0.8125rem]">
              <span className="text-muted">score </span>
              {a.blended_score != null ? a.blended_score.toFixed(1) : <span className="hatch text-unknown">{UNKNOWN}</span>}
              <span className="text-muted"> · premium </span>
              {money(a.premium)}
            </p>
          </li>
        ))}
      </ul>
    </div>
  );
}
```

- [ ] **Step 7: Restyle `RationaleTags`** — in `web/components/options/RationaleTags.tsx` change
  the two `className` strings on the `<li>` to:

```tsx
              unknown
                ? "hatch rounded-[6px] px-2 py-px text-xs font-semibold text-unknown"
                : "rounded-[6px] bg-sunk px-2 py-px text-xs font-semibold text-muted"
```

- [ ] **Step 8: Rewrite `web/components/options/ApprovalDetail.tsx`**

```tsx
"use client";

import Link from "next/link";
import { useQuery } from "@tanstack/react-query";
import { ChevronLeft } from "lucide-react";
import type { ReactNode } from "react";
import { Card } from "@/components/ui/Card";
import { StatusWord } from "@/components/ui/StatusWord";
import { Stub } from "@/components/ui/Stub";
import { proposalTitle } from "@/features/home/ProposalCard";
import { decisionWords, proposalSentence, proposalStub, rollSentence, rollStub } from "@/features/home/proposal";
import { apiFetch } from "@/lib/api";
import { UNKNOWN, formatDateTime, relativeAge } from "@/lib/format";
import { STRATEGY_EYEBROW, kindOf } from "@/lib/strategy";
import { AlternativesTable } from "./AlternativesTable";
import { DecideControls } from "./DecideControls";
import { IdealZoneBar } from "./IdealZoneBar";
import { RationaleTags } from "./RationaleTags";
import { ReviewPanel, hasReviewContent } from "./ReviewPanel";
import type { ApprovalDetail, ControlsResponse } from "./types";

const STATUS_WORD: Record<string, string> = {
  pending: "Pending",
  approved: "Approved",
  rejected: "Rejected",
  expired: "Expired",
};

export function BackToTrades() {
  return (
    <Link
      href="/trades"
      aria-label="Back to Trades"
      className="inline-flex min-h-11 items-center gap-1 text-[0.8125rem] font-semibold text-muted hover:text-content md:min-h-8"
    >
      <ChevronLeft size={16} aria-hidden="true" />
      Trades
    </Link>
  );
}

function Fact({ label, children }: { label: string; children: ReactNode }) {
  return (
    <div className="flex items-baseline justify-between gap-3 border-t border-border py-2 text-sm first:border-t-0">
      <dt className="text-muted">{label}</dt>
      <dd className="tabular text-right font-semibold">{children}</dd>
    </div>
  );
}

const Unknown = () => <span className="hatch text-unknown">{UNKNOWN}</span>;

const LEFT = "min-w-0 lg:col-start-1";

export function ApprovalDetailCard({ detail }: { detail: ApprovalDetail }) {
  // The drain's health drives the receipt's `stalled` state (spec §9.2 rule 3). `true` while the
  // query loads, so a not-yet-known drain is never falsely reported as dead.
  const controls = useQuery({
    queryKey: ["options", "controls"],
    queryFn: () => apiFetch<ControlsResponse>("/options/controls"),
    placeholderData: (prev) => prev,
    refetchInterval: 30_000,
  });
  const drainHealthy = controls.data?.drain_healthy ?? true;
  const kind = kindOf(detail.strategy, detail.right);
  const isRoll = detail.source === "roll";
  const eyebrow = isRoll ? "Roll" : kind ? STRATEGY_EYEBROW[kind] : detail.strategy;
  const decision = decisionWords(detail.status, detail.decided_by ?? null);
  const roll = isRoll ? rollStub(detail) : [];

  return (
    <div className="space-y-4">
      <BackToTrades />
      <header>
        <p className="text-xs font-bold uppercase tracking-[0.04em] text-muted">
          {eyebrow} · raised {formatDateTime(detail.created_at)}
        </p>
        <h1 className="mt-1 text-2xl font-extrabold tracking-[-0.015em]">{proposalTitle(detail)}</h1>
        <p className="mt-1 flex flex-wrap items-center gap-x-2.5 gap-y-1 text-sm text-muted">
          <StatusWord>{STATUS_WORD[detail.status] ?? detail.status}</StatusWord>
          {decision && decision !== STATUS_WORD[detail.status] && <span>{decision}</span>}
          <span>{isRoll ? "A roll of a position you hold" : "From the scan"}</span>
          {detail.order_state && <span>order {detail.order_state}</span>}
        </p>
      </header>

      {/* One grid placed by CSS: the DOM order is the phone's (trade, review, decision, the rest);
          from 1024px the decision takes a 340px column on the right beside everything else. */}
      <div className="grid items-start gap-x-6 gap-y-4 lg:grid-cols-[minmax(0,1fr)_340px]">
        <Card as="section" aria-labelledby="trade-title" className={LEFT}>
          <h2 id="trade-title" className="text-[1.0625rem] font-bold">
            The trade
          </h2>
          <p className="mt-1 text-sm">{isRoll ? rollSentence(detail) : proposalSentence(detail)}</p>
          {!isRoll && (
            <Stub label={`${detail.underlying} ${detail.right === "C" ? "call" : "put"} math`} lines={proposalStub(detail, new Date())} />
          )}
          {roll.length > 0 && <Stub label={`${detail.underlying} roll math`} lines={roll} />}
          <dl className="mt-3">
            <Fact label="Contracts">{detail.contracts}</Fact>
            <Fact label={isRoll ? "Net a share, as priced" : "Premium a share"}>
              {detail.premium != null ? `$${detail.premium.toFixed(2)}` : <Unknown />}
            </Fact>
            {detail.order_state === "filled" || detail.order_state === "partial" ? (
              <Fact label="Filled at">{detail.fill_price != null ? `$${detail.fill_price.toFixed(2)}` : <Unknown />}</Fact>
            ) : null}
            <Fact label="Score">{detail.blended_score != null ? detail.blended_score.toFixed(1) : <Unknown />}</Fact>
            <Fact label="Expiry">{detail.expiry ?? <Unknown />}</Fact>
          </dl>
          <div className="mt-3">
            <RationaleTags tags={detail.rationale_tags} />
          </div>
        </Card>

        {hasReviewContent(detail.review) && (
          <Card as="section" aria-labelledby="review-title" className={LEFT}>
            <h2 id="review-title" className="text-[1.0625rem] font-bold">
              Claude&apos;s review
            </h2>
            <p className="mb-3 text-[0.8125rem] text-muted">Claude&apos;s view of this proposal. It decides nothing.</p>
            <ReviewPanel review={detail.review} />
          </Card>
        )}

        <Card as="section" aria-labelledby="decision-title" className="lg:sticky lg:top-4 lg:col-start-2 lg:row-span-6 lg:row-start-1">
          <h2 id="decision-title" className="text-[1.0625rem] font-bold">
            Decision
          </h2>
          <div className="mt-3">
            <DecideControls approval={detail} drainHealthy={drainHealthy} />
          </div>
        </Card>

        {detail.ideal && (
          <Card as="section" aria-labelledby="ideal-title" className={LEFT}>
            <h2 id="ideal-title" className="text-[1.0625rem] font-bold">
              Ideal zone
            </h2>
            <div className="mt-2">
              <IdealZoneBar ideal={detail.ideal} premium={detail.premium} strike={detail.strike} />
            </div>
          </Card>
        )}

        {detail.gate_reasons.length > 0 && (
          <Card as="section" aria-labelledby="gate-title" className={LEFT}>
            <h2 id="gate-title" className="text-[1.0625rem] font-bold">
              Gate reasons
            </h2>
            <ul className="mt-1 list-disc space-y-1 pl-[18px] text-sm">
              {detail.gate_reasons.map((r, i) => (
                <li key={i}>{r}</li>
              ))}
            </ul>
          </Card>
        )}

        {detail.alternatives.length > 0 && (
          <Card as="section" className={LEFT} aria-label="Other contracts assessed on this run">
            <AlternativesTable alternatives={detail.alternatives} />
          </Card>
        )}

        {detail.fills.length > 0 && (
          <Card as="section" aria-labelledby="fills-title" className={LEFT}>
            <h2 id="fills-title" className="text-[1.0625rem] font-bold">
              Fills
            </h2>
            <ul className="mt-1">
              {detail.fills.map((f) => (
                <li key={f.id} className="flex items-baseline justify-between gap-3 border-t border-border py-2.5 text-sm first:border-t-0">
                  <p>
                    <span className="font-bold">{f.action}</span> {f.filled_qty.toFixed(0)} at{" "}
                    <span className="tabular font-mono">${f.avg_price.toFixed(2)}</span>
                  </p>
                  <p className="flex-none text-right text-xs text-muted">
                    {relativeAge(f.filled_at)} · {f.is_live ? "live" : "paper"}
                  </p>
                </li>
              ))}
            </ul>
          </Card>
        )}
      </div>
    </div>
  );
}
```

`features/home/proposal.ts`'s `ProposalFields` and `RollFields` need `strike: number`;
`ApprovalDetail` carries a number there, so it type-checks. A roll's stub is its two legs and the
net (Task 4), the same rule Home's card uses; a roll frozen before its legs were recorded has no
stub and says so. The header's status word says Approved, Rejected or Expired; the decision words
beside it add who decided only when that was recorded (so "Approved" never appears twice). Part 4 moves this file into `features/trades/`, which is why it may import from
`features/home` today.

- [ ] **Step 9: Rewrite `web/app/trades/[approvalId]/page.tsx`**

```tsx
"use client";

import { use } from "react";
import { useQuery } from "@tanstack/react-query";
import { ApprovalDetailCard, BackToTrades } from "@/components/options/ApprovalDetail";
import type { ApprovalDetail } from "@/components/options/types";
import { ApiError, apiFetch } from "@/lib/api";

const SHELL = "mx-auto max-w-[1200px] px-4 py-3 md:px-7 md:py-4";

export default function ApprovalDetailPage({ params }: { params: Promise<{ approvalId: string }> }) {
  const { approvalId } = use(params);
  const { data, isLoading, isError, error } = useQuery({
    queryKey: ["options", "approval", approvalId],
    queryFn: () => apiFetch<ApprovalDetail>(`/options/approvals/${approvalId}`),
    // A 404 will not change on a retry; anything else is worth one more try.
    retry: (n, e) => !(e instanceof ApiError && e.status === 404) && n < 1,
  });

  if (isLoading) {
    return (
      <div className={SHELL}>
        <BackToTrades />
        <div role="status" aria-busy="true" aria-label="Loading the proposal">
          <div className="mt-2 h-8 w-64 rounded-xl bg-sunk" />
          <div className="mt-4 h-64 rounded-[18px] bg-surface" />
        </div>
      </div>
    );
  }
  if (isError || !data) {
    const missing = error instanceof ApiError && error.status === 404;
    return (
      <div className={SHELL}>
        <BackToTrades />
        <h1 className="mt-2 text-2xl font-extrabold tracking-[-0.015em]">{missing ? "Not found" : "Not loaded"}</h1>
        <p className="mt-3 text-sm">
          {missing
            ? "This proposal does not exist or has been pruned."
            : "This proposal could not be loaded. Go back and open it again in a moment."}
        </p>
      </div>
    );
  }
  return (
    <div className={SHELL}>
      <ApprovalDetailCard detail={data} />
    </div>
  );
}
```

- [ ] **Step 10: Run the tests to verify they pass, then the gate**

Run: `cd web && npx vitest run components/options && npx tsc --noEmit && npm run lint && python3 ~/.claude/skills/da-vinci/scripts/lint.py components/options/ApprovalDetail.tsx components/options/ReviewPanel.tsx components/options/IdealZoneBar.tsx components/options/AlternativesTable.tsx`
Expected: PASS: every existing `ApprovalDetail`, `ReviewPanel` and `RationaleTags` test, the
replaced back-link assertion, 6 new detail tests and 5 IdealZoneBar tests; tsc 0; lint clean;
da-vinci lint exit 0. The detail tests that drive Approve, the confirm dialog and the stalled
receipt must pass unmodified: they are the decide flow's guarantee on this page.

- [ ] **Step 11: Commit** (with the Progress log row for Task 8 filled in)

```bash
git add web/components/options/ApprovalDetail.tsx web/components/options/ApprovalDetail.test.tsx \
  web/components/options/ReviewPanel.tsx web/components/options/IdealZoneBar.tsx \
  web/components/options/IdealZoneBar.test.tsx web/components/options/AlternativesTable.tsx \
  web/components/options/RationaleTags.tsx "web/app/trades/[approvalId]/page.tsx" \
  docs/superpowers/plans/2026-10-19-web-overhaul-2-trades.md
git commit -m "feat(web): approval detail on the payslip - the trade, Claude's review, the decision beside it"
```

---

### Task 10: Propose a roll moves to the short option's page

**Files:**
- Create: `web/components/options/RollProposal.tsx`
- Modify (whole file): `web/components/options/ShortsRow.tsx`
- Create: `web/features/position/RollCard.tsx`, `web/features/position/RollCard.test.tsx`
- Modify: `web/features/position/PositionPage.tsx`, `web/features/position/PositionPage.test.tsx`
- Modify: `web/features/home/positions.ts`, `web/features/home/PositionsCard.tsx`,
  `web/features/home/PositionsCard.test.tsx`, `web/features/home/HomePage.test.tsx`
- Create: `web/features/home/positions.alert.test.ts`
- Modify: `web/DESIGN.md` (§ Surfaces → Position, one bullet; § Components, the Roll card)

**Interfaces:**
- Consumes: `ShortListResponse` / `RollAlertSummary` (`components/options/types.ts`),
  `submitCommand("roll_request", { position_symbol })` (inside the hook only), `ConfirmAction`,
  `CommandReceipt`, `useControls`, `Button`, `Card`, `StatusWord`, `relativeAge`.
- Produces:
  - `useRollProposal(positionSymbol: string): RollProposal` (the exact state machine `ShortsRow`
    ran: storage key `short:{symbol}`, mount-only restore, persistence mirror, approvals
    invalidation on a terminal command, `inFlight` counting the live step)
  - `RollReceipt({ roll, drainHealthy })`, `RollDialogs({ roll, contract: { underlying, strike, right } })`
  - `RollCard({ underlying, symbol, strike, right })`
  - `buildPositionRows(groups, spreads, todayIso, underlying = "SPY", alerted: ReadonlySet<string> = new Set())`;
    `PositionRow.alert: boolean`

- [ ] **Step 1: Load da-vinci** if it is not already loaded, and write the contract first. In
  `web/DESIGN.md`:
  - Under `### Position`, change the **OWN-WORLD** bullet's last sentence "No lime: nothing on
    this page is an action." to "No lime. Its one action, Propose a roll on a held short option,
    is secondary: it raises a roll for approval and never trades."
  - Under `## Components`, after the **Position row** entry, add:

```markdown
**Roll card** (Position page, a held short option only): "Roll", then each alert the monitor
fired on this contract (the trigger as a flag word, its age, the detail, and Claude's stored
view labelled "Claude's view"), or "No roll alert has fired on this contract."; one sentence
("Proposing a roll prices one now and raises it for your approval. Nothing trades until you
approve it."); then **Propose a roll** (secondary, never lime), which opens the existing
confirmation; the command receipt follows, and "No qualifying roll" is a plain answer, not an
error. Home's position rows carry a flag word **Roll alert** when an alert has fired on that
contract.
```

Run: `python3 ~/.claude/skills/da-vinci/scripts/design_md_check.py web/DESIGN.md` → exit 0.

- [ ] **Step 2: Lift the flow out of `ShortsRow`** — create `web/components/options/RollProposal.tsx`

```tsx
"use client";

import Link from "next/link";
import { useEffect, useState } from "react";
import { useQueryClient } from "@tanstack/react-query";
import { ApiError } from "@/lib/api";
import {
  confirmCommand,
  loadPersistedCommand,
  savePersistedCommand,
  submitCommand,
  useCommandStatus,
  type CommandStatus,
} from "@/lib/commands";
import { CommandReceipt } from "./CommandReceipt";
import { ConfirmAction } from "./ConfirmAction";

/**
 * The roll-proposal flow (P2 M5 Task 5.2), lifted out of ShortsRow unchanged so the Shorts table
 * and the position page's Roll card run one state machine: a `confirming` state gates a
 * ConfirmAction before any request, `roll_request` fires once on confirm, a live-mode response
 * routes through a second LIVE confirmation, and the result is polled until terminal. The
 * in-flight command persists under `short:{position_symbol}` (lib/commands.ts), namespaced so it
 * never collides with an approval id or a `promote:` entry.
 */
export type RollProposal = {
  confirming: boolean;
  openConfirm: () => void;
  cancelConfirm: () => void;
  onConfirm: () => Promise<void>;
  liveStep: CommandStatus | null;
  onLiveConfirm: () => Promise<void>;
  cancelLive: () => void;
  current: CommandStatus | null;
  error: string | null;
  /** True while a request is out, the live confirmation is open, or the command is pending. */
  inFlight: boolean;
  /** The failed command's reason code, when it failed. */
  reason: string | undefined;
  successApprovalId: number | null;
  workingApprovalId: number | null;
};

export function useRollProposal(positionSymbol: string): RollProposal {
  const storageKey = `short:${positionSymbol}`;

  const [confirming, setConfirming] = useState(false);
  const [command, setCommand] = useState<CommandStatus | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [liveStep, setLiveStep] = useState<CommandStatus | null>(null);
  const [submitting, setSubmitting] = useState(false);

  // Restore an in-flight roll proposal (including one awaiting the live second confirmation)
  // after a page reload. Mount-only, so it never clobbers a command this flow is progressing.
  useEffect(() => {
    const persisted = loadPersistedCommand(storageKey);
    if (!persisted) return;
    if (persisted.needs_confirmation) setLiveStep(persisted);
    else setCommand(persisted);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  const qc = useQueryClient();

  // Poll every 2s while pending; stop once terminal (lib/commands.ts).
  const commandQuery = useCommandStatus(command?.id ?? null);
  const current = (commandQuery.data ?? command) as CommandStatus | null;

  // Mirror the in-flight command to localStorage.
  useEffect(() => {
    if (liveStep) {
      savePersistedCommand(storageKey, liveStep);
    } else if (current && current.status === "pending") {
      savePersistedCommand(storageKey, current);
    } else {
      savePersistedCommand(storageKey, null);
    }
  }, [storageKey, liveStep, current]);

  useEffect(() => {
    if (current && current.status !== "pending") {
      // A roll proposal raises an approval: refresh the approvals so the new card appears.
      qc.invalidateQueries({ queryKey: ["options", "approvals"] });
    }
  }, [current, qc]);

  // liveStep counts as in flight too: there is no command id to poll until the live
  // confirmation is released, so `current` alone would leave the button clickable meanwhile.
  const inFlight = submitting || liveStep != null || (current != null && current.status === "pending");

  async function onConfirm() {
    setConfirming(false);
    setError(null);
    setSubmitting(true);
    try {
      const resp = await submitCommand("roll_request", { position_symbol: positionSymbol });
      if (resp.needs_confirmation && resp.confirm_token) setLiveStep(resp);
      else setCommand(resp);
    } catch (e) {
      setError(describeError(e));
    } finally {
      setSubmitting(false);
    }
  }

  async function onLiveConfirm() {
    const cmd = liveStep;
    setLiveStep(null);
    if (cmd === null) return;
    setSubmitting(true);
    try {
      await confirmCommand(cmd.id, cmd.confirm_token ?? "");
      setCommand({ ...cmd, needs_confirmation: false, confirm_token: null });
    } catch (e) {
      setError(describeError(e));
    } finally {
      setSubmitting(false);
    }
  }

  function cancelLive() {
    setCommand(liveStep);
    setLiveStep(null);
  }

  const result = current?.result as
    | { reason?: string; approval_id?: number | null; detail?: { approval_id?: number | null } }
    | null;
  const reason = current?.status === "failed" ? result?.reason : undefined;
  const successApprovalId = current?.status === "applied" ? (result?.approval_id ?? null) : null;
  const workingApprovalId = reason === "roll_already_working" ? (result?.detail?.approval_id ?? null) : null;

  return {
    confirming,
    openConfirm: () => setConfirming(true),
    cancelConfirm: () => setConfirming(false),
    onConfirm,
    liveStep,
    onLiveConfirm,
    cancelLive,
    current,
    error,
    inFlight,
    reason,
    successApprovalId,
    workingApprovalId,
  };
}

/** Whether there is anything for RollReceipt to show. */
export function hasRollReceipt(roll: RollProposal): boolean {
  return roll.current != null || roll.error != null || roll.workingApprovalId != null || roll.successApprovalId != null;
}

/**
 * The roll's receipt. `no_qualifying_roll` is a plain answer, not red failed chrome;
 * `roll_already_working` links to the approval already in flight; success links to the new one.
 */
export function RollReceipt({ roll, drainHealthy }: { roll: RollProposal; drainHealthy: boolean }) {
  if (!hasRollReceipt(roll)) return null;
  const { current, error, reason, workingApprovalId, successApprovalId } = roll;
  return (
    <div className="mt-3">
      {error && (
        <p className="text-[0.8125rem] text-loss" data-testid="command-error" role="alert">
          {error}
        </p>
      )}
      {current && reason === "no_qualifying_roll" ? (
        <div data-testid="command-receipt" data-state="answered" className="mt-2 rounded-xl bg-sunk px-3 py-2.5 text-[0.8125rem]">
          <p className="flex flex-wrap items-baseline gap-x-2">
            <span className="font-semibold">No qualifying roll</span>
            <span className="text-muted">
              No roll on the current chain clears the roll&apos;s own bounds. That is a real answer, not an error.
            </span>
            <span className="ml-auto font-mono text-muted">intent {current.id}</span>
          </p>
        </div>
      ) : current ? (
        <CommandReceipt command={current} order={null} drainHealthy={drainHealthy} />
      ) : null}
      {workingApprovalId != null && (
        <p className="mt-1 text-[0.8125rem]">
          <Link href={`/trades/${workingApprovalId}`} className="font-semibold underline underline-offset-2">
            View the roll already in flight
          </Link>
        </p>
      )}
      {successApprovalId != null && (
        <p className="mt-1 text-[0.8125rem]">
          <Link href={`/trades/${successApprovalId}`} className="font-semibold underline underline-offset-2">
            View approval
          </Link>
        </p>
      )}
    </div>
  );
}

/** The two confirmations: the proposal itself, then (live mode only) the LIVE release. */
export function RollDialogs({
  roll,
  contract,
}: {
  roll: RollProposal;
  contract: { underlying: string; strike: number; right: string };
}) {
  return (
    <>
      {roll.liveStep && (
        <ConfirmAction
          title={`Confirm LIVE ${roll.liveStep.kind}`}
          summary={
            <span>
              This is the second, mandatory confirmation for live trading. The first confirmation queued the intent;
              releasing it now lets the trading service apply it. The execution-time [CONFIRM LIVE] Telegram step
              still fires afterwards.
            </span>
          }
          confirmLabel={`Release ${roll.liveStep.kind} intent`}
          onConfirm={roll.onLiveConfirm}
          onCancel={roll.cancelLive}
        />
      )}
      {roll.confirming && (
        <ConfirmAction
          title="Propose a roll"
          summary={
            <span>
              The system will price a roll for {contract.underlying} {contract.strike.toFixed(2)} {contract.right} and raise
              it as a pending approval. Nothing executes until you approve that proposal. The roll&apos;s own debit and
              delta-reduction bounds decide whether one qualifies.
            </span>
          }
          confirmLabel="Propose a roll"
          onConfirm={roll.onConfirm}
          onCancel={roll.cancelConfirm}
        />
      )}
    </>
  );
}

function describeError(e: unknown): string {
  if (e instanceof ApiError && e.status === 403) {
    return "You do not have permission to do this. Command not created.";
  }
  return "The command could not be created. Nothing was sent.";
}
```

If `ConfirmAction`'s `onConfirm` prop is typed `() => void`, an async function is still
assignable; leave `ConfirmAction` untouched either way (it is protected).

- [ ] **Step 3: Make `ShortsRow` thin** — replace `web/components/options/ShortsRow.tsx` with:

```tsx
"use client";

import { UNKNOWN, relativeAge } from "@/lib/format";
import { RollDialogs, RollReceipt, hasRollReceipt, useRollProposal } from "./RollProposal";
import type { ShortPosition } from "./types";

/**
 * One open short option position's table row. The roll control's flow lives in RollProposal.tsx
 * (shared with the position page's Roll card); this file is only the row. Not mounted since web
 * overhaul Part 2 (the Shorts tab left Trades); kept, with ShortsTable, because
 * ShortsTable.test.tsx is the roll flow's full regression suite until Part 4 ports it.
 *
 * The control is labelled "Propose a roll", not "Roll": the button does not roll the position.
 */
export function ShortsRow({ short, drainHealthy = true }: { short: ShortPosition; drainHealthy?: boolean }) {
  const roll = useRollProposal(short.position_symbol);
  return (
    <>
      <tr key={short.position_symbol}>
        <td className="py-2">
          <div className="font-mono text-xs text-content">
            {short.underlying} {short.strike.toFixed(2)} {short.right}
          </div>
          <div className="text-xs text-muted">{short.position_symbol}</div>
        </td>
        <td className="py-2 tabular text-content">{short.dte != null ? short.dte : UNKNOWN}</td>
        <td className="py-2 tabular text-content">{short.contracts}</td>
        <td className="py-2 tabular">{short.mark != null ? `$${short.mark.toFixed(2)}` : UNKNOWN}</td>
        <td className="py-2 tabular">
          {short.unrealized_pnl != null ? `$${short.unrealized_pnl.toFixed(0)}` : UNKNOWN}
        </td>
        <td className="py-2 tabular text-xs">
          {short.delta != null ? (
            <span className="text-content">
              {short.delta.value != null ? short.delta.value.toFixed(2) : UNKNOWN}
              <span className="ml-1 text-muted">{short.delta.source}</span>
            </span>
          ) : (
            UNKNOWN
          )}
        </td>
        <td className="py-2 text-xs text-muted">
          {short.alerts.length > 0 ? (
            <ul className="space-y-0.5">
              {short.alerts.map((a) => (
                <li key={a.id}>
                  <span className="text-content">{a.trigger_label}</span>
                  <span className="text-muted"> {a.detail}</span>
                  <span className="text-muted"> {relativeAge(a.created_at)} ago</span>
                  {a.claude_recommendation && (
                    <span className="text-muted"> Model opinion (Claude): {a.claude_recommendation}</span>
                  )}
                </li>
              ))}
            </ul>
          ) : null}
        </td>
        <td className="py-2">
          <button
            type="button"
            disabled={roll.inFlight}
            onClick={roll.openConfirm}
            className="rounded-sm border border-border bg-background px-3 py-1.5 text-sm text-content enabled:hover:bg-elevated disabled:cursor-default disabled:opacity-50 focus-visible:ring-focus"
          >
            Propose a roll
          </button>
        </td>
      </tr>
      {hasRollReceipt(roll) && (
        <tr>
          <td colSpan={8} className="pb-3">
            <RollReceipt roll={roll} drainHealthy={drainHealthy} />
          </td>
        </tr>
      )}
      <RollDialogs roll={roll} contract={short} />
    </>
  );
}
```

The row's cells render exactly what the old ones rendered (the alert's `{relativeAge(...)} ago`
included, double "ago" and all: the Shorts table test reads it, and this row is no longer
mounted, so it is left alone); only the flow moved.

Run: `cd web && npx vitest run components/options/ShortsTable.test.tsx`
Expected: PASS with **no change to the test file**. This is the proof the extraction changed no
behaviour; a failure means the hook differs from the old row, so fix the hook.

- [ ] **Step 4: Write the failing Roll card tests** — `web/features/position/RollCard.test.tsx`

```tsx
import { fireEvent, screen, waitFor, within } from "@testing-library/react";
import { beforeEach, describe, expect, it } from "vitest";
import { apiFetchMock, renderWithQuery } from "@/lib/test-query";
import { RollCard } from "./RollCard";

const SYMBOL = "AAPL  261121P00180000";

const controls = {
  as_of: "", autonomy: { level: "approve", label: "Approve each trade" }, rungs: [], halted: false,
  halt_reason: null, halted_at: null, mode: "paper", drain_healthy: true, drain_last_seen: null,
  pending_commands: 0,
};

const shorts = (alerts: unknown[]) => ({
  as_of: "",
  shorts: [
    {
      as_of: "", position_symbol: SYMBOL, underlying: "AAPL", right: "P", strike: 180, expiry: "2026-11-21",
      dte: 33, contracts: 1, avg_cost: 2.35, mark: 0.6, unrealized_pnl: 175, pnl_pct: 74, delta: null,
      assignment_risk: false, alerts,
    },
  ],
});

const alert = {
  id: 1, trigger: "delta_breach", trigger_label: "Delta breach", detail: "Delta reached -0.42.",
  claude_recommendation: "Roll down and out.", created_at: new Date(Date.now() - 3 * 3_600_000 - 60_000).toISOString(),
};

const command = (over: Record<string, unknown> = {}) => ({
  id: 51, kind: "roll_request", status: "pending", result: null, needs_confirmation: false,
  confirm_token: null, created_at: "x", applied_at: null, as_of: "x", created: true, ...over,
});

function writes(): Array<[unknown, unknown]> {
  return apiFetchMock.mock.calls
    .filter((c) => (c[1] as RequestInit | undefined)?.method === "POST")
    .map((c) => [c[0], JSON.parse(String((c[1] as RequestInit).body))]);
}

const card = <RollCard underlying="AAPL" symbol={SYMBOL} strike={180} right="P" />;

function confirmDialog() {
  const dialog = screen.getByRole("dialog");
  const buttons = dialog.querySelectorAll("button");
  fireEvent.click(buttons[buttons.length - 1]);
}

beforeEach(() => {
  (apiFetchMock as unknown as { mockClear: () => void }).mockClear();
  localStorage.clear();
});

describe("RollCard", () => {
  it("lists the alerts fired on this contract, with Claude's view labelled", async () => {
    renderWithQuery(card, { "/options/shorts": shorts([alert]), "/options/controls": controls });
    expect(await screen.findByText("Delta breach")).toBeInTheDocument();
    expect(screen.getByText("Delta reached -0.42.")).toBeInTheDocument();
    expect(screen.getByText("3h ago")).toBeInTheDocument();
    expect(screen.getByText("Claude's view:")).toBeInTheDocument();
    expect(screen.getByText(/Roll down and out\./)).toBeInTheDocument();
  });

  it("says so when no alert has fired", async () => {
    renderWithQuery(card, { "/options/shorts": shorts([]), "/options/controls": controls });
    expect(await screen.findByText("No roll alert has fired on this contract.")).toBeInTheDocument();
  });

  it("is a secondary button, never lime: it proposes, it does not trade", async () => {
    renderWithQuery(card, { "/options/shorts": shorts([]), "/options/controls": controls });
    expect(await screen.findByRole("button", { name: "Propose a roll" })).toHaveAttribute("data-variant", "secondary");
  });

  it("opens the confirmation before any request", async () => {
    renderWithQuery(card, { "/options/shorts": shorts([]), "/options/controls": controls });
    fireEvent.click(await screen.findByRole("button", { name: "Propose a roll" }));
    expect(screen.getByRole("dialog")).toBeInTheDocument();
    expect(writes()).toEqual([]);
  });

  it("sends one roll_request with the contract's symbol on confirm, then shows the receipt", async () => {
    renderWithQuery(card, { "/options/shorts": shorts([]), "/options/controls": controls, "/commands": command() });
    fireEvent.click(await screen.findByRole("button", { name: "Propose a roll" }));
    confirmDialog();
    await waitFor(() => expect(writes()).toEqual([["/commands", { kind: "roll_request", payload: { position_symbol: SYMBOL } }]]));
    expect(await screen.findByTestId("command-receipt")).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Propose a roll" })).toBeDisabled();
  });

  it("answers no_qualifying_roll in plain words, not as an error", async () => {
    renderWithQuery(card, {
      "/options/shorts": shorts([]),
      "/options/controls": controls,
      "/commands": command({ status: "failed", result: { reason: "no_qualifying_roll", detail: {} } }),
    });
    fireEvent.click(await screen.findByRole("button", { name: "Propose a roll" }));
    confirmDialog();
    const receipt = await screen.findByTestId("command-receipt");
    expect(receipt.getAttribute("data-state")).toBe("answered");
    expect(within(receipt).getByText(/real answer, not an error/)).toBeInTheDocument();
  });

  it("says the alerts could not be read, and still offers the roll", async () => {
    renderWithQuery(card, { "/options/controls": controls });
    expect(await screen.findByText("Roll alerts could not be loaded right now.")).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Propose a roll" })).toBeEnabled();
  });
});
```

`renderWithQuery` throws for an unmapped path, which the query reports as an error: that is how
the last test makes `/options/shorts` fail.

- [ ] **Step 5: Run them to verify they fail**

Run: `cd web && npx vitest run features/position/RollCard.test.tsx`
Expected: FAIL (`./RollCard` not found).

- [ ] **Step 6: Write `web/features/position/RollCard.tsx`**

```tsx
"use client";

import { useQuery } from "@tanstack/react-query";
import { RollDialogs, RollReceipt, useRollProposal } from "@/components/options/RollProposal";
import type { ShortListResponse } from "@/components/options/types";
import { useControls } from "@/components/shell/BotCard";
import { Button } from "@/components/ui/Button";
import { Card } from "@/components/ui/Card";
import { StatusWord } from "@/components/ui/StatusWord";
import { apiFetch } from "@/lib/api";
import { relativeAge } from "@/lib/format";

/**
 * Roll a held short option: the alerts the monitor fired on this contract, then Propose a roll,
 * which raises a roll for approval through the same confirm-then-receipt flow the Shorts table
 * ran (useRollProposal). Secondary, not lime: it proposes, it never trades.
 */
export function RollCard({
  underlying,
  symbol,
  strike,
  right,
}: {
  underlying: string;
  /** The OCC symbol: the roll_request payload and the alerts' key. */
  symbol: string;
  strike: number;
  right: "C" | "P";
}) {
  // Same key as the legacy ShortsTable and Home's Roll alert word: one request.
  const shorts = useQuery({
    queryKey: ["options", "shorts"],
    queryFn: () => apiFetch<ShortListResponse>("/options/shorts"),
    refetchInterval: 60_000,
  });
  const controls = useControls();
  const roll = useRollProposal(symbol);
  const alerts = shorts.data?.shorts.find((s) => s.position_symbol === symbol)?.alerts ?? [];

  return (
    <Card as="section" aria-labelledby="roll-title">
      <h2 id="roll-title" className="text-[1.0625rem] font-bold">
        Roll
      </h2>
      {shorts.isError && !shorts.data ? (
        <p className="mt-1 text-[0.8125rem] text-muted">Roll alerts could not be loaded right now.</p>
      ) : !shorts.data ? null : alerts.length === 0 ? (
        <p className="mt-1 text-[0.8125rem] text-muted">No roll alert has fired on this contract.</p>
      ) : (
        <ul className="mt-2 grid gap-3">
          {alerts.map((a) => (
            <li key={a.id} className="text-[0.8125rem]">
              <p className="flex flex-wrap items-center gap-2">
                <StatusWord tone="flag">{a.trigger_label}</StatusWord>
                <span className="text-muted">{relativeAge(a.created_at)}</span>
              </p>
              {a.detail && <p className="mt-1">{a.detail}</p>}
              {a.claude_recommendation && (
                <p className="mt-1 text-muted">
                  <span className="font-semibold">Claude&apos;s view:</span> {a.claude_recommendation}
                </p>
              )}
            </li>
          ))}
        </ul>
      )}
      <p className="mt-3 text-[0.8125rem] text-muted">
        Proposing a roll prices one now and raises it for your approval. Nothing trades until you approve it.
      </p>
      <Button variant="secondary" block className="mt-3" disabled={roll.inFlight} onClick={roll.openConfirm}>
        Propose a roll
      </Button>
      <RollReceipt roll={roll} drainHealthy={controls.data?.drain_healthy ?? true} />
      <RollDialogs roll={roll} contract={{ underlying, strike, right }} />
    </Card>
  );
}
```

Run: `cd web && npx vitest run features/position/RollCard.test.tsx`
Expected: PASS (7 tests).

- [ ] **Step 7: Mount it on the position page**

In `web/features/position/PositionPage.tsx` add `import { RollCard } from "./RollCard";` and, in
the right-hand column directly after the line
`{data.held ? <NowCard d={data} lastClose={lastClose} /> : data.closed && <TradeCard trade={data.closed} when="date" heading="none" />}`,
add:

```tsx
          {/* Only a held short option with a known contract can be rolled. */}
          {data.held && data.option?.short && typeof data.option.strike === "number" && data.option.right && (
            <RollCard
              underlying={data.underlying}
              symbol={data.option.symbol}
              strike={data.option.strike}
              right={data.option.right}
            />
          )}
```

In `web/features/position/PositionPage.test.tsx`, add two entries to the object `serve()`
returns (beside `"/research/AAPL/headlines": headlines,`):

```tsx
  "/options/shorts": { as_of: "", shorts: [] },
  "/options/controls": {
    as_of: "", autonomy: { level: "approve", label: "Approve each trade" }, rungs: [], halted: false,
    halt_reason: null, halted_at: null, mode: "paper", drain_healthy: true, drain_last_seen: null,
    pending_commands: 0,
  },
```

and append inside `describe("PositionPage")`:

```tsx
  it("offers Propose a roll on a held short option", async () => {
    renderWithQuery(<PositionPage underlying="AAPL" slug={SLUG} />, serve());
    expect(await screen.findByRole("button", { name: "Propose a roll" })).toBeInTheDocument();
  });

  it("offers no roll for a long option, a contract no longer held, or one whose strike is unknown", async () => {
    const held = detail();
    const cases = [
      detail({ option: { ...held.option!, short: false } }),
      detail({ held: false, option: null }),
      detail({ option: { ...held.option!, strike: null } }),
    ];
    for (const d of cases) {
      const { unmount } = renderWithQuery(<PositionPage underlying="AAPL" slug={SLUG} />, serve(d));
      await screen.findByRole("heading", { level: 1 });
      expect(screen.queryByRole("button", { name: "Propose a roll" })).toBeNull();
      unmount();
    }
  });
```

If `tsc` rejects `strike: null` because the generated `OptionLeg.strike` is `number | undefined`,
use `strike: undefined` and record it; the page's `typeof ... === "number"` covers both.

Run: `cd web && npx vitest run features/position`
Expected: PASS (every existing PositionPage test plus the two new ones, and RollCard's 7).

- [ ] **Step 8: The Roll alert word on Home's rows**

`web/features/home/positions.alert.test.ts`:

```ts
import { describe, expect, it } from "vitest";
import type { PositionGroupData } from "@/components/portfolio/types";
import { buildPositionRows } from "./positions";

const group = {
  as_of: "",
  underlying: "AAPL",
  stock: null,
  options: [
    {
      as_of: "", symbol: "AAPL  261121P00180000", right: "P", strike: 180, expiry: "2026-11-21", dte: 33,
      contracts: 1, short: true, delta: -0.2, delta_source: "ibkr", market_price: 0.6, market_value: -60,
      unrealized_pnl: 175, moneyness: "otm", assignment_risk: false,
    },
  ],
} as unknown as PositionGroupData;

describe("the Roll alert flag", () => {
  it("is set for a contract whose OCC symbol has an alert", () => {
    const [row] = buildPositionRows([group], [], "2026-10-19", "SPY", new Set(["AAPL  261121P00180000"]));
    expect(row.alert).toBe(true);
  });
  it("is off by default and for any other contract", () => {
    expect(buildPositionRows([group], [], "2026-10-19")[0].alert).toBe(false);
    expect(buildPositionRows([group], [], "2026-10-19", "SPY", new Set(["MSFT  261121C00420000"]))[0].alert).toBe(false);
  });
});
```

In `web/features/home/positions.ts`:
- add `/** A roll alert has fired on this option contract (from GET /options/shorts). */ alert: boolean;`
  to `PositionRow`;
- add a fifth parameter `alerted: ReadonlySet<string> = new Set()` to `buildPositionRows`;
- add `alert: alerted.has(o.symbol),` to the option row object, and `alert: false,` to the
  shares row and to the spread row objects.

In `web/features/home/PositionsCard.tsx`:
- add `import type { ShortListResponse } from "@/components/options/types";`
- after the `spreads` query add:

```tsx
  // Roll alerts the monitor fired (same key as the position page's Roll card). Unreadable means
  // no flag is shown; the rows themselves never depend on it.
  const shorts = useQuery({
    queryKey: ["options", "shorts"],
    queryFn: () => apiFetch<ShortListResponse>("/options/shorts"),
    refetchInterval: 60_000,
  });
  const alerted = new Set((shorts.data?.shorts ?? []).filter((s) => s.alerts.length > 0).map((s) => s.position_symbol));
```

- pass `alerted` as the fifth argument:
  `buildPositionRows(positions.data.groups, spreadRows, todayNewYork(), spreads.data?.underlying, alerted)`.
  `spreads.data?.underlying` may be `undefined`, which falls back to the `"SPY"` default; keep it.
- right after the `{r.status && (...)}` block in the row body, add:

```tsx
                  {r.alert && (
                    <span className="ml-1.5 align-[1px]">
                      <StatusWord tone="flag">Roll alert</StatusWord>
                    </span>
                  )}
```

In `web/features/home/PositionsCard.test.tsx` and `web/features/home/HomePage.test.tsx`, add
`"/options/shorts": { as_of: "", shorts: [] }` beside every `"/portfolio/positions"` response
key, so no test leans on a thrown mock. Then append to `PositionsCard.test.tsx` (inside its
top-level `describe`; reuse the file's existing imports, adding `within` if it is missing):

```tsx
  it("marks a short option the monitor raised a roll alert on, in words", async () => {
    const group = {
      as_of: "", underlying: "AAPL", stock: null,
      options: [{
        as_of: "", symbol: "AAPL  261121P00180000", right: "P", strike: 180, expiry: "2099-11-21", dte: 30,
        contracts: 1, short: true, delta: -0.2, delta_source: "ibkr", market_price: 0.6, market_value: -60,
        unrealized_pnl: 175, moneyness: "otm", assignment_risk: false,
      }],
    };
    renderWithQuery(<PositionsCard strategy="all" />, {
      "/portfolio/positions": { as_of: new Date().toISOString(), source: "monitor", degraded: false, groups: [group] },
      "/spreads/positions": { as_of: "", available: true, underlying: "SPY", mode: "paper", positions: [] },
      "/options/shorts": {
        as_of: "",
        shorts: [{
          position_symbol: "AAPL  261121P00180000",
          alerts: [{ id: 1, trigger: "delta_breach", trigger_label: "Delta breach", detail: "", claude_recommendation: null, created_at: "" }],
        }],
      },
    });
    const row = await screen.findByRole("link", { name: /AAPL \$180 put/ });
    expect(within(row).getByText("Roll alert")).toBeInTheDocument();
  });
```

Run: `cd web && npx vitest run features/home features/position components/options`
Expected: PASS (the new alert tests plus every existing Home, Position and options test).

- [ ] **Step 9: Gate and da-vinci lint**

Run: `cd web && npx vitest run && npx tsc --noEmit && npm run lint && python3 ~/.claude/skills/da-vinci/scripts/lint.py features/position features/home components/options/RollProposal.tsx`
Expected: all green; da-vinci lint exit 0. Also `grep -rn "submitCommand\|confirmCommand" web/features`
prints nothing (the Roll card reaches the command only through `RollProposal.tsx`).

- [ ] **Step 10: Commit** (with the Progress log row for Task 9 filled in)

```bash
git add web/DESIGN.md web/components/options/RollProposal.tsx web/components/options/ShortsRow.tsx \
  web/features/position/RollCard.tsx web/features/position/RollCard.test.tsx \
  web/features/position/PositionPage.tsx web/features/position/PositionPage.test.tsx \
  web/features/home/positions.ts web/features/home/positions.alert.test.ts \
  web/features/home/PositionsCard.tsx web/features/home/PositionsCard.test.tsx \
  web/features/home/HomePage.test.tsx docs/superpowers/plans/2026-10-19-web-overhaul-2-trades.md
git commit -m "feat(web): Propose a roll on the short option's page; a Roll alert word on Home's rows"
```

---
## Section D — Docs and finish (Task 11) · model: sonnet, then an opus whole-branch review

Looks at the result in a browser, runs the da-vinci finish, sweeps the docs and runs every gate.

**Entry checks (run before Task 11):**

- [ ] **D1. Section C landed.** `git log --oneline main..HEAD` shows ten commits (plus any review
  fix passes recorded in the Progress log); Tasks 8–10 are ticked.
- [ ] **D2. Every gate and the build green.** `python -m pytest -q && ruff check . && mypy src`,
  `cd web && npx vitest run && npx tsc --noEmit && npm run lint`, and the scratch-copy build from
  C2.
- [ ] **D3. The safety checks still hold.** C4 and C5 print nothing.
- [ ] **D4. A browser is available for the visual check.** The Claude-in-Chrome or Playwright
  tools load, or the operator agrees to take the screenshots in Step 2 by hand.

**Section exit (plan done):** eleven task commits (plus any review fix passes) and the Progress-log
commit; then the whole-branch review and superpowers:finishing-a-development-branch. No merge or
push without the operator.

---

### Task 11: Docs, the da-vinci finish, the full gate

**Files:**
- Modify: `web/DESIGN.md`, `web/CLAUDE.md`, `ARCHITECTURE.md`, `STATUS.md`, `SETUP.md`,
  `CLAUDE.md` (root), `docs/web/api.md`
- Modify: any file the finish review fixes (each fix with its test when behaviour changes)
- Create (scratch only, never committed): a mock API script in the session's scratchpad

**Interfaces:**
- Consumes: the whole branch.
- Produces: the finished Part 2; the Progress log complete.

- [ ] **Step 1: Run a synthetic API for the visual check.** Never point the console at the live
  API for this. Write this script to the scratchpad (not the repo) and run it in the background:

```python
"""A synthetic API for the Trades visual check (web overhaul Part 2, Task 11). Never the live
one. Serves the paths the shell, Trades, the detail page and a position page read."""

import json
from datetime import UTC, datetime, timedelta
from http.server import BaseHTTPRequestHandler, HTTPServer

now = datetime.now(UTC)
iso = lambda d: d.isoformat().replace("+00:00", "Z")  # noqa: E731

review = {
    "why_attractive": "IV rank 62, premium 18% above fair value.", "risks": "Earnings Oct 30 sits inside the window.",
    "tradeoffs": "", "assignment_considerations": "Owning AAPL at $180 is fine.", "rolling_considerations": "Roll down and out.",
    "summary": "Sell it: the premium is rich for the risk.", "recommendation": "sell", "evidence": ["F3", "N11"],
}

def approval(i, sym, strategy, right, strike, status="pending", **over):
    a = {"as_of": iso(now), "id": i, "candidate_id": f"c{i}", "status": status, "underlying": sym, "strategy": strategy,
         "right": right, "strike": strike, "expiry": "2026-11-20", "contracts": 1, "premium": 2.35, "blended_score": 71.5,
         "created_at": iso(now - timedelta(hours=2)), "expires_at": None, "decided_at": None, "order_state": None,
         "source": "scan", "review": review, "rationale_tags": ["iv_rank_unavailable"]}
    a.update(over)
    return a

LEG = {"strike": 250, "expiry": "2026-10-23", "right": "P", "contracts": 1, "old_mid": 2.1, "new_mid": 3.275}
PENDING = [approval(1, "AAPL", "cash_secured_put", "P", 180), approval(2, "NVDA", "cash_secured_put", "P", 165),
           approval(4, "MSFT", "covered_call", "C", 450),
           approval(6, "AMD", "roll", "P", 250, source="roll", expiry="2026-10-30", premium=1.175, roll_from=LEG)]
DECIDED = [approval(3, "TSLA", "cash_secured_put", "P", 260, "rejected", decided_at=iso(now - timedelta(days=1)), decided_by="telegram"),
           approval(5, "AMZN", "cash_secured_put", "P", 200, "approved", decided_at=iso(now - timedelta(hours=5)),
                    order_state="cancelled", decided_by="system"),
           approval(7, "KO", "covered_call", "C", 62, "expired", created_at=iso(now - timedelta(hours=1)))]
TRADE = {"key": "c8:opened", "action": "opened", "how": None, "kind": "csp", "source": "wheel", "underlying": "NVDA",
         "right": "P", "strike": 165, "long_strike": None, "expiry": "2026-11-20", "contracts": 1,
         "at": iso(now - timedelta(hours=2)), "is_live": False, "premium": 235, "bought_back": None, "commissions": 1.3,
         "commissions_complete": True, "net_pnl": None, "capital": 16500, "roc_pct": 1.42, "annualized_pct": 13.3,
         "pct_kept": None, "dte_at_open": 39, "days_held": None, "reason": None, "facts": [], "approval_id": 8,
         "review": review, "rolled_to": None, "decided_by": "system"}
DAY = {"as_of": iso(now), "date": now.date().isoformat(), "book": "paper", "strategy": "all", "trades": [TRADE],
       "spreads_available": True, "previous_day": (now.date() - timedelta(days=3)).isoformat(), "next_day": None}
DETAIL = {**PENDING[0], "snapshot": {}, "ideal": {"lo": 175, "hi": 185, "min_credit": 2.1}, "gate_reasons": [],
          "alternatives": [{"candidate_id": "c9", "strategy": "cash_secured_put", "strike": 175, "expiry": "2026-11-20",
                            "blended_score": 64.0, "premium": 1.6, "stage": "top_n", "reasons": []}],
          "order_id": None, "fills": []}
CONTROLS = {"as_of": iso(now), "autonomy": {"level": "approve", "label": "Approve each trade"}, "rungs": [], "halted": False,
            "halt_reason": None, "halted_at": None, "mode": "paper", "drain_healthy": True, "drain_last_seen": iso(now),
            "pending_commands": 0, "roll_mode": "propose"}
ORDER = {"as_of": iso(now), "id": 9, "candidate_id": "c5", "approval_id": 5, "underlying": "AMZN", "strategy": "cash_secured_put",
         "strike": 200, "expiry": "2026-11-20", "state": "submitted", "limit_price": 2.4, "filled_qty": 0, "avg_fill_price": None,
         "is_live": False, "detail": None, "created_at": iso(now), "updated_at": iso(now)}
ITEM = lambda letter, pos, s, l: {"letter": letter, "position": pos, "side": "put", "short_strike": s, "long_strike": l, "width": 5,  # noqa: E731
    "contracts": 21, "credit_mid": 0.25, "credit_after_costs": 0.144, "max_loss_per_contract_usd": 475, "short_delta": -0.14,
    "spot": 767.29, "dist_spot_pts": 5.29, "dist_em_multiple": 1.49, "be_nominal_exits": 0.9493}
PICKS = {"as_of": iso(now), "available": True, "underlying": "SPY", "mode": "paper", "ai_enabled": True,
         "day": now.date().isoformat(), "previous_day": (now.date() - timedelta(days=4)).isoformat(), "next_day": None,
         "picks": [{"pick_id": 2, "created_at": iso(now - timedelta(hours=1)), "book_mode": "paper", "choice": "A",
                    "reason": "A keeps the most room under spot in a negative-gamma tape.", "fallback_reason": None,
                    "executed_letter": "A", "send_rejected": False, "send_reasons": [], "filled": True,
                    "model": "claude-sonnet-5-5", "regime": "negative", "side": "put", "plan_bias": None, "event_flag": False,
                    "menu_readable": True, "menu": [ITEM("A", "inside", 763, 758), ITEM("B", "baseline", 762, 757),
                                                     ITEM("C", "outer", 760, 755)], "spread_id": "s1"},
                   {"pick_id": 1, "created_at": iso(now - timedelta(hours=3)), "book_mode": "paper", "choice": "skip",
                    "reason": "", "fallback_reason": "timeout", "executed_letter": "B", "send_rejected": True,
                    "send_reasons": ["stale_pick"], "filled": False, "model": "claude-sonnet-5-5", "regime": "positive",
                    "side": "put", "plan_bias": None, "event_flag": True, "menu_readable": False, "menu": [], "spread_id": None}],
         "positions": [{"as_of": iso(now), "spread_id": "s1", "mode": "paper", "side": "put", "expiry": now.date().isoformat(),
                        "short_strike": 763, "long_strike": 758, "width": 5, "contracts_opened": 21, "contracts": 21,
                        "entry_credit": 0.25, "entry_commission": 27.3, "opened_at": iso(now - timedelta(minutes=55)),
                        "status": "open", "exit_debit": None, "exit_commission": None, "exit_reason": None,
                        "closed_at": None, "realized_pnl_usd": None}]}

ROUTES = {
    "/options/approvals?status=pending": {"as_of": iso(now), "approvals": PENDING},
    "/options/approvals?status=all": {"as_of": iso(now), "approvals": PENDING + DECIDED},
    "/pnl/day": DAY,
    "/options/approvals/1": DETAIL,
    "/options/approvals/6": {**PENDING[3], "snapshot": {}, "ideal": None, "gate_reasons": [], "alternatives": [],
                             "order_id": None, "fills": []},
    "/options/controls": CONTROLS,
    "/options/orders": {"as_of": iso(now), "orders": [ORDER]},
    "/options/fills": {"as_of": iso(now), "fills": []},
    "/options/assessed": {"as_of": iso(now), "run_id": "r1", "computed_at": iso(now), "groups": []},
    "/options/shorts": {"as_of": iso(now), "shorts": []},
    "/spreads/picks": PICKS,
}

class Handler(BaseHTTPRequestHandler):
    def do_GET(self):  # noqa: N802
        body = ROUTES.get(self.path) or next((v for k, v in ROUTES.items() if self.path.startswith(k)), None)
        code = 200 if body is not None else 404
        payload = json.dumps(body if body is not None else {"detail": f"mock: no route for {self.path}"}).encode()
        self.send_response(code)
        self.send_header("Content-Type", "application/json")
        self.end_headers()
        self.wfile.write(payload)

HTTPServer(("127.0.0.1", 8799), Handler).serve_forever()
```

Start a dev server on a scratch copy pointed at it (never the operator's `web/` and its `.next`):

```bash
S="$(mktemp -d)/web" && rsync -a --exclude node_modules --exclude .next web/ "$S/" \
  && ln -s "$PWD/web/node_modules" "$S/node_modules" \
  && (cd "$S" && API_URL=http://127.0.0.1:8799 API_TOKEN=mock npx next dev -p 3100)
```

Run both in the background. Pages that read a route the mock lacks show their error sentence,
which is fine: the check is Trades, the detail page and the Roll card.

- [ ] **Step 2: Look at it.** At 1440px and 390px wide, in light and in dark (More → theme), open:
  `/trades` (it opens on Proposals, since the mock has some waiting; then History for today and
  for a past day, Assessed, then CSPs and Credit spreads on the switcher), Review on the AAPL
  card (the sheet, then Approve's confirmation; do not release anything), the AMD roll card and
  `/trades/6` (both legs and the net), `/trades/1`, Home's Needs you column (the roll card there
  too), and the 320px width for `/trades` (no horizontal scroll). Then empty the mock's PENDING
  list, reload `/trades` with no `?view=`, and check that it opens on History. For the Roll card, add a held short option
  to the mock (a `/portfolio/positions/AAPL/2026-11-20_P180` route and a matching `/options/shorts`
  entry with one alert) and open that page. Take a screenshot of each; keep them in the
  scratchpad, not the repo.

- [ ] **Step 3: da-vinci finish.** With da-vinci loaded, run its `critique` and `audit` over
  `/trades` (all views), `/trades/[id]` and the Roll card, then `polish` what they find. Rules for
  the fixes:
  - every behaviour change gets a test (RED first, then GREEN), recorded in the Progress log;
  - no new colour, font, radius, elevation or token without the operator (propose it in the log);
  - nothing in the protected files changes; if a finding is about their look, it goes to
    DESIGN.md's Open Decisions ("The decide controls' look"), not into code;
  - `python3 ~/.claude/skills/da-vinci/scripts/lint.py web/features web/components/options web/components/ui`
    exits 0 at the end.
  Commit the fixes on their own: `git commit -m "fix(web): da-vinci finish of Trades, the detail page and the Roll card"`.

- [ ] **Step 4: The doc sweep** (the root CLAUDE.md's mandatory doc-update table). Each item is a
  concrete edit:
  - **`web/DESIGN.md`**: under `## Components` add **In-flight order row** (History, today only:
    the ticker and contract bold, a state word, flag only for Partial, limit price and fills in
    the figure face with n/a hatched, the humanised detail beneath, the row a link to its approval
    when it has one; under the list, one sentence saying a working order is cancelled in IBKR
    until Part 5), **Not-traded row** (the Position row anatomy: the whole row opens the detail
    page; the outcome as a word (Expired, Rejected, Order cancelled, Order rejected); who decided
    and when it was raised beneath; the premium, or a roll's net "as priced", right-aligned),
    **History** (the day line with previous, next and Today; In flight, Traded, Not traded in that
    order; empty sections left out except Traded, which says so; under All, one line sending
    credit spreads to their switcher), **Spreads books** (the day's spreads as rows grouped by
    book, paper and baseline side by side from 1024px; a paper spread carries "The menu Claude
    saw", collapsed: the outcome sentence, "Claude's view:" and the lettered menu under a
    perforation with Baseline, Claude's pick and Sent as words; "Other picks" as short cards;
    "This menu could not be read." hatched; no lime), **Assessed card** (a symbol per card, stage
    counts in words, Promote secondary). Amend **Proposal card**'s first line to "(Trades and
    Home)" if it does not already say so, and **Strategy switcher**'s scope sentence to say that
    on Trades it also picks which views exist (the wheel: Proposals, History, Assessed; Credit
    spreads: Spreads only). Add a Decision Log entry dated today: Part 2 built, revised by the
    operator on 2026-10-19 for full autonomy (Proposals, History and Assessed; the smart default;
    `?view=` and `?day=`; who approved each trade recorded and shown; rolls naming both legs;
    the spreads books trade-first over `GET /spreads/picks`; Propose a roll moved to the short
    option's page with a Roll alert word on Home's rows; the controls strip off Trades; the ideal
    zone no longer plotting a premium on a strike axis), with "no new colour, font, radius,
    elevation or token" (or the operator-approved exceptions). Update the marker's `updated=`
    date; keep `status=ratified`. Run
    `python3 ~/.claude/skills/da-vinci/scripts/design_md_check.py web/DESIGN.md` → exit 0.
  - **`web/CLAUDE.md`** (`## Layout`): replace the `trades/` and `options/` page entries with the
    new page (`app/trades/page.tsx` mounts `<TradesPage/>` from `features/trades/`: the strategy
    switcher; Proposals, History and Assessed, or Spreads under Credit spreads, in `?view=`, with
    the smart default; History's day in `?day=`; the drain warning; the old tab bar,
    `ControlsStrip`, `TickerPillBar`, the Working and Decided tabs and the Shorts tab are gone);
    `options/[approvalId]/` → describe the payslip detail page (`BackToTrades`, the trade with its stub, Claude's review, the decision in a
    340px column, a roll's two legs and net, who decided, the ideal zone as two sentences,
    alternatives and fills as rows); add a `features/trades/` entry (TradesPage, views.ts,
    useTradesView + useTradesDay, useSubmittedApprovals, ProposalsView, HistoryView +
    useInFlightCount + useWorkingOrders, history.ts, time.ts, SpreadsView + spreads.ts, types.ts);
    under `components/options/` note `RollProposal.tsx` (useRollProposal, RollReceipt,
    RollDialogs), that `AssessedBrowser`, `AssessedRow`, `StageBadge`, `ReviewPanel`,
    `IdealZoneBar`, `AlternativesTable`, `RationaleTags` and `ApprovalDetail` are restyled, that
    `OrdersTable` and `FillsTable` are unmounted and unrestyled until Part 3 mounts them on
    Activity, that `ApprovalsList`, `ApprovalCard`, `ShortsTable` and `ShortsRow` are no longer
    mounted and stay for their tests until Part 4, and that `TickerPillBar` is deleted; under
    `features/position/` add `RollCard`; under `features/home/` the Roll alert word, the roll
    helpers and `decisionWords` in `proposal.ts`, who approved on `TradeCard`, and the calendar
    day panel's "Open this day in History"; under `lib/` add `useHydrated.ts`.
  - **`ARCHITECTURE.md`**: the `src/api/` folder guide (`routers/spreads.py` now serves
    `GET /spreads/picks` too; `spreads_db.py` gains `try_read_pick_rows`,
    `try_read_spread_rows_opened`, `read_activity_days`; the approvals routes carry `decided_by`,
    `roll_from` and `fill_price`; `/pnl/day` carries `previous_day` and `next_day`); the
    `src/storage/` section (`ApprovalRow.decided_by`, added through `_ADDED_COLUMNS`: who decided,
    a display record no trading code reads); the `src/notify/` and `src/execution/` entries (the
    three writers: `_process_button`'s `decided_by`, the drain indirection's `"web"`, the
    auto-queue's and the roll pipeline's `"system"`); the `src/reporting/` entry (`day.py`:
    `decided_by` on opened and rolled cards, `activity_days`); the data-flow section where the
    approval lifecycle is described (the decision now records who made it); the web routes
    paragraph (around the line that starts "- **Routes:** `/` Home, `/trades`"): `/trades` is
    Proposals, History and Assessed, or Spreads under Credit spreads, opening on History when
    nothing waits on you, and Propose a roll lives on a short option's position page; the `web/`
    folder guide gains `features/trades/`.
  - **`docs/web/api.md`**: on `GET /options/approvals` and `GET /options/approvals/{id}`, the
    three new fields (`decided_by`: `system` | `web` | `telegram` | null, null meaning not
    recorded, never inferred; `roll_from`: the buy-back leg and the mids the roll was priced at,
    null for an entry or a roll frozen before 2026-10-11; `fill_price`: the order's average fill
    per share, null until it fills) and that `source` is `roll` whenever the snapshot says so; on
    `GET /pnl/day`, `decided_by` on each card (opened and rolled only) and `previous_day` /
    `next_day` (the nearest New York days with a wheel trade or a wheel proposal in the scope;
    spreads not counted). Then a `GET /spreads/picks` section: owner-only; `?day=YYYY-MM-DD`
    (default today in New York; a bad date is 422); every field of `SpreadPicksResponse`,
    `SpreadPickOut` and `SpreadMenuItemOut` with its meaning; `available: false` only when the
    file is missing or `spread_positions` cannot be read; a file without `spread_picks` answers
    `available: true` with no picks; a menu that no longer parses is `menu_readable: false` with
    an empty `menu`; `send_rejected` covers both a refusal before sending and an order that did
    not fill; `previous_day` / `next_day` are the nearest days with a pick or an opened spread;
    positions are every mode opened that New York day, oldest first.
  - **`STATUS.md`**: a built entry "Web overhaul Part 2 — Trades (2026-10-19)" listing what
    shipped (including `approvals.decided_by`), and under known limitations: approvals decided
    before the column existed, or before the trading service was restarted onto it, read only
    "Approved"; an in-flight roll order carries no option right, so it shows only under All;
    shadow and baseline spreads have no position page; the Roll alert word shows for any alert
    ever fired on that contract; a working order cannot be cancelled from the web until Part 5
    (Order control); the raw order and fill lists are unmounted until Part 3 puts them on
    Activity; the legacy files are kept for their tests until Part 4.
  - **`SETUP.md`**: the web console table (around the "Approve / Reject", "Promote", "Propose a
    roll" and "Halt / Resume / Autonomy / Rolls" rows): Approve / Reject → Trades → Review (or
    Home's cards); what the system did, and who approved it → Trades → History (any day, from
    Home's realised calendar too); Promote → Trades → Assessed; Propose a roll → the short option's page (Home →
    Positions → the row) → Roll card; Halt / Resume / Autonomy / Rolls → Bot controls only (the
    bot card at the rail's foot; on a phone, under More).
  - **Root `CLAUDE.md`**: in the spreads-fence bullet that says the web API reads
    `data/spreads.db` only through `src/api/spreads_db.py`, list `GET /spreads/picks` beside
    `GET /spreads/positions` and `GET /pnl/month`. Under "## The web layer and the trading
    database", add one sentence: `approvals.decided_by` records who decided an approval (the
    system, the web or Telegram) for the console only; nothing in `src/engine/`,
    `src/strategies/` or `src/execution/` reads it, and
    `tests/test_approval_decided_by.py::test_the_trading_path_never_reads_who_decided` keeps it
    that way.
  - **`README.md`**: no change (no new Telegram command or top-level directory). Confirm and say
    so in the Progress log.

- [ ] **Step 5: The full gate.** All of these, with the counts recorded:

```bash
python -m pytest -q && ruff check . && mypy src
cd web && npx vitest run && npx tsc --noEmit && npm run lint && cd ..
python3 ~/.claude/skills/da-vinci/scripts/lint.py web/features web/components/options web/components/ui
python3 ~/.claude/skills/da-vinci/scripts/design_md_check.py web/DESIGN.md
grep -rn "submitCommand\|confirmCommand" web/features            # prints nothing
git diff --stat main -- web/components/options/DecideControls.tsx web/components/options/ConfirmAction.tsx \
  web/components/options/CommandReceipt.tsx web/components/options/HaltControl.tsx \
  web/components/options/AutonomyControl.tsx web/components/options/RollModeControl.tsx \
  web/lib/commands.ts web/lib/receipt.ts                          # prints nothing
```

and the scratch-copy `next build` from C2. Expected: pytest = baseline + 31; vitest green with
every new test; everything else clean.

- [ ] **Step 6: Commit the docs, then the Progress log**

```bash
git add web/DESIGN.md web/CLAUDE.md ARCHITECTURE.md STATUS.md SETUP.md CLAUDE.md docs/web/api.md
git commit -m "docs: web overhaul Part 2 - Trades, who decided, the spreads picks route, the Roll card"
```

Fill in the Task 11 row (both commits, the gate counts, the screenshots taken, every ruling and
finish fix) and commit the plan file:
`git commit -am "docs(plan): web overhaul Part 2 Progress log"` (only the plan file is modified at
this point; check `git status` first).

- [ ] **Step 7: Hand off.** Run the whole-branch review on the most capable model (opus):
  superpowers:requesting-code-review over `main..HEAD`, with this plan, `web/DESIGN.md` and the
  Review Focus above as its brief. Fix what it finds as one review fix pass (a commit, a Progress
  log line). Then superpowers:finishing-a-development-branch. Tell the operator that
  `./ibkr restart` is needed twice over: the API process serves `GET /spreads/picks` and the new
  fields only after it, and the trading service (approval_service, the scan loop, the monitor)
  writes `decided_by` only after it. Until then new approvals read only "Approved". The column
  itself is added by whichever process starts first (`init_db`'s `_ensure_added_columns`).

---

## Self-review (run by the plan's author, 2026-10-19; revised the same day after the operator's review)

- **Spec coverage.** Roadmap Part 2, as the operator revised it on 2026-10-19:
  - the strategy switcher and the views (Task 8);
  - Proposals, History, Assessed and Spreads (Tasks 3, 5, 6, 7) with the smart default (Task 3);
  - proposal cards at page width reusing `ProposalCard` and `ReviewSheet` (Task 3);
  - who approved, recorded (Task 2) and shown on History, the trade cards and the detail page
    (Tasks 4, 5, 9);
  - rolls with both legs on the card, the History rows and the detail page (Tasks 2, 4, 9);
  - the spreads view trade-first over a second read-only `/spreads/*` route (Tasks 1, 7);
  - "Propose a roll" moved (Task 10, onto the position page per ruling 7);
  - the legacy `components/options/*` styles migrated for what stays mounted (Tasks 5, 6, 9),
    with ruling 10 covering what does not;
  - Cancel moved out to Part 5 and the raw fills and orders ledger to Part 3 (Roadmap).

  DESIGN.md's Trades surface is written in Task 3 and built in Tasks 3–8.
- **Placeholders.** None: every code step carries its code, and the doc sweep names each edit.
- **Type consistency.**
  - `TradesView`, `viewsFor`, `explicitView`, `defaultView` and `useTradesView(strategy,
    pending)` (Task 3) are what Task 8 imports.
  - `useInFlightCount` and `HistoryView` (Task 5) are what Task 8 counts and mounts with.
  - `timeET` and `dayLabel` live in `time.ts` (Task 5), which `spreads.ts` re-exports (Task 7).
  - `decisionWords` and `rollTitle` (Task 4) are what History (Task 5) and the detail page
    (Task 9) use.
  - `SpreadPicksResponse` and the Task 2 fields are checked against the OpenAPI contract by B4.
  - `RollProposal` (Task 10) is used by `ShortsRow` and `RollCard` alike.
  - `buildPositionRows`' new fifth parameter has a default, so its other callers are unchanged.
- **Review Focus.** Each of the seven lines names the test that pins it, in the task that owns
  the code.
- **What changed in the revision, and what did not.**
  - Task 1 is unchanged.
  - Task 2 is new.
  - The old Working and Decided tasks became Task 5 (History). `OrdersTable` and `FillsTable`
    are no longer restyled here.
  - The old Assessed and Roll-card tasks are unchanged apart from their numbers.
  - The Spreads view keeps its logic module and changes its composition.
  - The page and the detail page carry the new views, the rolls and who decided.
