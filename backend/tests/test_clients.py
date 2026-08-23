import base64

import httpx
import pytest

from app.clients.ark import ArkClient
from app.clients.deepseek import DeepSeekClient


def test_deepseek_chat_json_parses():
    def handler(request: httpx.Request) -> httpx.Response:
        assert request.headers["Authorization"] == "Bearer sk-test"
        body = {
            "choices": [{"message": {"content": '{"a": 1}'}}],
        }
        return httpx.Response(200, json=body)

    client = DeepSeekClient(
        "https://fake", "sk-test", "deepseek-chat",
        transport=httpx.MockTransport(handler),
    )
    assert client.chat_json("sys", "user") == {"a": 1}


def test_deepseek_retries_on_bad_json():
    calls = {"n": 0}

    def handler(request: httpx.Request) -> httpx.Response:
        calls["n"] += 1
        content = "{bad" if calls["n"] < 2 else '{"ok": true}'
        return httpx.Response(200, json={"choices": [{"message": {"content": content}}]})

    client = DeepSeekClient(
        "https://fake", "k", "m",
        transport=httpx.MockTransport(handler), retries=2,
    )
    assert client.chat_json("s", "u") == {"ok": True}
    assert calls["n"] == 2


def test_ark_saves_b64_image(tmp_path):
    png = base64.b64encode(b"fakebytes").decode()

    def handler(request: httpx.Request) -> httpx.Response:
        payload = request.read()
        assert b'"1080x1620"' in payload
        return httpx.Response(200, json={"data": [{"b64_json": png}]})

    out = tmp_path / "img.jpg"
    client = ArkClient(
        "https://fake", "k", "model-x",
        transport=httpx.MockTransport(handler),
    )
    result = client.generate_image("prompt text", "1080x1620", out)
    assert result.exists()
    assert result.read_bytes() == b"fakebytes"


def test_ark_downloads_url(tmp_path):
    def handler(request: httpx.Request) -> httpx.Response:
        if request.url.path.endswith("/images/generations"):
            return httpx.Response(200, json={"data": [{"url": "https://fake/dl"}]})
        return httpx.Response(200, content=b"urlbytes")

    out = tmp_path / "img.jpg"
    client = ArkClient(
        "https://fake", "k", "m",
        transport=httpx.MockTransport(handler),
    )
    client.generate_image("p", "1080x1620", out)
    assert out.read_bytes() == b"urlbytes"


def test_ark_raises_when_empty(tmp_path):
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(200, json={"data": []})

    client = ArkClient(
        "https://fake", "k", "m",
        transport=httpx.MockTransport(handler),
    )
    with pytest.raises(RuntimeError):
        client.generate_image("p", "1080x1620", tmp_path / "x.jpg")
