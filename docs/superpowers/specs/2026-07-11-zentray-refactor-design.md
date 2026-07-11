# ZenTray 项目重构设计方案

> 日期: 2026-07-11
> 状态: 待审批
> 版本: v2.0 (整合代码审核发现 + 后续扩展预留)

---

## 一、重构目标

### 1.1 核心目标

| 目标 | 当前问题 | 重构后状态 |
|------|---------|-----------|
| **职责解耦** | TrayManager 27方法，God Object | 拆分为 4 个独立服务 |
| **依赖注入** | main.py 硬编码实例化 | 使用 injector 框架管理依赖 |
| **存储抽象** | Storage 静态方法，无接口 | Repository 接口 + 多后端适配 |
| **扩展机制** | 无插件系统 | ExtensionLoader + ScriptService |
| **测试覆盖** | 完全缺失 | pytest 单元测试框架 |

### 1.2 后续扩展预留

| 功能 | 预留设计 |
|------|---------|
| **脚本按钮** | `ScriptService` + `ExtensionLoader` + 状态栏日志接口 |
| **MySQL 存储** | `TaskRepository` 接口 + `MySQLTaskRepository` 适配器 |

---

## 二、架构设计

### 2.1 服务拆分方案（中粒度）

```
┌─────────────────────────────────────────────────────────────┐
│                    TrayController (协调者)                    │
│  - 事件路由 (handle_action → 命令模式)                        │
│  - 状态栏渲染委托 TrayRenderer                                │
│  - 扩展按钮协调                                              │
│  - 菜单构建 MenuBuilder                                      │
└─────────────────────────────────────────────────────────────┘
          │                    │                    │
          ▼                    ▼                    ▼
┌─────────────────┐  ┌─────────────────┐  ┌─────────────────┐
│   TaskService   │  │ PomodoroService │  │  ScriptService  │
│ - 任务 CRUD     │  │ - 专注计时      │  │ - 脚本执行      │
│ - 任务选择      │  │ - 延长/中止     │  │ - 日志收集      │
│ - 进度更新      │  │ - 状态查询      │  │ - 状态查询      │
└─────────────────┘  └─────────────────┘  └─────────────────┘
          │                                         │
          ▼                                         ▼
┌─────────────────┐                      ┌─────────────────┐
│ TaskRepository  │  ← MySQL 预留接口    │ ExtensionLoader │
│ (interface)     │                      │ - 插件发现      │
│ - FileTaskRepo  │  ← 当前实现          │ - 按钮注册      │
│ - MySQLTaskRepo │  ← 后续实现          │                 │
└─────────────────┘                      └─────────────────┘
```

### 2.2 新增模块结构

```
zentray/
├── core/
│   ├── models.py          # 数据模型（保持不变）
│   ├── scheduler.py       # 轮播调度器（保持不变）
│   └── repository.py      # 【新增】Repository 抽象接口
├── repositories/
│   ├── __init__.py
│   ├── file_repository.py # 【新增】JSON 文件存储实现
│   └── mysql_repository.py# 【新增】MySQL 存储实现（预留）
├── services/
│   ├── task_service.py    # 【新增】任务管理服务
│   ├── pomodoro_service.py# 【新增】番茄钟服务
│   ├── script_service.py  # 【新增】脚本执行服务（预留）
│   ├── notification.py    # 保持不变
│   ├── ai_review.py       # 保持不变
│   └── system_utils.py    # 保持不变
├── ui/
│   ├── controller.py      # 【新增】TrayController 协调者
│   ├── renderer.py        # 【新增】TrayRenderer 状态栏渲染
│   ├── menu_builder.py    # 【新增】MenuBuilder 菜单构建
│   ├── extensions/
│   │   ├── __init__.py
│   │   ├── interface.py   # 【新增】StatusBarExtension 接口
│   │   ├── loader.py      # 【新增】ExtensionLoader 加载器
│   │   └── script_button.py# 【新增】脚本按钮扩展示例
│   ├── tray.py            # 保持（底层实现）
│   ├── dialogs.py         # 保持（UI 对话框）
│   └── overlay.py         # 保持（闪电添加）
├── workers/
│   ├── watcher.py         # 重构：注入 TaskRepository
│   └── nightly_job.py     # 重构：注入 TaskRepository
├── config.py              # 重构：统一配置管理
├── dependencies.py        # 【新增】injector 模块配置
├── logging_config.py      # 保持
└── main.py                # 重构：使用 injector 启动
├── tests/                 # 【新增】测试目录
│   ├── __init__.py
│   ├── conftest.py        # pytest 配置
│   ├── unit/
│   │   ├── test_task_service.py
│   │   ├── test_pomodoro_service.py
│   │   └── test_repository.py
│   └── integration/
│   │   └ test_controller.py
├── extensions/            # 【新增】插件目录（项目根）
│   ├── __init__.py
│   └── health_check.py    # 示例插件
```

