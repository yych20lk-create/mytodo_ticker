"""周期任务调度纯函数：周期键、是否应派发、实例截止日期。"""
from __future__ import annotations

import calendar
import datetime
from typing import Optional, TYPE_CHECKING

if TYPE_CHECKING:
    from zentray.core.models import PeriodicTemplate


def period_key(
    periodicity: str,
    today: datetime.date,
    interval: int = 1,
) -> str:
    """
    当前「周期桶」标识。interval=N 表示每 N 天/周/月合并为一桶。
    """
    n = max(1, int(interval or 1))
    if periodicity == "weekly":
        iso_year, iso_week, _ = today.isocalendar()
        # 连续周序号
        week_ord = iso_year * 53 + iso_week
        bucket = week_ord // n
        return f"W{bucket}"
    if periodicity == "monthly":
        month_ord = today.year * 12 + (today.month - 1)
        bucket = month_ord // n
        y, m0 = divmod(bucket * n, 12)
        return f"M{y:04d}{(m0 + 1):02d}x{n}"
    # daily（默认）
    bucket = today.toordinal() // n
    return f"D{bucket}"


def period_display_prefix(
    periodicity: str,
    today: datetime.date,
    interval: int = 1,
) -> str:
    """用于任务标题的可读前缀。"""
    n = max(1, int(interval or 1))
    if periodicity == "weekly":
        iso_year, iso_week, _ = today.isocalendar()
        base = f"{str(iso_year)[2:]}第{iso_week}周"
        return f"{base}/每{n}周" if n > 1 else base
    if periodicity == "monthly":
        base = today.strftime("%y%m")
        return f"{base}/每{n}月" if n > 1 else base
    base = today.strftime("%y%m%d")
    return f"{base}/每{n}天" if n > 1 else base


def is_schedule_active(tmpl: "PeriodicTemplate", today: datetime.date) -> bool:
    """模板是否仍在调度有效期内。"""
    if getattr(tmpl, "long_term", True):
        return True
    end = getattr(tmpl, "schedule_end_date", None) or ""
    end = str(end).strip()
    if not end:
        return True
    try:
        end_d = datetime.date.fromisoformat(end)
    except ValueError:
        return True
    return today <= end_d


def should_spawn(tmpl: "PeriodicTemplate", today: datetime.date) -> bool:
    if not is_schedule_active(tmpl, today):
        return False
    key = period_key(
        tmpl.periodicity,
        today,
        getattr(tmpl, "interval", 1) or 1,
    )
    return tmpl.last_generated_period != key


def compute_instance_deadline(
    tmpl: "PeriodicTemplate",
    today: datetime.date,
) -> str:
    """
    按模板规则计算派发实例的截止日期 YYYY-MM-DD；无规则返回空串。
    """
    periodicity = tmpl.periodicity or "daily"
    if periodicity == "weekly":
        wd = getattr(tmpl, "deadline_weekday", None)
        if wd is None:
            return ""
        wd = int(wd) % 7
        # 本周目标 weekday；若已过则仍用本周该日（可能已逾期，交给 overdue 逻辑）
        delta = (wd - today.weekday()) % 7
        target = today + datetime.timedelta(days=delta)
        return target.isoformat()
    if periodicity == "monthly":
        dom = getattr(tmpl, "deadline_day_of_month", None)
        if dom is None:
            return ""
        dom = max(1, min(31, int(dom)))
        last = calendar.monthrange(today.year, today.month)[1]
        day = min(dom, last)
        return datetime.date(today.year, today.month, day).isoformat()
    # daily：默认当天
    return today.isoformat()


def spawn_key_after_create(tmpl: "PeriodicTemplate", today: datetime.date) -> str:
    return period_key(
        tmpl.periodicity,
        today,
        getattr(tmpl, "interval", 1) or 1,
    )
