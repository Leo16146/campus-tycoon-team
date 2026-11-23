# Campus Week: a campus kiosk trading game

Team project for Introduction to Programming at Nova SBE. Campus Week extends the
completed solo app *Campus Tycoon* into a game that several people can play at the
same time, each in a private game.

You run a campus kiosk with coffee, water and granola bars for five trading days.
Every day has an event that changes demand, for example an Open Day where nobody
pays a premium price. At the end the app compares your result with a simple
baseline strategy.

## Team and deployment

| | |
|---|---|
| Deployed app | **https://39p9i3vcvzvy66yjhja8xk.streamlit.app** (Streamlit Community Cloud, deployed from `main`, `app.py`, Python 3.12) |
| Team member and student number | Leo Böhler, 73262 |
| What is online | The app is deployed from `main`. Changes on branches that are not merged are not deployed. On 23.11.2026 the deployed app showed the behaviour of `main` @ `c825ef1` (see "Verification"). |

The earlier P0 prototype URL showed a throwaway test page (`spike_app.py` on the
branch `p0-token-spike`). It is not the finished app.

## Features

- **Private games.** Starting a game creates a private link (`?game=<token>`).
  Anyone with the link can play or delete that game. Without it, nobody can.
- **Two scenarios**, each with five fixed daily events:
  - *Exam Week*: revision and exam days double coffee demand. On Open Day nobody
    pays more than the reference price.
  - *Heatwave*: water sells best and coffee is weak. On Sports day the better price
    tier differs per product.
- **Today's event** is shown before you buy and set prices, with the demand per
  price tier for every product. *Expected sales* use the event and your stock.
- **Plan today:** one row per product with *Buy* and *Selling price* fields and a
  live preview (cost, demand, expected sales, total and cash after purchases).
  *Apply purchases and prices* saves everything together, or nothing if one input
  is invalid or the total is more than your cash. *Discard changes* restores the
  saved plan. *Start trading day* stays disabled while changes are not applied.
  If another window changed the game in the meantime, applying or trading is
  rejected and the current state is shown, so an old window never undoes newer
  changes.
  Unsold stock stays in the inventory and all amounts are whole cents.
- **How to play** on the start page explains the goal, the daily steps and the score;
  each scenario has a one-sentence description. Price fields explain the expected
  format (decimal point, no comma, no € symbol).
- **Day result right after trading:** units sold, revenue and gross profit of the
  last day next to the baseline's gross profit for that day. Error messages of the
  plan name the product, for example *"Coffee: The selling price must be positive."*
- **Final comparison** after day 5: your overall gain / loss next to the baseline
  strategy, the signed difference and the gross profit for each day.
- **Scenario leaderboards (optional):** after day 5 you can publish your result
  under a nickname. The start page shows the best 10 per scenario. The score is
  computed on the server from the saved game; only the nickname comes from the
  browser. Equal scores share a rank. You can remove your entry; deleting the
  game removes it too.
- **Clear layout:** each step is a card (inventory, today's event, plan, trading,
  results), the next step is always the highlighted button, and every number on the
  final screen appears once, with the calculation shown below it.
- **CSV download** of your daily results (the file name contains only the scenario,
  never the private link).
- **Delete with confirmation**, *Start another game*, and clear messages for
  invalid input, invalid links and a briefly busy database.

### Rules in short

| Selling price | Demand |
|---|---|
| At or below the reference price | lower tier of today's event |
| Above the reference price, up to and including twice it | upper tier of today's event |
| Above twice the reference price | 0 |

Sales are the smaller of demand and stock.

- **Gross profit** = revenue − units sold × unit cost.
- **Overall gain / loss** = final cash + remaining stock at unit cost − €100.00.

The **baseline strategy** keeps every selling price at the reference price. Each day
it buys stock up to the lower demand tier, in the order coffee, water, granola bar,
and only as much as its cash allows. It is a simple reference, not the best
possible strategy. With these rules it ends Exam Week at €229.00 and Heatwave at
€184.00.

## Local setup

You need [uv](https://docs.astral.sh/uv/). uv installs Python 3.12 (see
`.python-version`) and the locked dependencies from `uv.lock`.

