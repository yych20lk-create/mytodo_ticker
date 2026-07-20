"""进程内文件读写工具：线程锁 + 原子写。"""
from __future__ import annotations

import json
import os
import shutil
import threading
from pathlib import Path
from typing import Any, Dict, List

_locks_guard = threading.Lock()
_path_locks: Dict[str, threading.RLock] = {}


def path_lock(filepath: Path | str) -> threading.RLock:
    """同一路径共享一把可重入锁（支持同一线程内 load+save）。"""
    p = Path(filepath)
    try:
        key = str(p.resolve())
    except OSError:
        key = str(p.absolute())
    with _locks_guard:
        if key not in _path_locks:
            _path_locks[key] = threading.RLock()
        return _path_locks[key]


def load_json_list(filepath: Path) -> List[dict]:
    """读取 JSON 列表；损坏时备份并返回空列表。"""
    lock = path_lock(filepath)
    with lock:
        if not filepath.exists():
            return []
        try:
            with open(filepath, "r", encoding="utf-8") as f:
                data = json.load(f)
            if isinstance(data, list):
                return data
            return []
        except json.JSONDecodeError:
            backup = filepath.with_suffix(filepath.suffix + ".bak")
            try:
                shutil.copy(filepath, backup)
            except OSError:
                pass
            return []
        except OSError:
            return []


def save_json_list(filepath: Path, data: List[Any]) -> None:
    """原子写入 JSON 列表（temp + os.replace）。"""
    lock = path_lock(filepath)
    with lock:
        filepath.parent.mkdir(parents=True, exist_ok=True)
        tmp = filepath.with_suffix(filepath.suffix + ".tmp")
        with open(tmp, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2, ensure_ascii=False)
            f.flush()
            os.fsync(f.fileno())
        os.replace(tmp, filepath)


def append_text_line(filepath: Path, line: str) -> None:
    """线程安全追加一行文本。"""
    lock = path_lock(filepath)
    with lock:
        filepath.parent.mkdir(parents=True, exist_ok=True)
        with open(filepath, "a", encoding="utf-8") as f:
            f.write(line)
