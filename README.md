# openStawks

Automated, read-only stock research for OpenClaw on Raspberry Pi. It screens a stock universe, delegates bounded qualitative research to an OpenClaw agent, maintains a hypothetical model portfolio, renders a chart-heavy PDF, and sends the daily report to Telegram.

## What it does

- Deterministic market-data ingestion, scoring, portfolio accounting, and risk limits.
- OpenClaw-assisted company research, catalyst analysis, bear-case review, and investment synthesis.
- PDF reports with market dashboards, price/fundamental charts, recommendations, watchlist, sources, and model-portfolio performance.
- Daily scheduling through OpenClaw cron.
- Telegram PDF delivery.
- No broker integration, credentials, portfolio access, or trade execution path.

## Raspberry Pi install

```bash
git clone https://github.com/Bigcheese1989/openStawks.git
cd openStawks
chmod +x bootstrap-pi.sh
./bootstrap-pi.sh
```

The installer expects an existing working OpenClaw/OpenClawOS installation with a configured model provider. Telegram can be configured before or during setup.

## Documentation

- [Full README](README_FULL.md)
- [Installation guide](INSTALL.md)
- [Methodology](docs/METHODOLOGY.md)
- [Security model](docs/SECURITY.md)

## Build artifacts

The repository always contains the full unpacked source. Every push to `main` also runs **Package source artifacts** and produces two downloadable GitHub Actions artifacts:

- `openclaw-stock-analyst-pi-zip` containing `openclaw-stock-analyst-pi.zip`
- `openclaw-stock-analyst-pi-tar-gz` containing `openclaw-stock-analyst-pi.tar.gz`

Open the repository's **Actions** tab, select **Package source artifacts**, then open the latest successful run; the two downloads appear in that run's **Artifacts** section.

## Important boundary

openStawks is a research and paper/model-portfolio system. It deliberately contains no Interactive Brokers SDK, brokerage credentials, trading API, or order-placement implementation. You remain the execution layer.
