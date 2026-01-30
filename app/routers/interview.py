"""API эндпоинты для проведения интервью."""

from typing import Optional

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from app.agents.coordinator import coordinator
from app.models.session import (
    SessionStartRequest,
    SessionMessageRequest,
)
from app.models.feedback import FinalFeedback
from app.services.session_logger import session_logger

router = APIRouter(prefix="/interview", tags=["interview"])


class MessageResponse(BaseModel):
    """Ответ на сообщение с возможным фидбэком."""

    agent_message: str
    turn_id: int
    is_finished: bool = False
    feedback: Optional[FinalFeedback] = None


@router.post("/start", response_model=dict)
async def start_interview(request: SessionStartRequest):
    """Создание новой сессии интервью."""
    session = coordinator.create_session(
        participant_name=request.participant_name,
        position=request.position,
        grade=request.grade,
        experience=request.experience,
        script_number=request.script_number,
    )

    return {
        "session_id": session.session_id,
        "participant_name": session.participant_name,
        "position": session.position,
        "grade": session.grade,
        "script_number": session.script_number,
    }


@router.post("/message/{session_id}", response_model=MessageResponse)
async def send_message(session_id: str, request: SessionMessageRequest):
    """Отправка сообщения от кандидата и получение ответа интервьюера.

    Если сообщение содержит команду завершения (например, "Стоп игра"),
    интервью автоматически завершается и возвращается фидбэк.
    """
    session = coordinator.get_session(session_id)
    if not session:
        raise HTTPException(status_code=404, detail="Сессия не найдена")

    if session.status != "active":
        raise HTTPException(status_code=400, detail="Сессия не активна")

    try:
        agent_message, turn_id, should_stop = await coordinator.process_message(
            session_id=session_id,
            user_message=request.message,
        )

        # Если команда завершения - автоматически завершаем и возвращаем фидбэк
        if should_stop:
            feedback = await coordinator.stop_interview(session_id)
            session_logger.save_interview_log(session, feedback)

            return MessageResponse(
                agent_message=feedback.summary or "Интервью завершено.",
                turn_id=turn_id,
                is_finished=True,
                feedback=feedback,
            )

        return MessageResponse(
            agent_message=agent_message,
            turn_id=turn_id,
            is_finished=False,
            feedback=None,
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e)) from e
    except RuntimeError as e:
        raise HTTPException(status_code=500, detail=str(e)) from e


@router.post("/{session_id}/stop", response_model=FinalFeedback)
async def stop_interview(session_id: str):
    """Завершение интервью и получение финального фидбэка."""
    session = coordinator.get_session(session_id)
    if not session:
        raise HTTPException(status_code=404, detail="Сессия не найдена")

    if session.status != "active":
        raise HTTPException(status_code=400, detail="Сессия уже завершена")

    try:
        feedback = await coordinator.stop_interview(session_id)

        # Сохранение лога интервью в файл
        session_logger.save_interview_log(session, feedback)

        return feedback
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e)) from e
    except RuntimeError as e:
        raise HTTPException(status_code=500, detail=str(e)) from e


@router.get("/{session_id}/log")
async def get_session_log(session_id: str):
    """Получение полного лога сессии интервью."""
    session = coordinator.get_session(session_id)
    if not session:
        raise HTTPException(status_code=404, detail="Сессия не найдена")

    log = session_logger.get_interview_log(session.script_number)
    if not log:
        raise HTTPException(status_code=404, detail="Лог сессии не найден")

    return log


@router.get("/{session_id}/status")
async def get_session_status(session_id: str):
    """Получение текущего статуса сессии."""
    session = coordinator.get_session(session_id)
    if not session:
        raise HTTPException(status_code=404, detail="Сессия не найдена")

    return {
        "session_id": session.session_id,
        "status": session.status,
        "turns_count": len(session.turns),
        "current_topic": session.current_topic,
        "difficulty_level": session.difficulty_level,
    }
