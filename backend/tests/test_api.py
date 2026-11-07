from io import BytesIO

from fastapi.testclient import TestClient

from app.main import app


def test_create_and_get_job() -> None:
    with TestClient(app) as client:
        response = client.post(
            "/api/jobs",
            files={"file": ("sample.log", BytesIO(b"line one\nline two\n"), "text/plain")},
        )

        assert response.status_code == 201
        payload = response.json()
        assert payload["filename"] == "sample.log"
        assert payload["status"] == "queued"
        assert payload["completed_chunks"] == 0

        status_response = client.get(f"/api/jobs/{payload['id']}")

    assert status_response.status_code == 200
    assert status_response.json()["id"] == payload["id"]


def test_create_job_rejects_unsupported_extension() -> None:
    with TestClient(app) as client:
        response = client.post(
            "/api/jobs",
            files={"file": ("sample.csv", BytesIO(b"a,b\n"), "text/csv")},
        )

    assert response.status_code == 415
