# 脚本与服务插件运行时 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 在托盘提供可开关的「脚本与服务」插件入口；script 执行时抢占任务轮播，结束后恢复；插件经 plugin.yaml 校验门禁后才加载。

**Architecture:** `zentray/plugins/` 承载 manifest 校验、目录扫描与 QProcess 运行时；Controller 用 `display_mode`（tasks/pomodoro/ops）互斥抢占；MenuBuilder 注入插件子菜单；SettingsManager 增加 `OpsSettings`。

**Tech Stack:** Python 3.10+、PySide6（QProcess/Signal）、pytest、PyYAML（若未安装则用 json 清单——优先 stdlib 仅 YAML：用简单手写或 `yaml` 若已在依赖中；**采用 JSON 清单 `plugin.json` 作为实现简化？** 规格写的是 plugin.yaml —— 加依赖 `PyYAML` 或手写最小 YAML 子集。**实现：用 JSON `plugin.json` 与规格兼容字段，同时支持 `plugin.yaml` 若 PyYAML 可用；为降低依赖，MVP 只支持 `plugin.json`，文档注明与规格等价字段。** 重新对齐规格：规格要求 plugin.yaml。检查 requirements —— 无 PyYAML。实现用 **stdlib 可解析的 JSON 文件名 `plugin.json`，并在 validate 中同时接受 `plugin.yaml` 若存在 pyyaml；最简：只实现 `plugin.json` 并在 PLUGIN_SPEC 与设计备注「MVP 使用 plugin.json（字段同设计 doc）」。**  

为严格贴合已确认设计，**添加 `pyyaml` 到 dependencies**。

**Branch:** `feature/plugin-scripts-services`（必须在此分支开发，禁止推到 main 直接改）

## Global Constraints

- 入口 C3：菜单固定项 + 设置左键行为；不实现副指示器
- 入口 P2：插件根内任意可执行文件
- 总开关默认关闭
- 托盘日志截断 50 字符
- 同 id 用户插件覆盖内置
- 与番茄钟互斥（运行 script 时拒绝番茄，番茄中拒绝 script）
- 同时仅一个 script

---

### Task 1: Manifest 模型与校验

**Files:**
- Create: `zentray/plugins/__init__.py`
- Create: `zentray/plugins/models.py`
- Create: `zentray/plugins/manifest.py`
- Create: `tests/unit/test_plugin_manifest.py`
- Create: `tests/fixtures/plugins/sample-script/plugin.yaml`
- Create: `tests/fixtures/plugins/sample-script/run.sh`
- Create: `tests/fixtures/plugins/sample-service/plugin.yaml`
- Create: `tests/fixtures/plugins/sample-service/service.sh`
- Create: `tests/fixtures/plugins/bad-escape/plugin.yaml`（entry 含 `..`）
- Modify: `pyproject.toml` / `requirements.txt` 增加 `PyYAML`

**Produces:** `load_manifest(path) -> PluginManifest`, `validate_plugin_dir(path) -> ValidationResult`

- [ ] 实现 models + manifest + fixtures + 单测
- [ ] `pytest tests/unit/test_plugin_manifest.py -v` 通过
- [ ] Commit

### Task 2: PluginLoader 扫描

**Files:**
- Create: `zentray/plugins/loader.py`
- Create: `tests/unit/test_plugin_loader.py`

**Produces:** `PluginLoader.scan(dirs) -> list[LoadedPlugin]`（仅校验通过）

- [ ] 实现 + 测试用户覆盖内置 id
- [ ] Commit

### Task 3: PluginRuntime 执行与进度

**Files:**
- Create: `zentray/plugins/protocol.py`
- Create: `zentray/plugins/runtime.py`
- Create: `tests/unit/test_plugin_protocol.py`
- Create: `tests/unit/test_plugin_runtime.py`

**Produces:** `PluginRuntime` QObject，信号 `log_line`, `progress`, `script_finished`, `busy_changed`；方法 `run_script`, `service_cmd`, `is_busy`

- [ ] 解析 PROGRESS/LOG 行；QProcess 或 subprocess 线程
- [ ] 超时与互斥
- [ ] Commit

### Task 4: OpsSettings + 设置持久化

**Files:**
- Modify: `zentray/services/settings_manager.py`
- Create: `tests/unit/test_ops_settings.py`
- Modify: Vue settings 若有通用保存结构（`web/src/views/Settings.vue` 增加一节或 API）

**Produces:** `OpsSettings` 字段：enabled, load_bundled, load_user, user_plugins_dir, confirm_before_run, tray_left_click

- [ ] 读写 settings.json
- [ ] Commit

### Task 5: 菜单 + Controller 抢占轮播

**Files:**
- Modify: `zentray/ui/menu_builder.py`
- Modify: `zentray/ui/controller.py`
- Modify: `zentray/ui/commands.py`（或 controller 内处理 ops.*）
- Modify: `zentray/dependencies.py`
- Modify: `zentray/services/script_service.py`（委托 Runtime 或删除引用）

**Produces:** 菜单「脚本与服务」；display_mode ops 抢占；结束后恢复

- [ ] 接线
- [ ] 手动/单测能覆盖的部分
- [ ] Commit

### Task 6: validate CLI + 文档

**Files:**
- Create: `scripts/validate_plugin.py`
- Create: `docs/plugins/PLUGIN_SPEC.md`
- Create: `bundled_plugins/.gitkeep`

- [ ] CLI 可校验 fixtures
- [ ] Commit

---

## Spec coverage

| Spec 项 | Task |
|---------|------|
| 菜单入口 C3 | 5 |
| 左键设置 | 4–5 |
| script 抢占轮播 | 3, 5 |
| service start/stop/status | 3, 5 |
| plugin.yaml + 校验门禁 | 1, 2, 6 |
| P2 executable | 1, 3 |
| 设置开关默认关 | 4 |
| 与番茄互斥 | 5 |
| 副指示器 | 不做（预留 host 可选注释） |
