from __future__ import annotations

from pathlib import Path

from sparrow_agent.capabilities.base import Skill
from sparrow_agent.schemas.models import RuntimeContext


class KeywordSkill:
    def __init__(self, name: str, description: str, keywords: list[str], prompt: str) -> None:
        self.name = name
        self.description = description
        self.keywords = [keyword.lower() for keyword in keywords]
        self.prompt = prompt

    def matches(self, ctx: RuntimeContext) -> bool:
        user_text = ctx.user_input.lower()
        return any(keyword in user_text for keyword in self.keywords)

    def build_prompt(self, ctx: RuntimeContext) -> str:
        del ctx
        return self.prompt


class SkillRegistry:
    def __init__(self, skills: list[Skill] | None = None) -> None:
        self._skills = skills or []

    def register(self, skill: Skill) -> None:
        self._skills.append(skill)

    def resolve(self, ctx: RuntimeContext) -> list[Skill]:
        return [skill for skill in self._skills if skill.matches(ctx)]


def load_default_skills(skills_dir: Path | None = None) -> list[Skill]:
    del skills_dir
    return [
        KeywordSkill(
            name="memory-capture",
            description="Encourage concise extraction of stable preferences or facts.",
            keywords=["remember", "偏好", "喜欢", "habit", "preference"],
            prompt="Extract stable user preferences or facts if present, and keep the final answer concise.",
        )
    ]
