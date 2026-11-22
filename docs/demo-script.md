# Demo script and walkthrough preparation

A short plan for the live demo and the repository walkthrough. It lists what to show
and which questions to be ready for. It does **not** contain answers to learn by
heart. Each question points to the place in the code where the answer can be
found and explained in your own words.

## Before the presentation

- Open the deployed URL a few minutes early so the app is awake.
- After every merge to `main`, open the app once. If it shows an error right after an
  update, use *Manage app → Reboot app* on Streamlit Community Cloud. On 22.11.2026
  an `ImportError` after an update disappeared after a reboot.
- Use one browser window with only the tabs you need. Close dashboards and the agent.
- Start new games during the demo. Do not rely on games saved earlier: storage on
  Streamlit Community Cloud is temporary.
- Keep a second tab ready for step 5.

## Live demo (about 5 minutes)

1. **Start page.** Point out *How to play* and the two scenarios. Start
   *Exam Week*. The private link appears in the address bar.
2. **Today's event and the plan.**
   - Show the demand table for *Normal day*.
   - Enter *Buy* 5 / 5 / 5 and the prices 8.00 / 2.00 / 4.00.
   - Point at the preview (cost, demand, expected sales, total, cash after). Show
     that *Start trading day* is disabled until the plan is applied.
3. **Invalid input.**
   - Type `abc` as the coffee price and apply. The message names the product, and
     nothing is saved.
   - Fix the price and apply the plan.
4. **Trade and result.** Start the trading day.
   - The summary shows: *Day 1 result: 15 units sold · revenue €70.00 · gross
     profit €52.50 · baseline gross profit €35.00*.
5. **Protection against outdated windows** (optional, if time allows).
   - Open the same link in the second tab and type a purchase there without
     applying it.
   - In the first tab, apply a price change.
   - Back in the second tab, click *Apply*. The plan is rejected and the current
     state is shown.
6. **Final comparison.** If time allows, play days 2–5 with the strategy in
   `docs/acceptance-checklist.md`. The result is €319.00 against a baseline of
   €229.00, a difference of +€90.00.
   - The trap is Open Day: with premium prices, nothing sells that day.
7. **Leaderboard and export.** Publish the result under a nickname, show the rank and
   the leaderboard on the start page, and download the CSV. Classmates can start
   their own game from the URL and appear on the same leaderboard.

**If something fails:** say what happened and continue.

- **The app is asleep:** wait for it to wake up while you explain the idea.
- **A game is lost:** the app shows that the link is no longer available. Explain
  why storage is temporary and start a new game.
- **The database is busy:** the app asks you to try again. Nothing was changed.
- **An error right after an update:** reboot the app (see "Before the presentation").

## Questions to be ready for

The teaching staff can ask anyone about any part. For each question, open the
named place and explain what happens, why it was built that way and what its
limits are.

| Topic | Question | Where to look |
|---|---|---|
| Money | Why are all amounts whole cents? How is "4.01" turned into 401? | `logic.price_in_cents`, `app.euros` |
| Rules | How is today's demand calculated for a price? What happens above twice the reference price? | `logic.EVENTS`, `logic.demand`, `logic.sales_for_product` |
| Rules | Why do the events give demand per price tier instead of a factor? | README "How it works and why" |
| Baseline | What exactly does the baseline do each day? Why is it not the best strategy? | `logic.baseline_restock`, `logic.baseline_results` |
| Score | What is the difference between gross profit and overall gain / loss? | `logic.final_result`, README "Rules in short" |
| Storage | Where is the data stored? What happens after a restart on Streamlit Cloud? | `db.initialize`, README "Access and storage" |
| Access | How does a link give access to exactly one game? Why is only a hash stored? | `db.check_token`, `db.authorized_game`, `db.create_game` |
| Access | Why private links instead of passwords? What are their limits? | README "Known limits" |
| Transactions | What does `BEGIN IMMEDIATE` do? What happens if an error occurs halfway? | `db.transaction` |
| Concurrency | What happens if two windows change the same game at the same time? | `db.snapshot`, `db.check_unchanged`, `app.follow_saved_state` |
| Interface | Why does the daily plan not use `st.form`? When are the input fields reset? | `app.fill_draft`, `app.clear_draft`, `app.draft_changed` |
| Errors | What does the player see for invalid input, an invalid link or a busy database? | `app.notify`, `db.checked_plan`, `app.stop_when_busy` |
| Tests | What do the tests cover, and what do they not cover? How do they avoid touching real data? | README "Verification", `tests/` |
| Leaderboard | Why can a player not fake a score? Why is one entry per person not guaranteed? How are equal scores ranked? | `db.publish_result`, `db.leaderboard`, README "Known limits" |
| Change | How would you add persistent storage or accounts? What would change? | README "How it could change" |

## A good way to practise

1. Pick a question.
2. Open the file and read the function aloud.
3. Explain it without notes in about one minute: what it does, why, and one limit.
4. Check yourself by changing a value in a test and predicting the result before
   running `uv run pytest`.