---

## 三、核心模块设计

### 3.1 Repository 接口（存储抽象）

```python
# zentray/core/repository.py
from abc import ABC, abstractmethod
from typing import List, Optional
from zentray.core.models import Task, PeriodicTemplate

class TaskRepository(ABC):
    """任务存储抽象接口"""
    
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
        """查找所有未完成的活跃任务"""
        pass
    
    @abstractmethod
    def archive(self, task: Task, status: str) -> None:
        """归档任务"""
        pass

class PeriodicTemplateRepository(ABC):
    """周期任务模板存储抽象接口"""
    
    @abstractmethod
    def find_all(self) -> List[PeriodicTemplate]:
        pass
    
    @abstractmethod
    def save_all(self, templates: List[PeriodicTemplate]) -> None:
        pass
```

### 3.2 FileTaskRepository 实现

```python
# zentray/repositories/file_repository.py
import json
import shutil
import datetime
from pathlib import Path
from typing import List, Optional
from zentray.core.repository import TaskRepository, PeriodicTemplateRepository
from zentray.core.models import Task, PeriodicTemplate
from zentray.config import ACTIVE_TASKS_FILE, PERIODIC_TEMPLATES_FILE, ARCHIVE_DIR

class FileTaskRepository(TaskRepository):
    """基于 JSON 文件的存储实现"""
    
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
            # 备份损坏文件
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
        return self.find_all()  # JSON 模式下所有任务都是活跃的
    
    def archive(self, task: Task, status: str) -> None:
        date_str = datetime.datetime.now().strftime('%Y-%m-%d')
        archive_file = self.archive_dir / f"{date_str}.log"
        timestamp = datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        log_line = f"[{timestamp}] [状态: {status}] [分类: {task.category}] [{task.priority.upper()}] {task.title} - {task.details} (附件数: {len(task.attachments)})\n"
        with open(archive_file, 'a', encoding='utf-8') as f:
            f.write(log_line)

class FilePeriodicTemplateRepository(PeriodicTemplateRepository):
    """周期任务模板 JSON 存储"""
    
    def __init__(self):
        self.filepath = PERIODIC_TEMPLATES_FILE
    
    def find_all(self) -> List[PeriodicTemplate]:
        # 类似 FileTaskRepository 实现
        pass
    
    def save_all(self, templates: List[PeriodicTemplate]) -> None:
        pass
```

### 3.3 TaskService 设计

```python
# zentray/services/task_service.py
from typing import List, Optional
from zentray.core.repository import TaskRepository, PeriodicTemplateRepository
from zentray.core.models import Task, PeriodicTemplate
from zentray.core.scheduler import Scheduler

class TaskService:
    """任务管理服务 - 封装所有任务相关业务逻辑"""
    
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
        """将指定任务设为当前轮播焦点"""
        task = self.task_repo.find_by_id(task_id)
        if task:
            self.scheduler.pause()
            # 设置焦点任务
            self.scheduler.build_queue([task])
            self.scheduler.resume()
    
    def create_task(self, task_data: dict) -> Task:
        """创建新任务"""
        task = Task(**task_data)
        tasks = self.task_repo.find_all()
        tasks.append(task)
        self.task_repo.save_all(tasks)
        self._refresh_scheduler()
        return task
    
    def update_task(self, task_id: str, task_data: dict) -> Optional[Task]:
        """更新任务"""
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
        """更新任务进度"""
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
        """完成任务"""
        task = self.task_repo.find_by_id(task_id)
        if task:
            self.task_repo.archive(task, "DONE")
            self.task_repo.delete(task_id)
            self._refresh_scheduler()
    
    def abandon(self, task_id: str) -> None:
        """废弃任务"""
        task = self.task_repo.find_by_id(task_id)
        if task:
            self.task_repo.archive(task, "ABANDONED")
            self.task_repo.delete(task_id)
            self._refresh_scheduler()
    
    def _refresh_scheduler(self) -> None:
        tasks = self.task_repo.find_active()
        self.scheduler.build_queue(tasks)
```

