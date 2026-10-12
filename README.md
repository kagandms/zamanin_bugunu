# Zamanın Bugünü – Telegram & Threads Otomasyonu

Production-oriented Python bot that turns "On This Day" events into Turkish Telegram channel messages and Threads posts, enriches them with AI-generated copy, attaches an image, and posts them automatically.

![Sample output 1](docs/assets/bot-sample-output-1.png)
![Sample output 2](docs/assets/bot-sample-output-2.png)

## What It Does

- fetches events from the Turkish Wikipedia `onthisday` feed
- prioritizes Turkey-related events before falling back to other notable items
- rewrites selected events into short, engaging posts via OpenRouter AI
- downloads a Wikipedia image when available, otherwise generates a fallback image URL
- posts the formatted content to a Telegram Channel and Threads account
- stores posted content in a local database to reduce repeats

## Stack

- Python 3.11
- `httpx` for async HTTP calls and API integrations (Telegram & Threads)
- `SQLAlchemy` + `aiosqlite` for async persistence
- `pydantic-settings` for configuration
- GitHub Actions for scheduled execution

## Project Layout

```text
src/
  core/        configuration and logging
  data/        SQLAlchemy models and repository layer
  services/    content, AI, image, Telegram, and Threads integration
  utils/       text processing helpers
tests/         unit tests
archive/       deprecated pre-v4 reference scripts
docs/assets/   README screenshots
```

## Quick Start

1. Create a virtual environment and install dependencies.

```bash
python3.11 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

2. Create your local environment file.

```bash
cp .env.example .env
```

3. Run the bot in safe mode first.

```bash
python -m src.main
```

Set `DRY_RUN=true` in `.env` while validating the end-to-end flow. Switch it to `false` only after credentials and posting behavior are confirmed.

## Required Environment Variables

| Variable | Required | Purpose |
| --- | --- | --- |
| `TELEGRAM_BOT_TOKEN` | yes | Telegram Bot API token |
| `TELEGRAM_CHANNEL_ID` | yes | Telegram Channel username/ID (e.g. @your_channel) |
| `THREADS_ACCESS_TOKEN` | yes | Threads Graph API access token |
| `THREADS_USER_ID` | yes | Threads account user ID |
| `OPENROUTER_API_KEY` | yes | OpenRouter API key |
| `DATABASE_URL` | no | defaults to local SQLite |
| `DRY_RUN` | no | disables posting when `true` |

Threads Insights collection needs the `threads_manage_insights` permission. Verified direct-reply attribution also needs `threads_read_replies`; if Meta denies that endpoint, the report keeps organic reply counts unknown while showing the raw replies metric.

## GitHub Actions

The scheduled workflow lives at `.github/workflows/schedule.yml`.

Required repository secrets:

- `TELEGRAM_BOT_TOKEN`
- `TELEGRAM_CHANNEL_ID`
- `THREADS_ACCESS_TOKEN`
- `THREADS_USER_ID`
- `OPENROUTER_API_KEY`

## Operational Notes

- Runtime state uses SQLite at `sqlite+aiosqlite:///bot_data.db` by default. The scheduled workflow commits this database back to its checkout after the bot and analytics steps so publication history survives scheduled runs.
- Istanbul calendar days define the daily publication limit. A reserved or failed publication does not consume the limit; an event counts once after a confirmed main post on either platform.
- The additive migration preserves `post_history`. Legacy Threads IDs are imported with unknown publication time and state; the reservation timestamp is not reported as a publication time.
- `post_history.publication_status` summarizes each event as reserved, published, partial, failed, unknown, or dry-run. `platform_publications` and `publication_parts` retain platform outcomes and each published message/thread part. `metric_snapshots` retains one observation for each Threads part and age window (`24h`, `72h`, `7d`); failed observations are retried in place. The report includes target age, actual post age, and observation time.
- Threads Insights values missing from the API remain unknown. A permission or network error is separate from a metric value of zero. The report labels late or missed windows and reports direct replies by verified ownership when that endpoint is authorized; it never subtracts a guessed number from raw replies.
- Run analytics with `python3 src/analytics.py`. The CLI loads environment variables without reading `.env` and requires only `THREADS_ACCESS_TOKEN`, `THREADS_USER_ID`, and optionally `DATABASE_URL`. Its workflow step receives only the two Threads secrets.
- No automatic repost occurs after a confirmed main post. A reserved event that has no confirmed main part remains in deduplication history for manual review, and an ambiguous publish timeout is recorded as unknown.
- Logs are written to `logs/bot.log` locally.

## Tests

```bash
pytest -q
```

## Entry Points

- Supported runtime: `python -m src.main`
- Legacy reference scripts: `archive/`

### Analytics synchronization outcomes and retry history

The default analytics CLI performs synchronization and returns a structured summary: `due`, `attempted`, `success`, `failed`, `missed`, `unknown_time`, and separate optional reply lookup counts. Due counts outstanding windows selected at the start of the run. Attempted/success/failed refer to basic Insights client attempts; missed counts windows outside the allowed observation timing. A slow successful response can therefore be both an API success and a missed canonical window.

Exit codes are `0` when basic Insights operations succeed or no eligible windows exist, `2` when all attempted basic Insights operations fail, `3` when some basic operations fail alongside successes, and `1` for fatal initialization/database/report errors. Missing optional reply permissions do not fail successful basic Insights. The workflow's existing `if: always()` DB-save step retains both successful results and failure evidence after a nonzero sync exit. No blanket error suppression is used for analytics.

Use `python src/analytics.py --report-only` to read an already migrated DB without synchronization, API credentials or migration. This command fails if the schema is unavailable; it does not conceal sync failures.

`metric_snapshots` holds one canonical result per `(part_id, window)`. Both collector and repository use the same SQLite conditional UPSERT: on-time success outranks late success, which outranks missed windows, which outrank unsuccessful attempts. Within the same successful class the earliest observation wins; within unsuccessful attempts the latest error is canonical. Equal timestamps keep the incumbent. Later failures cannot erase a successful result or turn a real zero into NULL. Only the specified part/window conflict is handled; other integrity errors propagate.

`metric_attempts` preserves each completed Insights client attempt, including errors, response times and optional reply attribution evidence. Attempts and the canonical candidate commit atomically. SQLite triggers prohibit attempt updates and deletes. Idempotent runs that make no new request do not append attempts. Existing canonical rows are preserved by the additive migration; previous attempts are not fabricated from them.

Window selection time, Insights request start, Insights response observation and reply observation are distinct timestamps. Production uses a fresh UTC clock reading at each boundary; deterministic clocks remain injectable for tests. Replies never shift the recorded Insights observation time. An Insights response outside the allowed window remains in attempt history but cannot backfill the canonical window with current metrics.

Reply pagination follows `paging.next`, not page length or the presence of an `after` cursor alone. Meta's [official Graph SDK](https://github.com/facebook/facebook-python-business-sdk/blob/main/facebook_business/api.py) notes that terminal pages may still have `after`; the [Meta Graph pagination documentation](https://developers.meta.com/vr/documentation/native/ps-subscriptions-s2s/) identifies absence of `paging.next` as completion. Empty/short pages with continuation are followed. Returned next URLs are validated against the expected endpoint and used only to recover the cursor. Repeated cursors, conflicting reply ownership, malformed metadata, unverified parent/ownership, and the 100-page limit produce `unknown`, without claiming a complete organic count.
