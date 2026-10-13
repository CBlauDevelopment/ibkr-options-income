---
version: alpha
name: IBKR Income
description: A private options-income console for one operator who approves deterministic covered-call and cash-secured-put proposals, checked at a desk during US hours (Singapore night) and on a phone in daylight.
colors:
  primary: "#a6eb6e"
  primary-deep: "#8fdb55"
  on-primary: "#111410"
  ground: "#f2f4ef"
  surface: "#ffffff"
  sunk: "#e6eadf"
  sunk-deep: "#d9ded3"
  ink: "#111410"
  ink-muted: "#575d55"
  control-edge: "#7a8276"
  hairline: "#dce0d7"
  perforation: "#c9cfc2"
  gain: "#187a42"
  loss: "#c8322f"
  flag: "#fff1d6"
  on-flag: "#6b4500"
  unknown: "#6e7569"
  ground-dark: "#0f110f"
  surface-dark: "#191c19"
  sunk-dark: "#232723"
  ink-dark: "#eef1eb"
  ink-muted-dark: "#a3aa9f"
  control-edge-dark: "#7d8579"
  hairline-dark: "#262a26"
  perforation-dark: "#3a4038"
  gain-dark: "#5bd58a"
  loss-dark: "#ff7468"
  flag-dark: "#3a2e12"
  on-flag-dark: "#f5cf7a"
  unknown-dark: "#8a9286"
typography:
  display:
    fontFamily: "Hanken Grotesk, system-ui, sans-serif"
    fontSize: 2.875rem
    fontWeight: 800
    lineHeight: 1.05
    letterSpacing: -0.025em
  headline:
    fontFamily: "Hanken Grotesk, system-ui, sans-serif"
    fontSize: 1.5rem
    fontWeight: 800
    lineHeight: 1.15
    letterSpacing: -0.015em
  title:
    fontFamily: "Hanken Grotesk, system-ui, sans-serif"
    fontSize: 1.0625rem
    fontWeight: 700
    lineHeight: 1.3
    letterSpacing: -0.01em
  body:
    fontFamily: "Hanken Grotesk, system-ui, sans-serif"
    fontSize: 0.875rem
    fontWeight: 400
    lineHeight: 1.5
  label:
    fontFamily: "Hanken Grotesk, system-ui, sans-serif"
    fontSize: 0.75rem
    fontWeight: 600
    lineHeight: 1.3
    letterSpacing: 0.04em
  figure:
    fontFamily: "Red Hat Mono, ui-monospace, monospace"
    fontSize: 0.84375rem
    fontWeight: 500
    lineHeight: 1.45
    fontFeature: '"tnum" 1'
rounded:
  sm: 6px
  md: 12px
  lg: 18px
  sheet: 24px
  full: 999px
spacing:
  xxs: 2px
  xs: 4px
  sm: 8px
  md: 12px
  lg: 16px
  xl: 24px
  2xl: 32px
  3xl: 48px
components:
  button-primary:
    backgroundColor: "{colors.primary}"
    textColor: "{colors.on-primary}"
    typography: "{typography.title}"
    rounded: "{rounded.full}"
    padding: 11px 18px
  button-primary-hover:
    backgroundColor: "{colors.primary-deep}"
    textColor: "{colors.on-primary}"
  button-secondary:
    backgroundColor: "{colors.sunk}"
    textColor: "{colors.ink}"
    typography: "{typography.title}"
    rounded: "{rounded.full}"
    padding: 11px 18px
  button-secondary-hover:
    backgroundColor: "{colors.sunk-deep}"
    textColor: "{colors.ink}"
  card:
    backgroundColor: "{colors.surface}"
    textColor: "{colors.ink}"
    rounded: "{rounded.lg}"
    padding: 16px 18px
  disclosure:
    backgroundColor: "{colors.sunk}"
    textColor: "{colors.ink}"
    typography: "{typography.body}"
    rounded: "{rounded.md}"
    padding: 10px 12px
  stub:
    textColor: "{colors.ink}"
    typography: "{typography.figure}"
  status-word:
    backgroundColor: "{colors.sunk}"
    textColor: "{colors.ink-muted}"
    typography: "{typography.label}"
    rounded: "{rounded.sm}"
    padding: 1px 8px
  status-word-flag:
    backgroundColor: "{colors.flag}"
    textColor: "{colors.on-flag}"
  status-word-today:
    backgroundColor: "{colors.primary}"
    textColor: "{colors.on-primary}"
  strategy-switch:
    backgroundColor: "{colors.surface}"
    textColor: "{colors.ink-muted}"
    typography: "{typography.title}"
    rounded: "{rounded.full}"
    padding: 4px
  strategy-switch-selected:
    backgroundColor: "{colors.ink}"
    textColor: "{colors.ground}"
  range-chip:
    textColor: "{colors.ink-muted}"
    typography: "{typography.label}"
    rounded: "{rounded.full}"
    padding: 4px 11px
  range-chip-selected:
    backgroundColor: "{colors.ink}"
    textColor: "{colors.ground}"
  rail:
    backgroundColor: "{colors.surface}"
    textColor: "{colors.ink-muted}"
    typography: "{typography.body}"
    width: 200px
  tab-bar:
    backgroundColor: "{colors.surface}"
    textColor: "{colors.ink-muted}"
    typography: "{typography.label}"
    height: 64px
  sheet:
    backgroundColor: "{colors.surface}"
    textColor: "{colors.ink}"
    rounded: "{rounded.sheet}"
    padding: 24px
