from pathlib import Path

import pytest

from app.evidence import (
    EvidenceValidationError,
    validate_finding_against_source,
    validate_known_finding_evidence,
    validate_novel_finding_evidence,
)
from app.schemas import EvidenceItem, Finding


LOG = Path(__file__).parents[2] / "test-data" / "Cultive8_Workspace_Agrigen_Server.log"


def make_finding(actor: str, line: int) -> Finding:
    return Finding(
        attack_type="sql_injection",
        severity="High",
        actor_id=actor,
        evidence=[EvidenceItem(line=line, summary="test")],
        reason="test",
        suggested_action="test",
    )


def test_evidence_must_match_source_actor() -> None:
    with pytest.raises(EvidenceValidationError):
        validate_finding_against_source(make_finding("203.0.113.44", 29), LOG)


def test_evidence_line_must_exist_in_source() -> None:
    with pytest.raises(EvidenceValidationError):
        validate_finding_against_source(make_finding("203.0.113.72", 9999), LOG)


def test_valid_evidence_is_accepted() -> None:
    finding = validate_finding_against_source(make_finding("203.0.113.72", 29), LOG)
    assert finding.actor_id == "203.0.113.72"


def test_known_attack_cannot_use_an_ordinary_actor_line() -> None:
    finding = make_finding("203.0.113.72", 31)

    with pytest.raises(EvidenceValidationError):
        validate_known_finding_evidence(finding, {31: set()})


def test_novel_attack_type_can_pass_with_valid_source_evidence() -> None:
    finding = make_finding("203.0.113.72", 29).model_copy(
        update={"attack_type": "unexpected_parameter_abuse"}
    )

    assert validate_known_finding_evidence(finding, {29: set()}) == finding


def test_novel_attack_cannot_use_ordinary_get_evidence() -> None:
    finding = make_finding("novel_attack", 188)

    with pytest.raises(EvidenceValidationError):
        validate_novel_finding_evidence(finding, LOG, {})
