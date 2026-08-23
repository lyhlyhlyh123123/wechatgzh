from app.models import Topic
from app.seed import ensure_seed


def test_seed_visible_via_api(client):
    data = client.get("/api/topics").json()
    assert data["total"] >= 10


def test_seed_idempotent(test_session):
    ensure_seed(test_session)
    ensure_seed(test_session)
    assert test_session.query(Topic).count() >= 10


def test_topic_crud(client):
    r = client.post(
        "/api/topics",
        json={"drive_type": "站队", "category": "婚姻", "conflict": "爱情还是稳定"},
    )
    assert r.status_code == 200
    tid = r.json()["id"]
    assert r.json()["enabled"] is True

    r = client.patch(f"/api/topics/{tid}", json={"enabled": False})
    assert r.json()["enabled"] is False

    r = client.get("/api/topics", params={"drive_type": "站队"})
    assert any(t["id"] == tid for t in r.json()["items"])

    assert client.delete(f"/api/topics/{tid}").status_code == 204
