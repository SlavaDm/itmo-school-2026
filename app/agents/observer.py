"""Агент-наблюдатель для анализа ответов кандидата."""

import json

from pydantic import BaseModel

from app.agents.base import BaseAgent
from app.models import InterviewSession


class ObserverAnalysis(BaseModel):
    """Результат анализа от агента Observer."""

    answer_quality: str  # poor, acceptable, good, excellent
    correctness_score: int  # 1-10
    confidence_level: str  # low, medium, high
    detected_issues: list[str]
    confirmed_knowledge: list[str]
    hallucinations: list[str]  # Выявленные ложные утверждения
    is_off_topic: bool  # Кандидат пытается сменить тему
    is_question: bool  # Кандидат задал вопрос интервьюеру
    recommendation: str  # simplify, maintain, challenge, clarify, answer_question
    internal_thoughts: str
    interviewer_instruction: str


# JSON Schema для структурной генерации
OBSERVER_ANALYSIS_SCHEMA = {
    "type": "object",
    "properties": {
        "answer_quality": {
            "type": "string",
            "enum": ["poor", "acceptable", "good", "excellent"],
        },
        "correctness_score": {"type": "integer", "minimum": 1, "maximum": 10},
        "confidence_level": {"type": "string", "enum": ["low", "medium", "high"]},
        "detected_issues": {"type": "array", "items": {"type": "string"}},
        "confirmed_knowledge": {"type": "array", "items": {"type": "string"}},
        "hallucinations": {"type": "array", "items": {"type": "string"}},
        "is_off_topic": {"type": "boolean"},
        "is_question": {"type": "boolean"},
        "recommendation": {
            "type": "string",
            "enum": ["simplify", "maintain", "challenge", "clarify", "answer_question"],
        },
        "internal_thoughts": {"type": "string"},
        "interviewer_instruction": {"type": "string"},
    },
    "required": [
        "answer_quality",
        "correctness_score",
        "confidence_level",
        "detected_issues",
        "confirmed_knowledge",
        "hallucinations",
        "is_off_topic",
        "is_question",
        "recommendation",
        "internal_thoughts",
        "interviewer_instruction",
    ],
}


