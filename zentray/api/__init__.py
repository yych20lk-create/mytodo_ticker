"""本地 HTTP API：供 Vue 前端调用，业务逻辑仍走 TaskService / SettingsManager。"""

from zentray.api.server import LocalApiServer, get_api_server

__all__ = ["LocalApiServer", "get_api_server"]
