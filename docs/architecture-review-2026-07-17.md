# ZenTray 架构与功能完整性审查报告

> **日期:** 2026-07-17  
> **版本:** v3.7.0  
> **仓库:** `workspace/private/my_todo`  
> **背景:** 2026-07-11 DI/服务化重构中途中断；旧计划 checkbox 未更新，代码已半落地。  
> **配套计划:** [2026-07-17 补救修改计划](./superpowers/plans/2026-07-17-zentray-remediation-plan.md)

---

## 1. 审查范围与方法

### 1.1 范围

| 维度 | 内容 |
|------|------|
| 架构 | DI、分层、composition root、全局状态、接口 seam |
| 结构 | 目录树、README 宣称 vs 磁盘实况 |
| 构建 | `build_local.sh`、`zentray.spec`、`installer.spec`、依赖声明 |
| 主题功能 | GTD、番茄钟、周期任务、闪电添加、向导、设置、WxPusher、AI 复盘、扩展、跨平台托盘 |
| 测试 | `tests/unit/*` 与模块覆盖缺口 |
| 历史文档 | `docs/superpowers/plans/2026-07-11-zentray-refactor-plan.md`、`specs/2026-07-11-zentray-refactor-design.md`、`openspec/` |

### 1.2 方法

- 通读 `zentray/` 全部 Python 源码（约 4.9k LOC）与 `tests/`、构建脚本  
- 运行 `pytest tests/ -q`：**29 passed**  
- 运行 `./scripts/build_local.sh`：**成功**（`dist/ZenTray` ~69M）  
- 运行时核对 Linux 数据路径：`DATA_DIR` = `~/.local/share/ZenTray`，`get_user_data_dir()` = `~/.local/share/zentray`  
- 对照 README 架构图与 2026-07-11 重构计划（12 Task 全部仍为 `- [ ]`）

### 1.3 总判断

重构目标（拆分 God-object、Repository seam、命令模式、可测服务层）**方向正确且已完成大半**。当前主要债务是：

1. **文档/计划与代码脱节**  
2. **半完成 DI + 第二套 composition root**  
3. **若干产品级缺口**（番茄钟菜单、路径分裂、安装器 env、闪电添加稳健性等）  
4. **并发写路径不统一**（Watcher 用 `mutate_all`，TaskService 仍用 find_all + save_all）

**不建议推倒重来**，应在现有分层上做「收口 + 热修 + 统一领域逻辑」。

---

## 2. 当前架构（As-Built）

### 2.1 分层实况

```
[main.py  composition root #1]
   │
   ├─ setup_logging / validate_config / setup_wizard
   ├─ SingleInstanceGuard
   ├─ init_tray_controller(app)  ────────────┐
   │                                         │
   ├─ QuickAddOverlay ── injector.get(TaskService)  # service locator
   ├─ HotkeyListener(HOTKEY_QUICK_ADD)       │
   ├─ WatcherWorker(repos)  ── 直连仓库，绕过 TaskService
   └─ NightlyJobWorker(repo) if notification  # 启动时快照

[dependencies.py  composition root #2 / DI 子集]
   injector = Injector([AppModule()])
   AppModule 绑定:
     Scheduler, TaskRepository→FileTaskRepository,
     PeriodicTemplateRepository→FilePeriodicTemplateRepository,
     TaskService, PomodoroService, ScriptService(stub),
     MenuBuilder, ExtensionLoader
   未绑定 / 手写:
     TrayController, TrayRenderer(全局 _tray_renderer),
     SettingsManager(单例), NotificationClient, AIReviewService,
     workers, overlay, dialogs
```

### 2.2 运行时主路径

| 场景 | 路径 |
|------|------|
| 托盘轮播 | `TrayController.poll_timer` → `task_service.scheduler.get_next()` → `TrayRenderer` |
| 菜单操作 | backend `action_received` → `handle_action` → `commands.dispatch` → Service |
| 任务持久化 | `TaskService` → `TaskRepository`（JSON + `file_io` 锁/原子写） |
| 后台维护 | `WatcherWorker` 直接 mutate 仓库 → `tasks_updated` → `reload_data` |
| 闪电添加 | 热键 → Overlay → `TaskService.create_task` → `task_added` → reload |

