"""非工作日判断：周末 + 中国法定节假日（内置常见日期，可扩展）。"""
from __future__ import annotations

import datetime
from typing import Iterable, Set


# 内置法定节假日（含常见调休放假日，按国务院公告整理的常用集合；逐年可扩充）
# 格式 YYYY-MM-DD
_BUILTIN_CN_HOLIDAYS: Set[str] = {
    # 2025
    "2025-01-01",
    "2025-01-28", "2025-01-29", "2025-01-30", "2025-01-31",
    "2025-02-01", "2025-02-02", "2025-02-03", "2025-02-04",
    "2025-04-04", "2025-04-05", "2025-04-06",
    "2025-05-01", "2025-05-02", "2025-05-03", "2025-05-04", "2025-05-05",
    "2025-05-31", "2025-06-01", "2025-06-02",
    "2025-10-01", "2025-10-02", "2025-10-03", "2025-10-04",
    "2025-10-05", "2025-10-06", "2025-10-07", "2025-10-08",
    # 2026
    "2026-01-01", "2026-01-02",
    "2026-02-15", "2026-02-16", "2026-02-17", "2026-02-18",
    "2026-02-19", "2026-02-20", "2026-02-21", "2026-02-22", "2026-02-23",
    "2026-04-04", "2026-04-05", "2026-04-06",
    "2026-05-01", "2026-05-02", "2026-05-03", "2026-05-04", "2026-05-05",
    "2026-06-19", "2026-06-20", "2026-06-21",
    "2026-10-01", "2026-10-02", "2026-10-03", "2026-10-04",
    "2026-10-05", "2026-10-06", "2026-10-07",
    # 2027 固定类（农历相关为近似常用日，可后续用 holidays.json 覆盖）
    "2027-01-01",
    "2027-02-06", "2027-02-07", "2027-02-08", "2027-02-09",
    "2027-02-10", "2027-02-11", "2027-02-12",
    "2027-04-03", "2027-04-04", "2027-04-05",
    "2027-05-01", "2027-05-02", "2027-05-03",
    "2027-06-09", "2027-06-10", "2027-06-11",
    "2027-10-01", "2027-10-02", "2027-10-03", "2027-10-04",
    "2027-10-05", "2027-10-06", "2027-10-07",
}


def _load_extra_holidays() -> Set[str]:
    """可选：DATA_DIR/holidays.json 数组 ["2026-01-01", ...]"""
    try:
        from zentray.config import DATA_DIR
        import json

        path = DATA_DIR / "holidays.json"
        if not path.exists():
            return set()
        data = json.loads(path.read_text(encoding="utf-8"))
        if isinstance(data, list):
            return {str(x).strip() for x in data if x}
        if isinstance(data, dict) and "dates" in data:
            return {str(x).strip() for x in data["dates"] if x}
    except Exception:
        pass
    return set()


def holiday_set() -> Set[str]:
    return set(_BUILTIN_CN_HOLIDAYS) | _load_extra_holidays()


def is_weekend(d: datetime.date) -> bool:
    return d.weekday() >= 5  # 5=周六 6=周日


def is_cn_holiday(d: datetime.date) -> bool:
    return d.isoformat() in holiday_set()


def should_skip_auto_review(
    d: datetime.date,
    *,
    skip_weekends: bool,
    skip_holidays: bool,
    extra_holidays: Iterable[str] | None = None,
) -> bool:
    """
    自动调度是否应跳过当日。
    手动「立即 AI 复盘」不调用此函数。
    """
    if skip_weekends and is_weekend(d):
        return True
    if skip_holidays:
        dates = holiday_set()
        if extra_holidays:
            dates = dates | {str(x).strip() for x in extra_holidays if x}
        if d.isoformat() in dates:
            return True
    return False
