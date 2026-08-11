from __future__ import annotations

import html
import json
import shutil
import subprocess
from dataclasses import dataclass
from datetime import date
from pathlib import Path
from jinja2 import Environment, FileSystemLoader, select_autoescape

from .config import ROOT, paths
from .models import CommitteeDecision, CompanyResearch, Trade


@dataclass
class ReportArtifacts:
    html_path: Path
    pdf_path: Path


def _chromium() -> str:
    for name in ("chromium", "chromium-browser", "google-chrome", "google-chrome-stable"):
        found = shutil.which(name)
        if found:
            return found
    raise RuntimeError("Chromium/Chrome not found. Run bootstrap-pi.sh or install chromium.")


def _source_map(research: list[CompanyResearch]) -> list[dict]:
    out = []
    seen = set()
    for r in research:
        for source in r.sources:
            key = str(source.url)
            if key in seen:
                continue
            seen.add(key)
            out.append({
                "ticker": r.ticker,
                "id": source.id,
                "title": source.title,
                "url": key,
                "publisher": source.publisher or "",
                "published_at": source.published_at or "",
                "source_type": source.source_type,
            })
    return out


def build_report(
    report_date: date,
    settings: dict,
    screen_rows: list[dict],
    research: list[CompanyResearch],
    decision: CommitteeDecision,
    portfolio_before: dict,
    portfolio_after: dict,
    trades: list[Trade],
    charts: dict[str, str | None],
    history: list[dict],
) -> ReportArtifacts:
    p = paths()
    run_dir = p.reports / report_date.isoformat()
    run_dir.mkdir(parents=True, exist_ok=True)
    html_path = run_dir / f"daily-equity-research-{report_date.isoformat()}.html"
    pdf_path = p.reports / f"daily-equity-research-{report_date.isoformat()}.pdf"

    env = Environment(
        loader=FileSystemLoader(str(ROOT / "templates")),
        autoescape=select_autoescape(["html", "xml"]),
    )
    env.filters["pct"] = lambda x: f"{float(x) * 100:.1f}%" if x is not None else "—"
    env.filters["usd"] = lambda x: f"${float(x):,.2f}" if x is not None else "—"
    env.filters["score"] = lambda x: f"{float(x):.1f}"

    by_ticker = {r.ticker: r for r in research}
    action_research = []
    for target in decision.targets:
        if target.ticker in by_ticker and target.action in {"BUY", "REDUCE", "EXIT", "HOLD"}:
            action_research.append(by_ticker[target.ticker])
    ordered = action_research + sorted(research, key=lambda r: r.score.composite, reverse=True)
    details, used = [], set()
    for r in ordered:
        if r.ticker not in used:
            details.append(r)
            used.add(r.ticker)
        if len(details) >= int(settings["report"]["max_detail_companies"]):
            break

    target_map = {t.ticker: t for t in decision.targets}
    template = env.get_template("daily_report.html")
    rendered = template.render(
        report_date=report_date,
        generated_at=report_date.isoformat(),
        title=settings["report"]["title"],
        decision=decision,
        target_map=target_map,
        screen_rows=screen_rows[: int(settings["report"]["max_watchlist_rows"])],
        research=research,
        details=details,
        portfolio_before=portfolio_before,
        portfolio_after=portfolio_after,
        trades=trades,
        charts=charts,
        sources=_source_map(research),
        history=history,
    )
    html_path.write_text(rendered, encoding="utf-8")

    render_errors = []
    try:
        from weasyprint import HTML
        HTML(filename=str(html_path), base_url=str(run_dir)).write_pdf(str(pdf_path))
    except Exception as exc:
        render_errors.append(f"WeasyPrint: {exc}")

    if not pdf_path.exists() or pdf_path.stat().st_size < 10_000:
        try:
            browser = _chromium()
            cmd = [
                browser, "--headless", "--disable-gpu", "--disable-dev-shm-usage",
                "--no-sandbox", "--allow-file-access-from-files", "--no-pdf-header-footer",
                f"--print-to-pdf={pdf_path}", html_path.as_uri(),
            ]
            result = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, timeout=90)
            if result.returncode != 0:
                render_errors.append(f"Chromium: {result.stderr[-800:]}")
        except Exception as exc:
            render_errors.append(f"Chromium: {exc}")

    if not pdf_path.exists() or pdf_path.stat().st_size < 10_000:
        raise RuntimeError("PDF rendering failed. " + " | ".join(render_errors))
    return ReportArtifacts(html_path=html_path, pdf_path=pdf_path)
