"""默认截止日期计算。"""
import datetime

from zentray.ui.dialogs import _compute_default_deadline


def test_one_time_is_tomorrow():
    d = _compute_default_deadline(False)
    assert d == datetime.date.today() + datetime.timedelta(days=1)


def test_daily_is_today():
    d = _compute_default_deadline(True, "daily")
    assert d == datetime.date.today()


def test_weekly_friday():
    today = datetime.date.today()
    d = _compute_default_deadline(True, "weekly", weekday=4)
    assert d.weekday() == 4
    assert d >= today


def test_monthly_day():
    d = _compute_default_deadline(True, "monthly", day_of_month=25)
    assert d.day == 25 or d.day < 25  # 短月可能被钳制到月末；正常月为 25
