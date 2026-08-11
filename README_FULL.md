# Stock Analyst for OpenClaw on Raspberry Pi

A read-only daily US-equity research bot for an existing OpenClaw/OpenClawOS Raspberry Pi installation.

It does **not** connect to Interactive Brokers, Alpaca, a bank, or any brokerage account. It maintains only a hypothetical model portfolio, performs public-market research, generates an illustrated PDF, and sends that PDF through your existing OpenClaw Telegram channel.

## What it does each trading day

1. Fetches the current S&P 500 universe.
2. Downloads one year of price/volume history.
3. Runs a deterministic quantitative screen.
4. Selects the top candidates plus existing model-portfolio holdings.
5. Calls a dedicated, restricted OpenClaw research agent for each company.
6. Runs a separate investment-committee turn.
7. Enforces deterministic portfolio constraints.
8. Updates the hypothetical model portfolio and performance history.
9. Generates charts and an HTML report.
10. Uses WeasyPrint (with Chromium fallback) to create a PDF.
11. Sends the PDF to Telegram.

Default schedule: **08:10 America/New_York, Monday–Friday**. The Python pipeline checks the NYSE calendar and skips exchange holidays.

## Security design

The model-facing OpenClaw agent is limited to:

- `web_search`
- `web_fetch`
- workspace-only `read`

It is explicitly denied:

- shell/process execution
- file writes/edits/patches
- browser automation
- messaging
- cron changes
- gateway changes
- skill modification

The daily scheduler is an operator-owned OpenClaw **command cron** entry. The LLM cannot create or modify it.

There is no broker SDK, broker credential, order endpoint, or trading API in this repository.

See `docs/SECURITY.md`.

---

# Installation on your Raspberry Pi

## 1. Prerequisites

You need:

- Raspberry Pi OS / Debian-family ARM64 system
- existing working OpenClaw/OpenClawOS Gateway
- an LLM/provider already configured in OpenClaw
- Telegram already connected to OpenClaw
- internet access
- preferably a USB SSD for persistent data

Confirm OpenClaw first:

```bash
openclaw gateway status
openclaw channels status --probe
```

If Telegram is not configured yet, configure it in OpenClaw before continuing:

```bash
openclaw configure --section channels
```

Send your Telegram bot a message at least once so it is allowed to reply to you.

## 2. Copy this repository to the Pi

If you downloaded the ZIP on another computer:

```bash
scp openclaw-stock-analyst-pi.zip <pi-user>@<pi-host>:~/
ssh <pi-user>@<pi-host>
unzip openclaw-stock-analyst-pi.zip
cd openStawks
```

Or clone it directly:

```bash
git clone https://github.com/Bigcheese1989/openStawks.git
cd openStawks
```

## 3. Run the automated installer

```bash
chmod +x bootstrap-pi.sh
./bootstrap-pi.sh
```

The installer will:

- verify Linux/architecture and the existing OpenClaw CLI
- install Python/PDF-renderer native libraries/Chromium/fonts if `apt` is available
- create `.venv`
- install Python dependencies
- create the local SQLite model-portfolio database
- create/sync `~/.openclaw/workspace-stock-analyst`
- create the `stock-analyst` OpenClaw agent if needed
- apply the restrictive tool policy
- install/update the three workspace skills
- register the OpenClaw cron job
- run the test suite
- generate a synthetic sample PDF
- send that sample PDF through Telegram
- run the final health/security check

The only normal installer input is your Telegram delivery target.

## 4. Telegram target

`TELEGRAM_TARGET` is stored in `.env`.

Use the same target format accepted by your working OpenClaw Telegram channel. A numeric private-chat ID is the most reliable option.

Example:

```dotenv
TELEGRAM_TARGET=123456789
```

The installer sends a **SAMPLE REPORT** before declaring success. If that PDF arrives, the complete PDF/Telegram path works.

---

# Data location

Default:

```text
~/stock-analyst-data/
├── cache/
├── charts/
├── data/
├── database/
│   └── stock_analyst.sqlite3
├── logs/
├── reports/
└── research/
```

For a USB SSD, edit `.env` before/after installation:

```dotenv
STOCK_ANALYST_DATA_DIR=/mnt/ssd/stock-analyst
```

Then rerun:

```bash
./bootstrap-pi.sh
```

The installer is designed to be idempotent and does not reset an existing model portfolio.

---

# Manual validation

Activate the environment:

```bash
cd ~/openStawks
source .venv/bin/activate
```

Health/security check:

```bash
stock-analyst doctor
```

Generate another synthetic report without LLM or market-data calls:

```bash
stock-analyst sample-report
```

Generate and send the synthetic report:

```bash
stock-analyst sample-report --send
```

Run the full live pipeline without sending Telegram:

