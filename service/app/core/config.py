from typing import Optional
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    openai_api_key: Optional[str] = None
    openai_model: str = "gpt-4o-mini"
    database_url: str = "sqlite:///./corrector.db"
    secret_key: Optional[str] = None

    class Config:
        env_file = ".env"


settings = Settings()