### 2.3 已存在的有效 Seam

| Seam | 类型 | 实现 |
|------|------|------|
| `TaskRepository` | ABC | `FileTaskRepository` only |
| `PeriodicTemplateRepository` | ABC | `FilePeriodicTemplateRepository` only |
| `ActionCommand` | ABC | `commands.py` 多命令 |
| `StatusBarExtension` | ABC | 插件目录（**磁盘上目录缺失**） |
| `TrayImplementation` | 伪接口（非 ABC） | `LinuxBridgeTray` / `QtStandardTray` |

### 2.4 架构优点

- 旧 `TrayManager` 已拆成 Controller / Renderer / MenuBuilder / Services  
- 文件存储有路径级 RLock + temp+replace 原子写（`core/file_io.py`）  
- 命令模式替代巨型 if-elif，扩展 action 前缀清晰  
- 领域单测 fixture 正确隔离 `DATA_DIR`（`tests/conftest.py`）  
- 核心 GTD 闭环（创建→轮播→进度→完成/归档）可跑通  

### 2.5 架构问题（结构性）

| # | 问题 | 证据 | 影响 |
|---|------|------|------|
| A1 | 双 composition root | `main.py` + `init_tray_controller` | 依赖图不可见、难测、易漏接线 |
| A2 | SettingsManager 全局单例 + 服务内 service-locator | `task_service._refresh_scheduler`、`pomodoro.extend`、AI/WxPusher | 配置真源分散 |
| A3 | Worker 绕过 TaskService 写业务规则 | `watcher.py` 逾期/周期派发 | 规则双份、竞态 |
| A4 | TaskService RMW 未统一 `mutate_all` | `create_task`/`update_*` 用 find_all+save_all | 与 Watcher 并发可能丢更新 |
| A5 | Controller 穿透访问 `task_service.scheduler` | `controller.py` `_on_poll_tick` | 破坏服务边界 |
| A6 | Overlay 用全局 injector | `overlay.py` L27 | 偏离 ctor 注入 |
| A7 | 自定义 `di.py` 与真实 injector 双轨 | `dependencies.py` try/import | 能力不一致；`pyproject` 已强制 injector |
| A8 | TrayRenderer 模块级全局 | `_tray_renderer` | DI 不完整 |

---

## 3. 项目结构实况 vs 文档

### 3.1 实际包结构（精简）

```
my_todo/
├── pyproject.toml / requirements.txt / zentray.spec / installer.spec
├── scripts/build_local.sh
├── resources/icons/          # pie_*.png, app_icon.png
├── zentray/ui/styles/main.qss
├── installer/                # 独立安装向导
├── zentray/
│   ├── main.py, config.py, resources.py, dependencies.py, di.py
│   ├── core/   models, repository, scheduler, file_io
│   ├── repositories/
│   ├── services/
│   ├── ui/     controller, commands, tray, dialogs, overlay, wizard, settings, extensions/
│   └── workers/
├── tests/unit/               # 仅 unit，无 integration
└── docs/
```

### 3.2 README / 旧文档宣称但缺失或过时

| 宣称 | 实况 |
|------|------|
| `core/storage.py` 旧版兼容 | **源码已删除**（仅可能残留 pyc） |
| `extensions/` 用户插件目录 | **目录不存在** |
| `MySQLTaskRepository`「后续」 | 仅 `NotImplementedError`，无文件 |
| AppImage / dmg / Setup.exe + GHA CI | **不存在**；仅 `build_local.sh` → 二进制 + tar.gz |
| `scripts/build_linux.sh` 等平台脚本 | **不存在** |
| 所有服务由 injector 管理 | Settings/AI/通知/Worker/Controller 多数在外 |
| OpenSpec 变更流程 | `openspec/changes` 空、`specs` 空 |

### 3.3 依赖声明不一致

