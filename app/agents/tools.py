"""Инструменты для агентов."""

import os
from typing import List, Dict
from app.clients import GoogleSearchClient, GoogleSearchClientError


async def search_resources_for_roadmap(
    roadmap: List[str],
    max_results_per_topic: int = 3,
) -> Dict[str, List[Dict]]:
    """
    Найти ресурсы для всех тем из roadmap через Google Search.

    Args:
        roadmap: Список тем для изучения
        max_results_per_topic: Максимум ссылок на тему (по умолчанию 3)

    Returns:
        Словарь {тема: [{"title": ..., "url": ...}]}
    """
    result = {}

    for topic in roadmap:
        search_results = await search_web(f"{topic} tutorial", max_results_per_topic)
        print(search_results)
        if search_results:
            result[topic] = [
                {
                    "title": r.get("title", topic),
                    "url": r.get("href", r.get("source", r.get("link", ""))),
                }
                for r in search_results[:max_results_per_topic]
            ]
        else:
            result[topic] = []

    return result


async def search_web(search_query: str, max_results: int = 10) -> List[Dict]:
    """
    Выполнение веб-поиска через Google Custom Search API.

    Требуются переменные окружения:
    - GOOGLE_SEARCH_API_KEY: Google API ключ
    - GOOGLE_SEARCH_CX: ID пользовательского поискового движка

    Получить ключи: https://developers.google.com/custom-search/v1/overview

    Args:
        search_query: Поисковый запрос
        max_results: Максимальное количество результатов (по умолчанию: 10).
                     Google API ограничивает до 10 за запрос.

    Returns:
        Список результатов поиска с title, description и URL.
        Возвращает пустой список при ошибке.
    """
    try:
        # Получение ключей API из переменных окружения
        api_key = os.getenv("GOOGLE_SEARCH_API_KEY")
        cx = os.getenv("GOOGLE_SEARCH_CX")

        if not api_key or not cx:
            raise ValueError(
                "Отсутствуют ключи Google Search API. "
                "Установите GOOGLE_SEARCH_API_KEY и GOOGLE_SEARCH_CX в .env файле"
            )

        # Инициализация клиента Google Search
        google_client = GoogleSearchClient(api_key=api_key, cx=cx, timeout=30)

        # Выполнение поиска (Google API ограничивает до 10 результатов за запрос)
        results = await google_client.search(
            query=search_query,
            num=min(max_results, 10),
        )

        print(
            f"Google Search: Найдено {len(results)} результатов для запроса: {search_query}"
        )
        return results

    except GoogleSearchClientError as e:
        print(f"Ошибка Google Search API: {e}")
        return []
    except ValueError as e:
        print(f"Ошибка конфигурации: {e}")
        return []
