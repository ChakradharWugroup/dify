from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    app_name: str = "Enterprise AI Gateway"
    env: str = "development"
    host: str = "0.0.0.0"
    port: int = 8000
    database_url: str
    redis_url: str
    jwt_secret: str = "CHANGE_ME"
    jwt_expire_minutes: int = 60
    dify_base_url: str
    dify_api_key: str = ""
    gemini_enabled: bool = True
    web_search_enabled: bool = True
    rate_limit_per_minute: int = 30
    audit_log_enabled: bool = True

    class Config:
        env_file = "../../.env.development"

settings = Settings()