---
<!-- da-vinci schema=1 status=draft updated=2026-10-13 -->
# Design System: IBKR Income

## Overview

**The payslip.** Options income is a wage your capital earns, so the console reads like one: every
proposed trade and every month ends in a short perforated stub (premium in, buybacks and
commissions out, net, and what that is a year). The account value still leads the home screen, as
in any brokerage app, but the payslip is what this console has that a brokerage app does not. It
shows the money the system is *earning*, line by line, in sums you can check by eye.

The mood is calm, plain and exact: sage-tinted paper, white cards, near-black ink, and one bright
lime that only ever means "act here". It borrows Robinhood's quiet hierarchy (one huge number, a
chart, rows without table chrome), Wise's transparent arithmetic and consequence-first sentences,
and Puthouse's trade-at-a-glance cards with the reasoning beside them. It refuses the casino
(confetti, celebratory flashes, streaks), the marketing page, the SaaS KPI-tile grid, crypto neon,
and pages crammed with everything at once.

Key characteristics: one bold number per region; everything secondary collapsed behind a
disclosure until asked for; math as a visible sum, never a bare percentage; words for states, not
colours; nothing animated except the thing you just touched.

## Colors

**Restrained.** Tinted neutrals carry the whole interface; lime is reserved for primary actions;
green, red and amber are reserved for meaning. Every light token has a `-dark` twin with the same
role.

- **Sage paper** (`ground` / `ground-dark`): the page itself. A green-grey tint, so white cards sit
  on it by lightness alone.
- **Card white** (`surface` / `surface-dark`): every card, the rail, the tab bar, sheets.
- **Pressed sage** (`sunk`, `sunk-deep` / `sunk-dark`): fills *inside* a card: the Why disclosure,
  secondary buttons, unselected chips, the meter track.
- **Ink** (`ink` / `ink-dark`): text, the hero chart line, the selected chip fill, the focus ring.
  **Muted ink** (`ink-muted` / `ink-muted-dark`) for labels and secondary lines (6.1:1 and up on
  every ground it meets).
- **Lime** (`primary`, hover `primary-deep`, label `on-primary`): primary buttons, the pending-count
  badge, the pay meter fill, and the one "Expires today" status. Nothing decorative.
- **Gain / Loss** (`gain`, `loss` and dark twins): signed money only, always paired with a `+`/`−`
  sign or the words "open P&L", never as the only signal.
- **Flag amber** (`flag` with `on-flag`): warnings that need attention without being a loss,
  such as "Assignment likely", a degraded data source, or a stale quote.
- **Unknown** (`unknown` / `unknown-dark`): the hatch texture behind "n/a". Unknown is never zero.
- **Control edge** (`control-edge`): input and checkbox borders (3.6:1 on paper, 4.0:1 on white).
  **Hairline** and **perforation** are decorative separators only and never the sole boundary of a
  control.

**The Lime Means Act Rule.** Lime appears only where tapping does something primary. A screen with
lime on two competing buttons has one too many.

**The Words First Rule.** No state is shown by colour alone: gain carries a sign, flags carry a
word, unknown carries texture and "n/a", selected carries an ink fill. This keeps the existing
`web/CLAUDE.md` honesty rule intact.

## Typography

**Hanken Grotesk** carries everything: display and headings at 800 (900 for the hero number on large
screens), titles at 700, UI and body at 400 to 600. Its default figures are tabular (verified: "1111"
and "0000" set at equal width), so money columns align without a second face. **Red Hat Mono** is
the stub voice: every perforated sum, the ledger, and fill prices, where the typewriter cadence says
"this is arithmetic".

