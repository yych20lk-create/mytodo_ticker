# zentray/services/script_service.py
"""
脚本执行服务 —— 为后续脚本按钮功能预留。

管理已注册脚本的执行和日志收集。
"""
import datetime
from typing import Dict, List
from PySide6.QtCore import QObject, Signal


class ScriptService(QObject):
    """脚本执行服务"""

    log_updated = Signal(str)          # 日志更新
    script_finished = Signal(str, bool)  # 脚本结束 (脚本名, 成功与否)

    def __init__(self):
        super().__init__()
        self.registered_scripts: Dict[str, dict] = {}
        self.execution_logs: List[str] = []

    def register(self, name: str, command: str, description: str = "") -> None:
        """注册脚本"""
        self.registered_scripts[name] = {
            "command": command,
            "description": description,
        }

    def execute(self, name: str) -> bool:
        """执行已注册的脚本（当前为桩实现，后续完善）"""
        if name not in self.registered_scripts:
            self._log(f"[ERROR] 脚本 '{name}' 未注册")
            return False

        script = self.registered_scripts[name]
        self._log(f"[START] 执行脚本: {name} ({script['description']})")
        # 后续实现：subprocess.run(script["command"], ...)
        self._log(f"[INFO] 脚本执行功能将在后续迭代中完善")
        self.script_finished.emit(name, True)
        return True

    def get_logs(self) -> List[str]:
        """获取执行日志"""
        return self.execution_logs

    def get_registered_scripts(self) -> Dict[str, dict]:
        """获取已注册脚本列表"""
        return self.registered_scripts

    def _log(self, message: str) -> None:
        timestamp = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        log_entry = f"{timestamp} {message}"
        self.execution_logs.append(log_entry)
        self.log_updated.emit(log_entry)
