"""AI 教练风格：每日计划 / 每日复盘 各自内置毒舌·温柔·干练 + 自定义。"""
from __future__ import annotations

import copy
import uuid
from dataclasses import asdict, dataclass
from typing import Dict, List, Optional, Tuple

STYLE_TOXIC = "toxic"
STYLE_GENTLE = "gentle"
STYLE_CRISP = "crisp"

# 每日复盘默认提示词
_REVIEW_PROMPTS: Dict[str, Tuple[str, str]] = {
    STYLE_TOXIC: (
        "毒舌",
        "你是一个尖酸刻薄但内心温暖的高级效率教练。你会根据用户的待办完成情况和明日计划进行总结，"
        "毫不留情地指出用户的摸鱼行为，但结尾必须给予极其提振士气的鼓励。输出标准 Markdown 格式。",
    ),
    STYLE_GENTLE: (
        "温柔",
        "你是一位温和、善解人意的效率伙伴。请用鼓励与共情的语气复盘今日待办与明日计划，"
        "肯定已完成的努力，对未完成事项给出轻柔可行的小建议。输出标准 Markdown 格式。",
    ),
    STYLE_CRISP: (
        "干练",
        "你是一位简洁干练的执行教练。请用条目化、可行动的语言复盘今日完成情况与明日重点，"
        "少情绪多结构：亮点 / 缺口 / 明日 Top3。输出标准 Markdown 格式。",
    ),
}

# 每日计划默认提示词
_PLAN_PROMPTS: Dict[str, Tuple[str, str]] = {
    STYLE_TOXIC: (
        "毒舌",
        "你是一个毒舌但靠谱的日程规划师。根据用户当前活跃任务、优先级与截止日期，"
        "嘲讽不合理的贪多计划，并给出一份可执行的「今日作战序列」（时间块 / 优先级 / 必做与可砍）。"
        "输出标准 Markdown 格式。",
    ),
    STYLE_GENTLE: (
        "温柔",
        "你是一位温和的日程伙伴。根据用户当前待办与精力，给出一份务实、留有余白的今日计划，"
        "包含 3～5 个可完成重点与轻柔提醒。输出标准 Markdown 格式。",
    ),
    STYLE_CRISP: (
        "干练",
        "你是一位干练的执行参谋。根据活跃任务与截止日，输出：今日目标 Top3、时间块建议、"
        "风险与依赖。少废话、可直接照做。输出标准 Markdown 格式。",
    ),
}

# 兼容旧代码
_BUILTIN_PROMPTS = _REVIEW_PROMPTS


@dataclass
class AIStyle:
    id: str
    name: str
    system_prompt: str
    is_builtin: bool = False

    def to_dict(self) -> dict:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: dict) -> "AIStyle":
        return cls(
            id=data.get("id") or str(uuid.uuid4()),
            name=(data.get("name") or "自定义").strip() or "自定义",
            system_prompt=(data.get("system_prompt") or "").strip(),
            is_builtin=bool(data.get("is_builtin", False)),
        )


def builtin_styles(kind: str = "review") -> List[AIStyle]:
    """kind: review | plan"""
    table = _PLAN_PROMPTS if kind == "plan" else _REVIEW_PROMPTS
    styles = []
    for sid, (name, prompt) in table.items():
        styles.append(
            AIStyle(id=sid, name=name, system_prompt=prompt, is_builtin=True)
        )
    return styles


def default_system_prompt(style_id: str, kind: str = "review") -> Optional[str]:
    table = _PLAN_PROMPTS if kind == "plan" else _REVIEW_PROMPTS
    item = table.get(style_id)
    return item[1] if item else None


def merge_styles(
    stored: Optional[List[dict]],
    *,
    kind: str = "review",
) -> List[AIStyle]:
    """
    合并内置默认与用户存储：
    - 同 id 保留用户改过的 name/prompt（内置可改提示词）
    - 内置缺失的补齐
    - 保留用户自定义
    """
    table = _PLAN_PROMPTS if kind == "plan" else _REVIEW_PROMPTS
    by_id: Dict[str, AIStyle] = {}
    for b in builtin_styles(kind):
        by_id[b.id] = copy.deepcopy(b)

    for raw in stored or []:
        if not isinstance(raw, dict):
            continue
        s = AIStyle.from_dict(raw)
        if s.id in by_id and by_id[s.id].is_builtin:
            by_id[s.id] = AIStyle(
                id=s.id,
                name=s.name or by_id[s.id].name,
                system_prompt=s.system_prompt or by_id[s.id].system_prompt,
                is_builtin=True,
            )
        else:
            s.is_builtin = s.id in table
            if not s.system_prompt and s.id in table:
                s.system_prompt = table[s.id][1]
            by_id[s.id] = s

    ordered: List[AIStyle] = []
    for sid in (STYLE_TOXIC, STYLE_GENTLE, STYLE_CRISP):
        if sid in by_id:
            ordered.append(by_id.pop(sid))
    ordered.extend(by_id.values())
    return ordered


def resolve_active_style(
    styles: List[AIStyle], active_style_id: str
) -> AIStyle:
    for s in styles:
        if s.id == active_style_id and s.system_prompt:
            return s
    for s in styles:
        if s.id == STYLE_TOXIC:
            return s
    if styles:
        return styles[0]
    return builtin_styles("review")[0]
