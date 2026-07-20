"""微信 WxPusher 推送服务封装。"""
from __future__ import annotations

import logging
from typing import Any, Dict, Optional

import requests

logger = logging.getLogger(__name__)

API_URL = "https://wxpusher.zjiecode.com/api/send/message"


class WxPusherService:
    """调用 WxPusher HTTP API 发送消息。"""

    def __init__(self, app_token: str = "", uid: str = ""):
        self.app_token = app_token or ""
        self.uid = uid or ""

    @classmethod
    def from_settings(cls) -> "WxPusherService":
        from zentray.services.settings_manager import SettingsManager

        n = SettingsManager().notification
        return cls(app_token=n.wxpusher_app_token, uid=n.wxpusher_uid)

    def is_configured(self) -> bool:
        return bool(self.app_token and self.uid)

    def send_message(
        self,
        content: str,
        summary: str = "ZenTray 通知",
        content_type: int = 3,
    ) -> Dict[str, Any]:
        """
        发送消息。

        content_type: 1=文本, 2=html, 3=markdown
        """
        if not self.is_configured():
            return {"code": -1, "msg": "WXPUSHER token or UID is missing."}

        payload = {
            "appToken": self.app_token,
            "content": content,
            "summary": summary[:100] if summary else "ZenTray 通知",
            "contentType": content_type,
            "uids": [self.uid],
        }
        try:
            resp = requests.post(API_URL, json=payload, timeout=10)
            data = resp.json()
            if not isinstance(data, dict):
                return {"code": -1, "msg": f"unexpected response: {data}"}
            return data
        except Exception as e:
            logger.warning("WxPusher send failed: %s", e)
            return {"code": -1, "msg": str(e)}
