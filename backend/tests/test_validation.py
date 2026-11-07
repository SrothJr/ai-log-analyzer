import pytest

from app.validation import ModelResponseError, validate_findings


def test_validate_findings_accepts_fenced_json() -> None:
    result = validate_findings(
        """```json
        {"findings": [{"attack_type": "scanning", "severity": "Medium",
        "actor_id": "203.0.113.90", "evidence": [{"line": 12,
        "summary": "Probed a restricted path"}], "reason": "Repeated probes",
        "suggested_action": "Investigate the source"}]}
        ```""",
        start_line=10,
        end_line=20,
    )

    assert result.findings[0].attack_type == "scanning"


def test_validate_findings_accepts_empty_findings() -> None:
    assert validate_findings('{"findings": []}').findings == []


def test_validate_findings_rejects_out_of_range_evidence() -> None:
    content = '{"findings": [{"attack_type": "other", "severity": "Low", "actor_id": "x", "evidence": [{"line": 2, "summary": "x"}], "reason": "x", "suggested_action": "x"}]}'

    with pytest.raises(ModelResponseError):
        validate_findings(content, start_line=5, end_line=10)


def test_validate_findings_rejects_non_json() -> None:
    with pytest.raises(ModelResponseError):
        validate_findings("No structured response")