### 3.4 PomodoroService 设计

```python
# zentray/services/pomodoro_service.py
from typing import Optional
from PySide6.QtCore import QTimer, Signal, QObject
from zentray.config import POMODORO_MINUTES

class PomodoroService(QObject):
    """番茄钟专注服务"""
    
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
        """开始专注"""
        self.remaining_seconds = self.duration
        self.is_active = True
        self.timer.start(1000)  # 每秒触发
    
    def stop(self) -> None:
        """中止专注"""
        self.is_active = False
        self.timer.stop()
        self.remaining_seconds = 0
    
    def extend(self, additional_minutes: int = 10) -> None:
        """延长专注"""
        if self.is_active:
            self.remaining_seconds += additional_minutes * 60
    
    def get_remaining(self) -> int:
        """获取剩余秒数"""
        return self.remaining_seconds
    
    def get_status(self) -> dict:
        """获取状态摘要"""
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

### 3.5 ScriptService 设计（预留）

```python
# zentray/services/script_service.py
import subprocess
from typing import List, Optional
from PySide6.QtCore import QObject, Signal

class ScriptService(QObject):
    """脚本执行服务 - 为后续脚本按钮功能预留"""
    
    log_updated = Signal(str)       # 日志更新
    script_finished = Signal(str, bool)  # 脚本结束 (脚本名, 成功与否)
    
    def __init__(self):
        super().__init__()
        self.registered_scripts: dict = {}  # 脚本注册表
        self.execution_logs: List[str] = []
    
    def register(self, name: str, command: str, description: str = "") -> None:
        """注册脚本"""
        self.registered_scripts[name] = {
            "command": command,
            "description": description
        }
    
    def execute(self, name: str) -> bool:
        """执行已注册的脚本"""
        if name not in self.registered_scripts:
            self._log(f"[ERROR] 脚本 '{name}' 未注册")
            return False
        
        script = self.registered_scripts[name]
        self._log(f"[START] 执行脚本: {name}")
        
        try:
            result = subprocess.run(
                script["command"],
                shell=True,
                capture_output=True,
                text=True,
                timeout=60
            )
            if result.returncode == 0:
                self._log(f"[SUCCESS] {name} 执行成功")
                self.script_finished.emit(name, True)
                return True
            else:
                self._log(f"[FAILED] {name} 执行失败: {result.stderr}")
                self.script_finished.emit(name, False)
                return False
        except Exception as e:
            self._log(f"[ERROR] {name} 执行异常: {str(e)}")
            self.script_finished.emit(name, False)
            return False
    
    def get_logs(self) -> List[str]:
        """获取执行日志"""
        return self.execution_logs
    
    def get_registered_scripts(self) -> dict:
        """获取已注册脚本列表"""
        return self.registered_scripts
    
    def _log(self, message: str) -> None:
        timestamp = datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        log_entry = f"{timestamp} {message}"
        self.execution_logs.append(log_entry)
        self.log_updated.emit(log_entry)
```

### 3.6 ExtensionLoader 设计

```python
# zentray/ui/extensions/interface.py
from abc import ABC, abstractmethod
from typing import dict

class StatusBarExtension(ABC):
    """状态栏扩展接口"""
    
    @abstractmethod
    def get_button_config(self) -> dict:
        """返回按钮配置: {icon, tooltip, priority}"""
        pass
    
    @abstractmethod
    def handle_click(self) -> None:
        """按钮点击回调"""
        pass
    
    @abstractmethod
    def get_logs(self) -> List[str]:
        """返回日志列表（用于状态栏展示）"""
        pass

# zentray/ui/extensions/loader.py
import importlib
import pkgutil
from pathlib import Path
from typing import List
from .interface import StatusBarExtension

class ExtensionLoader:
    """动态加载状态栏扩展插件"""
    
    def __init__(self, package_path: str = "extensions"):
        self.package_path = Path(package_path)
        self.extensions: List[StatusBarExtension] = []
    
    def load_all(self) -> List[StatusBarExtension]:
        """加载所有插件"""
        if not self.package_path.exists():
            return []
        
        for _, name, _ in pkgutil.iter_modules([str(self.package_path)]):
            try:
                module = importlib.import_module(f"{self.package_path}.{name}")
                if hasattr(module, "get_extension"):
                    ext = module.get_extension()
                    if isinstance(ext, StatusBarExtension):
                        self.extensions.append(ext)
            except Exception as e:
                print(f"Extension load error: {name} - {e}")
        
        # 按优先级排序
        self.extensions.sort(key=lambda e: e.get_button_config().get("priority", 0))
        return self.extensions
    
    def get_buttons(self) -> List[dict]:
        """获取所有扩展按钮配置"""
        return [ext.get_button_config() for ext in self.extensions]
