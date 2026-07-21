"""每日计划/复盘调度判定回归。"""
from datetime import datetime
from pathlib import Path

from zentray.workers.ai_schedule import (
    JobScheduleState,
    is_at_or_after,
    load_state,
    save_state,
    should_fire_job,
    sync_trigger_keys,
)


def test_is_at_or_after():
    assert is_at_or_after(datetime(2026, 7, 21, 9, 55), 9, 55)
    assert is_at_or_after(datetime(2026, 7, 21, 10, 0), 9, 55)
    assert not is_at_or_after(datetime(2026, 7, 21, 9, 54), 9, 55)
    assert is_at_or_after(datetime(2026, 7, 21, 0, 0), 0, 0)


def test_should_fire_catchup_after_hour():
    """旧逻辑 hour== 会在 10:00 漏掉 9:55 的计划；新逻辑应补跑。"""
    now = datetime(2026, 7, 21, 10, 0)
    assert should_fire_job(
        now,
        enabled=True,
        last_date=None,
        trigger_hour=9,
        trigger_minute=55,
    )
    # 同日已跑
    assert not should_fire_job(
        now,
        enabled=True,
        last_date="2026-07-21",
        trigger_hour=9,
        trigger_minute=55,
    )
    # 未到点
    assert not should_fire_job(
        datetime(2026, 7, 21, 9, 54),
        enabled=True,
        last_date=None,
        trigger_hour=9,
        trigger_minute=55,
    )
    # 关闭
    assert not should_fire_job(
        now,
        enabled=False,
        last_date=None,
        trigger_hour=9,
        trigger_minute=55,
    )


def test_review_same_rules():
    now = datetime(2026, 7, 21, 18, 0)
    assert should_fire_job(
        now,
        enabled=True,
        last_date=None,
        trigger_hour=17,
        trigger_minute=40,
    )
    assert not should_fire_job(
        now,
        enabled=True,
        last_date="2026-07-21",
        trigger_hour=17,
        trigger_minute=40,
    )


def test_sync_trigger_clears_last_date(tmp_path: Path):
    state_path = tmp_path / "ai_schedule_state.json"
    state = JobScheduleState(
        last_plan_date="2026-07-21",
        last_review_date="2026-07-21",
        plan_hm="8:0",
        review_hm="17:40",
    )
    save_state(state, state_path)
    loaded = load_state(state_path)
    synced = sync_trigger_keys(
        loaded,
        plan_hour=9,
        plan_minute=55,
        review_hour=17,
        review_minute=40,
        path=state_path,
    )
    assert synced.last_plan_date is None  # 时刻变更
    assert synced.last_review_date == "2026-07-21"  # 复盘时刻未变
    assert synced.plan_hm == "9:55"
    # 再读盘
    again = load_state(state_path)
    assert again.last_plan_date is None
    assert again.plan_hm == "9:55"
