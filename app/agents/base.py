"""Базовый класс для всех агентов."""

from abc import ABC, abstractmethod
from typing import Optional, Any

from app.services.llm import OllamaService, ollama_service


class BaseAgent(ABC):
    """Базовый класс для всех агентов."""

    def __init__(
        self,
        name: str,
        llm_service: Optional[OllamaService] = None,
    ):
        self.name = name
        self.llm = llm_service or ollama_service

    @property
    @abstractmethod
    def system_prompt(self) -> str:
        """Системный промпт, определяющий поведение агента."""

    async def generate_response(
        self,
        prompt: str,
        conversation_history: Optional[list[dict]] = None,
        json_schema: Optional[dict[str, Any]] = None,
    ) -> str:
        """Генерация ответа с использованием LLM.

        Args:
            prompt: Текст запроса
            conversation_history: История диалога
            json_schema: JSON Schema для структурной генерации

        Returns:
            Текст ответа от модели
        """
        return await self.llm.generate(
            prompt=prompt,
            system_prompt=self.system_prompt,
            conversation_history=conversation_history,
            json_schema=json_schema,
        )
