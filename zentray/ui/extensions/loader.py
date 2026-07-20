# zentray/ui/extensions/loader.py
"""
扩展加载器 —— 动态发现和加载状态栏扩展插件。
"""
import importlib
import pkgutil
from pathlib import Path
from typing import List
from .interface import StatusBarExtension


class ExtensionLoader:
    """动态加载状态栏扩展插件"""

    def __init__(self, package_path: str | Path | None = None):
        if package_path is None:
            # 项目根 /extensions，不依赖 cwd
            from zentray.config import _PROJECT_ROOT

            package_path = _PROJECT_ROOT / "extensions"
        self.package_path = Path(package_path)
        self.extensions: List[StatusBarExtension] = []

    def load_all(self) -> List[StatusBarExtension]:
        """从插件目录加载所有扩展"""
        if not self.package_path.exists():
            return self.extensions

        # 将插件父目录加入 path，便于 import extensions.xxx
        parent = str(self.package_path.parent)
        import sys

        if parent not in sys.path:
            sys.path.insert(0, parent)

        for _, name, _ in pkgutil.iter_modules([str(self.package_path)]):
            try:
                module = importlib.import_module(
                    f"{self.package_path.name}.{name}"
                )
                if hasattr(module, "get_extension"):
                    ext = module.get_extension()
                    if isinstance(ext, StatusBarExtension):
                        self.extensions.append(ext)
            except Exception as e:
                print(f"扩展加载失败: {name} - {e}")

        # 按优先级排序
        self.extensions.sort(
            key=lambda e: e.get_button_config().get("priority", 0)
        )
        return self.extensions

    def get_buttons(self) -> List[dict]:
        """获取所有扩展按钮配置"""
        return [ext.get_button_config() for ext in self.extensions]
