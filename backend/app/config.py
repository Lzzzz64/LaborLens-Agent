from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    database_url: str = "mysql+pymysql://labor_lens:labor_lens@mysql:3306/labor_lens"
    chroma_url: str = "http://chroma:8000"
    model_base_url: str = "https://api.openai.com/v1"
    model_name: str = ""
    model_api_key: str = ""
    upload_ttl_minutes: int = 30

    model_config = SettingsConfigDict(env_file=".env", extra="ignore")


@lru_cache
def get_settings() -> Settings:
    return Settings()
