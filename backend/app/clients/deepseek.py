from __future__ import annotations

import json
import time

import httpx


class DeepSeekError(Exception):
    pass


class DeepSeekClient:
    def __init__(
        self,
        base_url: str,
        api_key: str,
        model: str,
        timeout: float = 60.0,
        transport: httpx.BaseTransport | None = None,
        retries: int = 3,
    ) -> None:
        self.base_url = base_url.rstrip("/")
        self.api_key = api_key
        self.model = model
        self.timeout = timeout
        self.transport = transport
        self.retries = retries

    def chat_json(self, system: str, user: str, temperature: float = 0.8) -> dict:
        last_exc: Exception | None = None
        for i in range(self.retries):
            try:
                return self._once(system, user, temperature)
            except httpx.HTTPStatusError as exc:
                if exc.response.status_code != 429 and exc.response.status_code < 500:
                    raise
                last_exc = exc
            except DeepSeekError as exc:
                last_exc = exc
            if i < self.retries - 1:
                time.sleep(1)
        raise DeepSeekError(f"生成失败（已重试{self.retries}次）: {last_exc}")

    def _once(self, system: str, user: str, temperature: float) -> dict:
        payload = {
            "model": self.model,
            "response_format": {"type": "json_object"},
            "messages": [
                {"role": "system", "content": system},
                {"role": "user", "content": user},
            ],
            "temperature": temperature,
        }
        headers = {"Authorization": f"Bearer {self.api_key}"}
        with httpx.Client(timeout=self.timeout, transport=self.transport) as client:
            resp = client.post(f"{self.base_url}/chat/completions", headers=headers, json=payload)
            resp.raise_for_status()
            raw = resp.json()
        try:
            content = raw["choices"][0]["message"]["content"]
            return json.loads(content)
        except (KeyError, IndexError, TypeError, json.JSONDecodeError) as exc:
            raise DeepSeekError(f"LLM 响应解析失败: {exc}") from exc