```sh
uv sync --locked
uv run pytest
uv run streamlit run app.py --server.address 127.0.0.1 --server.port 8503
```

Open http://127.0.0.1:8503 in your browser. Stop the server with Ctrl+C.

The app creates `campus_week.sqlite3` in this directory. Set `CAMPUS_TYCOON_DB` to
use another file. A database in the old solo format is left unchanged and reported
with an error. Local databases, virtual environments and secrets are excluded from
Git. The app needs no secrets or API keys.

## Files

| Path | Contents |
|---|---|
| `app.py` | Streamlit interface: start page, game screen, final comparison, messages |
| `logic.py` | Rules without a database: catalogue, scenarios and events, demand, sales, baseline |
| `db.py` | SQLite storage: tables, token check, one transaction per action, lock handling |
| `tests/` | pytest tests (see below) |
| `specs/campus-week.md` | Specification of the team extension with all expected values |
| `docs/acceptance-checklist.md` | Manual check on the deployed app |
| `docs/demo-script.md` | Plan for the live demo and questions for the walkthrough |
| `.streamlit/config.toml` | Look of the app: warm coffee colours, rounded cards, and only the viewer menu for visitors. Measured contrast on the page: body text 17.9:1, captions 4.8:1 (WCAG AA needs 4.5:1), primary button 6.2:1 |
| `.github/workflows/tests.yml` | Runs `uv sync --locked` and `uv run pytest` on GitHub for every push and pull request |
| `specs/first-feature.md`, `docs/product-brief.html` | Documents of the original solo project |

## Access and storage

- **Tokens.** A new game gets a random token (`secrets.token_urlsafe(32)`). The
  database stores only its SHA-256 hash. Every database function receives the
  token, looks up the game by its hash inside the transaction and works only on
  that game's rows. A game id from the browser never grants access.
- **Malformed links** are rejected before the database is opened.
- **Storage** is SQLite on the server. Each action (start game, apply plan, buy,
  set price, trade, delete) is one transaction: it is saved completely or not at
  all.
- **Temporary storage.** Streamlit Community Cloud does not guarantee that local
  files persist, so games can disappear, for example after a restart. The app says
  so on every game screen. A lost game shows the same message as an invalid link.
- **Busy database.** If another player is writing at the same moment and the lock
  is not free within 5 seconds, nothing is repeated automatically:
  - A busy **action** (buy, set price, trade, delete, start game) is not carried
    out. The app shows *"The game is busy right now. Nothing was changed. Please
    try again in a moment."* and stays on the same game, so a failed delete keeps
    the game link.
  - A busy **page load** shows *"The game is busy right now and could not be
    loaded. Please try again in a moment."* and a *Try again* button.

## How it works and why

The detailed specifications in `specs/` are written in German. This section
summarises the design in English.

### What happens on a click

Streamlit reruns `app.py` from top to bottom after every input or click. Take
*Apply purchases and prices* as an example:

1. The button's callback `apply_plan` in `app.py` collects the fields of today's
   plan and calls `db.apply_plan`.
2. `db.apply_plan` checks the token format (`check_token`) and opens one
   transaction (`transaction`).
3. Inside that transaction it:
   - finds the game by the token's hash (`authorized_game`),
   - checks the day (`current_game`) and that the window still shows the saved
     state (`check_unchanged`),
   - validates the plan (`checked_plan`, using `price_in_cents` from `logic.py`),
   - checks the total against the cash,
   - and only then writes all purchases and prices.
4. Streamlit reruns `app.py`. It loads the game again with `db.load` and shows
   the new state and the queued messages (`notify`, `show_notices`).

`logic.py` holds the rules and never touches the database: the catalogue,
`EVENTS`, `demand`, `sales_for_product`, `final_result` and the baseline. That
keeps the rules testable with small numbers.

### Why it is built this way

- **Whole cents instead of floats.** €0.10 + €0.20 is not exactly €0.30 as a
  float. All amounts are integers in cents and are only formatted as `€4.00` for
  display.
