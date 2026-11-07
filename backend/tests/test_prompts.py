from app.prompts import chunk_prompt


def test_chunk_prompt_supplies_deterministic_observations_as_hints() -> None:
    prompt = chunk_prompt(
        chunk_index=1,
        start_line=10,
        end_line=12,
        text="10: raw log",
        context=[],
        observations=[
            {
                "line": 10,
                "event_type": "sql_injection_attempt",
                "actor_id": "192.0.2.10",
                "summary": "SQL syntax",
            }
        ],
    )

    assert "Deterministic observations are hints" in prompt
    assert "sql_injection_attempt" in prompt
    assert "novel attack types" in prompt