```

### 3.7 TrayController 设计

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
from zentray.core.scheduler import Scheduler
from zentray.config import POLLING_INTERVAL_MS

class TrayController(QObject):
    """托盘协调者 - 职责: 事件路由 + 状态协调 + 扩展管理"""
    
    def __init__(
        self,
        app: QApplication,
        task_service: TaskService,
        pomodoro_service: PomodoroService,
        script_service: ScriptService,
        renderer: TrayRenderer,
        menu_builder: MenuBuilder,
        extension_loader: ExtensionLoader
    ):
        super().__init__()
        self.app = app
        self.task_service = task_service
        self.pomodoro_service = pomodoro_service
        self.script_service = script_service
        self.renderer = renderer
        self.menu_builder = menu_builder
        self.extension_loader = extension_loader
        
        # 连接信号
        self.pomodoro_service.time_updated.connect(self._on_pomodoro_tick)
        self.pomodoro_service.pomodoro_finished.connect(self._on_pomodoro_end)
        self.script_service.log_updated.connect(self._on_script_log)
        
        # 加载扩展
        self.extensions = self.extension_loader.load_all()
        
        # 启动轮播定时器
        self.poll_timer = QTimer()
        self.poll_timer.timeout.connect(self._update_display)
        self.poll_timer.start(POLLING_INTERVAL_MS)
    
    def handle_action(self, action_id: str) -> None:
        """中央事件路由 - 命令模式"""
        # 解析命令
        command = self._parse_action(action_id)
        command.execute(self)
    
    def _parse_action(self, action_id: str) -> 'ActionCommand':
        """将 action_id 解析为命令对象"""
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
        # ... 其他命令
        else:
            return UnknownCommand(action_id)
    
    def _update_display(self) -> None:
        """更新状态栏显示"""
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
        """脚本日志更新时短暂显示在状态栏"""
        self.renderer.set_text(log[:50])  # 限制长度
```

### 3.8 injector 模块配置

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
    """依赖注入模块配置"""
    
    @provider
    @singleton
    def provide_qapplication(self) -> QApplication:
        return QApplication.instance() or QApplication([])
    
    @provider
    @singleton
    def provide_task_repository(self) -> TaskRepository:
        if STORAGE_BACKEND == "mysql":
            # 后续实现
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

# 创建全局 injector
injector = Injector([AppModule()])
```

### 3.9 命令模式（事件路由重构）

```python
# zentray/ui/commands.py
from abc import ABC, abstractmethod
from typing import TYPE_CHECKING
if TYPE_CHECKING:
    from .controller import TrayController

class ActionCommand(ABC):
    """命令基类"""
    
    @abstractmethod
    def execute(self, controller: 'TrayController') -> None:
        pass

class NewTaskCommand(ActionCommand):
    def execute(self, controller: 'TrayController') -> None:
        from .dialogs import TaskDialog
        dialog = TaskDialog()
        if dialog.exec():
            data = dialog.get_data()
            controller.task_service.create_task(data)
            controller._update_display()

class DoneCommand(ActionCommand):
    def execute(self, controller: 'TrayController') -> None:
        task = controller.task_service.get_current_task()
        if task:
            controller.task_service.mark_done(task.id)
            controller._update_display()

class PomodoroCommand(ActionCommand):
    def __init__(self, action: str):
        self.action = action
    
    def execute(self, controller: 'TrayController') -> None:
        if self.action == "start":
            controller.pomodoro_service.start()
        elif self.action == "stop":
            controller.pomodoro_service.stop()
        elif self.action == "extend":
            controller.pomodoro_service.extend()
        controller._update_display()

class ScriptCommand(ActionCommand):
    def __init__(self, script_name: str):
        self.script_name = script_name
    
    def execute(self, controller: 'TrayController') -> None:
        controller.script_service.execute(self.script_name)

class QuitCommand(ActionCommand):
    def execute(self, controller: 'TrayController') -> None:
        controller.app.quit()