| 文件 | 问题 |
|------|------|
| `requirements.txt` | 固定包含 `openai`，代码实际用 `requests` 调 chat completions |
| `pyproject.toml` optional `ai` | 未在运行路径使用 openai SDK |
| optional `mysql` | 无实现仍声明 |
| dev 声明 `pytest-cov` | 当前 venv 未装，`--cov` 不可用 |

---

## 4. 构建与打包审查

### 4.1 本地构建链路（可用）

```
./scripts/build_local.sh
  → 语法检查 zentray/**/*.py
  → 确保 icons
  → PyInstaller zentray.spec
  → dist/ZenTray
  → dist/releases/ZenTray-{VERSION}-x86_64.tar.gz
可选: --installer → installer.spec → ZenTrayInstaller
```

**实测:** 构建成功；警告：`libtiff.so.5` 缺失（Qt TIFF 插件，通常可忽略）；Linux 忽略 `.ico`。

### 4.2 构建问题

| # | 问题 | 建议 |
|---|------|------|
| B1 | README 安装包形态与仓库产物不一致 | 文档对齐 tar.gz/本地二进制，或补真实 AppImage 流水线 |
| B2 | `zentray.spec` datas 含 styles/icons/bridge；部分模块靠隐式 import | 显式补 `settings_manager`、`setup_wizard`、`wxpusher` 等 hiddenimports 更稳 |
| B3 | 安装器写入 `install_dir/.env`，运行时只加载 project root + `DATA_DIR/.env` | **冻结运行凭据常失效**（见 P0-5） |
| B4 | ~~`run.sh` 仍启动外部 `notification_service`~~ | **已清理 (2026-07-17)**：run.sh/bat 仅启动主程序 |
| B5 | 无 CI | 发布质量依赖人工 |

---

## 5. 主题功能完整性矩阵

| 功能 | 判定 | 证据路径 | 说明 |
|------|------|----------|------|
| GTD 任务（托盘菜单式） | **完整** | `task_service.py`, `dialogs.py`, `commands.py`, `scheduler.py` | 非独立看板 UI；README「看板」易误解 |
| 任务归档 | **完整** | `FileTaskRepository.archive` → `archive/YYYY-MM-DD.log` | 文本日志，非结构化 |
| 周期任务 | **完整** | `create_template` + `WatcherWorker` | 派发逻辑重复 |
| 逾期惩罚 | **完整** | `watcher.py` 提优先级 + 顺延 deadline | 业务在 Worker 内 |
| 番茄钟计时 | **部分** | `pomodoro_service.py`, `controller.py` | 开始/结束 OK；**中止/延长菜单未接线** |
| 闪电添加 | **部分** | `overlay.py`, `HotkeyListener`, `main.py` | 主路径可通，UX/稳健性不足（见 P1-7） |
| 配置向导 | **部分** | `setup_wizard.py` | 文案「跳过全部」无按钮；关窗可能不写 `.setup_done` |
| 设置对话框 | **基本完整** | `settings_dialog.py`, `settings_manager.py` | 通知组 toggle 未连接等小缺陷 |
| WxPusher 推送 | **完整*** | `wxpusher.py`, `notification.py` | *需凭据；无成功路径单测 |
| AI 夜间复盘 | **部分** | `ai_review.py`, `nightly_job.py` | 依赖启动时通知已配置；中途开启不启 worker |
| 扩展系统 | **桩** | `extensions/interface.py`, `loader.py` | 无插件目录；ScriptService.execute 桩 |
| 跨平台托盘 | **部分** | `tray.py`, `linux_tray_bridge.py` | AppIndicator 探测与 bridge 偏好不一致；Qt 图标路径坏 |
| MySQL 存储 | **缺失** | `dependencies.py` | `STORAGE_BACKEND=mysql` 启动即炸 |
| 安装器 | **部分** | `installer/*` | UI 向导在；env 落地路径与运行时不一致 |

---

## 6. 问题清单与修改建议

### 6.1 P0 — 正确性 / 数据与运行时断裂

#### P0-1 Linux 用户数据目录分裂

