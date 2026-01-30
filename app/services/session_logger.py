"""Сервис для логирования сессий интервью в JSON."""

import json
from pathlib import Path
from typing import Optional

from app.models import InterviewSession, FinalFeedback


class SessionLogger:
    """Сервис для логирования сессий интервью в JSON."""

    def __init__(self, interviews_dir: str = "interviews"):
        self.interviews_dir = Path(interviews_dir)
        self._ensure_dir()

    def _ensure_dir(self):
        """Создание папки для логов если не существует."""
        self.interviews_dir.mkdir(exist_ok=True)

    def _get_log_path(self, script_number: int) -> Path:
        """Получение пути к файлу лога по номеру сценария."""
        return self.interviews_dir / f"interview_log_{script_number}.json"

    def save_interview_log(
        self,
        session: InterviewSession,
        feedback: FinalFeedback,
    ) -> str:
        """Сохранение лога интервью в файл.

        Args:
            session: Сессия интервью
            feedback: Финальный фидбэк

        Returns:
            Путь к сохранённому файлу
        """
        # Формируем turns в нужном формате
        turns = []
        for turn in session.turns:
            turns.append(
                {
                    "turn_id": turn.turn_id,
                    "agent_visible_message": turn.agent_visible_message,
                    "user_message": turn.user_message,
                    "internal_thoughts": turn.internal_thoughts,
                }
            )

        # Формируем итоговый объект
        log_data = {
            "participant_name": session.participant_name,
            "turns": turns,
            "final_feedback": feedback.to_markdown(),
        }

        # Сохраняем в файл
        log_path = self._get_log_path(session.script_number)
        log_path.write_text(
            json.dumps(log_data, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )

        return str(log_path)

    def get_interview_log(self, script_number: int) -> Optional[dict]:
        """Получение лога интервью по номеру сценария."""
        log_path = self._get_log_path(script_number)
        if not log_path.exists():
            return None

        try:
            content = log_path.read_text(encoding="utf-8")
            return json.loads(content)
        except (json.JSONDecodeError, FileNotFoundError):
            return None


# Глобальный экземпляр
session_logger = SessionLogger()
