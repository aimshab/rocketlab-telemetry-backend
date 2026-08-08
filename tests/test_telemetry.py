"""Unit tests for satellite telemetry API endpoints."""

from uuid import uuid4


VALID_PAYLOAD = {
    "satelliteId": "SAT-100",
    "timestamp": "2026-08-06T12:00:00.000Z",
    "altitude": 500.0,
    "velocity": 7.5,
    "status": "healthy",
}


class TestHealth:
    def test_health_ok(self, client):
        response = client.get("/health")
        assert response.status_code == 200
        assert response.json() == {"status": "ok"}


class TestListTelemetry:
    def test_list_empty(self, client):
        response = client.get("/telemetry")
        assert response.status_code == 200
        body = response.json()
        assert body["items"] == []
        assert body["page"] == 1
        assert body["limit"] == 10
        assert body["hasMore"] is False

    def test_list_returns_seeded(self, client, seeded_entries):
        response = client.get("/telemetry")
        assert response.status_code == 200
        body = response.json()
        assert len(body["items"]) == len(seeded_entries)
        assert body["hasMore"] is False

    def test_filter_by_satellite_id(self, client, seeded_entries):
        response = client.get("/telemetry", params={"satelliteId": "SAT-001"})
        body = response.json()
        assert len(body["items"]) == 2
        assert all(item["satelliteId"] == "SAT-001" for item in body["items"])
        assert body["hasMore"] is False

    def test_filter_by_status(self, client, seeded_entries):
        response = client.get("/telemetry", params={"status": "critical"})
        body = response.json()
        assert len(body["items"]) == 2
        assert all(item["status"] == "critical" for item in body["items"])
        assert body["hasMore"] is False

    def test_filter_combined(self, client, seeded_entries):
        response = client.get(
            "/telemetry",
            params={"satelliteId": "SAT-001", "status": "critical"},
        )
        body = response.json()
        assert len(body["items"]) == 1
        assert body["items"][0]["satelliteId"] == "SAT-001"
        assert body["items"][0]["status"] == "critical"
        assert body["hasMore"] is False

    def test_pagination(self, client, seeded_entries):
        response = client.get("/telemetry", params={"page": 1, "limit": 2})
        body = response.json()
        assert body["page"] == 1
        assert body["limit"] == 2
        assert len(body["items"]) == 2
        assert body["hasMore"] is True

        page2 = client.get("/telemetry", params={"page": 2, "limit": 2}).json()
        assert len(page2["items"]) == 2
        assert page2["page"] == 2
        assert page2["hasMore"] is True

        page3 = client.get("/telemetry", params={"page": 3, "limit": 2}).json()
        assert len(page3["items"]) == 1
        assert page3["page"] == 3
        assert page3["hasMore"] is False

    def test_pagination_beyond_last_page(self, client, seeded_entries):
        response = client.get("/telemetry", params={"page": 99, "limit": 10})
        body = response.json()
        assert body["items"] == []
        assert body["hasMore"] is False

    def test_pagination_invalid_params(self, client):
        assert client.get("/telemetry", params={"page": 0}).status_code == 422
        assert client.get("/telemetry", params={"limit": 0}).status_code == 422
        assert client.get("/telemetry", params={"limit": 101}).status_code == 422


class TestCreateTelemetry:
    def test_create_success(self, client, sample_payload):
        response = client.post("/telemetry", json=sample_payload)
        assert response.status_code == 201
        body = response.json()
        assert "id" in body
        assert body["satelliteId"] == sample_payload["satelliteId"]
        assert body["altitude"] == sample_payload["altitude"]
        assert body["velocity"] == sample_payload["velocity"]
        assert body["status"] == sample_payload["status"]

    def test_create_persists(self, client, sample_payload):
        created = client.post("/telemetry", json=sample_payload).json()
        fetched = client.get(f"/telemetry/{created['id']}")
        assert fetched.status_code == 200
        assert fetched.json()["id"] == created["id"]

    def test_reject_invalid_timestamp(self, client, sample_payload):
        sample_payload["timestamp"] = "not-a-date"
        response = client.post("/telemetry", json=sample_payload)
        assert response.status_code == 422

    def test_reject_non_iso8601_timestamp(self, client, sample_payload):
        # Parseable as a date, but not strict ISO 8601 with T + timezone
        sample_payload["timestamp"] = "2026-08-06 12:00:00"
        response = client.post("/telemetry", json=sample_payload)
        assert response.status_code == 422

    def test_reject_impossible_iso8601_timestamp(self, client, sample_payload):
        sample_payload["timestamp"] = "2026-13-40T99:00:00.000Z"
        response = client.post("/telemetry", json=sample_payload)
        assert response.status_code == 422

    def test_accept_iso8601_with_offset(self, client, sample_payload):
        sample_payload["timestamp"] = "2026-08-06T12:00:00+00:00"
        response = client.post("/telemetry", json=sample_payload)
        assert response.status_code == 201

    def test_reject_non_positive_altitude(self, client, sample_payload):
        sample_payload["altitude"] = -10
        response = client.post("/telemetry", json=sample_payload)
        assert response.status_code == 422

    def test_reject_zero_velocity(self, client, sample_payload):
        sample_payload["velocity"] = 0
        response = client.post("/telemetry", json=sample_payload)
        assert response.status_code == 422

    def test_reject_empty_satellite_id(self, client, sample_payload):
        sample_payload["satelliteId"] = "   "
        response = client.post("/telemetry", json=sample_payload)
        assert response.status_code == 422

    def test_reject_invalid_status(self, client, sample_payload):
        sample_payload["status"] = "unknown"
        response = client.post("/telemetry", json=sample_payload)
        assert response.status_code == 422

    def test_reject_invalid_status_filter(self, client):
        response = client.get("/telemetry", params={"status": "unknown"})
        assert response.status_code == 422

    def test_reject_missing_fields(self, client):
        response = client.post("/telemetry", json={"satelliteId": "SAT-1"})
        assert response.status_code == 422


class TestGetTelemetry:
    def test_get_existing(self, client, seeded_entries):
        entry_id = str(seeded_entries[0].id)
        response = client.get(f"/telemetry/{entry_id}")
        assert response.status_code == 200
        assert response.json()["id"] == entry_id

    def test_get_missing(self, client):
        response = client.get(f"/telemetry/{uuid4()}")
        assert response.status_code == 404
        assert response.json()["detail"] == "Telemetry entry not found"

    def test_get_invalid_uuid(self, client):
        response = client.get("/telemetry/not-a-uuid")
        assert response.status_code == 422


class TestDeleteTelemetry:
    def test_delete_existing(self, client, seeded_entries):
        entry_id = str(seeded_entries[0].id)
        response = client.delete(f"/telemetry/{entry_id}")
        assert response.status_code == 204
        assert response.content == b""

        follow_up = client.get(f"/telemetry/{entry_id}")
        assert follow_up.status_code == 404

    def test_delete_missing(self, client):
        response = client.delete(f"/telemetry/{uuid4()}")
        assert response.status_code == 404
        assert response.json()["detail"] == "Telemetry entry not found"
