"""v3.8 旧数据兼容：仅 category 字符串的任务可加载。"""
from zentray.core.models import Task
from zentray.core.reminder import TaskReminder
from zentray.services.settings_manager import SettingsManager


def test_task_from_legacy_dict():
    t = Task.from_dict({
        "title": "旧任务",
        "category": "工作",
        "priority": "high",
    })
    assert t.title == "旧任务"
    assert t.category_primary_id is None
    assert t.reminder is None


def test_task_with_reminder_roundtrip():
    t = Task(
        title="提醒任务",
        category="工作",
        reminder=TaskReminder(enabled=True, time_of_day="17:00"),
    )
    d = t.to_dict()
    t2 = Task.from_dict(d)
    assert t2.reminder is not None
    assert t2.reminder.enabled
    assert t2.reminder.time_of_day == "17:00"


def test_settings_default_categories_and_styles(tmp_data_dir):
    sm = SettingsManager.reload()
    assert sm.categories.primary_list
    assert sm.ai.styles
    assert sm.ai.active_style().system_prompt
