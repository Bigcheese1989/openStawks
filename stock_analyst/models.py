from __future__ import annotations

from datetime import date
from typing import Literal
from pydantic import BaseModel, Field, HttpUrl, field_validator, model_validator


class Source(BaseModel):
    id: str
    title: str
    url: HttpUrl
    publisher: str | None = None
    published_at: str | None = None
    source_type: Literal["regulatory", "company", "news", "market-data", "other"] = "other"


class CitedPoint(BaseModel):
    text: str
    source_ids: list[str] = Field(default_factory=list)


class ScoreCard(BaseModel):
    fundamentals: int = Field(ge=0, le=100)
    valuation: int = Field(ge=0, le=100)
    momentum: int = Field(ge=0, le=100)
    catalysts: int = Field(ge=0, le=100)
    risk: int = Field(ge=0, le=100, description="100 means low risk / favorable risk profile")

    @property
    def composite(self) -> float:
        return round(
            self.fundamentals * 0.30
            + self.valuation * 0.20
            + self.momentum * 0.15
            + self.catalysts * 0.20
            + self.risk * 0.15,
            1,
        )


class ValuationScenario(BaseModel):
    bear: float | None = None
    base: float | None = None
    bull: float | None = None
    currency: str = "USD"
    assumptions: list[str] = Field(default_factory=list)


class CompanyResearch(BaseModel):
    ticker: str
    company_name: str | None = None
    sector: str | None = None
    conclusion: Literal["BUY", "WATCH", "AVOID"]
    confidence: float = Field(ge=0, le=1)
    score: ScoreCard
    summary: str
    thesis: list[CitedPoint]
    risks: list[CitedPoint]
    catalysts: list[CitedPoint]
    invalidation: list[str]
    valuation: ValuationScenario = Field(default_factory=ValuationScenario)
    sources: list[Source]

    @field_validator("ticker")
    @classmethod
    def normalize_ticker(cls, value: str) -> str:
        return value.strip().upper()

    @model_validator(mode="after")
    def validate_citations(self):
        known = {s.id for s in self.sources}
        for point in [*self.thesis, *self.risks, *self.catalysts]:
            if not point.source_ids:
                raise ValueError("Every thesis/risk/catalyst point must cite at least one source ID")
            unknown = set(point.source_ids) - known
            if unknown:
                raise ValueError(f"Unknown source IDs: {sorted(unknown)}")
        return self


class TargetPosition(BaseModel):
    ticker: str
    target_weight: float = Field(ge=0, le=1)
    action: Literal["BUY", "HOLD", "REDUCE", "EXIT", "WATCH"]
    rationale: str

    @field_validator("ticker")
    @classmethod
    def normalize_ticker(cls, value: str) -> str:
        return value.strip().upper()


class CommitteeDecision(BaseModel):
    market_stance: Literal["bullish", "moderately_bullish", "neutral", "moderately_bearish", "bearish"]
    executive_summary: str
    key_market_risks: list[str]
    top_opportunity: str | None = None
    targets: list[TargetPosition]
    watchlist: list[str] = Field(default_factory=list)


class Holding(BaseModel):
    ticker: str
    shares: float
    last_price: float


class PortfolioSnapshot(BaseModel):
    as_of: date
    cash: float
    holdings: list[Holding]
    equity: float


class Trade(BaseModel):
    ticker: str
    side: Literal["BUY", "SELL"]
    shares: float
    price: float
    notional: float


class DailyRunResult(BaseModel):
    report_date: date
    pdf_path: str
    action_count: int
    sent: bool
