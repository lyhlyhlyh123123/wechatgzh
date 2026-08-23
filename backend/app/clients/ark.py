from __future__ import annotations

import base64
from pathlib import Path

import httpx


class ArkClient:
    def __init__(
        self,
        base_url: str,
        api_key: str,
        model: str,
        timeout: float = 180.0,
        transport: httpx.BaseTransport | None = None,
    ) -> None:
        self.base_url = base_url.rstrip("/")
        self.api_key = api_key
        self.model = model
        self.timeout = timeout
        self.transport = transport

    def generate_image(self, prompt: str, size: str, output_path: Path) -> Path:
        payload = {
            "model": self.model,
            "prompt": prompt,
            "size": size,
            "response_format": "b64_json",
            "watermark": False,
        }
        headers = {"Authorization": f"Bearer {self.api_key}"}
        with httpx.Client(timeout=self.timeout, transport=self.transport) as client:
            resp = client.post(f"{self.base_url}/images/generations", headers=headers, json=payload)
            resp.raise_for_status()
            raw = resp.json()

            data = raw.get("data") or []
            if not data:
                raise RuntimeError("ARK 未返回图片数据")

            item = data[0]
            output_path.parent.mkdir(parents=True, exist_ok=True)
            if item.get("b64_json"):
                output_path.write_bytes(base64.b64decode(item["b64_json"]))
            elif item.get("url"):
                dl = client.get(item["url"])
                dl.raise_for_status()
                output_path.write_bytes(dl.content)
            else:
                raise RuntimeError("ARK 响应缺少图片内容")
        return output_path
