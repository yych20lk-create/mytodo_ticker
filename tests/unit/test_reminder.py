"""提醒领域逻辑测试。"""
import datetime

from zentray.core.reminder import (
    ReminderSlot,
    TaskReminder,
    due_reminder_keys,
    fire_key,
    parse_hhmm,
)


def test_parse_hhmm():
    assert parse_hhmm("17:00") == (17, 0)
    assert parse_hhmm("9:30") == (9, 30)
    assert parse_hhmm("bad") == (17, 0)


def test_fire_key():
    d = datetime.date(2026, 7, 17)
    assert fire_key(d, "17:00") == "2026-07-17|17:00"


def test_due_daily_at_time():
    rem = TaskReminder(enabled=True, time_of_day="17:00")
    now = datetime.datetime(2026, 7, 17, 17, 0, 10)
    keys = due_reminder_keys(rem, now, periodicity="daily")
    assert keys == ["2026-07-17|17:00"]


def test_not_due_outside_window():
    rem = TaskReminder(enabled=True, time_of_day="17:00")
    now = datetime.datetime(2026, 7, 17, 17, 5, 0)
    keys = due_reminder_keys(rem, now, window_seconds=60)
    assert keys == []


def test_last_fired_suppresses():
    rem = TaskReminder(
        enabled=True,
        time_of_day="17:00",
        last_fired_key="2026-07-17|17:00",
    )
    now = datetime.datetime(2026, 7, 17, 17, 0, 10)
    assert due_reminder_keys(rem, now) == []


def test_weekly_slot():
    # 2026-07-17 is Friday → weekday 4
    rem = TaskReminder(
        enabled=True,
        slots=[ReminderSlot(time_of_day="09:00", weekday=4)],
    )
    now = datetime.datetime(2026, 7, 17, 9, 0, 5)
    keys = due_reminder_keys(rem, now, periodicity="weekly")
    assert keys == ["2026-07-17|09:00"]

    # Thursday should not fire
    now2 = datetime.datetime(2026, 7, 16, 9, 0, 5)
    assert due_reminder_keys(rem, now2, periodicity="weekly") == []


def test_monthly_slot():
    rem = TaskReminder(
        enabled=True,
        slots=[ReminderSlot(time_of_day="10:00", day_of_month=1)],
    )
    now = datetime.datetime(2026, 7, 1, 10, 0, 1)
    assert due_reminder_keys(rem, now, periodicity="monthly") == ["2026-07-01|10:00"]


def test_snooze():
    rem = TaskReminder(
        enabled=True,
        time_of_day="17:00",
        snooze_until="2026-07-17T18:00:00",
    )
    now = datetime.datetime(2026, 7, 17, 17, 0, 10)
    assert due_reminder_keys(rem, now) == []
