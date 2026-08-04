"""弹窗提醒时间冲突检测。"""
from zentray.core.models import PeriodicTemplate, Task
from zentray.core.reminder import TaskReminder
from zentray.services.reminder_conflict import find_reminder_conflicts, normalize_hhmm


def test_normalize():
    assert normalize_hhmm("9:5") == "09:05"
    assert normalize_hhmm("17:00") == "17:00"


def test_conflict_with_other_task():
    t1 = Task(
        title="A",
        category="工作",
        reminder=TaskReminder(enabled=True, time_of_day="17:00"),
    )
    cand = TaskReminder(enabled=True, time_of_day="17:00")
    conflicts = find_reminder_conflicts(
        cand,
        tasks=[t1],
        templates=[],
        exclude_task_id=None,
    )
    assert len(conflicts) == 1
    assert conflicts[0]["kind"] == "task"
    assert conflicts[0]["title"] == "A"


def test_exclude_self():
    t1 = Task(
        id="tid1",
        title="A",
        category="工作",
        reminder=TaskReminder(enabled=True, time_of_day="17:00"),
    )
    cand = TaskReminder(enabled=True, time_of_day="17:00")
    conflicts = find_reminder_conflicts(
        cand, tasks=[t1], exclude_task_id="tid1"
    )
    assert conflicts == []


def test_conflict_with_ai_plan_and_review():
    cand = TaskReminder(enabled=True, time_of_day="09:55")
    conflicts = find_reminder_conflicts(
        cand,
        tasks=[],
        plan_enabled=True,
        plan_hour=9,
        plan_minute=55,
        review_enabled=True,
        review_hour=17,
        review_minute=40,
    )
    assert any(c["kind"] == "ai_plan" for c in conflicts)
    assert not any(c["kind"] == "ai_review" for c in conflicts)

    cand2 = TaskReminder(enabled=True, time_of_day="17:40")
    conflicts2 = find_reminder_conflicts(
        cand2,
        tasks=[],
        plan_enabled=True,
        plan_hour=9,
        plan_minute=55,
        review_enabled=True,
        review_hour=17,
        review_minute=40,
    )
    assert any(c["kind"] == "ai_review" for c in conflicts2)


def test_template_conflict():
    tmpl = PeriodicTemplate(
        base_title="周期",
        category="工作",
        periodicity="daily",
        reminder=TaskReminder(enabled=True, time_of_day="08:30"),
    )
    cand = TaskReminder(enabled=True, time_of_day="08:30")
    conflicts = find_reminder_conflicts(cand, tasks=[], templates=[tmpl])
    assert len(conflicts) == 1
    assert conflicts[0]["kind"] == "template"


def test_disabled_candidate_no_conflict():
    t1 = Task(
        title="A",
        category="工作",
        reminder=TaskReminder(enabled=True, time_of_day="17:00"),
    )
    cand = TaskReminder(enabled=False, time_of_day="17:00")
    assert find_reminder_conflicts(cand, tasks=[t1]) == []
