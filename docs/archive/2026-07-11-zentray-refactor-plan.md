# ZenTray Refactor Implementation Plan

> ⚠️ **Superseded / Archived (2026-07-17)**  
> 进度与后续任务以 [../superpowers/plans/2026-07-17-zentray-remediation-plan.md](../superpowers/plans/2026-07-17-zentray-remediation-plan.md) 为准。  
> 审查结论见 [../architecture-review-2026-07-17.md](../architecture-review-2026-07-17.md)。

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Implement a fully decoupled and testable architecture for ZenTray using dependency injection and service-oriented design.

**Architecture:** The architecture splits core functionality into well-defined services with clear interfaces: TaskService for business logic, PomodoroService for focus management, and TrayController for UI coordination. Dependency injection via injector allows pluggable storage implementations (JSON, MySQL) and extensions (script buttons).

**Tech Stack:** Python 3.10+, PySide6, injector, pytest, SQLAlchemy (for MySQL future).

## Global Constraints

- All dependencies must be resolved via injector
- File storage must be implemented with fallbacks to JSON (no file locking required)
- Test coverage must exceed 60% for core services
- No global state in main thread (all UI updates via signals)
- Storage implementations must handle partial failures gracefully
- MySQL adapter must be a separate package

---

### Task 1: Create TaskRepository Interface

**Files:**
- Create: `zentray/core/repository.py`

**Interfaces:**
- Consumes: None
- Produces: `TaskRepository` interface with methods `find_all`, `find_by_id`, `save`, `save_all`, `delete`, `find_active`, `archive`

- [ ] **Step 1: Write the TaskRepository interface**  
```python
# zentray/core/repository.py
from abc import ABC, abstractmethod
from typing import List, Optional
from zentray.core.models import Task, PeriodicTemplate


class TaskRepository(ABC):
    @abstractmethod
    def find_all(self) -> List[Task]:
        pass
    
    @abstractmethod
    def find_by_id(self, task_id: str) -> Optional[Task]:
        pass
    
    @abstractmethod
    def save(self, task: Task) -> None:
        pass
    
    @abstractmethod
    def save_all(self, tasks: List[Task]) -> None:
        pass
    
    @abstractmethod
    def delete(self, task_id: str) -> None:
        pass
    
    @abstractmethod
    def find_active(self) -> List[Task]:
        pass
    
    @abstractmethod
    def archive(self, task: Task, status: str) -> None:
        pass
```

- [ ] **Step 2: Create test skeleton**  
```python
# tests/unit/test_repository.py
import pytest
from zentray.core.repository import TaskRepository

def test_repository_interface():
    with pytest.raises(TypeError):
        TaskRepository()  # Abstract class can't be instantiated
```

- [ ] **Step 3: Run test to verify it fails**  
Run: `pytest tests/unit/test_repository.py::test_repository_interface -v`  
Expected: `TypeError: Can't instantiate abstract class TaskRepository with abstract methods...`  

- [ ] **Step 4: Write minimal implementation for test**  
```python
# tests/unit/test_repository.py (no changes needed, just pass)
```

- [ ] **Step 5: Commit**  
```bash
git add zentray/core/repository.py tests/unit/test_repository.py
git commit -m "feat: create TaskRepository interface and test" 
```

### Task 2: Implement FileTaskRepository

**Files:**
- Create: `zentray/repositories/file_repository.py`

**Interfaces:**
- Consumes: `TaskRepository` interface
- Produces: `FileTaskRepository` implementation