| 项 | 内容 |
|----|------|
| **现象** | 任务/设置/日志 → `~/.local/share/ZenTray`；托盘图标同步 → `~/.local/share/zentray` |
| **根因** | `config._user_data_dir("ZenTray")` vs `resources.get_user_data_dir()` 使用小写 `zentray` |
| **影响** | 进度 pie 图标错位或缺失；用户资产分散两目录 |
| **建议** | 单一函数导出 `DATA_DIR`；`resources` 只 re-export；一次性迁移旧目录（若存在） |

#### P0-2 TaskService 与 Watcher 并发写不安全

| 项 | 内容 |
|----|------|
| **现象** | Watcher 用 `mutate_all`（锁内 RMW）；TaskService CRUD 多为 `find_all` → 改 → `save_all`，无跨操作原子语义 |
| **根因** | 重构未把 `mutate_all` 提升到接口；Service 未统一走该 API |
| **影响** | UI 操作与每分钟维护交错时可能丢更新 |
| **建议** | ABC 增加 `mutate_all`；Service 全部写路径经此方法；单测模拟交错写入 |

#### P0-3 周期实例派发双实现

| 项 | 内容 |
|----|------|
| **现象** | `TaskService._spawn_template_instance_if_needed` 与 `WatcherWorker` 周期块逻辑复制 |
| **影响** | 前缀规则/字段漂移风险；测试需双份 |
| **建议** | 领域方法只保留在 `TaskService`（或独立 `PeriodicDispatch` 模块）；Watcher 只调用服务 API |

### 6.2 P1 — 产品功能缺口

#### P1-4 番茄钟：命令有、菜单无

| 项 | 内容 |
|----|------|
| **证据** | `commands.py` 注册 `stop_pomodoro` / `extend_pomodoro`；`menu_builder.py` 专注中仅禁用「专注 25 分钟」 |
| **建议** | 专注中菜单改为：中止 / 延长 N 分钟；标签用 `SettingsManager.pomodoro.duration_minutes` 而非写死 25 |

#### P1-5 安装器 / 冻结运行 `.env` 路径

| 项 | 内容 |
|----|------|
| **现象** | 安装器写安装目录旁 `.env`；`config.py` 只读项目根 + `DATA_DIR/.env` |
| **建议** | frozen 时额外加载 `Path(sys.executable).parent / ".env"`；或安装器直接写 `DATA_DIR/.env` + `settings.json` |

#### P1-6 夜间 Worker 生命周期

| 项 | 内容 |
|----|------|
| **现象** | `main.py` 仅在启动时 `features["notification"]` 为真才 `start()`；设置中途开启不启动；仅 AI 无推送也不跑 |
| **建议** | Controller/`apply_settings` 统一 start/stop Nightly；允许「仅本地生成复盘文件」模式 |

#### P1-7 闪电添加：部分可用，稳健性与表达力不足

| 子问题 | 证据 | 建议 |
|--------|------|------|
| 字段写死 `工作`/`medium` | `overlay.py` `save_and_close` | 默认值读 Settings；可选快捷语法 `!高 #生活 标题`（Phase 4） |
| 热键启动无容错 | `HotkeyListener.start()` 直接 `GlobalHotKeys` | try/except + 日志 + 托盘提示；失败不阻断主程序 |
| 热键不热更新 | `main.py` 启动绑一次 | 设置变更后 restart listener |
| 失焦即关 | `changeEvent` ActivationChange → hide | 可选延迟关闭或确认；保留草稿到下次打开 |
| Service locator | `injector.get(TaskService)` | ctor 注入 TaskService（Phase 3） |
| 平台权限 | README 提 macOS 辅助功能；Linux Wayland 上 pynput 常失败 | 文档 + 运行时探测与降级说明 |

#### P1-8 配置向导「跳过全部」名不副实

| 项 | 内容 |
|----|------|
| **现象** | 文案存在「跳过全部」；无对应按钮；关闭窗口可能不写 `.setup_done` → 每次启动再弹 |
| **建议** | 增加 Skip 按钮；`reject`/`closeEvent` 也写入 marker（或明确「稍后配置」语义） |

#### P1-9 Qt 托盘路径不拷贝图标

