"""Агент-интервьюер для проведения интервью на любую позицию."""

from app.agents.base import BaseAgent
from app.agents.observer import ObserverAnalysis
from app.models import InterviewSession


class InterviewerAgent(BaseAgent):
    """Агент-интервьюер, проводящий техническое интервью."""

    def __init__(self):
        super().__init__(name="Interviewer")

    @property
    def system_prompt(self) -> str:
        return """Ты - опытный интервьюер для ЛЮБЫХ профессий.

===== ЯЗЫК =====
СТРОГО ОБЯЗАТЕЛЬНО: Пиши ТОЛЬКО НА РУССКОМ ЯЗЫКЕ!
ЗАПРЕЩЕНО: Английский, смешение языков, транслит.
Даже технические термины объясняй по-русски.

===== ПРИНЦИПЫ =====
1. Вопросы РЕЛЕВАНТНЫЕ ПОЗИЦИИ кандидата
2. Адаптируй сложность под уровень (Junior/Middle/Senior)
3. Если кандидат задает вопросы - отвечай на них
4. НИКОГДА не повторяй вопросы, которые уже задавал
5. Учитывай ответы кандидата - не спрашивай то, что он уже рассказал

===== УСТОЙЧИВОСТЬ =====
- Ложь кандидата - мягко поправь
- Уход от темы - вежливо верни к интервью
- Не поддерживай посторонние разговоры

===== ФОРМАТ =====
- Краткий комментарий + один вопрос
- 2-4 предложения максимум
- Только русский язык!"""

    async def generate_greeting(self, session: InterviewSession) -> str:
        """Генерация приветствия для начала интервью."""
        prompt = f"""Начни интервью на позицию "{session.position}".

КАНДИДАТ: {session.participant_name}
УРОВЕНЬ: {session.grade}
ОПЫТ: {session.experience}
СЛОЖНОСТЬ: {session.difficulty_level}/10

Поприветствуй, объясни формат и задай первый вопрос.
Ответь СТРОГО на русском языке (без английского!).
2-4 предложения."""

        return await self.generate_response(prompt)

    async def generate_next_question(
        self,
        session: InterviewSession,
        candidate_message: str,
        observer_analysis: ObserverAnalysis,
    ) -> str:
        """Генерация следующего вопроса на основе анализа Observer."""
        prompt = self._build_prompt(session, candidate_message, observer_analysis)

        return await self.generate_response(
            prompt=prompt,
            conversation_history=session.get_conversation_history()[-6:],
        )

    def _build_prompt(
        self,
        session: InterviewSession,
        candidate_message: str,
        analysis: ObserverAnalysis,
    ) -> str:
        """Построение промпта для генерации следующего вопроса."""

        difficulty_instruction = {
            "simplify": "Упрости вопрос.",
            "maintain": "Тот же уровень.",
            "challenge": "Усложни вопрос.",
            "clarify": "Попроси уточнить.",
            "answer_question": "Ответь на вопрос кандидата.",
        }.get(analysis.recommendation, "Продолжай.")

        hallucination_warning = ""
        if analysis.hallucinations:
            issues = ", ".join(analysis.hallucinations)
            hallucination_warning = f"\nЛОЖЬ КАНДИДАТА: {issues}\nМягко поправь!\n"

        off_topic_warning = ""
        if analysis.is_off_topic:
            off_topic_warning = "\nКандидат УШЁЛ ОТ ТЕМЫ! Вежливо верни к интервью.\n"

        question_info = ""
        response_format = "Дай краткий комментарий и задай один новый вопрос."
        if analysis.is_question:
            question_info = """
===== КАНДИДАТ ЗАДАЛ ВОПРОС =====
ОБЯЗАТЕЛЬНО: СНАЧАЛА ответь на вопрос кандидата!
ПОТОМ задай свой вопрос.
Формат ответа:
1. Ответ на вопрос кандидата (2-3 предложения)
2. Твой следующий вопрос (1 предложение)
"""
            response_format = "СНАЧАЛА ответь на вопрос, ПОТОМ задай свой вопрос."

        return f"""ПОЗИЦИЯ: {session.position}
УРОВЕНЬ: {session.grade}
СЛОЖНОСТЬ: {session.difficulty_level}/10

ОТВЕТ КАНДИДАТА: "{candidate_message}"

ИНСТРУКЦИЯ: {analysis.interviewer_instruction}
РЕКОМЕНДАЦИЯ: {difficulty_instruction}
{hallucination_warning}{off_topic_warning}{question_info}
НЕ повторяй вопросы из истории диалога выше.

Ответь СТРОГО на русском языке (без английского!).
{response_format}
2-4 предложения."""

    async def generate_closing(self, session: InterviewSession) -> str:
        """Генерация завершающего сообщения."""
        prompt = f"""Интервью с {session.participant_name} завершается.
Вопросов: {len(session.turns)}

Поблагодари и скажи про обратную связь.
2-3 предложения на русском."""

        return await self.generate_response(prompt)