- **Demand tiers instead of factors.** With unit costs at half the reference price,
  twice the reference price always earns more per unit. A plain factor would change
  only the quantity, not the better price. Fixed tiers per event, for example
  Open Day (14, 0), make the price decision depend on the day.
- **Fixed scenarios instead of live data.** Every player of a scenario gets the
  same five events, so results are comparable and the tests are deterministic.
  There is no external service that can fail during the demo.
- **Private links instead of passwords.** A random token from
  `secrets.token_urlsafe(32)` has 256 random bits, so guessing one is
  computationally infeasible. Storing only its SHA-256 hash means a copy of the
  database does not reveal working links. A slow password hash is unnecessary
  here, because the token is random and not chosen by a person. Own passwords
  would need slow hashing, rate limits and password resets, and Streamlit loses
  `st.session_state` on every reload.
- **Authorisation in `db.py`, not in the interface.** Every function that reads or
  changes a game receives the token and works only on the rows of the game found
  for it. A game id from the browser never grants access.
- **One transaction per action.** Every database access runs inside
  `transaction()`:
  - Writing actions (create, apply plan, buy, set price, trade, delete) start with
    `BEGIN IMMEDIATE`, which takes SQLite's write lock at once.
  - Reading (`load`, the table check in `initialize`) starts with a plain `BEGIN`
    and only has to wait while another connection is committing.
  - The block is committed at the end and rolled back on any error, so a purchase
    or a trading day is saved completely or not at all.
  - If a lock is not free within 5 seconds, `DatabaseBusy` is raised and the app
    asks the player to try again. Nothing is retried automatically.
- **Snapshots against outdated windows.** Each window remembers what it showed
  (`snapshot`: day, cash, stock and price per product). `apply_plan` and `trade`
  compare it with the saved state inside the transaction. So an old window cannot
  undo prices set in another window, or trade with prices it never displayed.
- **No `st.form` for the daily plan.** A form sends its values only when it is
  submitted, so the live preview of cost and expected sales would not update.
  Normal widgets rerun the app on every input. Nothing is saved before *Apply*.
  The draft is kept in `st.session_state`. `fill_draft`, `clear_draft` and
  `follow_saved_state` decide when it is filled, reset or discarded.
- **SQLite on Streamlit Community Cloud.** SQLite needs no secrets and no extra
  service, and it is what the course apps use. The price is temporary storage. The
  app says so on every game screen, and a lost game shows a clear message instead
  of an error.

### What the tests cover and what they do not

- **Covered:** the rules with hand-computed values, accepted and rejected actions,
  separate games, invalid tokens, rollbacks, locked databases, two windows and the
  full five-day games.
- **How:** storage tests use temporary SQLite files. Interface tests drive
  `app.py` with Streamlit's `AppTest`.
- **Not covered:** a real browser, Streamlit Community Cloud, page layout and
  narrow screens. These are checked by hand with `docs/acceptance-checklist.md`.

## Known limits

- Games are stored temporarily and can be lost. A bookmark does not guarantee
  that a game can be resumed.
- Whoever has the link has full access to that game. The link does not identify
  a person.
- The leaderboard has no accounts: one person can enter several times with several
  games, nicknames are not moderated, and it is stored as temporarily as the games.
- The game is deterministic and everything is known in advance. A player who
  understands "3 × min(upper, stock) > min(lower, stock)" can solve it. This is
  intended for a learning game.
- The number of games is not limited and old games are not cleaned up.
- The hint "three times as much gross profit at twice the reference price" holds
  because every unit cost is exactly half the reference price.

## How it could change

- **Persistent storage:** replace SQLite with a hosted database such as Postgres.
  Most storage changes would be concentrated in `db.py`; the dependencies, the
  configuration (a connection secret on the host) and the storage tests would
  also have to change.
- **Accounts:** use `st.login` to identify players, still with one game per
  authorised owner.
- **Accounts for the leaderboard:** with `st.login`, the leaderboard could allow one
  entry per person instead of one per game.
- **More scenarios:** add new keys to `EVENTS` in `logic.py`. Never change an
  existing key.

## Verification