| 项 | 内容 |
|----|------|
| **现象** | 仅 `LinuxBridgeTray` 拷贝 icons；且目标目录错误（见 P0-1）。`QtStandardTray` 读 `DATA_DIR/icons` 时常为空 |
| **建议** | 启动时统一 `ensure_icons(DATA_DIR/icons)`，所有 backend 共用 |

#### P1-10 AppIndicator 探测与 Bridge 不一致

| 项 | 内容 |
|----|------|
| **现象** | 探测只试 `AppIndicator3`；bridge 优先 `AyatanaAppIndicator3` |
| **影响** | 部分 GNOME 用户被错误回退到 Qt，丢失顶栏文本滚动体验 |
| **建议** | 探测顺序与 bridge 一致（Ayatana → AppIndicator3） |

### 6.3 P2 — 质量、文档、可维护性

| ID | 问题 | 建议 |
|----|------|------|
| P2-1 | 无 watcher / nightly / settings / UI 单测 | Phase 5 按风险补测 |
| P2-2 | README 架构图过度理想化 | 改为 as-built + 目标态两节 |
| P2-3 | 2026-07-11 plan 全未勾选但代码已部分完成 | 标记 superseded，改以本报告 + 补救计划为准 |
| P2-4 | ScriptService / extensions 桩 | 实现 subprocess 或 README 标明「未实现」 |
| P2-5 | MySQL 营销过度 | 文档改为 future work；启动时友好报错而非硬崩 |
| P2-6 | MenuBuilder `_last_items` 类属性 | 改为实例属性 |
| P2-7 | 设置 UI 通知组 toggle 未 connect | 接上 `_toggle_notif_group` |
| P2-8 | 周期实例 `deadline=""`，对话框默认 deadline 未进入派发 | 模板增加默认 deadline 策略或文档说明 |
| P2-9 | `requirements.txt` 与 `pyproject` / 实际 import 不一致 | 对齐；openai 改为 optional |
| P2-10 | OpenSpec 空壳 | 启用则写第一条 change；否则 README 去掉暗示 |

---

## 7. 与 2026-07-11 重构计划对照

旧计划 12 个 Task（checkbox 全未勾选）与代码对照：

| Task | 计划内容 | 代码状态 |
|------|----------|----------|
| 1 TaskRepository 接口 | 是 | **已实现** `core/repository.py` |
| 2 FileTaskRepository | 是 | **已实现**（且增强了 lock/`mutate_all`） |
| 3 PeriodicTemplateRepository | 是 | **已实现** |
| 4 FilePeriodicTemplateRepository | 是 | **已实现** |
| 5 Injector AppModule | 是 | **部分**（无完整 UI 图） |
| 6 TaskService | 是 | **已实现**（RMW 未完成统一） |
| 7 PomodoroService | 是 | **已实现**（菜单接线缺） |
| 8 TrayController/Renderer/MenuBuilder | 是 | **已实现** |
| 9 Command 模式 | 是 | **已实现** |
| 10 main.py 用 injector | 是 | **部分**（半 DI） |
| 11 pytest 框架 | 是 | **已实现** 29 tests；覆盖不足 |
| 12 Worker 注入 Repository | 是 | **已实现** 注入 repo；**未**走 TaskService |

结论：计划文档已失效为进度源。后续以 [补救计划](./superpowers/plans/2026-07-17-zentray-remediation-plan.md) 为准。

---

## 8. 建议原则（后续修改应遵守）

1. **单一 composition root**  
   启动装配集中一处；禁止 UI 组件 `injector.get`。

2. **业务规则只经 Service**  
   Worker/UI 不直接编码逾期/派发策略；可调 Service 或共享领域模块。

3. **写路径统一经仓储事务式 API**  
   接口层提供 `mutate_all`（或等价单元），File/未来 MySQL 都实现。

4. **配置单一真源**  
   运行时以 `SettingsManager`（或注入的 Settings 对象）为准；`config` 只负责路径与启动引导。

5. **路径与资源单一入口**  
   `DATA_DIR` / icons / `.env` 规则写死一处，开发态与 frozen 态表格化文档化。

