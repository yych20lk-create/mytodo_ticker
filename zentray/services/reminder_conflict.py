"""弹窗提醒时间冲突检测。

冲突定义（api_version=1）：
- 候选提醒的「钟点」HH:mm 与其它任务/周期模板的启用弹窗提醒相同；或
- 与每日计划 / 每日复盘的调度时刻相同。
周/月 slot 额外在文案中标注周几/日期，但冲突键仍以 HH:mm 为主
（同钟点即视为冲突，避免用户同一时刻被多个弹窗打断）。
"""
from __future__ import annotations

from typing import Any, Dict, List, Optional, Set

from zentray.core.reminder import TaskReminder, parse_hhmm


def normalize_hhmm(value: str) -> str:
    h, m = parse_hhmm(value)
    return f"{h:02d}:{m:02d}"


def _times_from_reminder(rem: Any) -> List[str]:
    """从 TaskReminder / dict 提取启用中的 HH:mm 列表。"""
    if rem is None:
        return []
    if isinstance(rem, dict):
        rem = TaskReminder.from_dict(rem)
    if not isinstance(rem, TaskReminder) or not rem.enabled:
        return []
    out: List[str] = []
    for slot in rem.effective_slots():
        out.append(normalize_hhmm(slot.time_of_day))
    return out


def _format_slot_hint(rem: Any) -> str:
    if rem is None:
        return ""
    if isinstance(rem, dict):
        rem = TaskReminder.from_dict(rem)
    if not isinstance(rem, TaskReminder) or not rem.enabled:
        return ""
    parts = []
    for s in rem.effective_slots():
        t = normalize_hhmm(s.time_of_day)
        if s.weekday is not None:
            names = "一二三四五六日"
            wd = int(s.weekday)
            w = names[wd] if 0 <= wd < 7 else str(wd)
            parts.append(f"周{w} {t}")
        elif s.day_of_month is not None:
            parts.append(f"每月{int(s.day_of_month)}日 {t}")
        else:
            parts.append(t)
    return "、".join(parts) if parts else normalize_hhmm(rem.time_of_day)


def collect_candidate_times(reminder: Any) -> Set[str]:
    return set(_times_from_reminder(reminder))


def find_reminder_conflicts(
    candidate_reminder: Any,
    *,
    tasks: List[Any],
    templates: Optional[List[Any]] = None,
    exclude_task_id: Optional[str] = None,
    exclude_template_id: Optional[str] = None,
    plan_enabled: bool = False,
    plan_hour: int = 8,
    plan_minute: int = 0,
    review_enabled: bool = False,
    review_hour: int = 23,
    review_minute: int = 30,
) -> List[Dict[str, str]]:
    """
    返回冲突列表，每项:
      kind: task | template | ai_plan | ai_review
      id, title, time, detail
    """
    cand = collect_candidate_times(candidate_reminder)
    if not cand:
        return []

    conflicts: List[Dict[str, str]] = []

    for t in tasks or []:
        tid = getattr(t, "id", None) or (t.get("id") if isinstance(t, dict) else None)
        if exclude_task_id and tid == exclude_task_id:
            continue
        rem = getattr(t, "reminder", None) if not isinstance(t, dict) else t.get("reminder")
        times = set(_times_from_reminder(rem))
        hit = sorted(cand & times)
        if not hit:
            continue
        title = getattr(t, "title", None) or (t.get("title") if isinstance(t, dict) else "") or "未命名"
        conflicts.append(
            {
                "kind": "task",
                "id": str(tid or ""),
                "title": str(title),
                "time": "、".join(hit),
                "detail": f"任务弹窗 {_format_slot_hint(rem)}",
            }
        )

    for tmpl in templates or []:
        tid = getattr(tmpl, "template_id", None) or (
            tmpl.get("template_id") if isinstance(tmpl, dict) else None
        )
        if exclude_template_id and tid == exclude_template_id:
            continue
        rem = (
            getattr(tmpl, "reminder", None)
            if not isinstance(tmpl, dict)
            else tmpl.get("reminder")
        )
        times = set(_times_from_reminder(rem))
        hit = sorted(cand & times)
        if not hit:
            continue
        title = (
            getattr(tmpl, "base_title", None)
            or (tmpl.get("base_title") if isinstance(tmpl, dict) else None)
            or (tmpl.get("title") if isinstance(tmpl, dict) else None)
            or "未命名模板"
        )
        conflicts.append(
            {
                "kind": "template",
                "id": str(tid or ""),
                "title": str(title),
                "time": "、".join(hit),
                "detail": f"周期模板弹窗 {_format_slot_hint(rem)}",
            }
        )

    if plan_enabled:
        pt = normalize_hhmm(f"{int(plan_hour)}:{int(plan_minute)}")
        if pt in cand:
            conflicts.append(
                {
                    "kind": "ai_plan",
                    "id": "ai_plan",
                    "title": "每日计划",
                    "time": pt,
                    "detail": f"AI 每日计划调度 {pt}",
                }
            )

    if review_enabled:
        rt = normalize_hhmm(f"{int(review_hour)}:{int(review_minute)}")
        if rt in cand:
            conflicts.append(
                {
                    "kind": "ai_review",
                    "id": "ai_review",
                    "title": "每日复盘",
                    "time": rt,
                    "detail": f"AI 每日复盘调度 {rt}",
                }
            )

    return conflicts
