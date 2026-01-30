Interview Coach — мультиагентная система для проведения тренировочных интервью. Использует Ollama для локального LLM и поддерживает интервью для любых профессий на русском языке.

## Commands

```bash
# Установка зависимостей
uv sync

# Запуск сервера
uv run uvicorn app.main:app --reload

# Линтер
uv run pylint app/

# Форматирование
uv run black app/
```

## Architecture

Система использует четырёх-агентную архитектуру с координатором:

### Agents (`app/agents/`)

| Агент                    | Роль                                                                                               |
| ------------------------ | -------------------------------------------------------------------------------------------------- |
| **InterviewerAgent**     | Ведёт диалог, генерирует вопросы адаптированные под позицию и уровень                              |
| **ObserverAgent**        | Скрытый аналитик: оценивает ответы, выявляет галлюцинации и off-topic, даёт инструкции Interviewer |
| **HRManagerAgent**       | Принимает решение о найме, формирует финальный фидбэк                                              |
| **InterviewCoordinator** | Оркестратор: управляет сессиями, координирует агентов, регулирует сложность                        |

### Structured Generation

Observer и HRManager используют JSON Schema для структурной генерации через Ollama:

- `OBSERVER_ANALYSIS_SCHEMA` — схема для анализа ответов
- `HR_FEEDBACK_SCHEMA` — схема для финального фидбэка

### Flow

1. Создание сессии: `POST /interview/start` с `participant_name`, `position`, `grade`, `experience`
2. Обработка сообщения: Observer анализ → обновление сложности → Interviewer ответ
3. Команды завершения: "стоп игра", "давай фидбэк" и др.
4. Финальный фидбэк: HRManager генерирует решение + поиск ресурсов для roadmap

### Key Models (`app/models/`)

- `InterviewSession`: состояние сессии, turns, difficulty_level (1-10)
- `Turn`: `turn_id`, `user_message`, `agent_visible_message`, `internal_thoughts`
- `FinalFeedback`: Decision, TechnicalReview, SoftSkills, roadmap_with_resources
- `SessionStartRequest`: `participant_name`, `position`, `grade`, `experience`

### Services (`app/services/`)

- `OllamaService`: взаимодействие с Ollama, поддержка `json_schema` для structured output
- `SessionLogger`: логирование сессий в JSON

### Clients (`app/clients/`)

- `GoogleSearchClient`: поиск ресурсов для roadmap через Google Custom Search API

### Tools (`app/agents/tools.py`)

- `search_web()`: веб-поиск через Google API
- `search_resources_for_roadmap()`: поиск ресурсов для тем из roadmap (до 3 ссылок на тему)

## Configuration (`app/config.py`)

Переменные окружения с префиксом `INTERVIEW_`:

- `INTERVIEW_OLLAMA_BASE_URL` (default: `http://localhost:11434`)
- `INTERVIEW_OLLAMA_MODEL` (default: `llama3.2:3b`)

Для поиска ресурсов (опционально):

- `GOOGLE_SEARCH_API_KEY`
- `GOOGLE_SEARCH_CX`

## API Endpoints

| Метод | Endpoint                          | Описание                            |
| ----- | --------------------------------- | ----------------------------------- |
| POST  | `/interview/start`                | Создать сессию (без приветствия)    |
| POST  | `/interview/message/{session_id}` | Отправить сообщение, получить ответ |
| POST  | `/interview/{session_id}/stop`    | Завершить интервью, получить фидбэк |
| GET   | `/interview/{session_id}/log`     | Получить полный лог сессии          |
| GET   | `/interview/{session_id}/status`  | Получить статус сессии              |

## Requirements

- Python 3.11+
- Ollama llama3.2:3b
- Google Search API (опционально, для roadmap ресурсов)
