"""Конфигурация приложения."""

from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    """Настройки приложения."""

    # Настройки Ollama
    ollama_base_url: str = "http://localhost:11434"
    ollama_model: str = "llama3.2:3b"

    # Настройки интервью
    default_language: str = "ru"
    max_turns: int = 50

    # Логирование
    log_file: str = "interview_log.json"

    class Config:
        """Конфигурация Pydantic."""

        env_prefix = "INTERVIEW_"


settings = Settings()
