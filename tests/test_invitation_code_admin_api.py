"""Invitation code admin route tests."""

from __future__ import annotations

from typing import Any

from fastapi.testclient import TestClient


SAMPLE_CODE_ROW = {
    "id": 1,
    "code": "RADAR-ABC123",
    "code_type": "radar",
    "prefix": "RADAR-",
    "code_length": 12,
    "max_uses": 3,
    "used_count": 1,
    "valid_from": "2026-05-01T00:00:00Z",
    "valid_until": "2026-06-01T00:00:00Z",
    "status": "active",
    "note": "radar beta",
    "created_by": "admin",
    "created_at": "2026-05-25T00:00:00Z",
    "updated_at": "2026-05-25T00:00:00Z",
    "disabled_at": None,
}


class TestInvitationCodeAdminRoutes:
    def test_list_invitation_codes(
        self,
        client: TestClient,
        monkeypatch,
    ) -> None:
        captured: dict[str, Any] = {}

        def fake_list_invitation_codes(**kwargs):
            captured.update(kwargs)
            return {
                "items": [SAMPLE_CODE_ROW],
                "page": kwargs["page"],
                "page_size": kwargs["page_size"],
                "total": 1,
            }

        monkeypatch.setattr(
            "src.api.routes.invitation_code.list_invitation_codes",
            fake_list_invitation_codes,
        )

        response = client.get(
            "/api/admin/invitation-codes",
            params={
                "code_type": "radar",
                "status": "active",
                "keyword": "beta",
                "page": 2,
                "page_size": 10,
            },
        )

        assert response.status_code == 200
        payload = response.json()
        assert payload["items"][0]["code"] == "RADAR-ABC123"
        assert payload["total"] == 1
        assert captured == {
            "code_type": "radar",
            "status": "active",
            "keyword": "beta",
            "page": 2,
            "page_size": 10,
        }

    def test_create_invitation_code(
        self,
        client: TestClient,
        monkeypatch,
    ) -> None:
        def fake_create_invitation_code(payload):
            assert payload.code == "RADAR-ABC123"
            assert payload.code_type == "radar"
            return SAMPLE_CODE_ROW

        monkeypatch.setattr(
            "src.api.routes.invitation_code.create_invitation_code",
            fake_create_invitation_code,
        )

        response = client.post(
            "/api/admin/invitation-codes",
            json={
                "code": "RADAR-ABC123",
                "code_type": "radar",
                "prefix": "RADAR-",
                "code_length": 12,
                "max_uses": 3,
                "valid_from": "2026-05-01T00:00:00Z",
                "valid_until": "2026-06-01T00:00:00Z",
                "note": "radar beta",
                "created_by": "admin",
            },
        )

        assert response.status_code == 201
        assert response.json()["code"] == "RADAR-ABC123"

    def test_patch_invitation_code(
        self,
        client: TestClient,
        monkeypatch,
    ) -> None:
        def fake_patch_invitation_code(invitation_code_id, payload):
            assert invitation_code_id == 1
            assert payload.status == "disabled"
            return {
                **SAMPLE_CODE_ROW,
                "status": "disabled",
                "disabled_at": "2026-05-25T01:00:00Z",
            }

        monkeypatch.setattr(
            "src.api.routes.invitation_code.patch_invitation_code",
            fake_patch_invitation_code,
        )

        response = client.patch(
            "/api/admin/invitation-codes/1",
            json={"status": "disabled"},
        )

        assert response.status_code == 200
        assert response.json()["status"] == "disabled"

    def test_delete_invitation_code(
        self,
        client: TestClient,
        monkeypatch,
    ) -> None:
        deleted_ids: list[int] = []

        def fake_delete_invitation_code(invitation_code_id):
            deleted_ids.append(invitation_code_id)

        monkeypatch.setattr(
            "src.api.routes.invitation_code.delete_invitation_code",
            fake_delete_invitation_code,
        )

        response = client.delete("/api/admin/invitation-codes/1")

        assert response.status_code == 200
        assert response.json() == {"deleted": True, "id": 1}
        assert deleted_ids == [1]

    def test_list_invitation_code_usages(
        self,
        client: TestClient,
        monkeypatch,
    ) -> None:
        def fake_list_invitation_code_usages(**kwargs):
            assert kwargs == {"invitation_code_id": 1, "page": 1, "page_size": 20}
            return {
                "items": [
                    {
                        "id": 10,
                        "code": "RADAR-ABC123",
                        "user_id": "user_1",
                        "used_at": "2026-05-25T02:00:00Z",
                    }
                ],
                "page": 1,
                "page_size": 20,
                "total": 1,
            }

        monkeypatch.setattr(
            "src.api.routes.invitation_code.list_invitation_code_usages",
            fake_list_invitation_code_usages,
        )

        response = client.get("/api/admin/invitation-codes/1/usages")

        assert response.status_code == 200
        payload = response.json()
        assert payload["items"][0]["user_id"] == "user_1"
        assert payload["total"] == 1