```

---

## 四、配置管理重构

### 4.1 统一配置类

```python
# zentray/config.py
import os
import sys
from pathlib import Path
from dataclasses import dataclass
from platformdirs import user_data_dir

@dataclass
class AppConfig:
    """应用配置 - 统一管理"""
    
    # 应用信息
    app_name: str = "ZenTray"
    app_author: str = "Zen-Geek"
    
    # 数据目录
    data_dir: Path = None
    active_tasks_file: Path = None
    periodic_templates_file: Path = None
    archive_dir: Path = None
    
    # 存储后端
    storage_backend: str = "file"  # file | mysql
    
    # WxPusher
    wxpusher_app_token: str = None
    wxpusher_uid: str = None
    
    # AI 配置
    ai_api_base_url: str = None
    ai_api_key: str = None
    ai_model_name: str = None
    
    # UI 配置
    polling_interval_ms: int = 30000
    pomodoro_minutes: int = 25
    hotkey_quick_add: str = None
    
    def __post_init__(self):
        # 加载 .env
        self._load_env()
        
        # 初始化路径
        self.data_dir = Path(user_data_dir(self.app_name, self.app_author))
        self.active_tasks_file = self.data_dir / "active_tasks.json"
        self.periodic_templates_file = self.data_dir / "periodic_templates.json"
        self.archive_dir = self.data_dir / "archive"
        
        # 设置快捷键
        self.hotkey_quick_add = "<cmd>+<alt>+t" if sys.platform == 'darwin' else "<ctrl>+<alt>+t"
        
        # 创建目录
        os.makedirs(self.archive_dir, exist_ok=True)
    
    def _load_env(self) -> None:
        env_path = Path(__file__).parent.parent / ".env"
        if env_path.exists():
            with open(env_path, "r", encoding="utf-8") as f:
                for line in f:
                    line = line.strip()
                    if line and not line.startswith("#") and "=" in line:
                        key, val = line.split("=", 1)
                        os.environ.setdefault(key.strip(), val.strip())
        
        # 读取环境变量
        self.wxpusher_app_token = os.getenv("WXPUSHER_APP_TOKEN")
        self.wxpusher_uid = os.getenv("WXPUSHER_UID")
        self.ai_api_base_url = os.getenv("AI_API_BASE_URL", "https://api.openai.com/v1")
        self.ai_api_key = os.getenv("AI_API_KEY")
        self.ai_model_name = os.getenv("AI_MODEL_NAME", "gpt-4o")
        self.storage_backend = os.getenv("STORAGE_BACKEND", "file")
    
    def validate(self) -> bool:
        """验证必需配置"""
        required = {
            "WXPUSHER_APP_TOKEN": self.wxpusher_app_token,
            "WXPUSHER_UID": self.wxpusher_uid,
            "AI_API_KEY": self.ai_api_key
        }
        missing = [k for k, v in required.items() if not v]
        if missing:
            print(f"配置错误: 缺少必需环境变量: {', '.join(missing)}", file=sys.stderr)
            sys.exit(1)
        return True

# 全局配置实例
config = AppConfig()
```

---

## 五、main.py 重构

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
    # 1. 配置验证
    config.validate()
    logging_config.setup_logging()
    
    # 2. 单例锁
    SingleInstanceGuard()
    
    # 3. 初始化 QApplication
    app = QApplication(sys.argv)
    app.setQuitOnLastWindowClosed(False)
    
    # 4. 通过 injector 获取控制器
    controller = injector.get(TrayController)
    
    # 5. 初始化闪电添加界面
    overlay = QuickAddOverlay()
    overlay.task_added.connect(controller._update_display)
    
    hotkey = HotkeyListener(config.hotkey_quick_add)
    hotkey.triggered.connect(overlay.show_center)
    hotkey.start()
    
    # 6. 启动后台 worker（注入 repository）
    task_repo = injector.get(TaskRepository)
    watcher = WatcherWorker(task_repo)
    watcher.tasks_updated.connect(controller._update_display)
    watcher.start()
    
    nightly = NightlyJobWorker(task_repo)
    nightly.job_completed.connect(controller.renderer.show_notification)
    nightly.start()
    
    # 7. 进入事件循环
    sys.exit(app.exec())

if __name__ == "__main__":
    main()
```

---

## 六、测试框架设计

### 6.1 pytest 配置

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

### 6.2 测试示例

