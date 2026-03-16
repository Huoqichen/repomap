from fastapi.testclient import TestClient

from repomap_api.main import app


client = TestClient(app)


def test_health_endpoint() -> None:
    response = client.get("/health")

    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


def test_branches_endpoint(monkeypatch) -> None:
    def fake_list_remote_branches(repo_url: str) -> tuple[str | None, list[str]]:
        assert repo_url == "https://github.com/Huoqichen/repograph"
        return "main", ["main", "dev"]

    monkeypatch.setattr("repomap_api.main.list_remote_branches", fake_list_remote_branches)

    response = client.get("/api/branches", params={"repo_url": "https://github.com/Huoqichen/repograph"})

    assert response.status_code == 200
    assert response.json() == {
        "default_branch": "main",
        "branches": ["main", "dev"],
    }
