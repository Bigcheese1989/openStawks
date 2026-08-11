from __future__ import annotations

import json
import os
import re
import subprocess
from datetime import date
from typing import TypeVar, Type

from pydantic import BaseModel, ValidationError

from .config import load_environment, load_prompt_rules
from .models import CompanyResearch, CommitteeDecision

T = TypeVar("T", bound=BaseModel)


def _model_args(kind: str) -> list[str]:
    load_environment()
    env_name = "OPENCLAW_RESEARCH_MODEL" if kind == "research" else "OPENCLAW_COMMITTEE_MODEL"
    model = os.getenv(env_name, "").strip()
    thinking = os.getenv("OPENCLAW_THINKING", "high").strip()
    args: list[str] = []
    if model:
        args.extend(["--model", model])
    if thinking:
        args.extend(["--thinking", thinking])
    return args


def call_openclaw(prompt: str, session_key: str, kind: str, timeout: int = 900) -> str:
    load_environment()
    agent = os.getenv("OPENCLAW_AGENT_ID", "stock-analyst")
    cmd = [
        "openclaw", "agent", "--agent", agent,
        "--session-key", session_key,
        "--message-file", "-",
        "--json",
        "--timeout", str(timeout),
        *_model_args(kind),
    ]
    proc = subprocess.run(
        cmd,
        input=prompt,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        timeout=timeout + 60,
    )
    if proc.returncode != 0:
        raise RuntimeError(f"OpenClaw agent run failed: {proc.stderr.strip()[-1200:]}")
    try:
        envelope = json.loads(proc.stdout)
    except json.JSONDecodeError as exc:
        raise RuntimeError(f"OpenClaw returned non-JSON CLI output: {proc.stdout[:500]}") from exc
    text = _extract_text(envelope)
    if not text:
        raise RuntimeError("OpenClaw returned no assistant text")
    return text


def _extract_text(obj) -> str:
    if isinstance(obj, dict):
        if isinstance(obj.get("final"), str) and obj["final"].strip():
            return obj["final"].strip()
        for key in ("payloads", "result"):
            if key in obj:
                found = _extract_text(obj[key])
                if found:
                    return found
        if isinstance(obj.get("text"), str) and obj["text"].strip():
            return obj["text"].strip()
        for value in obj.values():
            found = _extract_text(value)
            if found:
                return found
    elif isinstance(obj, list):
        texts = [_extract_text(x) for x in obj]
        texts = [x for x in texts if x]
        return "\n".join(texts)
    return ""


def _json_from_text(text: str) -> dict:
    cleaned = text.strip()
    if cleaned.startswith("```"):
        cleaned = re.sub(r"^```(?:json)?\s*", "", cleaned, flags=re.I)
        cleaned = re.sub(r"\s*```$", "", cleaned)
    try:
        return json.loads(cleaned)
    except json.JSONDecodeError:
        start = cleaned.find("{")
        end = cleaned.rfind("}")
        if start >= 0 and end > start:
            return json.loads(cleaned[start:end + 1])
        raise


def _validate_or_repair(text: str, model: Type[T], session_key: str, kind: str) -> T:
    try:
        return model.model_validate(_json_from_text(text))
    except (json.JSONDecodeError, ValidationError) as first_error:
        repair = f"""Your previous response failed strict JSON/schema validation.
Return ONLY a corrected JSON object. Do not add markdown or commentary.
Do not add factual claims or sources that were absent from the prior response; this is formatting/schema repair only.

SCHEMA:
{json.dumps(model.model_json_schema(), indent=2)}

PRIOR RESPONSE:
{text}

VALIDATION ERROR:
{first_error}
"""
        repaired = call_openclaw(repair, session_key + "-repair", kind, timeout=300)
        return model.model_validate(_json_from_text(repaired))


def research_company(report_date: date, candidate: dict, price_context: dict) -> CompanyResearch:
    rules = load_prompt_rules()
    schema = CompanyResearch.model_json_schema()
    prompt = f"""Research this equity for today's read-only daily research report.
Use web_search/web_fetch as needed. Apply the equity-research and bear-case skills.
Return ONLY one JSON object matching the schema below; no markdown fences and no prose outside JSON.

DATE: {report_date.isoformat()}
CANDIDATE:
{json.dumps(candidate, indent=2, default=str)}
PRICE/MOMENTUM CONTEXT FROM DETERMINISTIC CODE:
{json.dumps(price_context, indent=2, default=str)}

RESEARCH POLICY:
{json.dumps(rules, indent=2)}

SCORING:
- fundamentals: business quality, financial strength, earnings/cash-flow quality and durability.
- valuation: attractiveness of valuation relative to growth, history, peers and reasonable scenarios.
- momentum: use the supplied deterministic momentum data plus relevant earnings/estimate direction.
- catalysts: evidence-backed upcoming or continuing drivers.
- risk: 100 means low/favorable risk; 0 means severe/unacceptable risk.
- conclusion may be BUY, WATCH, or AVOID. Do not force BUY.

SOURCE REQUIREMENTS:
- `sources` must contain real URLs you actually inspected or relied upon.
- Use unique IDs like S1, S2, S3.
- Every thesis/risk/catalyst item must list supporting source_ids.
- Prefer SEC/official company sources for financial facts and high-quality independent news for current developments.
- Never invent consensus estimates or future event dates.

SCHEMA:
{json.dumps(schema, indent=2)}
"""
    ticker = candidate["ticker"].replace("-", "_")
    text = call_openclaw(prompt, f"research-{report_date:%Y%m%d}-{ticker}", "research")
    return _validate_or_repair(text, CompanyResearch, f"research-{report_date:%Y%m%d}-{ticker}", "research")


def run_committee(report_date: date, research: list[CompanyResearch], portfolio_state: dict, settings: dict) -> CommitteeDecision:
    schema = CommitteeDecision.model_json_schema()
    compact = [r.model_dump(mode="json") for r in research]
    prompt = f"""Act as the investment committee for a hypothetical model portfolio.
Apply the investment-committee skill. Use ONLY the supplied research packages and portfolio state; web research is allowed only to verify a material ambiguity.
Return ONLY one JSON object matching the schema; no markdown and no additional prose.

DATE: {report_date.isoformat()}
PORTFOLIO CONSTRAINTS:
{json.dumps(settings['portfolio'], indent=2)}
CURRENT MODEL PORTFOLIO (not the user's real portfolio):
{json.dumps(portfolio_state, indent=2, default=str)}
RESEARCH PACKAGES:
{json.dumps(compact, indent=2, default=str)}

DECISION RULES:
- No more than {settings['portfolio']['maximum_new_buys_per_day']} new BUY actions.
- Maximum target weight per stock: {settings['portfolio']['maximum_position_weight']:.1%}.
- Keep at least {settings['portfolio']['minimum_cash_weight']:.1%} cash in aggregate.
- Prefer HOLD/WATCH/no change when evidence is insufficient.
- `targets` should describe only positions whose desired target/action is meaningful; deterministic code preserves omitted current holdings.
- `target_weight` is a fraction from 0 to 1.
- EXIT requires target_weight 0.
- The model portfolio is an evaluation device, not a brokerage account.

SCHEMA:
{json.dumps(schema, indent=2)}
"""
    text = call_openclaw(prompt, f"committee-{report_date:%Y%m%d}", "committee")
    return _validate_or_repair(text, CommitteeDecision, f"committee-{report_date:%Y%m%d}", "committee")
