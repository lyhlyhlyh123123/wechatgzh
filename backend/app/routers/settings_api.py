import os

from fastapi import APIRouter, Request
from pydantic import BaseModel

from app.config import get_presets
from app.config import settings as cfg
from app.services.envfile import read_env, write_env

WRITABLE_KEYS = {
    "DEEPSEEK_API_KEY": "deepseek_api_key",
    "DEEPSEEK_MODEL": "deepseek_model",
    "VOLCENGINE_ARK_API_KEY": "volcengine_ark_api_key",
    "VOLCENGINE_ARK_IMAGE_MODEL": "volcengine_ark_image_model",
    "IMAGE_SIZE_DEFAULT": "image_size_default",
    "IMAGE_COUNT_DEFAULT": "image_count_default",
}

ENV_PATH = os.environ.get("WECHATGZH_ENV_FILE", ".env")

router = APIRouter(prefix="/api", tags=["settings"])


class SettingsIn(BaseModel):
    deepseek_api_key: str | None = None
    deepseek_model: str | None = None
    volcengine_ark_api_key: str | None = None
    volcengine_ark_image_model: str | None = None
    image_size_default: str | None = None
    image_count_default: int | None = None


def _mask(value: str) -> str:
    if not value:
        return ""
    return "*" * max(len(value) - 4, 0) + value[-4:]


@router.get("/presets")
def presets():
    return get_presets()


@router.get("/settings")
def get_settings():
    return {
        "deepseek_api_key_masked": _mask(cfg.deepseek_api_key),
        "deepseek_model": cfg.deepseek_model,
        "volcengine_ark_api_key_masked": _mask(cfg.volcengine_ark_api_key),
        "volcengine_ark_image_model": cfg.volcengine_ark_image_model,
        "image_size_default": cfg.image_size_default,
        "presets": get_presets(),
        "image_count_default": cfg.image_count_default,
        "image_count_max": cfg.image_count_max,
        "api_ready": bool(cfg.deepseek_api_key and cfg.volcengine_ark_api_key),
    }


@router.put("/settings")
def put_settings(data: SettingsIn, request: Request):
    incoming = data.model_dump(exclude_none=True)
    env_updates = {}
    for env_key, field in WRITABLE_KEYS.items():
        if field in incoming:
            env_updates[env_key] = str(incoming[field])
            setattr(cfg, field, incoming[field])
    if env_updates:
        write_env(env_updates, path=ENV_PATH)
    request.app.state.default_size = cfg.image_size_default
    request.app.state.max_count = cfg.image_count_max
    if cfg.deepseek_api_key and cfg.deepseek_model:
        from app.clients.deepseek import DeepSeekClient

        request.app.state.llm = DeepSeekClient(
            cfg.deepseek_base_url, cfg.deepseek_api_key, cfg.deepseek_model,
        )
    if cfg.volcengine_ark_api_key and cfg.volcengine_ark_image_model:
        from app.clients.ark import ArkClient

        request.app.state.ark = ArkClient(
            cfg.volcengine_ark_base_url, cfg.volcengine_ark_api_key,
            cfg.volcengine_ark_image_model,
        )
    return {"ok": True}
