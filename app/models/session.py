"""Модели для сессий интервью."""

import uuid
from datetime import datetime
from enum import Enum

from pydantic import BaseModel, Field


class SessionStatus(str, Enum):
    """Статус сессии интервью."""

    ACTIVE = "active"
    COMPLETED = "completed"
    CANCELLED = "cancelled"


class Turn(BaseModel):
    """Один ход в диалоге интервью."""

    turn_id: int
    timestamp: datetime = Field(default_factory=datetime.now)
    user_message: str
    agent_visible_message: str
    internal_thoughts: str = ""  # Скрытые наблюдения от Observer


class SessionStartRequest(BaseModel):
    """Запрос на создание новой сессии интервью."""

    participant_name: str
    position: str
    grade: str = "Junior"
    experience: str = ""
    script_number: int = 1


class SessionMessageRequest(BaseModel):
    """Запрос на отправку сообщения в сессии."""

    message: str


class SessionMessageResponse(BaseModel):
    """Ответ от агента-интервьюера."""

    agent_message: str
    turn_id: int


class InterviewSession(BaseModel):
    """Состояние сессии интервью."""

    session_id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    participant_name: str
    position: str
    grade: str
    experience: str
    script_number: int = 1
    status: SessionStatus = SessionStatus.ACTIVE
    created_at: datetime = Field(default_factory=datetime.now)
    turns: list[Turn] = Field(default_factory=list)
    current_topic: str = ""
    difficulty_level: int = 5  # Шкала 1-10

    def add_turn(
        self, user_message: str, agent_visible_message: str, internal_thoughts: str = ""
    ) -> Turn:
        """Добавление нового хода в диалог."""
        turn = Turn(
            turn_id=len(self.turns) + 1,
            user_message=user_message,
            agent_visible_message=agent_visible_message,
            internal_thoughts=internal_thoughts,
        )
        self.turns.append(turn)
        return turn

    def get_conversation_history(self) -> list[dict]:
        """Получение истории диалога для контекста LLM."""
        history = []
        for turn in self.turns:
            history.append({"role": "user", "content": turn.user_message})
            history.append({"role": "assistant", "content": turn.agent_visible_message})
        return history
