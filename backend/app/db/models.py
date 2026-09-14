from datetime import datetime, timezone
from typing import Any
from uuid import uuid4

from sqlalchemy import DateTime, ForeignKey, Index, Integer, JSON, String, Text, UniqueConstraint
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


class Base(DeclarativeBase):
    pass


class CaseModel(Base):
    __tablename__ = "cases"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid4()))
    kind: Mapped[str] = mapped_column(String(32), nullable=False)
    goal: Mapped[str] = mapped_column(Text, nullable=False)
    status: Mapped[str] = mapped_column(String(32), nullable=False, default="created", index=True)
    workflow_version: Mapped[str | None] = mapped_column(String(64))
    analysis_state: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now, onupdate=utc_now, nullable=False)

    facts: Mapped[list["CaseFactModel"]] = relationship(cascade="all, delete-orphan")
    question_rounds: Mapped[list["QuestionRoundModel"]] = relationship(cascade="all, delete-orphan")
    risk_findings: Mapped[list["RiskFindingModel"]] = relationship(cascade="all, delete-orphan")
    citations: Mapped[list["CitationModel"]] = relationship(cascade="all, delete-orphan")
    reports: Mapped[list["ReportModel"]] = relationship(cascade="all, delete-orphan")


class CaseFactModel(Base):
    __tablename__ = "case_facts"
    __table_args__ = (UniqueConstraint("case_id", name="uq_case_facts_case_id"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    case_id: Mapped[str] = mapped_column(ForeignKey("cases.id", ondelete="CASCADE"), nullable=False)
    schema_version: Mapped[str] = mapped_column(String(64), nullable=False)
    payload: Mapped[dict[str, Any]] = mapped_column(JSON, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now, nullable=False)


class QuestionRoundModel(Base):
    __tablename__ = "question_rounds"
    __table_args__ = (UniqueConstraint("case_id", "round_no", name="uq_question_round_case_round"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    case_id: Mapped[str] = mapped_column(ForeignKey("cases.id", ondelete="CASCADE"), nullable=False)
    round_no: Mapped[int] = mapped_column(Integer, nullable=False)
    questions: Mapped[list[str]] = mapped_column(JSON, nullable=False)
    answers: Mapped[list[str | None]] = mapped_column(JSON, nullable=False)
    skipped: Mapped[bool] = mapped_column(default=False, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now, nullable=False)


class RiskFindingModel(Base):
    __tablename__ = "risk_findings"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    case_id: Mapped[str] = mapped_column(ForeignKey("cases.id", ondelete="CASCADE"), nullable=False)
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    level: Mapped[str] = mapped_column(String(32), nullable=False, index=True)
    decision_type: Mapped[str] = mapped_column(String(16), nullable=False)
    conclusion: Mapped[str] = mapped_column(Text, nullable=False)
    confidence: Mapped[float] = mapped_column(nullable=False)
    citation_ids: Mapped[list[str]] = mapped_column(JSON, nullable=False)
    limitations: Mapped[list[str]] = mapped_column(JSON, nullable=False)
    supporting_facts: Mapped[list[str]] = mapped_column(JSON, nullable=False)
    action_suggestions: Mapped[list[str]] = mapped_column(JSON, nullable=False)
    rule_version: Mapped[str | None] = mapped_column(String(64))


class CitationModel(Base):
    __tablename__ = "citations"
    __table_args__ = (UniqueConstraint("case_id", "source_id", name="uq_citation_case_source"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    case_id: Mapped[str] = mapped_column(ForeignKey("cases.id", ondelete="CASCADE"), nullable=False)
    source_id: Mapped[str] = mapped_column(String(128), nullable=False)
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    article: Mapped[str | None] = mapped_column(String(128))
    status: Mapped[str] = mapped_column(String(32), nullable=False)
    url: Mapped[str] = mapped_column(Text, nullable=False)
    excerpt: Mapped[str] = mapped_column(Text, nullable=False)
    applicability: Mapped[str] = mapped_column(Text, nullable=False)
    jurisdiction: Mapped[str] = mapped_column(String(128), nullable=False)
    effective_date: Mapped[str | None] = mapped_column(String(10))
    verified_at: Mapped[str | None] = mapped_column(String(10))
    knowledge_version: Mapped[str | None] = mapped_column(String(64))


class ReportModel(Base):
    __tablename__ = "reports"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    case_id: Mapped[str] = mapped_column(ForeignKey("cases.id", ondelete="CASCADE"), nullable=False)
    report_version: Mapped[str] = mapped_column(String(64), nullable=False)
    payload: Mapped[dict[str, Any]] = mapped_column(JSON, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now, nullable=False)


class EvaluationRunModel(Base):
    __tablename__ = "evaluation_runs"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid4()))
    status: Mapped[str] = mapped_column(String(32), nullable=False, index=True)
    dataset_version: Mapped[str] = mapped_column(String(64), nullable=False)
    knowledge_version: Mapped[str] = mapped_column(String(64), nullable=False)
    model_config: Mapped[dict[str, Any]] = mapped_column(JSON, nullable=False)
    prompt_version: Mapped[str] = mapped_column(String(64), nullable=False)
    rule_version: Mapped[str] = mapped_column(String(64), nullable=False)
    metrics: Mapped[dict[str, Any]] = mapped_column(JSON, nullable=False)
    failures: Mapped[list[dict[str, Any]]] = mapped_column(JSON, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now, nullable=False)


Index("ix_question_rounds_case_id", QuestionRoundModel.case_id)
Index("ix_risk_findings_case_id", RiskFindingModel.case_id)
Index("ix_citations_case_id", CitationModel.case_id)
Index("ix_reports_case_id", ReportModel.case_id)