```bash
stock-analyst daily --dry-run --force
```

Run the full live pipeline and send the resulting PDF:

```bash
stock-analyst daily --force
```

`--force` only bypasses the NYSE-calendar skip; it does not alter research or portfolio constraints.

---

# OpenClaw scheduling

The installer creates one Gateway cron job named:

```text
Stock Analyst Daily PDF
```

Inspect it:

```bash
openclaw cron list --all
```

Inspect recent runs:

```bash
openclaw cron list --all --json
```

The schedule is configured by `scripts/install-cron.sh`:

```text
08:10 America/New_York, Monday-Friday
```

To change it, edit that script and rerun:

```bash
./scripts/install-cron.sh
```

The script replaces only the job with the exact project-owned name.

---

# Configuration

Main configuration:

```text
config/settings.yaml
```

Important defaults:

```yaml
research_count: 6
screen_count: 25

portfolio:
  starting_cash: 100000
  minimum_cash_weight: 0.10
  maximum_position_weight: 0.10
  maximum_daily_turnover: 0.15
  minimum_trade_weight: 0.005
  maximum_new_buys_per_day: 3
```

The scoring weights for the deterministic shortlist are also in `config/settings.yaml`.

Research/source rules are in:

```text
config/prompt_rules.yaml
```

Do not put credentials in those files.

## OpenClaw model selection

By default the research agent inherits the model route already configured in OpenClaw.

Optional `.env` overrides:

```dotenv
OPENCLAW_RESEARCH_MODEL=
OPENCLAW_COMMITTEE_MODEL=
OPENCLAW_THINKING=high
```

If blank, the configured OpenClaw default is used.

---

# PDF contents

A live PDF contains:

- executive summary and market stance
- model-portfolio actions or explicit `NO CHANGE`
- market relative-performance graph
- sector-performance graph
- quantitative-ranking graph
- current model-portfolio allocation
- model portfolio vs S&P 500 benchmark history
- detailed researched-company sections
- price/50-day/200-day charts
- research scorecards
- thesis and supporting source IDs
- bear case and risks
- catalysts
- thesis-invalidation conditions
- bear/base/bull valuation scenarios
- watchlist/quantitative shortlist
- complete source URL section

Validated research JSON is retained alongside the report under `research/YYYY-MM-DD/`.

---

# Updating

If this folder is a Git checkout:

```bash
./update.sh
```

That performs a fast-forward pull, updates Python dependencies, resyncs skills, reapplies the OpenClaw security policy, reinstalls the project cron entry, runs tests, and runs the health check.

---

# Uninstalling

Remove the cron job and dedicated OpenClaw agent while preserving model-portfolio/history data:

```bash
./uninstall.sh
```

Delete persistent data too:

```bash
./uninstall.sh --purge-data
```

The script does not uninstall OpenClaw.

---

# Troubleshooting

## `stock-analyst doctor`

Start here:

```bash
source .venv/bin/activate
stock-analyst doctor
```

## Telegram PDF did not arrive

Verify OpenClaw itself can send a local document:

```bash
openclaw message send \
  --channel telegram \
  --target YOUR_TARGET \
  --message "OpenClaw document test" \
  --media "$HOME/stock-analyst-data/reports/sample-report.pdf"
```

Then verify:

```bash
openclaw channels status --probe
```

## Research JSON failure

The original model output is saved under:

```text
~/stock-analyst-data/research/YYYY-MM-DD/
```

The pipeline allows one deterministic schema-repair turn. It does not silently invent missing citations or investment facts.

## Chromium / PDF problems

Check:

```bash
command -v chromium || command -v chromium-browser
chromium --version 2>/dev/null || chromium-browser --version
```

Re-run `./bootstrap-pi.sh` to reinstall required OS packages.

---

# Market-data limitation

The initial implementation uses `yfinance` for price/volume history because it requires no additional API account and makes installation simple. It is intentionally isolated in `stock_analyst/market.py`.

For meaningful capital, replace that layer with a licensed/reliable provider appropriate to your requirements. Do not treat an unofficial free quote source as institutional-grade market infrastructure.

The qualitative OpenClaw research is separately required to use real source URLs and prioritize filings/company materials/high-quality current news.

---

# Relevant OpenClaw documentation

- Raspberry Pi: https://docs.openclaw.ai/install/raspberry-pi
- Agents: https://docs.openclaw.ai/cli/agents
- Agent workspace: https://docs.openclaw.ai/concepts/agent-workspace
- Skills: https://docs.openclaw.ai/skills
- Tool policy: https://docs.openclaw.ai/tools/multi-agent-sandbox-tools
- Cron: https://docs.openclaw.ai/automation/cron-jobs
- Telegram/document sending: https://docs.openclaw.ai/cli/message
