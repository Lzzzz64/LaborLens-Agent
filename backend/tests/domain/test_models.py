import pytest
from pydantic import ValidationError

from app.domain.models import QuestionRound, RiskFinding


def test_question_round_rejects_more_than_three_questions():
    with pytest.raises(ValidationError):
        QuestionRound(round_no=1, questions=["a", "b", "c", "d"])


def test_question_round_rejects_more_than_three_rounds():
    with pytest.raises(ValidationError):
        QuestionRound(round_no=4, questions=["是否签字？"])


def test_question_round_rejects_more_answers_than_questions():
    with pytest.raises(ValidationError):
        QuestionRound(round_no=1, questions=["是否签字？"], answers=["否", "不确定"])


def test_high_risk_requires_support_or_becomes_unverified():
    finding = RiskFinding.model_validate(
        {
            "title": "试用期解除风险",
            "level": "high",
            "decision_type": "model",
            "conclusion": "可能违法",
            "confidence": 0.7,
            "citation_ids": [],
        }
    )

    assert finding.level == "unverified"
    assert finding.confidence == 0.49
    assert finding.limitations == ["缺少可核验法律依据"]


def test_high_risk_with_rule_version_keeps_level():
    finding = RiskFinding(
        title="试用期工资比例风险",
        level="high",
        decision_type="rule",
        conclusion="约定比例低于法定标准",
        confidence=0.95,
        citation_ids=[],
        rule_version="probation-pay-v1",
    )

    assert finding.level == "high"


def test_mutable_defaults_are_not_shared():
    first = RiskFinding(
        title="风险一",
        level="low",
        decision_type="model",
        conclusion="结论一",
        confidence=0.5,
    )
    second = RiskFinding(
        title="风险二",
        level="low",
        decision_type="model",
        conclusion="结论二",
        confidence=0.5,
    )

    first.limitations.append("仅属于第一个对象")

    assert second.limitations == []
