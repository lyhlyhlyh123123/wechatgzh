def test_env_roundtrip(tmp_path):
    from app.services.envfile import read_env, write_env

    env_path = tmp_path / ".env"
    env_path.write_text(
        "A=1\nB=2\n", encoding="utf-8",
    )
    write_env({"A": "9", "C": "3"}, path=str(env_path))
    data = read_env(str(env_path))
    assert data["A"] == "9"
    assert data["B"] == "2"
    assert data["C"] == "3"


def test_get_and_put_settings(client, tmp_path, monkeypatch):
    from app.routers import settings_api as settings_api_module

    monkeypatch.setattr(settings_api_module, "ENV_PATH", str(tmp_path / ".env"))
    data = client.get("/api/settings").json()
    assert "presets" in data and len(data["presets"]) >= 3
    assert data["image_size_default"] == "1080x1620"
    assert "deepseek_api_key" not in data

    client.app.state.storage_root
    r = client.put("/api/settings", json={
        "deepseek_model": "deepseek-chat",
        "image_count_default": 2,
    })
    assert r.status_code == 200
    assert client.app.state.max_count == 3
    assert client.app.state.default_count == 2


def test_presets_endpoint(client):
    data = client.get("/api/presets").json()
    assert {"label": "2:3", "size": "1080x1620"} in data
