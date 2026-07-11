# zentray/ui/extensions/interface.py
"""
状态栏扩展接口定义。

所有需要在状态栏中注册自定义按钮的扩展都应实现此接口。
"""
from abc import ABC, abstractmethod
from typing import List


class StatusBarExtension(ABC):
    """状态栏扩展接口"""

    @abstractmethod
    def get_button_config(self) -> dict:
        """
        返回按钮配置

        Returns:
            dict: {"icon": str, "tooltip": str, "priority": int}
        """
        pass

    @abstractmethod
    def handle_click(self) -> None:
        """按钮点击回调"""
        pass

    @abstractmethod
    def get_logs(self) -> List[str]:
        """返回日志列表（用于状态栏展示）"""
        pass