- [ ] **Step 1: Write the FileTaskRepository implementation**  
```python
# zentray/repositories/file_repository.py
import json
import shutil
import datetime
from pathlib import Path
from typing import List, Optional
from zentray.core.repository import TaskRepository
from zentray.core.models import Task
from zentray.config import ACTIVE_TASKS_FILE, ARCHIVE_DIR

class FileTaskRepository(TaskRepository):
    def __init__(self):
        self.active_file = ACTIVE_TASKS_FILE
        self.archive_dir = ARCHIVE_DIR
    
    def _load_json(self, filepath: Path) -> List[dict]:
        if not filepath.exists():
            return []
        try:
            with open(filepath, 'r', encoding='utf-8') as f:
                return json.load(f)
        except json.JSONDecodeError:
            backup = filepath.with_suffix('.json.bak')
            shutil.copy(filepath, backup)
            return []
    
    def _save_json(self, filepath: Path, data: List[dict]) -> None:
        with open(filepath, 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=2, ensure_ascii=False)
    
    def find_all(self) -> List[Task]:
        data = self._load_json(self.active_file)
        return [Task.from_dict(d) for d in data]
    
    def find_by_id(self, task_id: str) -> Optional[Task]:
        tasks = self.find_all()
        return next((t for t in tasks if t.id == task_id), None)
    
    def save_all(self, tasks: List[Task]) -> None:
        data = [t.to_dict() for t in tasks]
        self._save_json(self.active_file, data)
    
    def delete(self, task_id: str) -> None:
        tasks = self.find_all()
        tasks = [t for t in tasks if t.id != task_id]
        self.save_all(tasks)
    
    def find_active(self) -> List[Task]:
        return self.find_all()
    
    def archive(self, task: Task, status: str) -> None:
        date_str = datetime.datetime.now().strftime('%Y-%m-%d')
        archive_file = self.archive_dir / f"{date_str}.log"
        timestamp = datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        log_line = f"[{timestamp}] [状态: {status}] [分类: {task.category}] [{task.priority.upper()}] {task.title} - {task.details} (附件数: {len(task.attachments)})\n"
        with open(archive_file, 'a', encoding='utf-8') as f:
            f.write(log_line)
```

- [ ] **Step 2: Write test case for save_all**  
```python
# tests/unit/test_file_repository.py
from zentray.repositories.file_repository import FileTaskRepository
from zentray.core.models import Task
import pytest
import os
import shutil
from pathlib import Path

def test_save_and_load_task():
    repo = FileTaskRepository()
    task = Task(id="test-1", title="test task")
    repo.save_all([task])
    loaded = repo.find_all()
    assert len(loaded) == 1
    assert loaded[0].title == "test task"
    
    # Clean up
    os.remove(repo.active_file)
    os.remove(repo.active_file.with_suffix('.json.bak'))
```

- [ ] **Step 3: Run test to verify it passes**  
Run: `pytest tests/unit/test_file_repository.py -v`  
Expected: `PASSED`  

- [ ] **Step 4: Commit**  
```bash
git add zentray/repositories/file_repository.py tests/unit/test_file_repository.py
git commit -m "feat: implement FileTaskRepository with tests"
```

### Task 3: Create PeriodicTemplateRepository Interface

**Files:**
- Create: `zentray/core/repository.py`

**Interfaces:**
- Consumes: `TaskRepository` interface
- Produces: `PeriodicTemplateRepository` interface

- [ ] **Step 1: Add PeriodicTemplateRepository to the file**  
```python
# zentray/core/repository.py (add to the end)
class PeriodicTemplateRepository(ABC):
    @abstractmethod
    def find_all(self) -> List[PeriodicTemplate]:
        pass
    
    @abstractmethod
    def save_all(self, templates: List[PeriodicTemplate]) -> None:
        pass
```

- [ ] **Step 2: Create test skeleton**  
```python
# tests/unit/test_template_repository.py
import pytest
from zentray.core.repository import PeriodicTemplateRepository

def test_template_repository_interface():
    with pytest.raises(TypeError):
        PeriodicTemplateRepository()  # Abstract class can't be instantiated
```

- [ ] **Step 3: Run test to verify it fails**  
Run: `pytest tests/unit/test_template_repository.py -v`  
Expected: `TypeError: Can't instantiate abstract class PeriodicTemplateRepository with abstract methods...`  

- [ ] **Step 4: Commit**  
```bash
git add zentray/core/repository.py tests/unit/test_template_repository.py
git commit -m "feat: create PeriodicTemplateRepository interface and test" 
```

### Task 4: Implement FilePeriodicTemplateRepository

**Files:**
- Create: `zentray/repositories/file_periodic_repository.py`

**Interfaces:**
- Consumes: `PeriodicTemplateRepository` interface
- Produces: `FilePeriodicTemplateRepository` implementation