Scale (fixed rem, ratio about 1.2, no fluid headings on these Operate surfaces): display 46px for
the hero number (38px on phones), headline 24px for page titles, title 17px for card titles and
buttons, body 14px, label 12px semibold with slight tracking for eyebrows, chips and status words,
figure 13.5px mono. Prose (the Explain pages, Claude's review text, news explanations) keeps a 65 to
75 character measure; tables may run wider.

Replaces IBM Plex Sans and Mono, which `web/CLAUDE.md` currently names. That file changes with
the build.

## Layout

Desktop: a 200px rail on the left with Home, Trades, Portfolio, Activity, Research, News, More, and
the bot card pinned at its foot. From 1024px up, Home adds a 340px right column for "needs you";
below 1024px that column becomes a one-line proposals banner under the hero. Content max width is
1200px. Below 768px the rail disappears, and a bottom tab bar (Home, Trades, Portfolio, Activity,
More) takes its place. Everything is one column, in this order on Home: strategy switcher, hero,
proposals banner, October pay, positions.

Spacing runs on a 4px base (2, 4, 8, 12, 16, 24, 32, 48). Cards pad 16 to 18px; card stacks gap
16px; sections inside a page gap 24px. Touch targets are at least 44px on phones. DENSITY 5: rows
are compact (about 11px vertical padding), but every card shows one idea, and anything secondary
sits behind a disclosure.

**The One Idea Per Card Rule.** A card answers one question (what am I earning this month, what
needs me, what do I hold). A second question gets a second card or a disclosure, never a cramped
second half.

## Elevation & Depth

Tonal layering only: paper ground, white surface, pressed-sage fills inside. No drop shadows on
cards, buttons or rows, and never a border plus a shadow on one element. A hairline separates rows
inside a card. The single exception is the review **sheet** and the confirm dialog, which rise over
a black scrim at 50% (light) or 60% (dark). The sheet carries one soft ambient shadow so it reads as
lifted off the page beneath.

## Shapes

Gently rounded throughout: 6px for status words, 12px for inner blocks (the Why disclosure,
inputs), 18px for cards, 24px for the top corners of sheets, fully round for buttons, chips, the
count badge and the meter. The recurring silhouette is the **perforation**: a 2px dashed rule that
opens every stub, the console's only ornament.

## Components

**Proposal card** (Trades and Home): eyebrow with the strategy in words (CASH-SECURED PUT, COVERED
CALL, CREDIT SPREAD), expiry and days left at the right, then a title ("AAPL · Sell $180 put"), then
one consequence-first sentence. Below it, the **Why this trade** disclosure (Claude's review,
collapsed by default, sitting *above* the stub; it carries For, Against and If challenged lines and
is labelled as Claude's view), then the stub, then Review (primary, opens the review sheet) and
Details (secondary, the full approval page). Approve and reject happen only inside the sheet,
behind the existing confirmation, so the card itself never decides anything in one tap. States:
pending, submitted (receipt replaces buttons), decided (decision line replaces buttons), stale data
(flag word on the eyebrow row).

**Stub**: the perforation, then two to four `figure` lines, then a total line with a hairline above.
Each line is a button that toggles a one-sentence explanation beneath it. Unknown inputs render
"n/a" with hatch; a total built on an unknown says so in words instead of summing.

**October pay card** (Home): collapsible. Closed, it shows the title, net so far against target,
the lime meter, and "71% of target · 18 days left". Open, it shows the month's stub. The target is
`web.monthly_income_target_pct` of the month-start account value.

**Strategy switcher**: a segmented control on a white pill track, one button per kind of trade:
All, CSPs, CCs, Credit spreads, each with its live count. It sits at the very top of Home and
Trades. The selected button takes an ink fill (never lime or green) and `aria-pressed`. It scopes
everything below the hero: proposals, October pay (that strategy's premium and stub), and
positions. The account-value hero stays account-wide, because account value cannot be split by
strategy honestly. The choice is kept in the URL (`?strategy=csp`), so a link or reload keeps it.
The Positions card carries the same tabs as smaller chips, plus Shares.

**Position row**: ticker and contract bold, then a status word, then a muted sub-line (expiry,
coverage, % of premium kept); value right-aligned with its label beneath ("sold for", "open P&L").
Status words: Expires today (lime); Assignment likely and In the money (flag); At the money and
Out of the money (sunk). They come only from fields the API returns (expiry, assignment risk,
moneyness). A position with none of those known shows no status word rather than a guessed one.

**Review sheet**: a bottom sheet on phones, a right-side sheet on desktop. One step at a time:
(1) the trade, its stub and Why, with Approve; (2) the existing confirmation (exact contract and
count); (3) in live mode only, the separate LIVE confirmation. Then the command receipt in place.
Focus is trapped, Escape closes, and focus returns to the trigger.

**Bot card** (rail foot): running or halted in words, mode (paper or live), the autonomy rung,
and a flag line when the trading service is not draining commands. It opens the Bot sheet: Halt is one tap; Resume needs the typed word RESUME;
rung changes confirm first. Halted state also shows a full-width banner on every page.

**Disclosure**: a summary row with a round chevron chip that rotates 180°, `aria-expanded` on a
real button or native `details`, focus ring in ink.

**Buttons**: primary lime, secondary pressed sage, both fully round. Hover deepens one step;
focus-visible draws a 2px ink ring at 3px offset; pressed scales to 0.98; disabled drops to muted
ink on sunk with no lime; loading keeps the label and adds "…" (no spinner when the wait is a
command poll, since the receipt already states progress).

**Range chips** (1D 1W 1M 3M YTD All): selected is an ink fill, never lime or green, so selected
never reads as "up".

## Do's and Don'ts

- Do end every trade and every income figure in a stub or a sentence; never a bare percentage.
- Do collapse secondary detail (Claude's review, the month's breakdown, alternatives) behind a
  disclosure, closed by default.
- Do write consequences in plain English: "If AAPL closes under $180 on Nov 21, you buy 100 shares
  at $180."
- Do render unknown values as "n/a" with hatch, never "$0" or "0%".
- Don't use lime for anything that is not a primary action, the pay meter, the count badge or
  "Expires today".
- Don't celebrate: no confetti, flashes, streaks or sounds on fills.
- Don't animate chart data in, and don't use a shadow anywhere except the sheet and dialog.
- Don't put an em dash in UI copy, and don't use "seamless", "robust", "unlock" or "elevate".
- Don't let Claude's text look like a decision: it is always labelled as Claude's view and never
  sits on a button.
- Approved exceptions to da-vinci tells: none.

## Motion

MOTION 2. Only touched things move: disclosures (the chevron rotates 180ms ease-out; the panel
appears in place, with no height animation),
sheets (slide in 240ms ease-out, out 180ms), button press (scale 0.98, 90ms). Exits are faster than
entrances. Charts never animate their data in; scrubbing updates the hero number instantly. Under
`prefers-reduced-motion` every transition is removed and sheets appear in place.

## Brief

A private web console for a semi-autonomous options-income system on Interactive Brokers. Python
scans, scores and gates covered calls and cash-secured puts deterministically; a separate process
trades daily SPY credit spreads. Claude reviews proposals but can never place, size or gate an order.
The web proposes intents (approve, promote, roll, halt) that the trading service drains; it never
trades directly.

**Mechanism:** a deterministic Rules Engine proposes each trade and you approve it, so the screen
has to show why the gate let it through and exactly what happened after you approved, not sell the
trade.

**Users and scene:** one operator in Singapore. At a desk during US market hours (21:30 to 04:00
SGT), in long sessions in a dim room. On a phone in daylight for quick checks and approvals. Often
tired at night, so states must be unambiguous and the destructive or irreversible paths deliberate.

| Setting | Value |
|---|---|
| Platform | web (responsive: desktop rail, phone tab bar) |
| Stack | Next.js 15 App Router, React 19, Tailwind CSS v4, react-query, cmdk, lightweight-charts, recharts |
| Design system | none (own components on Tailwind v4 tokens; lucide-react icons) |
| Dials | VARIANCE 3, MOTION 2, DENSITY 5 |
| Theme | both: light default, dark toggle, and a "follow OS" option |
| Accessibility | WCAG 2.2 AA; 44px touch targets on phone; no state by colour alone |

**Evidence on hand:** real account, position, P&L, ledger, approval and news data through the API.
No logo, favicon or brand assets yet. Must not fabricate: prices, fills, targets, probabilities or
any figure the API does not return; mockups label their data synthetic.

**Brand commitments:** the product name in the shell is "IBKR Income" (inferred). Lime on primary
actions is the user's explicit choice.

**Must remain untouched:** the honesty rules (n/a with hatch, never colour alone, receipts never
overstate, charts never animate in); the safety friction (confirm before any order intent, one-tap
halt, typed RESUME, the second LIVE confirmation); stable URLs (`/options/[id]`, `/stock/[symbol]`,
`/ledger/...` keep working or redirect); copy rules (no em dashes, the banned words).

## Inspirations

- **Robinhood.** Take: one huge number over a scrubbable chart with range chips; quiet list rows
  without table chrome; a focused review step before an order. Leave: true-black canvas, neon
  green, Capsule Sans, celebratory motion.
- **Wise.** Take: transparent line-by-line math; consequence-first plain English; one bright accent
  on chunky round buttons; one decision per step. Leave: the marketing-scale 900-weight display
  type and its exact lime.
- **Puthouse.** Take: each proposed trade as a card judged at a glance; income progress as the
  headline goal; the AI's reason beside the trade; a clearly visible bot state. Leave: any claim of
  autonomy the system does not have.
- **Anti-references:** casino or gamified brokerage; marketing-page layouts; generic SaaS KPI-tile
  grids; crypto neon, glow and glassmorphism; cluttered pages that show everything at once.

## Surfaces

### Home
Operate. Dials as the project default.
- **THESIS:** the account as a payslip: value on top, this month's earnings as a stub, then what
  you hold. Refuses the brokerage home where account value is the only number.
- **OWN-WORLD:** sage paper, white cards, ink hero line, perforated stubs, lime only on Review and
  the pay meter.
- **STORY:** you see what the account is worth, whether this month's income is on pace, what needs
  you, and which positions need watching, in that order of glance.
- **FIRST VIEWPORT:** desktop: the strategy switcher (All, CSPs, CCs, Credit spreads) across the
  very top; hero number, delta and 1M chart with range chips top-left; collapsed
  October pay card below it; positions card below that; the "Needs you" column of proposal cards on
  the right. Phone: strategy switcher, hero, chart, one-line proposals banner, October pay,
  positions.
- **FORM:** the payslip, candidate 1 of 7 (Claude's pick), roll seed 1090290943, revised by the
  user: Why collapsible above the stub, pay card collapsible, positions beneath it.
- **FINISH:** unreviewed and undocumented is unfinished.

### Trades
Operate. Proposals, Working, Decided, Assessed and Spreads segments. Proposal cards as on Home, at
full width; the review sheet opens from Review. Spreads is read-only.

### Portfolio
Operate. Positions, Campaigns, Expiry calendar. Position rows as on Home; "Propose a roll" moves
onto the short-option rows.

### Activity
Operate. Pay (P&L summary and equity curve), Ledger, Fills and orders, System (score-vs-outcome).
Ledger and stubs use the figure face.

### Research
Read. Search, watchlist, sectors, the stock page, and Universe. VARIANCE 3, DENSITY 6.

### News
Read. Feed and calendar; ticker briefs.

### More
Read and Operate. How it works (the System Explanation pages), Bot controls, Theme, Ledger import.

## Agent Prompt Guide

Quick reference: paper `#f2f4ef` with white `#ffffff` cards, ink `#111410`, muted `#575d55`, lime
`#a6eb6e` for primary actions only, gain `#187a42`, loss `#c8322f`, flag `#fff1d6`/`#6b4500`; dark twins
end in `-dark`. Hanken Grotesk (800 headings, tabular by default) and Red Hat Mono for stubs. Tonal
elevation, no shadows except the sheet; 18px cards, round buttons; dashed perforation opens every
stub.

- "Build the Trades proposals list per web/DESIGN.md: Operate, payslip world, proposal cards with
  the Why disclosure above the stub, lime only on Review."
- "Restyle the Ledger table per web/DESIGN.md: Red Hat Mono figures, hairline rows, n/a with hatch
  for unknowns, no table borders."

Iteration: change one component at a time and name it by its `components:` key; add variants as
sibling keys; re-run the check after edits.

## Open Decisions

- **Monthly income target %:** `web.monthly_income_target_pct` applied to month-start net
  liquidation value. The default is owed by the user (the plan ships it unset, and the meter reads
  "No target set" until it is).
- **Product name in the shell:** "IBKR Income" is inferred; confirm or rename.
- **Logo and favicon:** none exist; a wordmark set in Hanken Grotesk 800 is the interim.
- **Icons:** lucide-react inferred; confirm.
- **Spreads data:** needs a new read-only `/spreads` API over `data/spreads.db`; the endpoint shape
  is settled in the implementation plan.

## Decision Log

- 2026-10-13: Added the strategy switcher (All, CSPs, CCs, Credit spreads) at the top of Home and
  Trades, plus the same tabs on the Positions card, at the user's request. It scopes everything
  below the hero; the hero stays account-wide.
- 2026-10-13: Created from the thorough interview, replacing the dark-only IBM Plex world. Direction:
  the payslip (candidate 1 of 7, Claude's pick, roll seed 1090290943), revised by the user with a
  collapsible Why above the stub, a collapsible October pay card, and positions beneath it. Theme:
  light default with a dark toggle and a follow-OS option. Navigation: Home, Trades, Portfolio,
  Activity, Research, News, More. Monthly target is a percentage of account value.
