# tests/unit/test_notification.py
from zentray.services.wxpusher import WxPusherService
from zentray.services.notification import NotificationClient


def test_wxpusher_missing_credentials():
    svc = WxPusherService(app_token="", uid="")
    assert not svc.is_configured()
    result = svc.send_message("hello")
    assert result["code"] == -1


def test_notification_client_unconfigured():
    client = NotificationClient(app_token="", uid="")
    result = client.send("t", "c")
    assert result["status"] == "error"
