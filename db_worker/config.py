from pydantic_settings import BaseSettings, SettingsConfigDict


class Config(BaseSettings):
    model_config = SettingsConfigDict(
        env_file='.env',
        env_file_encoding='utf-8',
        case_sensitive=False,
        extra='ignore'
    )
    
    # Redis
    redis_host: str = 'localhost'
    redis_port: int = 6379
    
    # PostgreSQL
    postgres_host: str = 'localhost'
    postgres_port: int = 5432
    postgres_db: str = 'sticker_collector'
    postgres_user: str = 'bot_user'
    postgres_password: str


# Create global config instance
config = Config()
