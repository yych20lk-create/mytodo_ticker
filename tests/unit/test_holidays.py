"""周末 / 节假日跳过逻辑。"""
import datetime

from zentray.core.holidays import is_weekend, should_skip_auto_review


def test_weekend():
    # 2026-07-18 Saturday
    sat = datetime.date(2026, 7, 18)
    sun = datetime.date(2026, 7, 19)
    mon = datetime.date(2026, 7, 20)
    assert is_weekend(sat)
    assert is_weekend(sun)
    assert not is_weekend(mon)


def test_skip_weekends_only():
    sat = datetime.date(2026, 7, 18)
    mon = datetime.date(2026, 7, 20)
    assert should_skip_auto_review(sat, skip_weekends=True, skip_holidays=False)
    assert not should_skip_auto_review(mon, skip_weekends=True, skip_holidays=False)


def test_skip_holidays():
    # 国庆
    d = datetime.date(2026, 10, 1)
    assert should_skip_auto_review(d, skip_weekends=False, skip_holidays=True)
    assert not should_skip_auto_review(
        datetime.date(2026, 7, 20), skip_weekends=False, skip_holidays=True
    )


def test_manual_not_affected_by_logic_when_flags_off():
    sat = datetime.date(2026, 7, 18)
    assert not should_skip_auto_review(sat, skip_weekends=False, skip_holidays=False)
