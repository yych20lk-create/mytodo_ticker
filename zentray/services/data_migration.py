"""跨设备数据迁移：导出 / 导入（替换）/ 归档打包。"""
from __future__ import annotations

import json
import logging
import shutil
import zipfile
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Dict, Iterable, List, Optional, Sequence, Set

from zentray.config import (
    ACTIVE_TASKS_FILE,
    ARCHIVE_DIR,
    DATA_DIR,
    PERIODIC_TEMPLATES_FILE,
    VERSION,
)

logger = logging.getLogger(__name__)

FORMAT_NAME = "zentray-backup"
FORMAT_VERSION = 1

# include 键 → 相对 DATA_DIR 的路径（文件或目录）
INCLUDE_MAP: Dict[str, str] = {
    "tasks": "active_tasks.json",
    "templates": "periodic_templates.json",
    "settings": "settings.json",
    "history": "activity.jsonl",
    "archive": "archive",
    "reviews": "reviews",
    "env": ".env",
    "plugins": "plugins",
    "schedule": "ai_schedule_state.json",
    "holidays": "holidays.json",
}

DEFAULT_INCLUDE: List[str] = [
    "tasks",
    "templates",
    "settings",
    "history",
    "archive",
    "reviews",
]

EXPORTS_DIR_NAME = "exports"


@dataclass
class MigrationResult:
    ok: bool
    message: str = ""
    path: Optional[str] = None
    size: int = 0
    include: List[str] = field(default_factory=list)
    safety_backup: Optional[str] = None
    details: Dict[str, str] = field(default_factory=dict)

    def to_dict(self) -> dict:
        return {
            "ok": self.ok,
            "message": self.message,
            "path": self.path,
            "size": self.size,
            "include": self.include,
            "safety_backup": self.safety_backup,
            "details": self.details,
        }


def exports_dir(data_dir: Optional[Path] = None) -> Path:
    root = Path(data_dir) if data_dir else DATA_DIR
    d = root / EXPORTS_DIR_NAME
    d.mkdir(parents=True, exist_ok=True)
    return d


def normalize_include(include: Optional[Sequence[str]]) -> List[str]:
    if not include:
        return list(DEFAULT_INCLUDE)
    seen: Set[str] = set()
    out: List[str] = []
    for raw in include:
        key = str(raw or "").strip().lower()
        if key in INCLUDE_MAP and key not in seen:
            seen.add(key)
            out.append(key)
    return out or list(DEFAULT_INCLUDE)


def _stamp() -> str:
    return datetime.now().strftime("%Y%m%d_%H%M%S")


def _add_path_to_zip(zf: zipfile.ZipFile, src: Path, arcname: str) -> None:
    if src.is_file():
        zf.write(src, arcname)
        return
    if src.is_dir():
        empty = True
        for child in sorted(src.rglob("*")):
            if child.is_file():
                empty = False
                rel = child.relative_to(src)
                zf.write(child, f"{arcname}/{rel.as_posix()}")
        if empty:
            # 保留空目录占位
            zf.writestr(f"{arcname}/", "")


def create_export_zip(
    include: Optional[Sequence[str]] = None,
    *,
    data_dir: Optional[Path] = None,
    prefix: str = "zentray-backup",
) -> MigrationResult:
    root = Path(data_dir) if data_dir else DATA_DIR
    keys = normalize_include(include)
    out_dir = exports_dir(root)
    out_path = out_dir / f"{prefix}-{_stamp()}.zip"
    details: Dict[str, str] = {}
    packed: List[str] = []

    try:
        with zipfile.ZipFile(out_path, "w", compression=zipfile.ZIP_DEFLATED) as zf:
            for key in keys:
                rel = INCLUDE_MAP[key]
                src = root / rel
                if not src.exists():
                    details[key] = "missing"
                    continue
                _add_path_to_zip(zf, src, rel)
                packed.append(key)
                details[key] = "ok"
            manifest = {
                "format": FORMAT_NAME,
                "format_version": FORMAT_VERSION,
                "app_version": VERSION,
                "created_at": datetime.now().isoformat(timespec="seconds"),
                "include": packed,
                "requested_include": keys,
            }
            zf.writestr(
                "manifest.json",
                json.dumps(manifest, ensure_ascii=False, indent=2),
            )
        size = out_path.stat().st_size
        return MigrationResult(
            ok=True,
            message="导出成功",
            path=str(out_path),
            size=size,
            include=packed,
            details=details,
        )
    except Exception as e:
        logger.exception("导出失败")
        if out_path.exists():
            try:
                out_path.unlink()
            except OSError:
                pass
        return MigrationResult(ok=False, message=f"导出失败: {e}", include=keys)


def pack_archive(
    *,
    data_dir: Optional[Path] = None,
) -> MigrationResult:
    """仅打包 archive/ 目录。"""
    root = Path(data_dir) if data_dir else DATA_DIR
    return create_export_zip(
        ["archive"],
        data_dir=root,
        prefix="zentray-archive",
    )


