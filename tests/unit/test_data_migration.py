"""跨设备迁移：导出 / 导入替换 round-trip。"""
from __future__ import annotations

import json
import zipfile
from pathlib import Path

from zentray.services import data_migration as mig


def _seed(data_dir: Path) -> None:
    data_dir.mkdir(parents=True, exist_ok=True)
    (data_dir / "active_tasks.json").write_text(
        json.dumps([{"id": "t1", "title": "hello"}], ensure_ascii=False),
        encoding="utf-8",
    )
    (data_dir / "periodic_templates.json").write_text("[]", encoding="utf-8")
    (data_dir / "settings.json").write_text(
        json.dumps({"appearance": {"theme": "dark", "autostart": False}}),
        encoding="utf-8",
    )
    (data_dir / "activity.jsonl").write_text(
        '{"time":"2026-01-01T00:00:00","category":"task","action":"create"}\n',
        encoding="utf-8",
    )
    arch = data_dir / "archive"
    arch.mkdir()
    (arch / "2026-01-01.log").write_text("done\n", encoding="utf-8")
    rev = data_dir / "reviews"
    rev.mkdir()
    (rev / "2026-01-01.md").write_text("# review\n", encoding="utf-8")
    (data_dir / ".env").write_text("AI_API_KEY=secret\n", encoding="utf-8")


def test_export_default_excludes_env(tmp_path: Path):
    root = tmp_path / "data"
    _seed(root)
    result = mig.create_export_zip(data_dir=root)
    assert result.ok, result.message
    assert result.path
    with zipfile.ZipFile(result.path) as zf:
        names = zf.namelist()
        assert "manifest.json" in names
        assert "active_tasks.json" in names
        assert ".env" not in names
        manifest = json.loads(zf.read("manifest.json"))
        assert manifest["format"] == "zentray-backup"
        assert "env" not in manifest["include"]


def test_export_can_include_env(tmp_path: Path):
    root = tmp_path / "data"
    _seed(root)
    result = mig.create_export_zip(["tasks", "env"], data_dir=root)
    assert result.ok
    with zipfile.ZipFile(result.path) as zf:
        assert ".env" in zf.namelist()


def test_import_replace_roundtrip(tmp_path: Path):
    src = tmp_path / "src"
    dst = tmp_path / "dst"
    _seed(src)
    _seed(dst)
    # 修改目标，导入后应被覆盖
    (dst / "active_tasks.json").write_text(
        json.dumps([{"id": "old", "title": "old"}], ensure_ascii=False),
        encoding="utf-8",
    )

    exported = mig.create_export_zip(
        ["tasks", "settings", "archive"],
        data_dir=src,
    )
    assert exported.ok

    imported = mig.import_replace(
        exported.path,
        ["tasks", "settings", "archive"],
        data_dir=dst,
        make_safety_backup=True,
    )
    assert imported.ok, imported.message
    assert imported.safety_backup
    tasks = json.loads((dst / "active_tasks.json").read_text(encoding="utf-8"))
    assert tasks[0]["id"] == "t1"
    settings = json.loads((dst / "settings.json").read_text(encoding="utf-8"))
    assert settings["appearance"]["theme"] == "dark"
    assert (dst / "archive" / "2026-01-01.log").read_text(encoding="utf-8") == "done\n"


def test_pack_archive(tmp_path: Path):
    root = tmp_path / "data"
    _seed(root)
    result = mig.pack_archive(data_dir=root)
    assert result.ok
    with zipfile.ZipFile(result.path) as zf:
        assert any(n.startswith("archive/") for n in zf.namelist())


def test_list_include_options():
    opts = mig.list_include_options()
    keys = {o["key"] for o in opts}
    assert "tasks" in keys and "env" in keys
    env = next(o for o in opts if o["key"] == "env")
    assert env["sensitive"] is True
    assert env["default"] is False