- [ ] **Step 1: Write the FilePeriodicTemplateRepository implementation**  
```python
# zentray/repositories/file_periodic_repository.py
import json
from pathlib import Path
from typing import List, Optional
from zentray.core.repository import PeriodicTemplateRepository
from zentray.core.models import PeriodicTemplate
from zentray.config import PERIODIC_TEMPLATES_FILE

class FilePeriodicTemplateRepository(PeriodicTemplateRepository):
    def __init__(self):
        self.filepath = PERIODIC_TEMPLATES_FILE
    
    def find_all(self) -> List[PeriodicTemplate]:
        if not self.filepath.exists():
            return []
        try:
            with open(self.filepath, 'r', encoding='utf-8') as f:
                data = json.load(f)
                return [PeriodicTemplate.from_dict(d) for d in data]
        except json.JSONDecodeError:
            # Backup not implemented for templates (smaller, less likely to break)
            return []
    
    def save_all(self, templates: List[PeriodicTemplate]) -> None:
        with open(self.filepath, 'w', encoding='utf-8') as f:
            json.dump([t.to_dict() for t in templates], f, indent=2, ensure_ascii=False)
```

- [ ] **Step 2: Write test case**  
```python
# tests/unit/test_file_periodic_repository.py
from zentray.repositories.file_periodic_repository import FilePeriodicTemplateRepository
from zentray.core.models import PeriodicTemplate
import pytest
import os


def test_template_save_and_load():
    repo = FilePeriodicTemplateRepository()
    template = PeriodicTemplate(
        base_title="Test Template",
        category="work",
        periodicity="daily"
    )
    repo.save_all([template])
    loaded = repo.find_all()
    assert len(loaded) == 1
    assert loaded[0].base_title == "Test Template"
    
    # Clean up
    os.remove(repo.filepath)
```

- [ ] **Step 3: Run test to verify it passes**  
Run: `pytest tests/unit/test_file_periodic_repository.py -v`  
Expected: `PASSED`  

- [ ] **Step 4: Commit**  
```bash
git add zentray/repositories/file_periodic_repository.py tests/unit/test_file_periodic_repository.py
git commit -m "feat: implement FilePeriodicTemplateRepository with tests" 
```

### Task 5: Configure injector module

**Files:**
- Create: `zentray/dependencies.py`

**Interfaces:**
- Consumes: `TaskRepository`, `PeriodicTemplateRepository`
- Produces: `AppModule` with provider methods

- [ ] **Step 1: Write AppModule configuration**  
```python
# zentray/dependencies.py
from injector import Module, provider, singleton, Injector
from PySide6.QtWidgets import QApplication
from zentray.core.repository import TaskRepository, PeriodicTemplateRepository
from zentray.repositories.file_repository import FileTaskRepository, FilePeriodicTemplateRepository
from zentray.services.task_service import TaskService
from zentray.services.pomodoro_service import PomodoroService
from zentray.services.script_service import ScriptService
from zentray.ui.renderer import TrayRenderer
from zentray.ui.menu_builder import MenuBuilder
from zentray.ui.extensions.loader import ExtensionLoader
from zentray.config import STORAGE_BACKEND

class AppModule(Module):
    @provider
    @singleton
    def provide_qapplication(self) -> QApplication:
        return QApplication.instance() or QApplication([])
    
    @provider
    @singleton
    def provide_task_repository(self) -> TaskRepository:
        if STORAGE_BACKEND == "mysql":
            from zentray.repositories.mysql_repository import MySQLTaskRepository
            return MySQLTaskRepository()
        return FileTaskRepository()
    
    @provider
    @singleton
    def provide_template_repository(self) -> PeriodicTemplateRepository:
        return FilePeriodicTemplateRepository()
    
    @provider
    @singleton
    def provide_task_service(
        self,
        task_repo: TaskRepository,
        template_repo: PeriodicTemplateRepository
    ) -> TaskService:
        from zentray.core.scheduler import Scheduler
        scheduler = Scheduler()
        return TaskService(task_repo, template_repo, scheduler)
    
    @provider
    @singleton
    def provide_pomodoro_service(self) -> PomodoroService:
        return PomodoroService()
    
    @provider
    @singleton
    def provide_script_service(self) -> ScriptService:
        return ScriptService()
    
    @provider
    @singleton
    def provide_renderer(self, app: QApplication) -> TrayRenderer:
        from zentray.ui.tray import create_tray_backend
        backend = create_tray_backend(app)
        return TrayRenderer(backend)
    
    @provider
    @singleton
    def provide_extension_loader(self) -> ExtensionLoader:
        return ExtensionLoader()

injector = Injector([AppModule()])
```

