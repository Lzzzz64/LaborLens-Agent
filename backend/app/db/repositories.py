from collections.abc import Mapping
from typing import Any

from sqlalchemy import delete
from sqlalchemy.orm import Session
from pydantic import TypeAdapter
from pydantic_core import to_jsonable_python

from app.db.models import (
    CaseFactModel,
    CaseModel,
    CitationModel,
    QuestionRoundModel,
    ReportModel,
    RiskFindingModel,
)
from app.domain.models import (
    CaseFacts,
    CaseKind,
    CaseRecord,
    CaseStatus,
    Citation,
    FinalReport,
    QuestionRound,
    RiskFinding,
)


def _json(model: Any) -> dict[str, Any]:
    return model.model_dump(mode="json")


class CaseRepository:
    def __init__(self, session: Session):
        self.session = session

    def create(self, kind: CaseKind, goal: str) -> CaseRecord:
        validated_kind = TypeAdapter(CaseKind).validate_python(kind)
        case = CaseModel(kind=validated_kind, goal=goal, status="created")
        self.session.add(case)
        self.session.commit()
        self.session.refresh(case)
        return self._to_record(case)

    def save_analysis(self, case_id: str, state: Mapping[str, Any]) -> None:
        case = self.session.get(CaseModel, case_id)
        if case is None:
            raise LookupError(f"case not found: {case_id}")

        try:
            if "status" in state:
                case.status = TypeAdapter(CaseStatus).validate_python(state["status"])
            case.workflow_version = state.get("workflow_version", case.workflow_version)
            case.analysis_state = self._serializable_state(state)

            self._replace_facts(case_id, state.get("case_facts"))
            self._replace_rounds(case_id, state.get("question_rounds"))
            self._replace_citations(case_id, state.get("citations"))
            self._replace_findings(case_id, state.get("risk_findings"))
            self._replace_report(case_id, state.get("report"))
            self.session.commit()
        except Exception:
            self.session.rollback()
            raise

    def _replace_facts(self, case_id: str, value: Any) -> None:
        if value is None:
            return
        facts = value if isinstance(value, CaseFacts) else CaseFacts.model_validate(value)
        self.session.execute(delete(CaseFactModel).where(CaseFactModel.case_id == case_id))
        self.session.add(
            CaseFactModel(case_id=case_id, schema_version=facts.schema_version, payload=_json(facts))
        )

    def _replace_rounds(self, case_id: str, values: Any) -> None:
        if values is None:
            return
        rounds = [item if isinstance(item, QuestionRound) else QuestionRound.model_validate(item) for item in values]
        self.session.execute(delete(QuestionRoundModel).where(QuestionRoundModel.case_id == case_id))
        self.session.add_all(
            QuestionRoundModel(
                case_id=case_id,
                round_no=item.round_no,
                questions=item.questions,
                answers=item.answers,
                skipped=item.skipped,
            )
            for item in rounds
        )

    def _replace_citations(self, case_id: str, values: Any) -> None:
        if values is None:
            return
        citations = [item if isinstance(item, Citation) else Citation.model_validate(item) for item in values]
        self.session.execute(delete(CitationModel).where(CitationModel.case_id == case_id))
        self.session.add_all(CitationModel(case_id=case_id, **_json(item)) for item in citations)

    def _replace_findings(self, case_id: str, values: Any) -> None:
        if values is None:
            return
        findings = [item if isinstance(item, RiskFinding) else RiskFinding.model_validate(item) for item in values]
        self.session.execute(delete(RiskFindingModel).where(RiskFindingModel.case_id == case_id))
        self.session.add_all(RiskFindingModel(case_id=case_id, **_json(item)) for item in findings)

    def _replace_report(self, case_id: str, value: Any) -> None:
        if value is None:
            return
        report = value if isinstance(value, FinalReport) else FinalReport.model_validate(value)
        self.session.execute(delete(ReportModel).where(ReportModel.case_id == case_id))
        self.session.add(
            ReportModel(case_id=case_id, report_version=report.report_version, payload=_json(report))
        )

    @staticmethod
    def _serializable_state(state: Mapping[str, Any]) -> dict[str, Any]:
        return to_jsonable_python(
            {
                key: value
                for key, value in state.items()
                if key not in {"case_facts", "question_rounds", "citations", "risk_findings", "report"}
            }
        )

    @staticmethod
    def _to_record(case: CaseModel) -> CaseRecord:
        return CaseRecord(
            id=case.id,
            kind=case.kind,
            goal=case.goal,
            status=case.status,
            created_at=case.created_at,
            updated_at=case.updated_at,
        )
