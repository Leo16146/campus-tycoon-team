# Campus Week: a campus kiosk trading game

Team project for Introduction to Programming at Nova SBE. Campus Week extends the
completed solo app *Campus Tycoon* into a game that several people can play at the
same time, each in a private game.

You run a campus kiosk with coffee, water and granola bars for five trading days.
Every day has an event that changes demand, for example an Open Day where nobody
pays a premium price. At the end the app compares your result with a simple
baseline strategy.

## Team and deployment

> **Missing before submission:** the deployed URL and the names and student numbers
> of all team members. These details have not been added yet.

| | |
|---|---|
| Deployed app (from `main`, `app.py`, Python 3.12) | *not deployed yet* |
| Team members and student numbers | *to be added* |

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
- **How to play** on the start page explains the goal, the daily steps and the score.
- **Final comparison** after day 5: your overall gain / loss next to the baseline
  strategy, the signed difference and the gross profit for each day.
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
| `specs/first-feature.md`, `docs/product-brief.html` | Documents of the original solo project |

## Access and storage

- **Tokens.** A new game gets a random token (`secrets.token_urlsafe(32)`). The
  database stores only its SHA-256 hash. Every database function receives the
  token, looks up the game by its hash inside the transaction and works only on
  that game's rows. A game id from the browser never grants access.
- **Malformed links** are rejected before the database is opened.
- **Storage** is SQLite on the server. Each action (buy, set price, trade,
  delete) is one transaction: it is saved completely or not at all.
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

## Known limits

- Games are stored temporarily and can be lost. A bookmark does not guarantee
  that a game can be resumed.
- Whoever has the link has full access to that game. The link does not identify
  a person.
- There is no shared competition or leaderboard between games.
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
- **Leaderboard:** compare results per scenario, which is fair because all players
  of a scenario get the same events.
- **More scenarios:** add new keys to `EVENTS` in `logic.py`. Never change an
  existing key.

## Verification

**Automated** (`uv run pytest`, 132 tests). All pass on `main` @ `5471fe0`, run in a
fresh copy on 22.11.2026:

| File | What it covers |
|---|---|
| `tests/test_games.py` | Separate games, token hash only, rejected and unknown tokens, deleting one game, solo schema left untouched, unknown scenarios |
| `tests/test_kiosk.py` | Purchases, exact cash, rejected quantities and prices, stale day, unknown product, rollback, finished game |
| `tests/test_scenarios.py` | Both event tables against the specification, price tiers, scarce stock, settlement with events, today's event in the UI |
| `tests/test_baseline.py` | Baseline (€229.00 / €184.00), full five-day games (€319.00 / €270.00), results above and below the baseline, budget rule |
| `tests/test_locks.py` | Busy database: message instead of crash, no partial changes, success once after release, no automatic retry, busy delete keeps the link, separate message for page loads, other errors not hidden |
| `tests/test_daily_plan.py` | Daily plan: preview, atomic apply, rejected inputs kept for correction, total above cash, catalogue check, rollback, other games unchanged, day finished or game changed in another window, numeric price comparison, discard, full game through the UI |
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

**Not done yet:** deploying the finished app and running the acceptance checklist
on it.

**Dependency audit** (22.11.2026):

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
