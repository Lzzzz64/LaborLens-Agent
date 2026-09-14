from datetime import date, datetime
from typing import Any, Literal

from pydantic import BaseModel, Field, HttpUrl, model_validator


CaseKind = Literal["contract_review", "experience_analysis"]
CaseStatus = Literal[
    "created",
    "parsing",
    "questioning",
    "retrieving",
    "analyzing",
    "report_ready",
    "failed",
    "parse_failed",
]
RiskLevel = Literal["high", "medium", "low", "unverified"]
DecisionType = Literal["rule", "model"]


class CaseFacts(BaseModel):
    parties: dict[str, str] = Field(default_factory=dict)
    location: str | None = None
    dates: dict[str, date | str] = Field(default_factory=dict)
    contract_terms: dict[str, Any] = Field(default_factory=dict)
    employer_actions: list[str] = Field(default_factory=list)
    user_goal: str = ""
    evidence: list[str] = Field(default_factory=list)
    known_facts: list[str] = Field(default_factory=list)
    user_claims: list[str] = Field(default_factory=list)
    inferred_facts: list[str] = Field(default_factory=list)
    unknown_facts: list[str] = Field(default_factory=list)
    raw_output: dict[str, Any] = Field(default_factory=dict)
    schema_version: str = "facts-v1"


class QuestionRound(BaseModel):
    round_no: int = Field(ge=1, le=3)
    questions: list[str] = Field(min_length=1, max_length=3)
    answers: list[str | None] = Field(default_factory=list, max_length=3)
    skipped: bool = False

    @model_validator(mode="after")
    def answers_must_match_questions(self) -> "QuestionRound":
        if len(self.answers) > len(self.questions):
            raise ValueError("answers cannot outnumber questions")
        return self


class UrgentFlag(BaseModel):
    title: str
    reason: str
    action: str
    deadline: date | None = None
    level: Literal["high", "medium"] = "high"
    rule_version: str | None = None


class Citation(BaseModel):
    source_id: str
    title: str
    article: str | None = None
    status: Literal["effective", "amended", "repealed", "unknown"]
    url: HttpUrl
    excerpt: str
    applicability: str
    jurisdiction: str = "中国大陆"
    effective_date: date | None = None
    verified_at: date | None = None
    knowledge_version: str | None = None


class RiskFinding(BaseModel):
    title: str
    level: RiskLevel
    decision_type: DecisionType
    conclusion: str
    confidence: float = Field(ge=0, le=1)
    citation_ids: list[str] = Field(default_factory=list)
    limitations: list[str] = Field(default_factory=list)
    rule_version: str | None = None
    supporting_facts: list[str] = Field(default_factory=list)
    action_suggestions: list[str] = Field(default_factory=list)

    @model_validator(mode="after")
    def prevent_unsupported_high_risk(self) -> "RiskFinding":
        has_support = bool(self.citation_ids or self.rule_version)
        if self.level == "high" and not has_support:
            self.level = "unverified"
            self.confidence = min(self.confidence, 0.49)
            if "缺少可核验法律依据" not in self.limitations:
                self.limitations.append("缺少可核验法律依据")
        return self


class FinalReport(BaseModel):
    summary: str
    priority_actions: list[str] = Field(default_factory=list, max_length=3)
    fact_summary: CaseFacts
    unknown_facts: list[str] = Field(default_factory=list)
    risks: list[RiskFinding] = Field(default_factory=list)
    citations: list[Citation] = Field(default_factory=list)
    evidence_plan: list[str] = Field(default_factory=list)
    communication_scripts: list[str] = Field(default_factory=list)
    capability_boundary: str = "本系统仅提供信息分析，不构成律师服务或正式法律意见。"
    report_version: str = "report-v1"


class CaseRecord(BaseModel):
    id: str
    kind: CaseKind
    goal: str
    status: CaseStatus = "created"
    created_at: datetime
    updated_at: datetime
