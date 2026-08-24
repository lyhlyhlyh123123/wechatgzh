from tests.test_generation_api import BUILD_BODY, make_article


def test_patch_and_status_and_list(client, test_engine):
    art = make_article(client, test_engine)
    aid = art["id"]

    r = client.patch(f"/api/articles/{aid}", json={"body": "手工改过的正文"})
    assert r.json()["body"] == "手工改过的正文"
    assert r.json()["title"] == art["title"]

    r = client.post(f"/api/articles/{aid}/status", json={"status": "approved"})
    assert r.json()["status"] == "approved"
    r = client.post(f"/api/articles/{aid}/status", json={"status": "draft"})
    assert r.json()["status"] == "draft"

    make_article(client, test_engine, title="第二篇")
    r = client.get("/api/articles")
    assert r.json()["total"] == 2
    r = client.get("/api/articles", params={"q": "第二篇"})
    assert r.json()["total"] == 1
    assert r.json()["items"][0]["title"] == "第二篇"


def test_status_validated(client, test_engine):
    art = make_article(client, test_engine)
    r = client.post(f"/api/articles/{art['id']}/status", json={"status": "nope"})
    assert r.status_code == 422


def test_delete_removes_files(client, test_engine):
    art = make_article(client, test_engine)
    aid = art["id"]
    f = client.storage_root / art["image_paths"][0]
    assert f.exists()
    assert client.delete(f"/api/articles/{aid}").status_code == 204
    assert not f.exists()
    assert client.get(f"/api/articles/{aid}").status_code == 404


def test_build_body_fixture_fields_preserved(client, test_engine):
    art = make_article(client, test_engine)
    assert art["title"] == BUILD_BODY["title"]
    assert art["image_prompt"] == BUILD_BODY["image_prompt"]