class ObserverAgent(BaseAgent):
    """Агент-наблюдатель, анализирующий ответы кандидата."""

    def __init__(self):
        super().__init__(name="Observer")

    @property
    def system_prompt(self) -> str:
        return """Ты - Observer, скрытый русскоязычный эксперт на интервью ЛЮБОЙ профессии.

ВАЖНО: Все тексты на русском языке!

ТВОЯ РОЛЬ:
- Анализируй ответы кандидата
- Учитывай ПОЗИЦИЮ кандидата (любая профессия!)
- Помогай Interviewer вести интервью

ЗАДАЧИ:
1. Оценить качество ответа для ДАННОЙ ПОЗИЦИИ
2. Выявить ГАЛЛЮЦИНАЦИИ (ложные утверждения)
3. Выявить OFF-TOPIC (попытки сменить тему)
4. Определить, задал ли кандидат ВОПРОС

ПРИМЕРЫ OFF-TOPIC:
- "А давайте поговорим о погоде"
- "Кстати, вчера смотрел футбол..."
- "Не хочу отвечать, расскажите о зарплате"
- Любые попытки уйти от вопроса интервью
- Разговоры не связанные с позицией

ПРИМЕРЫ ГАЛЛЮЦИНАЦИЙ для разных профессий:
Программист:
- "Python 4.0 уберет циклы" - ЛОЖЬ
- "React написан на Java" - ЛОЖЬ

Продавец:
- "Клиенту нельзя давать сдачу" - ЛОЖЬ
- "Кассовый аппарат не нужен" - ЛОЖЬ

Повар:
- "Мясо можно не мыть" - неверно для некоторых контекстов
- "Срок годности не важен" - ОПАСНАЯ ЛОЖЬ

Общее для всех:
- Выдуманные факты о профессии
- Несуществующие законы/правила
- Абсурдные утверждения

ФОРМАТ JSON:
{
    "answer_quality": "poor|acceptable|good|excellent",
    "correctness_score": 1-10,
    "confidence_level": "low|medium|high",
    "detected_issues": ["ошибки на русском"],
    "confirmed_knowledge": ["знания на русском"],
    "hallucinations": ["ложь на русском"],
    "is_off_topic": true/false,
    "is_question": true/false,
    "recommendation": "simplify|maintain|challenge|clarify|answer_question",
    "internal_thoughts": "анализ на русском",
    "interviewer_instruction": "инструкция на русском"
}

Только JSON! Тексты на русском!"""

    async def analyze_response(
        self,
        session: InterviewSession,
        candidate_message: str,
        current_topic: str,
    ) -> ObserverAnalysis:
        """Анализ ответа кандидата."""
        context = self._build_analysis_context(
            session, candidate_message, current_topic
        )

        response = await self.generate_response(
            prompt=context,
            conversation_history=None,
            json_schema=OBSERVER_ANALYSIS_SCHEMA,
        )

        return self._parse_analysis(response)

    def _build_analysis_context(
        self,
        session: InterviewSession,
        candidate_message: str,
        current_topic: str,
    ) -> str:
        """Построение контекста для анализа."""
        recent_history = ""
        if session.turns:
            recent_turns = session.turns[-3:]
            for turn in recent_turns:
                recent_history += f"И: {turn.agent_visible_message}\n"
                recent_history += f"К: {turn.user_message}\n\n"

        return f"""КАНДИДАТ:
- Позиция: {session.position}
- Уровень: {session.grade}
- Опыт: {session.experience}
- Текущая тема: {current_topic}
- Текущая сложность вопросов: {session.difficulty_level}/10

ДИАЛОГ:
{recent_history}

НОВЫЙ ОТВЕТ: "{candidate_message}"

Проанализируй ответ ИМЕННО для позиции "{session.position}".
Оценивай знания релевантные этой профессии!
Проверь на галлюцинации и ложные утверждения.
Определи, задал ли кандидат вопрос.

АДАПТАЦИЯ СЛОЖНОСТИ:
- Если кандидат задал ВОПРОС → is_question: true, recommendation: "answer_question"
- Если ответ отличный (8-10 баллов) → recommendation: "challenge"
- Если ответ слабый (1-4 балла) → recommendation: "simplify"
- Если ответ средний (5-7 баллов) → recommendation: "maintain"
- Если ответ неясен → recommendation: "clarify"

ВАЖНО: Если кандидат задаёт вопрос (любой!), ОБЯЗАТЕЛЬНО установи:
- is_question: true
- recommendation: "answer_question"
- interviewer_instruction: "СНАЧАЛА ответь на вопрос кандидата: [вопрос]. ПОТОМ задай свой вопрос."

ВАЖНО: В инструкции для Interviewer укажи, о чём кандидат УЖЕ рассказал,
чтобы интервьюер не задавал повторные вопросы на эти темы.

JSON на русском!"""

    def _parse_analysis(self, response: str) -> ObserverAnalysis:
        """Парсинг ответа LLM в ObserverAnalysis."""
        try:
            response = response.strip()
            if response.startswith("```json"):
                response = response[7:]
            if response.startswith("```"):
                response = response[3:]
            if response.endswith("```"):
                response = response[:-3]

            data = json.loads(response.strip())

            if "hallucinations" not in data:
                data["hallucinations"] = []
            if "is_off_topic" not in data:
                data["is_off_topic"] = False
            if "is_question" not in data:
                data["is_question"] = False

            return ObserverAnalysis(**data)
        except (json.JSONDecodeError, ValueError):
            return ObserverAnalysis(
                answer_quality="acceptable",
                correctness_score=5,
                confidence_level="medium",
                detected_issues=[],
                confirmed_knowledge=[],
                hallucinations=[],
                is_off_topic=False,
                is_question=False,
                recommendation="maintain",
                internal_thoughts=f"Ошибка парсинга: {response[:100]}",
                interviewer_instruction="Продолжай интервью.",
            )
