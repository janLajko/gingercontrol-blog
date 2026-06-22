"""User management admin route tests."""

from __future__ import annotations

from typing import Any

from fastapi.testclient import TestClient


SAMPLE_USER_ROW = {
    "id": 1,
    "email": "alice@gingercontrol.com",
    "name": "Alice",
    "avatar_url": None,
    "provider": "manual",
    "provider_sub": "manual:alice@gingercontrol.com",
    "company_name": "Ginger Control",
    "job_title": "Ops",
    "profile_completed": True,
    "email_verified": True,
    "last_login_at": None,
    "created_at": "2026-06-22T00:00:00Z",
    "updated_at": "2026-06-22T00:00:00Z",
    "source": "manual",
    "callsign": "ALICE",
    "language": "en",
    "password": "123456",
    "is_deleted": False,
}


class TestUserManageAdminRoutes:
    def test_list_users(self, client: TestClient, monkeypatch) -> None:
        captured: dict[str, Any] = {}

        def fake_list_users(**kwargs):
            captured.update(kwargs)
            return {
                "items": [SAMPLE_USER_ROW],
                "page": kwargs["page"],
                "page_size": kwargs["page_size"],
                "total": 1,
            }

        monkeypatch.setattr("src.api.routes.user_manage.list_users", fake_list_users)

        response = client.get(
            "/api/admin/users",
            params={"keyword": "alice", "page": 2, "page_size": 10},
        )

        assert response.status_code == 200
        payload = response.json()
        assert payload["items"][0]["email"] == "alice@gingercontrol.com"
        assert payload["total"] == 1
        assert captured == {"keyword": "alice", "page": 2, "page_size": 10}

    def test_create_user(self, client: TestClient, monkeypatch) -> None:
        def fake_create_user(payload):
            assert payload.email_prefix == "alice"
            return SAMPLE_USER_ROW

        monkeypatch.setattr("src.api.routes.user_manage.create_user", fake_create_user)

        response = client.post(
            "/api/admin/users",
            json={
                "email_prefix": "Alice",
                "name": "Alice",
                "company_name": "Ginger Control",
            },
        )

        assert response.status_code == 201
        assert response.json()["profile_completed"] is True
        assert response.json()["email_verified"] is True
        assert response.json()["source"] == "manual"

    def test_get_user(self, client: TestClient, monkeypatch) -> None:
        def fake_get_user(user_id):
            assert user_id == 1
            return SAMPLE_USER_ROW

        monkeypatch.setattr("src.api.routes.user_manage.get_user", fake_get_user)

        response = client.get("/api/admin/users/1")

        assert response.status_code == 200
        assert response.json()["id"] == 1

    def test_delete_user(self, client: TestClient, monkeypatch) -> None:
        deleted_ids: list[int] = []

        def fake_delete_user(user_id):
            deleted_ids.append(user_id)

        monkeypatch.setattr("src.api.routes.user_manage.delete_user", fake_delete_user)

        response = client.delete("/api/admin/users/1")

        assert response.status_code == 200
        assert response.json() == {"deleted": True, "id": 1}
        assert deleted_ids == [1]
