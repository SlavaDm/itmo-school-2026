"""Сервис для взаимодействия с Ollama LLM."""

from typing import Optional, Any

import httpx

from app.config import settings


class OllamaService:
    """Сервис для взаимодействия с Ollama LLM."""

    def __init__(
        self,
        base_url: str = settings.ollama_base_url,
        model: str = settings.ollama_model,
    ):
        self.base_url = base_url
        self.model = model
        self.client = httpx.AsyncClient(timeout=120.0)

    async def generate(
        self,
        prompt: str,
        system_prompt: Optional[str] = None,
        conversation_history: Optional[list[dict]] = None,
        json_schema: Optional[dict[str, Any]] = None,
    ) -> str:
        """Генерация ответа от Ollama.

        Args:
            prompt: Текст запроса
            system_prompt: Системный промпт
            conversation_history: История диалога
            json_schema: JSON Schema для структурной генерации

        Returns:
            Текст ответа от модели
        """
        messages = []

        if system_prompt:
            messages.append({"role": "system", "content": system_prompt})

        if conversation_history:
            messages.extend(conversation_history)

        messages.append({"role": "user", "content": prompt})

        payload = {
            "model": self.model,
            "messages": messages,
            "stream": False,
        }

        # Добавляем структурную генерацию если передана schema
        if json_schema:
            payload["format"] = json_schema

        try:
            response = await self.client.post(
                f"{self.base_url}/api/chat",
                json=payload,
            )
            response.raise_for_status()
            data = response.json()
            return data.get("message", {}).get("content", "")
        except httpx.HTTPError as e:
            raise RuntimeError(f"Ошибка запроса к Ollama: {e}") from e

    async def check_health(self) -> bool:
        """Проверка доступности Ollama."""
        try:
            response = await self.client.get(f"{self.base_url}/api/tags")
            return response.status_code == 200
        except httpx.HTTPError:
            return False

    async def close(self):
        """Закрытие HTTP клиента."""
        await self.client.aclose()


# Глобальный экземпляр
ollama_service = OllamaService()