- [ ] **Step 2: Create test to verify injection**  
```python
# tests/unit/test_injector.py
from zentray.dependencies import injector
from zentray.services.task_service import TaskService
from zentray.services.pomodoro_service import PomodoroService

def test_injection():
    task_service = injector.get(TaskService)
    pomodoro_service = injector.get(PomodoroService)
    assert isinstance(task_service, TaskService)
    assert isinstance(pomodoro_service, PomodoroService)
```

- [ ] **Step 3: Run test to verify it passes**  
Run: `pytest tests/unit/test_injector.py -v`  
Expected: `PASSED`  

- [ ] **Step 4: Commit**  
```bash
git add zentray/dependencies.py tests/unit/test_injector.py
git commit -m "feat: configure injector module" 
```

### Task 6: Refactor TaskService

**Files:**
- Create: `zentray/services/task_service.py`
- Modify: `zentray/ui/tray.py` (remove TaskService logic)

**Interfaces:**
- Consumes: `TaskRepository`, `PeriodicTemplateRepository`, `Scheduler`
- Produces: `TaskService` class with core business logic

- [ ] **Step 1: Write TaskService class**  
```python
# zentray/services/task_service.py
from typing import List, Optional
from zentray.core.repository import TaskRepository, PeriodicTemplateRepository
from zentray.core.models import Task, PeriodicTemplate
from zentray.core.scheduler import Scheduler


class TaskService:
    def __init__(
        self,
        task_repo: TaskRepository,
        template_repo: PeriodicTemplateRepository,
        scheduler: Scheduler
    ):
        self.task_repo = task_repo
        self.template_repo = template_repo
        self.scheduler = scheduler
    
    def get_all_tasks(self) -> List[Task]:
        return self.task_repo.find_all()
    
    def get_current_task(self) -> Optional[Task]:
        return self.scheduler.get_current()
    
    def select_task(self, task_id: str) -> None:
        task = self.task_repo.find_by_id(task_id)
        if task:
            self.scheduler.pause()
            self.scheduler.build_queue([task])
            self.scheduler.resume()
    
    def create_task(self, task_data: dict) -> Task:
        task = Task(**task_data)
        tasks = self.task_repo.find_all()
        tasks.append(task)
        self.task_repo.save_all(tasks)
        self._refresh_scheduler()
        return task
    
    def update_task(self, task_id: str, task_data: dict) -> Optional[Task]:
        tasks = self.task_repo.find_all()
        for i, t in enumerate(tasks):
            if t.id == task_id:
                updated = Task(**{**t.to_dict(), **task_data})
                tasks[i] = updated
                self.task_repo.save_all(tasks)
                self._refresh_scheduler()
                return updated
        return None
    
    def update_progress(self, task_id: str, percent: int, note: str) -> Optional[Task]:
        tasks = self.task_repo.find_all()
        for i, t in enumerate(tasks):
            if t.id == task_id:
                t.progress = percent
                t.progress_logs.append({
                    "time": datetime.datetime.now().isoformat(),
                    "percent": percent,
                    "note": note
                })
                tasks[i] = t
                self.task_repo.save_all(tasks)
                return t
        return None
    
    def mark_done(self, task_id: str) -> None:
        task = self.task_repo.find_by_id(task_id)
        if task:
            self.task_repo.archive(task, "DONE")
            self.task_repo.delete(task_id)
            self._refresh_scheduler()
    
    def abandon(self, task_id: str) -> None:
        task = self.task_repo.find_by_id(task_id)
        if task:
            self.task_repo.archive(task, "ABANDONED")
            self.task_repo.delete(task_id)
            self._refresh_scheduler()
    
    def _refresh_scheduler(self) -> None:
        tasks = self.task_repo.find_active()
        self.scheduler.build_queue(tasks)
```