6. **深度模块优先**  
   例如「周期派发」一个小接口 + 深实现，避免 Watcher/Service 两处浅复制。

7. **文档跟随代码**  
   README 功能表与架构图只描述已交付；未来项单独 Future 节。

8. **测试跟着风险**  
   并发写、周期派发、settings 优先级、图标路径、热键失败降级 — 优先于再堆接口空测。

---

## 9. 建议优先级总览

```
P0 路径统一 + 并发写安全 + 周期逻辑单点
  ↓
P1 番茄钟菜单 / 安装 env / nightly 生命周期 / 闪电添加稳健性 / 向导跳过 / 图标与 tray 探测
  ↓
P2 文档收口 + 测试补齐 + 扩展真实现 or 降级声明 + 依赖对齐
  ↓
P3 / M5 功能扩展（v3.8）二级分类 + 弹窗提醒 + AI 风格
  ↓
P4（可选立项）MySQL / 真看板 UI / AppImage CI
```

---

## 9.1 已规划功能扩展（v3.8 / Phase 7）

> 详细任务与数据模型见 [补救计划 Phase 7](./superpowers/plans/2026-07-17-zentray-remediation-plan.md#phase-7--功能扩展与体验优化v38)。  
> **建议在 M1 热修完成后实施**，避免与路径/设置债务叠加。

| ID | 能力 | 要点 | 计划任务 |
|----|------|------|----------|
| **F1** | 二级任务分类 | 一级仅设置页编辑；二级可在设置与任务编辑中添加；托盘标题前缀；一级 wrap 修饰符（`【】`/`<>` 等）；开关：启用二级、二级是否进标题、一二级分隔符 | 7.1–7.4 |
| **F2** | 弹窗提醒 | 任务级启用 + 默认 17:00；到点模态弹窗（更新状态 / 忽略贪睡 / 关闭本次）；非每日周期支持多 slot（周几或每月几号 + 时间） | 7.5–7.6 |
| **F3** | AI 教练风格 | 预设毒舌/温柔/干练；可自定义风格；system 提示词可编辑；复盘 API 使用当前风格 | 7.7 |

**与现状差距（实现时需改动的热点）:**

| 现状 | 扩展后 |
|------|--------|
| `Task.category: str` 单层 | primary/secondary id + 分类库；兼容旧字符串 |
| `Scheduler.format_display_title` 仅逾期前缀 | 叠加可配置分类前缀块（不写回 title） |
| 无提醒字段 / worker | `TaskReminder` + `ReminderWorker` + `ReminderDialog` |
| `AIReviewService` 硬编码毒舌 system prompt | `AISettings.styles` + `active_style_id` |

**依赖/风险:** 分类与标题展示依赖统一的 `get_task_display_title`；提醒弹窗必须主线程；旧 JSON 迁移必须 `from_dict` 宽松。

---

## 10. 相关文件索引

| 类别 | 路径 |
|------|------|
| 入口 | `zentray/main.py` |
| DI | `zentray/dependencies.py`, `zentray/di.py` |
| 配置/路径 | `zentray/config.py`, `zentray/resources.py` |
| 领域 | `zentray/core/{models,repository,scheduler,file_io}.py` |
| 服务 | `zentray/services/*.py` |
| UI | `zentray/ui/*.py` |
| Worker | `zentray/workers/*.py` |
| 构建 | `scripts/build_local.sh`, `zentray.spec`, `installer.spec` |
| 测试 | `tests/unit/*`, `tests/conftest.py` |
| 旧计划（归档） | `docs/archive/2026-07-11-zentray-refactor-plan.md` |
| 旧设计（归档） | `docs/archive/2026-07-11-zentray-refactor-design.md` |
| 补救计划 | `docs/superpowers/plans/2026-07-17-zentray-remediation-plan.md` |
| v3.8 功能扩展 | 同补救计划 **Phase 7**（F1 分类 / F2 提醒 / F3 AI 风格） |

---

*本报告含审查建议与已确认的 v3.8 功能规格索引；代码实施以配套补救计划 checkbox 为准。*
