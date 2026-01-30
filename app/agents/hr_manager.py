"""Агент HR-менеджер для принятия решений о найме."""

import json

from app.agents.base import BaseAgent
from app.agents.observer import ObserverAnalysis
from app.agents.tools import search_resources_for_roadmap
from app.models import (
    InterviewSession,
    FinalFeedback,
    Decision,
    TechnicalReview,
    SoftSkills,
    KnowledgeGap,
    RoadmapItem,
)

# JSON Schema для структурной генерации фидбэка
HR_FEEDBACK_SCHEMA = {
    "type": "object",
    "properties": {
        "hiring_recommendation": {
            "type": "string",
            "enum": ["Strong Hire", "Hire", "Maybe", "No Hire"],
        },
        "actual_grade": {"type": "string", "enum": ["Junior", "Middle", "Senior"]},
        "confidence_score": {"type": "integer", "minimum": 0, "maximum": 100},
        "confirmed_skills": {"type": "array", "items": {"type": "string"}},
        "knowledge_gaps": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "topic": {"type": "string"},
                    "correct_answer": {"type": "string"},
                },
                "required": ["topic", "correct_answer"],
            },
        },
        "clarity": {"type": "integer", "minimum": 1, "maximum": 10},
        "honesty": {"type": "integer", "minimum": 1, "maximum": 10},
        "engagement": {"type": "integer", "minimum": 1, "maximum": 10},
        "roadmap": {"type": "array", "items": {"type": "string"}},
        "summary": {"type": "string"},
    },
    "required": [
        "hiring_recommendation",
        "actual_grade",
        "confidence_score",
        "confirmed_skills",
        "knowledge_gaps",
        "clarity",
        "honesty",
        "engagement",
        "roadmap",
        "summary",
    ],
}


def _clean_json_response(response: str) -> str:
    """Очистка ответа от markdown-разметки."""
    response = response.strip()
    if response.startswith("```json"):
        response = response[7:]
    if response.startswith("```"):
        response = response[3:]
    if response.endswith("```"):
        response = response[:-3]
    return response.strip()


