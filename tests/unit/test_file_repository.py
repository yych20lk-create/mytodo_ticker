# tests/unit/test_file_repository.py
from zentray.core.models import Task


def test_save_and_load_task(task_repo, tmp_data_dir):
    task = Task(id="test-1", title="test task", category="工作")
    task_repo.save_all([task])
    loaded = task_repo.find_all()
    assert len(loaded) == 1
    assert loaded[0].title == "test task"
    assert loaded[0].category == "工作"


def test_save_single_and_delete(task_repo):
    t1 = Task(id="a", title="A", category="工作")
    t2 = Task(id="b", title="B", category="生活")
    task_repo.save(t1)
    task_repo.save(t2)
    assert len(task_repo.find_all()) == 2
    task_repo.delete("a")
    remaining = task_repo.find_all()
    assert len(remaining) == 1
    assert remaining[0].id == "b"


def test_archive_writes_log(task_repo, tmp_data_dir):
    task = Task(id="x", title="归档我", category="工作", priority="high")
    task_repo.archive(task, "DONE")
    logs = list((tmp_data_dir / "archive").glob("*.log"))
    assert logs
    content = logs[0].read_text(encoding="utf-8")
    assert "DONE" in content
    assert "归档我" in content