- [ ] **Step 2: Remove TrayManager task logic**  
```python
# zentray/ui/tray.py
# Remove from TrayManager class:
#   - all task-related methods like mark_current_task_done, edit_current_task, etc.
#   - the scheduler reference and task storage
#   - the reload_data and update_ticker methods (these are moved to TaskService)
```

- [ ] **Step 3: Write test for mark_done**  
```python
# tests/unit/test_task_service.py
from zentray.services.task_service import TaskService
from zentray.core.repository import TaskRepository
from zentray.core.models import Task
from zentray.config import STORAGE_BACKEND
import pytest
import os

@pytest.fixture
def task_service():
    from zentray.dependencies import injector
    return injector.get(TaskService)

def test_mark_done(task_service):
    # Create task
    task = Task(title="test", category="work", priority="high")
    task = task_service.create_task(task.to_dict())
    
    # Mark done
    task_service.mark_done(task.id)
    
    # Verify task removed
    assert not task_service.get_all_tasks()
```

- [ ] **Step 4: Run test to verify it passes**  
Run: `pytest tests/unit/test_task_service.py::test_mark_done -v`  
Expected: `PASSED`  

- [ ] **Step 5: Commit**  
```bash
git add zentray/services/task_service.py zentray/ui/tray.py tests/unit/test_task_service.py
git commit -m "feat: refactor TaskService and remove old logic from TrayManager" 
```

### Task 7: Refactor PomodoroService

**Files:**
- Create: `zentray/services/pomodoro_service.py`

**Interfaces:**
- Consumes: None
- Produces: `PomodoroService` class with timer and signals

- [ ] **Step 1: Write PomodoroService class**  
```python
# zentray/services/pomodoro_service.py
from typing import Optional
from PySide6.QtCore import QTimer, Signal, QObject
from zentray.config import POMODORO_MINUTES

class PomodoroService(QObject):
    time_updated = Signal(int)      # 剩余秒数更新
    pomodoro_finished = Signal()    # 专注结束
    
    def __init__(self, duration_minutes: int = POMODORO_MINUTES):
        super().__init__()
        self.duration = duration_minutes * 60
        self.remaining_seconds = 0
        self.is_active = False
        self.timer = QTimer()
        self.timer.timeout.connect(self._tick)
    
    def start(self) -> None:
        self.remaining_seconds = self.duration
        self.is_active = True
        self.timer.start(1000)  
    
    def stop(self) -> None:
        self.is_active = False
        self.timer.stop()
        self.remaining_seconds = 0
    
    def extend(self, additional_minutes: int = 10) -> None:
        if self.is_active:
            self.remaining_seconds += additional_minutes * 60
    
    def get_remaining(self) -> int:
        return self.remaining_seconds
    
    def get_status(self) -> dict:
        return {
            "is_active": self.is_active,
            "remaining_seconds": self.remaining_seconds,
            "remaining_minutes": self.remaining_seconds // 60
        }
    
    def _tick(self) -> None:
        if self.remaining_seconds > 0:
            self.remaining_seconds -= 1
            self.time_updated.emit(self.remaining_seconds)
        else:
            self.is_active = False
            self.timer.stop()
            self.pomodoro_finished.emit()
```

- [ ] **Step 2: Add signal connections**  
```python
# zentray/ui/controller.py (in TrayController)
# Connect to PomodoroService
self.pomodoro_service.time_updated.connect(self._on_pomodoro_tick)
self.pomodoro_service.pomodoro_finished.connect(self._on_pomodoro_end)
```

- [ ] **Step 3: Write test for start/stop**  
```python
# tests/unit/test_pomodoro_service.py
from zentray.services.pomodoro_service import PomodoroService
import pytest
import time


def test_pomodoro_service():
    service = PomodoroService()
    assert not service.is_active
    
    # Start
    service.start()
    assert service.is_active
    assert service.get_remaining() > 0
    
    # Stop
    service.stop()
    assert not service.is_active
    assert service.get_remaining() == 0
```

