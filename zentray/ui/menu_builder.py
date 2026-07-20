# zentray/ui/menu_builder.py
"""菜单构建器 —— 动态生成托盘右键菜单结构。"""
from typing import List, Optional, Any


class MenuBuilder:
    """托盘右键菜单构建器"""

    def __init__(self):
        self._last_items = None

    def build_extension_buttons(self, extensions: list) -> List[dict]:
        if not extensions:
            return []
        items = []
        for ext in extensions:
            config = ext.get_button_config()
            items.append({
                "id": f"extension_{ext.__class__.__name__}",
                "label": f"🔧 {config.get('tooltip', '脚本')}",
            })
        return items

    def build_ops_submenu(self, plugins: list = None) -> Optional[dict]:
        """构建「脚本与服务」子菜单；无插件时仍返回入口（空提示）。"""
        plugins = plugins or []
        scripts = []
        services = []
        for p in plugins:
            m = p.manifest
            if m.type.value == "script":
                scripts.append({
                    "id": f"ops.script.{m.id}",
                    "label": m.name,
                    "enabled": True,
                })
            else:
                services.append({
                    "id": f"ops.service.{m.id}",
                    "label": m.name,
                    "submenu": [
                        {"id": f"ops.service.{m.id}.start", "label": "▶ 启动"},
                        {"id": f"ops.service.{m.id}.stop", "label": "⏹ 停止"},
                        {"id": f"ops.service.{m.id}.status", "label": "ℹ 状态"},
                    ],
                })

        submenu: List[dict] = []
        if scripts:
            submenu.append({"id": "ops._hdr_scripts", "label": "📜 脚本", "enabled": False})
            submenu.extend(scripts)
        if services:
            if submenu:
                submenu.append("separator")
            submenu.append({"id": "ops._hdr_services", "label": "🔧 服务", "enabled": False})
            submenu.extend(services)
        if not submenu:
            submenu.append({
                "id": "ops._empty",
                "label": "（无可用插件）",
                "enabled": False,
            })
        submenu.append("separator")
        submenu.append({"id": "ops.open_last_log", "label": "📄 上次运行日志"})
        return {"id": "ops_menu", "label": "🧩 脚本与服务", "submenu": submenu}

    def build_main_menu(
        self,
        task_exists: bool,
        is_pomodoro: bool,
        tasks: list = None,
        current_task=None,
        extensions: list = None,
        pomodoro_minutes: Optional[int] = None,
        extend_minutes: Optional[int] = None,
        ops_enabled: bool = False,
        ops_plugins: list = None,
        ops_busy: bool = False,
    ) -> List[dict]:
        """
        构建主菜单。

        注意：菜单结构不依赖轮播当前标题/当前任务星标，避免轮播时整菜单重建闪动。
        tasks/current_task 参数保留兼容，不再用于生成子菜单。
        """
        if pomodoro_minutes is None or extend_minutes is None:
            try:
                from zentray.services.settings_manager import SettingsManager

                sm = SettingsManager()
                if pomodoro_minutes is None:
                    pomodoro_minutes = sm.pomodoro.duration_minutes
                if extend_minutes is None:
                    extend_minutes = sm.pomodoro.extend_minutes
            except Exception:
                pomodoro_minutes = pomodoro_minutes or 25
                extend_minutes = extend_minutes or 10

        extensions = extensions or []
        ext_buttons = self.build_extension_buttons(extensions)

        items = [
            {
                "id": "progress",
                "label": "📊 更新进度",
                "enabled": task_exists and not is_pomodoro,
            },
            {
                "id": "edit",
                "label": "📝 编辑查看",
                "enabled": task_exists and not is_pomodoro,
            },
            {
                "id": "task_list",
                "label": "📋 任务列表",
                "enabled": not is_pomodoro,
            },
        ]

        if ops_enabled:
            ops_menu = self.build_ops_submenu(ops_plugins)
            if ops_menu:
                # 运行中禁用脚本子项：在 submenu 层简单标记
                if ops_busy:
                    for it in ops_menu.get("submenu") or []:
                        if isinstance(it, dict) and str(it.get("id", "")).startswith(
                            "ops.script."
                        ):
                            it["enabled"] = False
                items.insert(0, ops_menu)
                items.insert(1, "separator")

        items.append("separator")
        items.append({
            "id": "new",
            "label": "➕ 新建任务",
            "enabled": not is_pomodoro,
        })
        items.append({
            "id": "periodic_manage",
            "label": "🔁 周期任务管理",
            "enabled": not is_pomodoro,
        })

        if is_pomodoro:
            items.append({
                "id": "stop_pomodoro",
                "label": "⏹ 中止专注",
                "enabled": True,
            })
            items.append({
                "id": "extend_pomodoro",
                "label": f"⏱ 延长 {extend_minutes} 分钟",
                "enabled": True,
            })
        else:
            items.append({
                "id": "pomodoro",
                "label": f"🍅 专注 {pomodoro_minutes} 分钟",
                "enabled": not ops_busy,
            })

        if ext_buttons:
            items.append("separator")
            items.extend(ext_buttons)

        items.append("separator")
        items.append({
            "id": "history",
            "label": "📜 历史记录",
            "enabled": not is_pomodoro,
        })
        items.append({"id": "settings", "label": "⚙️ 设置"})
        items.append({"id": "quit", "label": "❌ 退出程序"})

        return items

    def should_update(self, items: List[dict]) -> bool:
        if items != self._last_items:
            self._last_items = items
            return True
        return False
