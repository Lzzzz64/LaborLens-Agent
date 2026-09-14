from sqlalchemy import create_engine, select
from sqlalchemy.orm import Session
from pydantic import ValidationError
import pytest

from app.db.models import (
    Base,
    CaseFactModel,
    CaseModel,
    CitationModel,
    QuestionRoundModel,
    ReportModel,
    RiskFindingModel,
)
from app.db.repositories import CaseRepository
from app.domain.models import (
    CaseFacts,
    Citation,
    FinalReport,
    QuestionRound,
    RiskFinding,
    UrgentFlag,
)


def make_session() -> Session:
    engine = create_engine("sqlite+pysqlite:///:memory:")
    Base.metadata.create_all(engine)
    return Session(engine)


def test_create_persists_case_and_returns_domain_record():
    with make_session() as session:
        record = CaseRepository(session).create("experience_analysis", "确认解除是否合法")

        stored = session.scalar(select(CaseModel).where(CaseModel.id == record.id))
        assert record.kind == "experience_analysis"
        assert record.goal == "确认解除是否合法"
        assert record.status == "created"
        assert stored is not None
        assert stored.goal == "确认解除是否合法"


def test_create_rejects_unknown_case_kind_without_persisting_it():
    with make_session() as session:
        repository = CaseRepository(session)

        with pytest.raises(ValidationError):
            repository.create("unsupported", "确认风险")

        assert session.scalar(select(CaseModel)) is None


def test_save_analysis_round_trips_structured_state():
    with make_session() as session:
        repository = CaseRepository(session)
        case = repository.create("contract_review", "识别合同风险")
        facts = CaseFacts(
            parties={"employee": "张某", "employer": "示例公司"},
            location="杭州",
            known_facts=["合同约定试用期工资为转正工资的 70%"],
            unknown_facts=["劳动合同期限"],
            user_goal="识别合同风险",
            schema_version="facts-v1",
        )
        question_round = QuestionRound(
            round_no=1,
            questions=["劳动合同期限是多久？"],
            answers=[None],
        )
        citation = Citation(
            source_id="law-001",
            title="中华人民共和国劳动合同法",
            article="第二十条",
            status="effective",
            url="https://example.gov.cn/law-001",
            excerpt="试用期工资不得低于约定工资的百分之八十。",
            applicability="用于核验试用期工资比例",
        )
        finding = RiskFinding(
            title="试用期工资比例风险",
            level="high",
            decision_type="rule",
            conclusion="约定比例可能低于法定标准",
            confidence=0.95,
            citation_ids=[citation.source_id],
            rule_version="probation-pay-v1",
        )
        report = FinalReport(
            summary="试用期工资约定存在高风险。",
            priority_actions=["核对合同期限"],
            fact_summary=facts,
            unknown_facts=facts.unknown_facts,
            risks=[finding],
            evidence_plan=["保留工资约定原件"],
            communication_scripts=["请公司说明试用期工资计算依据。"],
        )

        repository.save_analysis(
            case.id,
            {
                "status": "report_ready",
                "case_facts": facts,
                "question_rounds": [question_round],
                "urgent_flags": [
                    UrgentFlag(
                        title="签字提醒",
                        reason="合同条款尚未核清",
                        action="核清后再签字",
                    )
                ],
                "citations": [citation],
                "risk_findings": [finding],
                "report": report,
                "workflow_version": "workflow-v1",
            },
        )

        assert session.scalar(select(CaseModel)).status == "report_ready"
        assert session.scalar(select(CaseFactModel)).payload["location"] == "杭州"
        assert session.scalar(select(QuestionRoundModel)).questions == ["劳动合同期限是多久？"]
        assert session.scalar(select(CitationModel)).source_id == "law-001"
        assert session.scalar(select(RiskFindingModel)).rule_version == "probation-pay-v1"
        assert session.scalar(select(ReportModel)).payload["summary"] == "试用期工资约定存在高风险。"


def test_save_analysis_replaces_prior_snapshot_instead_of_duplicating_rows():
    with make_session() as session:
        repository = CaseRepository(session)
        case = repository.create("experience_analysis", "确认风险")
        first = CaseFacts(known_facts=["第一次抽取"], schema_version="facts-v1")
        second = CaseFacts(known_facts=["修正后的事实"], schema_version="facts-v2")

        repository.save_analysis(case.id, {"case_facts": first})
        repository.save_analysis(case.id, {"case_facts": second})

        stored = session.scalars(select(CaseFactModel)).all()
        assert len(stored) == 1
        assert stored[0].payload["known_facts"] == ["修正后的事实"]
        assert stored[0].schema_version == "facts-v2"


def test_save_analysis_rejects_unknown_case():
    with make_session() as session:
        repository = CaseRepository(session)

        try:
            repository.save_analysis("missing-case", {"status": "analyzing"})
        except LookupError as error:
            assert str(error) == "case not found: missing-case"
        else:
            raise AssertionError("missing case must be rejected")
