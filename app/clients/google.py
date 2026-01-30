"""Клиент для Google Custom Search API."""

from typing import List, Dict
import httpx

BASE_URL: str = "https://www.googleapis.com/customsearch/v1"


class GoogleSearchClientError(Exception):
    """Исключение для ошибок GoogleSearchClient."""


def _parse_search_result(response: Dict) -> Dict:
    """
    Парсинг одного результата поиска из ответа Google API.

    Извлекает title, snippet (описание) и link из ответа API
    и возвращает словарь с унифицированными именами полей.

    Args:
        response: Словарь с одним результатом поиска от Google API.

    Returns:
        Dict: Результат поиска с ключами: title, description, source, href, body.
    """
    return {
        "title": response.get("title", ""),
        "description": response.get("snippet", ""),
        "source": response.get("link", ""),
        "href": response.get("link", ""),
        "body": response.get("snippet", ""),
    }


class GoogleSearchClient:
    """
    Асинхронный клиент для Google Custom Search API.

    Требуется:
    - Google API Key (GOOGLE_SEARCH_API_KEY)
    - Custom Search Engine ID (GOOGLE_SEARCH_CX)

    Получить ключи: https://developers.google.com/custom-search/v1/overview
    """

    def __init__(self, api_key: str, cx: str, timeout: int = 30) -> None:
        """
        Инициализация клиента Google Search.

        Args:
            api_key: Google API ключ
            cx: ID пользовательского поискового движка
            timeout: Таймаут запроса в секундах
        """
        self._api_key = api_key
        self._cx = cx
        self._base_url = BASE_URL
        self._timeout = timeout

    async def search(
        self, query: str, num: int = 10, language: str = "lang_ru"
    ) -> List[Dict]:
        """
        Выполнение поискового запроса через Google Custom Search API.

        Args:
            query: Поисковый запрос
            num: Количество результатов (1-10, по умолчанию: 10)
            language: Языковое ограничение (по умолчанию: lang_ru для русского)

        Returns:
            Список результатов поиска с title, description и URL

        Raises:
            GoogleSearchClientError: Если запрос к API не удался
        """
        # Google API ограничивает num до 10 за запрос
        num = min(num, 10)

        params = {
            "key": self._api_key,
            "cx": self._cx,
            "q": query,
            "lr": language,
            "num": num,
            "hl": "ru",  # Язык интерфейса
            "gl": "ru",  # Географическое расположение
        }

        try:
            async with httpx.AsyncClient(timeout=self._timeout) as client:
                response = await client.get(self._base_url, params=params)
                response.raise_for_status()

                data = response.json()

                # Проверка на ошибки API
                if "error" in data:
                    error_info = data["error"]
                    raise GoogleSearchClientError(
                        f"Ошибка Google API: {error_info.get('message', 'Неизвестная ошибка')}"
                    )

                # Парсинг результатов
                if "items" in data:
                    return [_parse_search_result(item) for item in data["items"]]

                # Результаты не найдены
                return []

        except httpx.HTTPStatusError as e:
            raise GoogleSearchClientError(
                f"HTTP ошибка {e.response.status_code}: {e.response.text}"
            ) from e
        except httpx.RequestError as e:
            raise GoogleSearchClientError(f"Ошибка запроса: {str(e)}") from e
        except Exception as e:
            raise GoogleSearchClientError(f"Неожиданная ошибка: {str(e)}") from e
