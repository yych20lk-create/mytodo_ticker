# zentray/ui/menu_builder.py
"""
菜单构建器 —— 负责动态生成托盘右键菜单结构。

将原 TrayManager.update_menu_state() 中的菜单构建逻辑
独立出来，支持扩展按钮的动态注册。
"""
from typing import List


class MenuBuilder:
    """托盘右键菜单构建器"""

    # 菜单项状态缓存，避免重复渲染相同菜单
    _last_items = None

    def build_status_menu(
        self, task_exists: bool, is_pomodoro: bool
    ) -> List[dict]:
        """构建状态更新子菜单"""
        return [
            {
                "id": "done",
                "label": "✅ 完成",
                "enabled": task_exists and not is_pomodoro,
            },
            {
                "id": "abandon",
                "label": "❌ 废弃",
                "enabled": task_exists and not is_pomodoro,
            },
        ]

    def build_task_list_submenu(
        self, tasks, current_task
    ) -> List[dict]:
        """构建任务列表子菜单"""
        submenu = []

        if tasks:
            submenu.append({
                "id": "label_active",
                "label": "【当前活跃任务】",
                "enabled": False,
            })
            for t in tasks:
                prefix = "★ " if current_task and t.id == current_task.id else ""
                submenu.append({
                    "id": f"task_action_{t.id}",
                    "label": f"{prefix}{t.title}",
                })
        else:
            submenu.append({
                "id": "no_tasks",
                "label": "暂无待办任务",
                "enabled": False,
            })

        return submenu

    def build_extension_buttons(
        self, extensions: list
    ) -> List[dict]:
        """构建扩展按钮菜单项"""
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

    def build_main_menu(
        self,
        task_exists: bool,
        is_pomodoro: bool,
        tasks: list,
        current_task,
        extensions: list,
    ) -> List[dict]:
        """构建完整的主菜单"""
        status_submenu = self.build_status_menu(task_exists, is_pomodoro)
        task_list_submenu = self.build_task_list_submenu(tasks, current_task)
        ext_buttons = self.build_extension_buttons(extensions)

        items = [
            {
                "id": "status_update",
                "label": "🔄 状态更新",
                "submenu": status_submenu,
                "enabled": task_exists and not is_pomodoro,
            },
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
        ]

        if task_list_submenu:
            items.append({
                "id": "task_list",
                "label": "📋 任务列表",
                "submenu": task_list_submenu,
                "enabled": not is_pomodoro,
            })

        items.append("separator")
        items.append({
            "id": "new",
            "label": "➕ 新建任务",
            "enabled": not is_pomodoro,
        })
        items.append({
            "id": "pomodoro",
            "label": "🍅 专注 25 分钟" if not is_pomodoro else "🍅 专注中...",
            "enabled": not is_pomodoro,
        })

        if ext_buttons:
            items.append("separator")
            items.extend(ext_buttons)

        items.append("separator")
        items.append({"id": "quit", "label": "❌ 退出程序"})

        return items

    def should_update(self, items: List[dict]) -> bool:
        """检查菜单是否需要更新（避免重复渲染）"""
        if items != self._last_items:
            self._last_items = items
            return True
        return False
