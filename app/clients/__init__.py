"""Модуль клиентов для внешних API."""

from .google import GoogleSearchClient, GoogleSearchClientError

__all__ = [
    "GoogleSearchClient",
    "GoogleSearchClientError",
]