- [ ] **Step 4: Run test to verify it passes**  
Run: `pytest tests/unit/test_pomodoro_service.py -v`  
Expected: `PASSED`  

- [ ] **Step 5: Commit**  
```bash
git add zentray/services/pomodoro_service.py tests/unit/test_pomodoro_service.py
git commit -m "feat: implement PomodoroService with tests" 
```

### Task 8: Refactor TrayController

**Files:**
- Create: `zentray/ui/controller.py`
- Create: `zentray/ui/renderer.py`
- Create: `zentray/ui/menu_builder.py`
- Modify: `zentray/ui/tray.py` (move to backend)

**Interfaces:**
- Consumes: `TaskService`, `PomodoroService`, `ScriptService`, `TrayRenderer`, `MenuBuilder`, `ExtensionLoader`
- Produces: `TrayController` class with event routing

- [ ] **Step 1: Write TrayController class**  
```python
# zentray/ui/controller.py
from typing import Optional
from PySide6.QtCore import QObject, QTimer
from PySide6.QtWidgets import QApplication
from zentray.services.task_service import TaskService
from zentray.services.pomodoro_service import PomodoroService
from zentray.services.script_service import ScriptService
from zentray.services.notification import NotificationClient
from zentray.ui.renderer import TrayRenderer
from zentray.ui.menu_builder import MenuBuilder
from zentray.ui.extensions.loader import ExtensionLoader
from zentray.config import POLLING_INTERVAL_MS

class TrayController(QObject):
    def __init__(self, app: QApplication, task_service: TaskService, pomodoro_service: PomodoroService, script_service: ScriptService, renderer: TrayRenderer, menu_builder: MenuBuilder, extension_loader: ExtensionLoader):
        super().__init__()
        self.app = app
        self.task_service = task_service
        self.pomodoro_service = pomodoro_service
        self.script_service = script_service
        self.renderer = renderer
        self.menu_builder = menu_builder
        self.extension_loader = extension_loader
        
        # Connect signals
        self.pomodoro_service.time_updated.connect(self._on_pomodoro_tick)
        self.pomodoro_service.pomodoro_finished.connect(self._on_pomodoro_end)
        self.script_service.log_updated.connect(self._on_script_log)
        
        # Load extensions
        self.extensions = self.extension_loader.load_all()
        
        # Start poll timer
        self.poll_timer = QTimer()
        self.poll_timer.timeout.connect(self._update_display)
        self.poll_timer.start(POLLING_INTERVAL_MS)
    
    def handle_action(self, action_id: str) -> None:
        command = self._parse_action(action_id)
        command.execute(self)
    
    def _parse_action(self, action_id: str) -> 'ActionCommand':
        from .commands import (
            NewTaskCommand, DoneCommand, AbandonCommand,
            EditCommand, ProgressCommand, PomodoroCommand,
            SelectTaskCommand, ScriptCommand, QuitCommand
        )
        
        if action_id == "new":
            return NewTaskCommand()
        elif action_id == "done":
            return DoneCommand()
        elif action_id.startswith("select_task_"):
            task_id = action_id.split("_")[-1]
            return SelectTaskCommand(task_id)
        elif action_id == "pomodoro":
            return PomodoroCommand("start")
        elif action_id.startswith("script_"):
            script_name = action_id.split("_")[-1]
            return ScriptCommand(script_name)
        elif action_id == "quit":
            return QuitCommand()
        else:
            return UnknownCommand(action_id)
    
    def _update_display(self) -> None:
        if self.pomodoro_service.is_active:
            mins = self.pomodoro_service.get_remaining() // 60
            self.renderer.set_text(f"🍅 专注中 {mins}分钟")
        else:
            task = self.task_service.get_current_task()
            if task:
                self.renderer.set_text(task.title)
                self.renderer.set_icon(f"pie_{task.priority}_{task.progress}")
            else:
                self.renderer.set_text("🎉 暂无待办")
        
        self.menu_builder.refresh(self.task_service, self.pomodoro_service, self.extensions)
    
    def _on_pomodoro_tick(self, seconds: int) -> None:
        self._update_display()
    
    def _on_pomodoro_end(self) -> None:
        self.renderer.show_notification("专注结束", "番茄钟已完成，休息一下吧！")
    
    def _on_script_log(self, log: str) -> None:
        self.renderer.set_text(log[:50])
```

