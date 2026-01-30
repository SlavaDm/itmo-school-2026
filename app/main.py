"""Главный модуль FastAPI приложения."""

from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from dotenv import load_dotenv

from app.routers import interview_router
from app.services.llm import ollama_service

load_dotenv()


@asynccontextmanager
async def lifespan(_app: FastAPI):
    """Обработчик жизненного цикла приложения."""
    # Запуск
    health = await ollama_service.check_health()
    if health:
        print("[OK] Соединение с Ollama установлено")
    else:
        print("[WARN] Ollama недоступна. Убедитесь, что она запущена.")

    yield

    # Завершение
    await ollama_service.close()


app = FastAPI(
    title="Interview Coach",
    description="Мультиагентный тренер для технических интервью по Python",
    version="0.1.0",
    lifespan=lifespan,
)

# Middleware для CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Подключение роутеров
app.include_router(interview_router)


@app.get("/")
async def root():
    """Корневой эндпоинт с информацией об API."""
    return {
        "name": "Interview Coach API",
        "version": "0.1.0",
        "endpoints": {
            "start_interview": "POST /interview/start",
            "send_message": "POST /interview/{session_id}/message",
            "stop_interview": "POST /interview/{session_id}/stop",
            "get_log": "GET /interview/{session_id}/log",
            "get_status": "GET /interview/{session_id}/status",
        },
    }
