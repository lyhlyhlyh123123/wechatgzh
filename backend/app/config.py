from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    deepseek_api_key: str = ""
    deepseek_base_url: str = "https://api.deepseek.com"
    deepseek_model: str = "deepseek-chat"
    volcengine_ark_api_key: str = ""
    volcengine_ark_base_url: str = "https://ark.cn-beijing.volces.com/api/v3"
    volcengine_ark_image_model: str = ""
    image_preset: str = "2:3_1080x1620,1:1_1080x1080,3:4_750x1000,16:9_1920x1080,9:16_1080x1920"
    image_size_default: str = "1080x1620"
    image_count_default: int = 1
    image_count_max: int = 3
    host: str = "127.0.0.1"
    port: int = 8000

    model_config = {"env_file": ".env", "env_file_encoding": "utf-8"}


settings = Settings()


def get_presets() -> list[dict]:
    result = []
    for item in settings.image_preset.split(","):
        label, _, size = item.strip().partition("_")
        if label and size:
            result.append({"label": label, "size": size})
    return result