**Automated** (`uv run pytest`, 176 tests, all passing on 24.11.2026). GitHub
Actions (`.github/workflows/tests.yml`) runs the same tests on every push and pull
request:

| File | What it covers |
|---|---|
| `tests/test_games.py` | Separate games, token hash only, rejected and unknown tokens, deleting one game, solo schema left untouched, unknown scenarios |
| `tests/test_kiosk.py` | Purchases, exact cash, rejected quantities and prices, stale day, unknown product, rollback, finished game |
| `tests/test_scenarios.py` | Both event tables against the specification, price tiers, scarce stock, settlement with events, today's event in the UI |
| `tests/test_baseline.py` | Baseline (€229.00 / €184.00), full five-day games (€319.00 / €270.00), results above and below the baseline, budget rule |
| `tests/test_locks.py` | Busy database: message instead of crash, no partial changes, success once after release, no automatic retry, busy delete keeps the link, separate message for page loads, other errors not hidden |
| `tests/test_daily_plan.py` | Daily plan: preview, atomic apply, rejected inputs kept for correction, total above cash, catalogue check, rollback, other games unchanged, day finished or game changed in another window, numeric price comparison, discard, full game through the UI |
| `tests/test_polish.py` | Day result summary (also below the baseline and only for its own game), product names in plan errors |
| `tests/test_leaderboard.py` | Leaderboard: only finished games, score from the saved game, one entry per game, nickname rules (accents allowed, symbols rejected), shared ranks, withdraw, delete, schema upgrade, locks, no tokens on the page |
| `tests/test_csv.py` | CSV content in euros, file name without token, only the own game |
| `tests/test_app.py` | Start page, invalid links, new session via link, two windows, switching links, delete with confirmation, final results |

The expected values are computed by hand in `specs/campus-week.md`, not by the
code under test.

**Not covered by automated tests:** real browsers, Streamlit Community Cloud, page
reloads and bookmarks in a browser, and narrow screens. These are checked by hand
with `docs/acceptance-checklist.md`.

**Manual checks done so far:** P0 prototype on Community Cloud (22.11.2026). Python
3.12 and the build from `uv.lock` work, a reload or bookmark keeps the token,
separate links keep separate data and invalid links are rejected. Whether data
survived a reboot was not clearly recorded.

**Local browser check** (22.11.2026, automated): the acceptance checklist was run
automatically in Chromium (Playwright) against the app on `localhost` with an empty
temporary database, at 1280 px and 375 px width. 30 of 30 checks passed, including
the two-tab cases, the leaderboard, the CSV download and no horizontal scrolling on
the narrow screen. This is not a check of the deployed app.

**Acceptance on the deployed app** (https://39p9i3vcvzvy66yjhja8xk.streamlit.app):

- 22.11.2026, `main` @ `047290e`: the acceptance checklist was run automatically in
  Chromium against the public URL. All workflows passed: invalid input, five days with
  €319.00 against the baseline's €229.00, CSV download, leaderboard (also a nickname
  with accents), resume by link, invalid links, separate games, both two-tab cases,
  delete with cancel and confirm, and no horizontal scrolling at 375 px. Test entries
  and test games were removed afterwards.
- 23.11.2026, `main` @ `c825ef1`: a short check confirmed that the last fix is live
  (no leftover message after deleting a game in two tabs); the test game was deleted.
- Checked by hand on a real phone: the app runs.

**Dependency audit** (22.11.2026, 02:16 and repeated at 15:00 CET):

1. Exported `uv.lock` with `uv export --frozen --all-groups --no-emit-project
   --format requirements-txt` to a temporary file outside the repository.
2. Ran `pip-audit 2.10.1 -r <file> --require-hashes --disable-pip`. It checked 37
   packages.
3. Audited the two platform-specific packages (`colorama`, `watchdog`) separately.

Result: **no known vulnerabilities in all 39 locked packages.** Runtime
dependency: `streamlit` only. Development dependency: `pytest`.

## Origin

Based on the completed Campus Tycoon solo project, commit
`a10728f4edfacce67ff5523d1749ea92a9a360ee`, kept separately in `../campus-tycoon`.