```python
# tests/unit/test_task_service.py
import pytest
from zentray.services.task_service import TaskService
from zentray.core.models import Task

class TestTaskService:
    
    def test_create_task(self, task_service, sample_task):
        task_data = sample_task.to_dict()
        created = task_service.create_task(task_data)
        assert created.id is not None
        assert created.title == "测试任务"
    
    def test_get_current_task(self, task_service):
        # 初始无任务
        current = task_service.get_current_task()
        assert current is None
    
    def test_mark_done(self, task_service, sample_task):
        # 先创建任务
        task_service.create_task(sample_task.to_dict())
        tasks = task_service.get_all_tasks()
        task_id = tasks[0].id
        
        # 完成任务
        task_service.mark_done(task_id)
        
        # 验证已删除
        remaining = task_service.get_all_tasks()
        assert len(remaining) == 0
    
    def test_update_progress(self, task_service, sample_task):
        created = task_service.create_task(sample_task.to_dict())
        updated = task_service.update_progress(created.id, 50, "完成一半")
        assert updated.progress == 50
        assert len(updated.progress_logs) == 1
```

---

## 七、实施里程碑

| 阶段 | 时间 | 任务 | 交付物 |
|------|------|------|--------|
| **M1: 基础架构** | 3天 | Repository接口 + File实现 + injector配置 | 可切换存储后端 |
| **M2: 服务拆分** | 4天 | TaskService + PomodoroService + TrayController | TrayManager职责解耦 |
| **M3: 扩展机制** | 2天 | ScriptService + ExtensionLoader + 命令模式 | 支持脚本按钮扩展 |
| **M4: 测试覆盖** | 2天 | pytest配置 + 核心单元测试 | 可测试架构 |
| **M5: Worker重构** | 1天 | 注入依赖到 Watcher/NightlyJob | 所有模块依赖注入 |

---

## 八、后续扩展路径

### 8.1 MySQL 存储实现

```python
# zentray/repositories/mysql_repository.py (后续实现)
from sqlalchemy import create_engine, Column, String, Integer, DateTime
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
from zentray.core.repository import TaskRepository
from zentray.core.models import Task

Base = declarative_base()

class TaskModel(Base):
    __tablename__ = "tasks"
    id = Column(String, primary_key=True)
    title = Column(String, nullable=False)
    category = Column(String)
    priority = Column(String)
    deadline = Column(String)
    details = Column(String)
    progress = Column(Integer, default=0)
    created_at = Column(DateTime)

class MySQLTaskRepository(TaskRepository):
    def __init__(self, db_url: str):
        self.engine = create_engine(db_url)
        Base.metadata.create_all(self.engine)
        self.Session = sessionmaker(bind=self.engine)
    
    def find_all(self) -> List[Task]:
        # ORM 实现
        pass
```

### 8.2 脚本按钮扩展示例

```python
# extensions/health_check.py
from zentray.ui.extensions.interface import StatusBarExtension
from zentray.services.script_service import ScriptService

class HealthCheckExtension(StatusBarExtension):
    def __init__(self, script_service: ScriptService):
        self.script_service = script_service
        # 注册脚本
        self.script_service.register(
            "system_health",
            "systemctl --type=service --state=failed",
            "检查系统服务健康状态"
        )
    
    def get_button_config(self) -> dict:
        return {
            "icon": "health",
            "tooltip": "系统健康检查",
            "priority": 10
        }
    
    def handle_click(self) -> None:
        self.script_service.execute("system_health")
    
    def get_logs(self) -> List[str]:
        return self.script_service.get_logs()

def get_extension(script_service):
    return HealthCheckExtension(script_service)
```

---

## 九、风险评估

| 风险 | 影响 | 缓解措施 |
|------|------|---------|
| **injector 学习曲线** | 中 | 提供示例代码，逐步迁移 |
| **TrayManager 拆分遗漏** | 高 | 逐方法审计，确保职责归属 |
| **Worker 依赖注入** | 中 | 提供 fixture，先测试后集成 |
| **MySQL 迁移数据丢失** | 高 | 提供备份脚本 + 回退机制 |

---

## 十、验收标准

1. ✅ TrayManager 方法数降至 < 10
2. ✅ 所有服务通过 injector 获取
3. ✅ Repository 接口可切换 file/mysql
4. ✅ pytest 测试覆盖率 > 60%
5. ✅ ExtensionLoader 可加载脚本按钮
6. ✅ 原有功能完全保留