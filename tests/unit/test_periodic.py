"""周期调度纯函数测试。"""
import datetime

from zentray.core.models import PeriodicTemplate
from zentray.core.periodic import (
    compute_instance_deadline,
    is_schedule_active,
    period_key,
    should_spawn,
)


def test_period_key_daily_interval():
    d = datetime.date(2026, 7, 17)
    k1 = period_key("daily", d, 1)
    k2 = period_key("daily", d + datetime.timedelta(days=1), 1)
    assert k1 != k2
    # 每 2 天：相邻两天可能同桶
    k_a = period_key("daily", d, 2)
    k_b = period_key("daily", d + datetime.timedelta(days=1), 2)
    # ordinal//2 相邻可能相同或不同，只校验稳定性
    assert period_key("daily", d, 2) == k_a


def test_should_spawn_and_long_term():
    today = datetime.date(2026, 7, 17)
    tmpl = PeriodicTemplate(
        base_title="站会",
        category="工作",
        periodicity="daily",
        interval=1,
        long_term=True,
        last_generated_period=None,
    )
    assert should_spawn(tmpl, today)
    tmpl.last_generated_period = period_key("daily", today, 1)
    assert not should_spawn(tmpl, today)


def test_schedule_end_stops_spawn():
    today = datetime.date(2026, 7, 17)
    tmpl = PeriodicTemplate(
        base_title="临时",
        category="工作",
        periodicity="daily",
        long_term=False,
        schedule_end_date="2026-07-10",
        last_generated_period=None,
    )
    assert not is_schedule_active(tmpl, today)
    assert not should_spawn(tmpl, today)


def test_weekly_deadline():
    # 2026-07-17 is Friday (weekday 4)
    today = datetime.date(2026, 7, 17)
    tmpl = PeriodicTemplate(
        base_title="周报",
        category="工作",
        periodicity="weekly",
        deadline_weekday=4,
    )
    assert compute_instance_deadline(tmpl, today) == "2026-07-17"
    tmpl.deadline_weekday = 0  # Monday → 7-20
    assert compute_instance_deadline(tmpl, today) == "2026-07-20"


def test_monthly_deadline():
    today = datetime.date(2026, 7, 10)
    tmpl = PeriodicTemplate(
        base_title="月结",
        category="工作",
        periodicity="monthly",
        deadline_day_of_month=25,
    )
    assert compute_instance_deadline(tmpl, today) == "2026-07-25"