class HRManagerAgent(BaseAgent):
    """Агент HR-менеджер, принимающий решение о найме."""

    def __init__(self):
        super().__init__(name="HRManager")

    @property
    def system_prompt(self) -> str:
        return """Ты - опытный русскоязычный HR-менеджер.

ТВОЯ РОЛЬ:
- Принимать решения о найме на основе данных интервью
- Оценивать соответствие кандидата позиции
- Формировать объективный фидбэк

ПРИНЦИПЫ:
1. Оценивай навыки РЕЛЕВАНТНЫЕ позиции кандидата
2. Не оценивай программирование для продавца и наоборот
3. Галлюцинации (ложные утверждения) - серьёзный минус
4. Учитывай уровень (Junior/Middle/Senior) при оценке
5. Будь объективен и конструктивен

ФОРМАТ ОТВЕТА - только JSON на русском языке."""

    async def generate_feedback(
        self,
        session: InterviewSession,
        analyses: list[ObserverAnalysis],
    ) -> FinalFeedback:
        """Генерация финального фидбэка и решения о найме."""
        # Агрегация данных от Observer
        all_confirmed = []
        all_issues = []
        all_hallucinations = []
        total_score = 0
        score_count = 0

        for analysis in analyses:
            all_confirmed.extend(analysis.confirmed_knowledge)
            all_issues.extend(analysis.detected_issues)
            all_hallucinations.extend(analysis.hallucinations)
            total_score += analysis.correctness_score
            score_count += 1

        avg_score = total_score / score_count if score_count > 0 else 5

        # Построение резюме разговора
        conversation_summary = self._build_conversation_summary(session)

        # Формирование строк для промпта
        confirmed_str = (
            ", ".join(set(all_confirmed)) if all_confirmed else "не выявлены"
        )
        issues_str = ", ".join(set(all_issues)) if all_issues else "не выявлены"
        hallucinations_str = (
            ", ".join(set(all_hallucinations)) if all_hallucinations else "не выявлены"
        )

        prompt = f"""Проанализируй интервью и прими решение о найме.

КАНДИДАТ:
- Имя: {session.participant_name}
- Позиция: {session.position}
- Уровень: {session.grade}
- Опыт: {session.experience}

СТАТИСТИКА ОТ OBSERVER:
- Вопросов: {len(session.turns) - 1}
- Средний балл: {avg_score:.1f}/10
- Подтверждённые знания: {confirmed_str}
- Выявленные проблемы: {issues_str}
- Галлюцинации: {hallucinations_str}

ДИАЛОГ:
{conversation_summary}

ПРАВИЛА ОЦЕНКИ:

1. РЕШЕНИЕ О НАЙМЕ (hiring_recommendation):
   - Strong Hire: отличные ответы, нет галлюцинаций
   - Hire: хорошие ответы, нет галлюцинаций
   - Maybe: средние ответы ИЛИ есть небольшие проблемы
   - No Hire: слабые ответы ИЛИ ЕСТЬ ГАЛЛЮЦИНАЦИИ (ложь!)
   ВАЖНО: Если кандидат врал/выдумывал факты → максимум "Maybe"!

2. CONFIDENCE_SCORE (0-100):
   - Без проблем: 70-100
   - С галлюцинациями: максимум 50!

3. SOFT SKILLS (1-10):
   - clarity: ясность изложения
   - honesty: ГАЛЛЮЦИНАЦИИ → максимум 4 балла!
   - engagement: вовлечённость

Ответь JSON (все тексты на русском):
{{
    "hiring_recommendation": "Strong Hire|Hire|Maybe|No Hire",
    "actual_grade": "Junior|Middle|Senior",
    "confidence_score": 0-100,
    "confirmed_skills": ["навыки релевантные позиции {session.position}"],
    "knowledge_gaps": [{{"topic": "тема", "correct_answer": "ответ"}}],
    "clarity": 1-10,
    "honesty": 1-10 (галлюцинации = максимум 4),
    "engagement": 1-10,
    "roadmap": ["рекомендации для развития"],
    "summary": "резюме на русском языке"
}}

Только JSON. Все тексты на русском!"""

        response = await self.generate_response(prompt, json_schema=HR_FEEDBACK_SCHEMA)

        feedback = self._parse_feedback(
            session, response, avg_score, all_confirmed, all_issues, all_hallucinations
        )

        # Поиск ресурсов для тем из roadmap
        if feedback.roadmap:
            resources = await search_resources_for_roadmap(
                feedback.roadmap, max_results_per_topic=3
            )
            feedback.roadmap_with_resources = [
                RoadmapItem(topic=topic, resources=resources.get(topic, []))
                for topic in feedback.roadmap
            ]

        return feedback

    def _build_conversation_summary(self, session: InterviewSession) -> str:
        """Построение резюме разговора для анализа."""
        summary_parts = []
        skip_messages = (
            "[Начало интервью]",
            "[Завершение интервью]",
            "[Команда завершения получена]",
        )
        for turn in session.turns:
            if turn.user_message not in skip_messages:
                summary_parts.append(f"Q: {turn.agent_visible_message[:100]}...")
                summary_parts.append(f"A: {turn.user_message[:150]}...")
                summary_parts.append("")
        return "\n".join(summary_parts[-12:])  # Последние 4 пары Q&A

    def _parse_feedback(
        self,
        session: InterviewSession,
        response: str,
        avg_score: float,
        confirmed: list[str],
        issues: list[str],
        hallucinations: list[str],
    ) -> FinalFeedback:
        """Парсинг ответа в FinalFeedback."""
        try:
            data = json.loads(_clean_json_response(response))

            knowledge_gaps = [
                KnowledgeGap(topic=gap["topic"], correct_answer=gap["correct_answer"])
                for gap in data.get("knowledge_gaps", [])
            ]

            # Добавляем галлюцинации как пробелы в знаниях
            for hallucination in set(hallucinations):
                knowledge_gaps.append(
                    KnowledgeGap(
                        topic=f"Ложное утверждение: {hallucination[:50]}",
                        correct_answer="Требуется проверка фактов",
                    )
                )

            # Корректировка при наличии галлюцинаций
            honesty_score = data.get("honesty", 5)
            hiring_rec = data.get("hiring_recommendation", "Maybe")
            confidence = data.get("confidence_score", int(avg_score * 10))

            if hallucinations:
                # Честность не выше 4
                honesty_score = min(honesty_score, 4)
                # Рекомендация не выше "Maybe"
                if hiring_rec in ("Strong Hire", "Hire"):
                    hiring_rec = "Maybe"
                # Уверенность не выше 50
                confidence = min(confidence, 50)

            return FinalFeedback(
                session_id=session.session_id,
                participant_name=session.participant_name,
                position=session.position,
                decision=Decision(
                    grade=data.get("actual_grade", session.grade),
                    hiring_recommendation=hiring_rec,
                    confidence_score=confidence,
                ),
                technical_review=TechnicalReview(
                    confirmed_skills=data.get("confirmed_skills", list(set(confirmed))),
                    knowledge_gaps=knowledge_gaps,
                ),
                soft_skills=SoftSkills(
                    clarity=data.get("clarity", 5),
                    honesty=honesty_score,
                    engagement=data.get("engagement", 5),
                ),
                roadmap=data.get("roadmap", []),
                summary=data.get("summary", ""),
            )
        except (json.JSONDecodeError, KeyError, ValueError):
            # Возврат фидбэка по умолчанию при ошибке парсинга
            knowledge_gaps_default = [
                KnowledgeGap(topic=issue, correct_answer="Требуется изучение")
                for issue in list(set(issues))[:3]
            ]
            for hallucination in set(hallucinations):
                knowledge_gaps_default.append(
                    KnowledgeGap(
                        topic=f"Ложное утверждение: {hallucination[:50]}",
                        correct_answer="Требуется проверка фактов",
                    )
                )

            # При ошибке парсинга - безопасные значения
            fallback_confidence = (
                min(int(avg_score * 10), 50) if hallucinations else int(avg_score * 10)
            )

            return FinalFeedback(
                session_id=session.session_id,
                participant_name=session.participant_name,
                position=session.position,
                decision=Decision(
                    grade=session.grade,
                    hiring_recommendation="No Hire" if hallucinations else "Maybe",
                    confidence_score=fallback_confidence,
                ),
                technical_review=TechnicalReview(
                    confirmed_skills=list(set(confirmed))[:5],
                    knowledge_gaps=knowledge_gaps_default,
                ),
                soft_skills=SoftSkills(
                    clarity=5,
                    honesty=4 if hallucinations else 5,
                    engagement=5,
                ),
                roadmap=[
                    f"Углубить знания по позиции {session.position}",
                    "Практиковать навыки на реальных задачах",
                ],
                summary="Интервью завершено. Требуется дополнительный анализ.",
            )