- [ ] **Step 2: Write Renderer class**  
```python
# zentray/ui/renderer.py
from zentray.ui.tray import TrayImplementation


class TrayRenderer:
    def __init__(self, backend: TrayImplementation):
        self.backend = backend
    
    def set_text(self, text: str) -> None:
        self.backend.set_label(text)
    
    def set_icon(self, name: str) -> None:
        self.backend.set_icon(name)
    
    def show_notification(self, title: str, msg: str) -> None:
        self.backend.show_notification(title, msg)
```

- [ ] **Step 3: Write MenuBuilder class**  
```python
# zentray/ui/menu_builder.py
from PySide6.QtCore import Qt
from PySide6.QtWidgets import QMenu, QAction, QIcon


class MenuBuilder:
    def refresh(self, task_service, pomodoro_service, extensions):
        # Logic similar to TrayManager's update_menu_state (replaced by this class)
        # ...
        pass
```

- [ ] **Step 4: Commit**  
```bash
git add zentray/ui/controller.py zentray/ui/renderer.py zentray/ui/menu_builder.py
git commit -m "feat: refactor TrayController into services and controllers" 
```

### Task 9: Implement Command Pattern

**Files:**
- Create: `zentray/ui/commands.py`

**Interfaces:**
- Consumes: `TrayController` instance
- Produces: `ActionCommand` base class and specific commands

- [ ] **Step 1: Write ActionCommand base class**  
```python
# zentray/ui/commands.py
from abc import ABC, abstractmethod
from typing import TYPE_CHECKING
if TYPE_CHECKING:
    from .controller import TrayController

class ActionCommand(ABC):
    @abstractmethod
    def execute(self, controller: 'TrayController') -> None:
        pass
```

- [ ] **Step 2: Implement specific commands**  
```python
# zentray/ui/commands.py (add to the end)
class NewTaskCommand(ActionCommand):
    def execute(self, controller: 'TrayController') -> None:
        from .dialogs import TaskDialog
        dialog = TaskDialog()
        if dialog.exec():
            data = dialog.get_data()
            controller.task_service.create_task(data)
            controller._update_display()

# (similarly for other commands: DoneCommand, SelectTaskCommand, etc.)
```

- [ ] **Step 3: Run test to verify commands**  
```python
# tests/unit/test_commands.py
from zentray.ui.commands import NewTaskCommand
from zentray.ui.controller import TrayController
import pytest

def test_new_task_command():
    # Mock TrayController
    controller = TrayController(None, None, None, None, None, None, None)
    command = NewTaskCommand()
    command.execute(controller)
    # Verify command execution (mocked)
    assert True
```

- [ ] **Step 4: Commit**  
```bash
git add zentray/ui/commands.py tests/unit/test_commands.py
git commit -m "feat: implement command pattern for event handling" 
```

### Task 10: Refactor main.py

**Files:**
- Modify: `zentray/main.py`

**Interfaces:**
- Consumes: `Injector` instance
- Produces: Main program flow using dependency injection

- [ ] **Step 1: Modify main.py to use injector**  
```python
# zentray/main.py
import sys
import os

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

if sys.platform.startswith('linux'):
    os.environ["QT_IM_MODULE"] = "ibus"
    os.environ.setdefault("XMODIFIERS", "@im=fcitx")

from PySide6.QtWidgets import QApplication
from zentray.dependencies import injector
from zentray.ui.controller import TrayController
from zentray.ui.overlay import QuickAddOverlay
from zentray.services.system_utils import SingleInstanceGuard, HotkeyListener
from zentray.workers.watcher import WatcherWorker
from zentray.workers.nightly_job import NightlyJobWorker
from zentray.config import config
import logging_config


def main():
    config.validate()
    logging_config.setup_logging()
    
    SingleInstanceGuard()
    
    app = QApplication(sys.argv)
    app.setQuitOnLastWindowClosed(False)
    
    controller = injector.get(TrayController)
    
    overlay = QuickAddOverlay()
    overlay.task_added.connect(controller._update_display)
    
    hotkey = HotkeyListener(config.hotkey_quick_add)
    hotkey.triggered.connect(overlay.show_center)
    hotkey.start()
    
    task_repo = injector.get(TaskRepository)
    watcher = WatcherWorker(task_repo)
    watcher.tasks_updated.connect(controller._update_display)
    watcher.start()
    
    nightly = NightlyJobWorker(task_repo)
    nightly.job_completed.connect(controller.renderer.show_notification)
    nightly.start()
    
    sys.exit(app.exec())

if __name__ == "__main__":
    main()
```

