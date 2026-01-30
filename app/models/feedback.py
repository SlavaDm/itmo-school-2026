"""Модели для финального фидбэка по интервью."""

from pydantic import BaseModel, Field


class KnowledgeGap(BaseModel):
    """Пробел в знаниях, выявленный на интервью."""

    topic: str
    correct_answer: str


class Decision(BaseModel):
    """Решение о найме."""

    grade: str  # Junior, Middle, Senior
    hiring_recommendation: str  # Hire, No Hire, Strong Hire, Maybe
    confidence_score: int = Field(ge=0, le=100)


class TechnicalReview(BaseModel):
    """Оценка технических навыков."""

    confirmed_skills: list[str] = Field(default_factory=list)
    knowledge_gaps: list[KnowledgeGap] = Field(default_factory=list)


class SoftSkills(BaseModel):
    """Оценка soft skills."""

    clarity: int = Field(ge=1, le=10, description="Ясность коммуникации")
    honesty: int = Field(ge=1, le=10, description="Честность и самосознание")
    engagement: int = Field(ge=1, le=10, description="Вовлеченность и энтузиазм")


class RoadmapItem(BaseModel):
    """Элемент roadmap с ресурсами для изучения."""

    topic: str
    resources: list[dict] = Field(default_factory=list)  # [{"title": ..., "url": ...}]


class FinalFeedback(BaseModel):
    """Полный фидбэк по интервью."""

    session_id: str
    participant_name: str
    position: str
    decision: Decision
    technical_review: TechnicalReview
    soft_skills: SoftSkills
    roadmap: list[str] = Field(default_factory=list)
    roadmap_with_resources: list[RoadmapItem] = Field(default_factory=list)
    summary: str = ""

    def to_markdown(self) -> str:
        """Конвертация фидбэка в Markdown формат."""
        # Эмодзи для рекомендаций
        rec_emoji = {
            "Strong Hire": "🟢",
            "Hire": "🟡",
            "Maybe": "🟠",
            "No Hire": "🔴",
        }
        emoji = rec_emoji.get(self.decision.hiring_recommendation, "⚪")

        # Шкала для soft skills
        def skill_bar(value: int) -> str:
            filled = "█" * value
            empty = "░" * (10 - value)
            return f"{filled}{empty} {value}/10"

        lines = [
            "# Результаты интервью",
            "",
            f"**Кандидат:** {self.participant_name}  ",
            f"**Позиция:** {self.position}  ",
            f"**Уровень:** {self.decision.grade}",
            "",
            "---",
            "",
            f"## {emoji} Решение: {self.decision.hiring_recommendation}",
            "",
            f"**Уверенность:** {self.decision.confidence_score}%",
            "",
            "---",
            "",
            "## Техническая оценка",
            "",
        ]

        # Подтверждённые навыки
        if self.technical_review.confirmed_skills:
            lines.append("### ✅ Подтверждённые навыки")
            for skill in self.technical_review.confirmed_skills:
                lines.append(f"- {skill}")
            lines.append("")

        # Пробелы в знаниях
        if self.technical_review.knowledge_gaps:
            lines.append("### ❌ Пробелы в знаниях")
            for gap in self.technical_review.knowledge_gaps:
                lines.append(f"- **{gap.topic}**")
                lines.append(f"  - _{gap.correct_answer}_")
            lines.append("")

        # Soft Skills
        lines.extend(
            [
                "---",
                "",
                "## Soft Skills",
                "",
                "| Навык | Оценка |",
                "|-------|--------|",
                f"| Ясность изложения | {skill_bar(self.soft_skills.clarity)} |",
                f"| Честность | {skill_bar(self.soft_skills.honesty)} |",
                f"| Вовлечённость | {skill_bar(self.soft_skills.engagement)} |",
                "",
            ]
        )

        # Roadmap с ресурсами
        if self.roadmap_with_resources:
            lines.extend(
                [
                    "---",
                    "",
                    "## 📚 Рекомендации по развитию",
                    "",
                ]
            )
            for item in self.roadmap_with_resources:
                lines.append(f"### {item.topic}")
                if item.resources:
                    for res in item.resources:
                        title = res.get("title", "Ресурс")
                        url = res.get("url", "")
                        if url:
                            lines.append(f"- [{title}]({url})")
                        else:
                            lines.append(f"- {title}")
                else:
                    lines.append("- _Ресурсы не найдены_")
                lines.append("")

        # Резюме
        if self.summary:
            lines.extend(
                [
                    "---",
                    "",
                    "## Резюме",
                    "",
                    self.summary,
                    "",
                ]
            )

        return "\n".join(lines)
