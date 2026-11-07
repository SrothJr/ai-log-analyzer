from pathlib import Path

from app.detector import detect_observations
from app.deterministic_findings import build_findings


LOG = Path(__file__).parents[2] / "test-data" / "Cultive8_Workspace_Agrigen_Server.log"


def observations_of(event_type: str):
    return [item for item in detect_observations(LOG) if item.event_type == event_type]


def test_deterministic_detector_matches_security_indicators() -> None:
    assert {item.line for item in observations_of("sql_injection_attempt")} == {29, 30, 32, 222, 223}
    assert {item.line for item in observations_of("endpoint_scan")} == {54, 56, 58, 60, 62, 64, 67, 69}
    assert {item.line for item in observations_of("path_traversal_attempt")} == {99, 101}
    assert {item.line for item in observations_of("request_rate_anomaly")} == set(range(159, 171))


def test_detector_does_not_turn_normal_errors_or_gets_into_attacks() -> None:
    observations = detect_observations(LOG)
    lines = {item.line for item in observations}

    assert 11 not in lines
    assert 207 not in lines
    assert 1 not in lines
    assert 217 in {item.line for item in observations_of("prompt_injection_payload")}
    assert not any(item.event_type == "prompt_injection_payload" for item in observations_of("authentication_failure"))


def test_global_findings_correlate_login_sequence() -> None:
    observations = detect_observations(LOG)
    findings = build_findings(observations)

    brute_force = next(item for item in findings if item.attack_type == "brute_force")
    compromise = next(item for item in findings if item.attack_type == "unauthorized_access")
    assert brute_force.actor_id == "203.0.113.44"
    assert {item.line for item in brute_force.evidence} >= {5, 13, 23, 35, 50, 65, 80, 94, 108, 123, 153, 189}
    assert {item.line for item in compromise.evidence} >= {189, 196, 198, 201}


def test_findings_are_actor_specific() -> None:
    findings = build_findings(detect_observations(LOG))

    sql = next(item for item in findings if item.attack_type == "sql_injection")
    scanning = next(item for item in findings if item.attack_type == "scanning")
    assert sql.actor_id == "203.0.113.72"
    assert scanning.actor_id == "203.0.113.90"
    assert all(item.line not in {1, 11, 207} for item in sql.evidence + scanning.evidence)


def test_single_failed_login_then_success_is_not_confirmed_compromise() -> None:
    findings = build_findings(detect_observations(LOG))

    assert not any(
        item.attack_type == "unauthorized_access" and item.actor_id == "198.51.100.96"
        for item in findings
    )
