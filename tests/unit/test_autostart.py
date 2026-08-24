"""开机自启服务基础测试（不依赖真实写注册表/桌面项时的路径解析）。"""
from __future__ import annotations

from zentray.services import autostart as autostart_svc


def test_resolve_launch_target_returns_strings():
    exe, workdir = autostart_svc.resolve_launch_target()
    assert isinstance(exe, str) and exe
    assert isinstance(workdir, str) and workdir


def test_status_shape():
    st = autostart_svc.status()
    assert "enabled" in st
    assert "launch_target" in st
    assert "platform" in st
