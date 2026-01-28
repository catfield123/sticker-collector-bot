import os
from pydantic_settings import BaseSettings, SettingsConfigDict


class Config(BaseSettings):
    model_config = SettingsConfigDict(
        env_file='.env',
        env_file_encoding='utf-8',
        case_sensitive=False,
        extra='ignore'
    )
    
    # Telegram Bot
    bot_token: str
    
    # Redis
    redis_host: str = 'localhost'
    redis_port: int = 6379
    
    @property
    def instruction_video_path(self) -> str:
        """Get the path to the instruction video."""
        return os.path.join(os.path.dirname(__file__), 'media', 'instruction_video.mp4')


# Create global config instance
config = Config()