def read_manifest(zip_path: Path) -> Optional[dict]:
    try:
        with zipfile.ZipFile(zip_path, "r") as zf:
            if "manifest.json" in zf.namelist():
                return json.loads(zf.read("manifest.json").decode("utf-8"))
    except Exception:
        logger.exception("读取 manifest 失败")
    return None


def import_replace(
    zip_path: str | Path,
    include: Optional[Sequence[str]] = None,
    *,
    data_dir: Optional[Path] = None,
    make_safety_backup: bool = True,
) -> MigrationResult:
    """
    替换模式导入：按 include 覆盖 DATA_DIR 对应文件。
    导入前默认对当前数据做安全备份。
    """
    root = Path(data_dir) if data_dir else DATA_DIR
    src = Path(zip_path).expanduser().resolve()
    if not src.is_file():
        return MigrationResult(ok=False, message=f"备份文件不存在: {src}")

    try:
        with zipfile.ZipFile(src, "r") as zf:
            names = set(zf.namelist())
    except zipfile.BadZipFile:
        return MigrationResult(ok=False, message="不是有效的 zip 文件")
    except Exception as e:
        return MigrationResult(ok=False, message=f"无法打开备份: {e}")

    manifest = read_manifest(src)
    if manifest and manifest.get("format") not in (None, FORMAT_NAME):
        return MigrationResult(
            ok=False,
            message=f"不支持的备份格式: {manifest.get('format')}",
        )

    # 决定导入键：请求 ∩ 包内实际存在
    if include:
        keys = normalize_include(include)
    elif manifest and manifest.get("include"):
        keys = normalize_include(manifest["include"])
    else:
        keys = list(DEFAULT_INCLUDE)

    available: List[str] = []
    for key in keys:
        rel = INCLUDE_MAP[key]
        if rel in names or any(n.startswith(rel.rstrip("/") + "/") for n in names):
            available.append(key)
    if not available:
        return MigrationResult(ok=False, message="备份中没有可导入的数据项", include=keys)

    safety_path: Optional[str] = None
    if make_safety_backup:
        safety = create_export_zip(
            available,
            data_dir=root,
            prefix="zentray-pre-import",
        )
        if safety.ok:
            safety_path = safety.path
        else:
            logger.warning("安全备份失败，仍继续导入: %s", safety.message)

    details: Dict[str, str] = {}
    try:
        with zipfile.ZipFile(src, "r") as zf:
            for key in available:
                rel = INCLUDE_MAP[key]
                dest = root / rel
                # 清理目标
                if dest.is_file():
                    dest.unlink()
                elif dest.is_dir():
                    shutil.rmtree(dest)

                # 提取
                members = [
                    n
                    for n in zf.namelist()
                    if n == rel or n.startswith(rel.rstrip("/") + "/")
                ]
                if not members:
                    details[key] = "missing_in_zip"
                    continue

                # 单文件
                if rel in members and not rel.endswith("/"):
                    dest.parent.mkdir(parents=True, exist_ok=True)
                    with zf.open(rel) as src_f, open(dest, "wb") as out_f:
                        shutil.copyfileobj(src_f, out_f)
                    details[key] = "replaced_file"
                    continue

                # 目录
                dest.mkdir(parents=True, exist_ok=True)
                for name in members:
                    if name.endswith("/"):
                        (root / name).mkdir(parents=True, exist_ok=True)
                        continue
                    target = root / name
                    target.parent.mkdir(parents=True, exist_ok=True)
                    with zf.open(name) as src_f, open(target, "wb") as out_f:
                        shutil.copyfileobj(src_f, out_f)
                details[key] = "replaced_dir"

        return MigrationResult(
            ok=True,
            message="导入成功（替换）。建议刷新任务列表或重启应用。",
            path=str(src),
            include=available,
            safety_backup=safety_path,
            details=details,
        )
    except Exception as e:
        logger.exception("导入失败")
        return MigrationResult(
            ok=False,
            message=f"导入失败: {e}",
            include=available,
            safety_backup=safety_path,
            details=details,
        )


def list_include_options() -> List[dict]:
    """前端勾选列表。"""
    defaults = set(DEFAULT_INCLUDE)
    labels = {
        "tasks": "活跃任务",
        "templates": "周期模板",
        "settings": "应用配置",
        "history": "操作历史",
        "archive": "任务归档",
        "reviews": "AI 复盘报告",
        "env": ".env 密钥（含 API Key）",
        "plugins": "用户插件",
        "schedule": "AI 调度状态",
        "holidays": "节假日配置",
    }
    return [
        {
            "key": k,
            "label": labels.get(k, k),
            "path": rel,
            "default": k in defaults,
            "sensitive": k == "env",
        }
        for k, rel in INCLUDE_MAP.items()
    ]
