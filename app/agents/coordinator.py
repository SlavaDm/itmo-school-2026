"""Координатор рабочего процесса между агентами."""

import re
from typing import Optional

from app.agents.interviewer import InterviewerAgent
from app.agents.observer import ObserverAgent, ObserverAnalysis
from app.agents.hr_manager import HRManagerAgent
from app.models import (
    InterviewSession,
    SessionStatus,
    FinalFeedback,
)

# Паттерны для распознавания команды завершения интервью
STOP_PATTERNS = [
    r"стоп\s*игра",
    r"давай\s*фидбэк",
    r"заверши\s*интервью",
    r"хватит",
    r"стоп",
    r"закончи",
    r"завершай",
]


def _is_stop_command(message: str) -> bool:
    """Проверка, является ли сообщение командой завершения."""
    message_lower = message.lower().strip()
    for pattern in STOP_PATTERNS:
        if re.search(pattern, message_lower):
            return True
    return False


class InterviewCoordinator:
    """Координатор рабочего процесса интервью между агентами."""

    def __init__(self):
        self.interviewer = InterviewerAgent()
        self.observer = ObserverAgent()
        self.hr_manager = HRManagerAgent()
        self.sessions: dict[str, InterviewSession] = {}
        self.session_analyses: dict[str, list[ObserverAnalysis]] = {}

    def create_session(
        self,
        participant_name: str,
        fullname: str,
        position: str,
        grade: str,
        experience: str,
        script_number: int = 1,
    ) -> InterviewSession:
        """Создание новой сессии интервью."""
        # Определение начального уровня сложности по грейду
        if grade == "Junior":
            difficulty = 5
        elif grade == "Middle":
            difficulty = 7
        else:
            difficulty = 8

        session = InterviewSession(
            participant_name=participant_name,
            fullname=fullname,
            position=position,
            grade=grade,
            experience=experience,
            script_number=script_number,
            current_topic=f"Основы для {position}",
            difficulty_level=difficulty,
        )
        self.sessions[session.session_id] = session
        self.session_analyses[session.session_id] = []
        return session

    def get_session(self, session_id: str) -> Optional[InterviewSession]:
        """Получение существующей сессии."""
        return self.sessions.get(session_id)

    def is_stop_command(self, message: str) -> bool:
        """Проверка, является ли сообщение командой завершения."""
        return _is_stop_command(message)

    async def start_interview(self, session_id: str) -> str:
        """Начало интервью и получение приветственного сообщения."""
        session = self.sessions.get(session_id)
        if not session:
            raise ValueError(f"Сессия {session_id} не найдена")

        greeting = await self.interviewer.generate_greeting(session)

        # Добавление начального хода с пустым сообщением пользователя
        session.add_turn(
            user_message="[Начало интервью]",
            agent_visible_message=greeting,
            internal_thoughts="[Observer]: Интервью начинается. Ожидаем первый ответ.\n[Interviewer]: Приветствую кандидата и задаю первый вопрос.\n",
        )

        return greeting

    async def process_message(
        self,
        session_id: str,
        user_message: str,
    ) -> tuple[str, int, bool]:
        """Обработка сообщения пользователя и возврат ответа интервьюера.

        Returns:
            tuple: (ответ агента, номер хода, флаг завершения)
        """
        session = self.sessions.get(session_id)
        if not session:
            raise ValueError(f"Сессия {session_id} не найдена")

        # Проверка на команду завершения
        if _is_stop_command(user_message):
            # Записываем команду завершения
            session.add_turn(
                user_message=user_message,
                agent_visible_message="[Команда завершения получена]",
                internal_thoughts="[Observer]: Кандидат запросил завершение интервью.\n[Interviewer]: Получена команда завершения.\n",
            )
            return "[Завершаю интервью и формирую фидбэк...]", len(session.turns), True

        # Шаг 1: Observer анализирует ответ
        analysis = await self.observer.analyze_response(
            session=session,
            candidate_message=user_message,
            current_topic=session.current_topic,
        )
        self.session_analyses[session_id].append(analysis)

        # Шаг 2: Обновление сложности на основе рекомендации
        self._update_difficulty(session, analysis)

        # Шаг 3: Interviewer генерирует ответ с учетом указаний Observer
        interviewer_response = await self.interviewer.generate_next_question(
            session=session,
            candidate_message=user_message,
            observer_analysis=analysis,
        )

        # Шаг 4: Запись хода
        internal_thoughts = self._format_internal_thoughts(analysis)
        turn = session.add_turn(
            user_message=user_message,
            agent_visible_message=interviewer_response,
            internal_thoughts=internal_thoughts,
        )

        return interviewer_response, turn.turn_id, False

    def _update_difficulty(self, session: InterviewSession, analysis: ObserverAnalysis):
        """Обновление сложности сессии на основе рекомендации Observer."""
        if analysis.recommendation == "simplify" and session.difficulty_level > 1:
            session.difficulty_level -= 1
        elif analysis.recommendation == "challenge" and session.difficulty_level < 10:
            session.difficulty_level += 1

    def _format_internal_thoughts(self, analysis: ObserverAnalysis) -> str:
        """Форматирование внутренних мыслей агентов."""
        # Observer
        observer_thought = (
            f"{analysis.internal_thoughts} "
            f"Качество: {analysis.answer_quality} ({analysis.correctness_score}/10). "
            f"Рекомендация: {analysis.recommendation}."
        )
        if analysis.hallucinations:
            observer_thought += f" Галлюцинации: {', '.join(analysis.hallucinations)}."
        if analysis.is_off_topic:
            observer_thought += " Кандидат ушёл от темы."
        if analysis.is_question:
            observer_thought += " Кандидат задал вопрос."

        # Interviewer
        interviewer_thought = analysis.interviewer_instruction

        return f"[Observer]: {observer_thought}\n[Interviewer]: {interviewer_thought}\n"

    async def stop_interview(self, session_id: str) -> FinalFeedback:
        """Завершение интервью и генерация финального фидбэка."""
        session = self.sessions.get(session_id)
        if not session:
            raise ValueError(f"Сессия {session_id} не найдена")

        # Генерация завершающего сообщения от Interviewer
        closing = await self.interviewer.generate_closing(session)
        session.add_turn(
            user_message="[Завершение интервью]",
            agent_visible_message=closing,
            internal_thoughts="[Observer]: Интервью завершено. Передаю данные HR-менеджеру.\n[Interviewer]: Прощаюсь с кандидатом.\n[HRManager]: Формирую итоговый фидбэк и решение о найме.\n",
        )

        # Отметка сессии как завершенной
        session.status = SessionStatus.COMPLETED

        # HR Manager принимает решение о найме
        analyses = self.session_analyses.get(session_id, [])
        feedback = await self.hr_manager.generate_feedback(session, analyses)

        return feedback


# Глобальный экземпляр координатора
coordinator = InterviewCoordinator()