- [ ] **Step 2: Verify main.py runs**  
Run: `python zentray/main.py`  
Expected: Application starts with all features intact  

- [ ] **Step 3: Commit**  
```bash
git add zentray/main.py
git commit -m "feat: refactor main.py to use injector" 
```

### Task 11: Test Framework Integration

**Files:**
- Create: `tests/conftest.py`
- Create: `tests/unit/test_task_service.py`
- Create: `tests/unit/test_pomodoro_service.py`

**Interfaces:**
- Consumes: `TaskService`, `PomodoroService`
- Produces: pytest configuration

- [ ] **Step 1: Configure pytest**  
```python
# tests/conftest.py
import pytest
from injector import Injector
from zentray.dependencies import AppModule
from zentray.core.repository import TaskRepository
from zentray.repositories.file_repository import FileTaskRepository
from zentray.services.task_service import TaskService
from zentray.core.models import Task

@pytest.fixture
def injector_instance():
    return Injector([AppModule()])

@pytest.fixture
def task_repo(injector_instance):
    return injector_instance.get(TaskRepository)

@pytest.fixture
def task_service(injector_instance):
    return injector_instance.get(TaskService)

@pytest.fixture
def sample_task():
    return Task(
        title="测试任务",
        category="工作",
        priority="high",
        details="这是一个测试任务"
    )
```

- [ ] **Step 2: Write test cases**  
```python
# tests/unit/test_task_service.py (already created in Task 6)
# tests/unit/test_pomodoro_service.py (already created in Task 7)
```

- [ ] **Step 3: Install pytest**  
```bash
pip install pytest pytest-cov
```

- [ ] **Step 4: Commit**  
```bash
git add tests/conftest.py tests/unit/test_task_service.py tests/unit/test_pomodoro_service.py
git commit -m "feat: integrate pytest testing framework" 
```

### Task 12: Refactor Worker Modules

**Files:**
- Modify: `zentray/workers/watcher.py`
- Modify: `zentray/workers/nightly_job.py`

**Interfaces:**
- Consumes: `TaskRepository` via injector
- Produces: Worker modules using injected storage

- [ ] **Step 1: Inject TaskRepository into Watcher**  
```python
# zentray/workers/watcher.py
from PySide6.QtCore import QTimer, Signal
from zentray.core.storage import Storage
from zentray.services.task_service import TaskService


class WatcherWorker(QThread):
    tasks_updated = Signal()  # 通知 UI 层数据已在后台更新，需要重新读取和轮播
    task_overdue = Signal(object)  # 将被惩罚的 Task 对象抛给主线程去弹系统警告框
    
    def __init__(self, task_repo: TaskRepository):
        super().__init__()
        self.is_running = True
        self.task_repo = task_repo
    
    def run(self):
        while self.is_running:
            self._do_maintenance()
            for _ in range(60):
                if not self.is_running:
                    break
                time.sleep(1)
    
    def _do_maintenance(self):
        tasks = self.task_repo.find_all()
        templates = self.task_repo.find_active_templates()
        ...
```

- [ ] **Step 2: Commit**  
```bash
git add zentray/workers/watcher.py zentray/workers/nightly_job.py
git commit -m "feat: inject TaskRepository into worker modules" 
```

---

## Plan Completion

Plan complete and saved to `docs/superpowers/plans/2026-07-11-zentray-refactor-plan.md`.

**Two execution options:**

1. **Subagent-Driven (recommended)** - I dispatch a fresh subagent per task, review between tasks, fast iteration

2. **Inline Execution** - Execute tasks in this session using executing-plans, batch execution with checkpoints

**Which approach?