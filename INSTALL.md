# Installation - Raspberry Pi / OpenClawOS

## 1. Verify the existing OpenClaw installation

```bash
openclaw gateway status
openclaw channels status --probe
```

Telegram must already be configured in OpenClaw. If it is not:

```bash
openclaw configure --section channels
```

Send the Telegram bot at least one message before testing outbound delivery.

## 2. Copy and unpack

From your computer:

```bash
scp openclaw-stock-analyst-pi.zip <pi-user>@<pi-host>:~/
```

On the Pi:

```bash
ssh <pi-user>@<pi-host>
unzip openclaw-stock-analyst-pi.zip
cd openStawks
```

## 3. Install

```bash
chmod +x bootstrap-pi.sh
./bootstrap-pi.sh
```

Enter the Telegram target when requested. A numeric private-chat ID is the most reliable target.

The script will install dependencies, create the restricted OpenClaw agent, install its skills, initialize the hypothetical model portfolio, register the weekday 08:10 ET cron job, run tests, generate a sample PDF, send it to Telegram, and run the security/health check.

## 4. Confirm success

The installer should finish with all `stock-analyst doctor` checks showing `OK`, and Telegram should receive a document labeled as a sample report.

Manual checks:

```bash
source .venv/bin/activate
stock-analyst doctor
stock-analyst sample-report --send
```

Full live dry run without Telegram delivery:

```bash
stock-analyst daily --dry-run --force
```

Full live run with PDF delivery:

```bash
stock-analyst daily --force
```

## 5. USB SSD storage - recommended

Edit `.env`:

```dotenv
STOCK_ANALYST_DATA_DIR=/mnt/ssd/stock-analyst
```

Then rerun:

```bash
./bootstrap-pi.sh
```

The source tree and persistent model-portfolio/report data are intentionally separate.

## Daily operation

No manual action is required. OpenClaw Gateway cron runs the project at 08:10 America/New_York on weekdays. The pipeline checks the NYSE trading calendar and does not send a normal report on exchange holidays.

Inspect the scheduler:

```bash
openclaw cron list --all
```

Inspect project logs:

```bash
ls -lt ~/stock-analyst-data/logs/
```

See `README_FULL.md` for configuration, methodology, security boundaries, update/uninstall procedures, and troubleshooting.
