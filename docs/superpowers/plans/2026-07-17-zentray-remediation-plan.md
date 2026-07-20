# ZenTray 补救与收口实施计划

> **日期:** 2026-07-17  
> **状态:** M1 热修 + Phase 7（v3.8 功能扩展）已落地一批实现；Phase 2–3 架构深改仍待执行  

> **前置审查:** [architecture-review-2026-07-17.md](../../architecture-review-2026-07-17.md)  
> **替代:** 本计划 supersede [归档: 2026-07-11-zentray-refactor-plan.md](../../archive/2026-07-11-zentray-refactor-plan.md) 作为进度源

**Goal:** 在现有半完成重构之上，先修正确性与产品缺口，再收口 DI/领域一致性，补测试与文档，并在稳定底座上交付 **v3.8 功能扩展**：二级分类、弹窗提醒、AI 教练风格。

**Non-goals（除非单独立项）:** MySQL 后端完整实现、独立 GTD 看板窗口、AppImage/DMG/NSIS 完整 CI 矩阵。

**依赖关系:** Phase 7 功能扩展 **建议在 M1（Phase 0–1）完成后启动**；强依赖路径/设置/托盘展示链路稳定。与 Phase 2–3 可并行时注意：分类展示与 `Scheduler.format_display_title`、设置页、Task 模型变更交叉，宜先完成 Task 7.x 的领域模型设计再动 UI。

**Tech stack:** Python 3.10+、PySide6、injector、pytest、PyInstaller。

---

## 全局约束

- 业务写路径优先经 `TaskService`（或明确的领域模块），Worker 不复制策略代码  
- 文件写必须可与后台线程安全交错（`mutate_all` / 等价锁）  
- 用户数据路径唯一：`DATA_DIR`  
- 每个 Phase 结束：`pytest tests/ -q` 全绿；涉及打包时 `./scripts/build_local.sh` 成功  
- 修改尽量小步、可回滚；不顺手大重构无关模块  

---

## Phase 0 — 文档与进度收口

**目标:** 消除「三份真相」（README / 旧 plan / 代码）。

### Task 0.1 标记旧重构计划状态

**Files:**
- Modify: `docs/superpowers/plans/2026-07-11-zentray-refactor-plan.md`（文件头）

- [ ] **Step 1:** 在旧 plan 顶部增加 banner：

```markdown
> ⚠️ **Superseded (2026-07-17)**  
> 进度与后续任务以 [2026-07-17-zentray-remediation-plan.md](./2026-07-17-zentray-remediation-plan.md) 为准。  
> 审查结论见 [architecture-review-2026-07-17.md](../../architecture-review-2026-07-17.md)。
```

- [ ] **Step 2:** 可选：按审查对照表手工把已落地 Task 勾为 `[x]`（不强制，避免与历史 commit 混淆）。

**验收:** 打开旧 plan 能立刻跳到新计划。

---

### Task 0.2 README 降噪（与代码对齐）

**Files:**
- Modify: `README.md`

- [ ] **Step 1:** 架构图改为 as-built：注明 TrayController 手写装配、Worker 在 main 接线、ScriptService 为桩。  
- [ ] **Step 2:** 项目结构删除不存在的 `core/storage.py`、标明 `extensions/` 可选/未创建。  
- [ ] **Step 3:** 安装包章节改为「当前提供：本地 `build_local.sh` → `dist/ZenTray` + tar.gz」；AppImage/dmg 移入 Future。  
- [ ] **Step 4:** 功能表：番茄钟注明「托盘可开始；中止/延长见版本说明」或修复后改回完整（与 Phase 1 联动）。  
- [ ] **Step 5:** 闪电添加注明平台权限与默认字段限制（或 Phase 1 修完后更新）。

**验收:** 新用户按 README 不会去找不存在的 CI 产物 / storage.py。

---

### Task 0.3 OpenSpec 决策（二选一，记录即可）

- [ ] **Option A:** 不用 OpenSpec → README/AGENTS 不提 openspec skills；保留空目录无妨。  
- [ ] **Option B:** 启用 → 用 `openspec` 建 change「remediation-2026-07」，链到本 plan。

**验收:** 团队约定唯一流程源。

---

## Phase 1 — 正确性热修（高 ROI）

**目标:** 不改大架构，修用户可感知与数据路径错误。

### Task 1.1 统一 `DATA_DIR` / 图标目录

**Files:**
- Modify: `zentray/resources.py`
- Modify: `zentray/config.py`（如需 re-export）
- Modify: `zentray/ui/tray.py`（LinuxBridgeTray 拷贝目标）
- Optional: 启动时迁移 `~/.local/share/zentray` → `ZenTray`

- [ ] **Step 1:** `get_user_data_dir()` 与 `config.DATA_DIR` 使用同一实现（Linux 统一 `.../ZenTray` 或统一小写，**选与现有任务数据一致的 `ZenTray`**，避免用户丢数据）。  
- [ ] **Step 2:** 增加 `ensure_app_icons()`：把 `resources/icons/*.png` 同步到 `DATA_DIR / "icons"`。  
- [ ] **Step 3:** `LinuxBridgeTray` 与 `QtStandardTray` 均使用该目录。  
- [ ] **Step 4:** 若存在旧 `~/.local/share/zentray/icons`，可复制后保留或记日志。  
- [ ] **Step 5:** 手动验证：开发模式与（可选）打包二进制下 pie 图标随进度变化。

**验收:**

```bash
python -c "from zentray.config import DATA_DIR; from zentray.resources import get_user_data_dir; assert DATA_DIR == get_user_data_dir()"
```

---

### Task 1.2 番茄钟菜单：中止 / 延长

**Files:**
- Modify: `zentray/ui/menu_builder.py`
- Modify: `zentray/ui/controller.py`（若需）
- Optional test: `tests/unit/test_menu_builder.py`

- [ ] **Step 1:** `is_pomodoro=True` 时菜单项：  
  - `stop_pomodoro` → 「中止专注」  
  - `extend_pomodoro` → 「延长 N 分钟」（N 来自 settings）  
  - 禁用或隐藏「开始专注」  
- [ ] **Step 2:** 非专注时标签使用 `duration_minutes`，禁止写死「25」。  
- [ ] **Step 3:** 手工：开始 → 菜单见中止/延长 → 延长后剩余增加 → 中止后恢复任务轮播。

**验收:** 菜单 action id 与 `COMMAND_MAP` 一致；无新回归。

---

### Task 1.3 配置向导：真正可跳过

**Files:**
- Modify: `zentray/ui/setup_wizard.py`

- [ ] **Step 1:** 欢迎页增加「跳过全部」按钮 → 写 `.setup_done` → accept/关闭。  
- [ ] **Step 2:** `reject` / 窗口关闭：同样写 marker（或二次确认「下次不再显示」）。  
- [ ] **Step 3:** 验证第二次启动不再弹窗。

**验收:** 全新 `DATA_DIR` 下点跳过，再启动无向导。

---

### Task 1.4 Frozen / 安装器 `.env` 加载

**Files:**
- Modify: `zentray/config.py`
- Modify: `installer/install_wizard.py`（优先直接写 `DATA_DIR`）

- [ ] **Step 1:** 定义加载顺序文档化：  
  1. 已有环境变量  
  2. `DATA_DIR/.env`（最高用户配置）  
  3. frozen: `Path(sys.executable).parent / ".env"`  
  4. 开发: 项目根 `.env`  
- [ ] **Step 2:** 安装器完成时写入 `DATA_DIR/.env` 与 `settings.json`，而不仅是 install dir。  
- [ ] **Step 3:** 用临时 `.env` 测 `is_notification_enabled()`。

**验收:** 模拟 install_dir `.env` 或 DATA_DIR `.env` 均可被读取（按最终设计至少 DATA_DIR 必成）。

---

### Task 1.5 设置变更后启动/停止 NightlyWorker

**Files:**
- Modify: `zentray/main.py` 或 `zentray/ui/controller.py`
- Modify: `zentray/ui/commands.py` / `SettingsCommand` 路径

- [ ] **Step 1:** 将 `NightlyJobWorker` 生命周期交给 Controller（或小型 `WorkerSupervisor`）：`start_nightly_if_needed` / `stop`。  
- [ ] **Step 2:** `apply_settings()` 内根据 `is_notification_configured()`（及可选 AI）启停。  
- [ ] **Step 3:** 启动时也走同一函数，删除 main 里分叉逻辑重复。

**验收:** 运行中配置 WxPusher 保存设置后，日志出现 worker 启动；清除配置后停止。

---

### Task 1.6 闪电添加：热键容错 + 默认可配置

**Files:**
- Modify: `zentray/services/system_utils.py` (`HotkeyListener`)
- Modify: `zentray/ui/overlay.py`
- Modify: `zentray/services/settings_manager.py`（可选字段 `quick_add.default_category/priority`）
- Modify: `zentray/main.py`

- [ ] **Step 1:** `HotkeyListener.start()` 包裹 try/except；失败打 error 日志并 `start()` 返回 False，**不**抛死主进程。  
- [ ] **Step 2:** main 中若热键失败，`renderer.show_notification` 提示用户检查权限/Wayland。  
- [ ] **Step 3:** Overlay 创建任务时默认 category/priority 读 Settings（仍可先写死到 settings 默认值）。  
- [ ] **Step 4:** （可选本 Phase）失焦关闭改为 200–300ms 延迟，避免抢焦点误关。

**验收:** 模拟 pynput 失败时应用仍进入托盘；正常环境热键仍可用。

---

### Task 1.7 Tray 探测与 Ayatana 对齐

**Files:**
- Modify: `zentray/ui/tray.py` `create_tray_backend`

- [ ] **Step 1:** 探测顺序与 `linux_tray_bridge.py` 一致：Ayatana → AppIndicator3。  
- [ ] **Step 2:** 在常见 GNOME 上确认走 LinuxBridge 而非误回退 Qt。

**验收:** 有 Ayatana 的环境选择 bridge。

---

### Task 1.8 设置页通知开关接线

**Files:**
- Modify: `zentray/ui/settings_dialog.py`

- [ ] **Step 1:** 将 `_toggle_notif_group` 连接到 `notif_enabled` 的 toggled 信号。  
- [ ] **Step 2:** 加载设置后调用一次以同步 enable 状态。

**验收:** 取消「启用推送」后 token 输入框禁用。

---

## Phase 2 — 并发与领域逻辑统一

**目标:** 数据竞争与双份业务规则清零。

### Task 2.1 `mutate_all` 进入 Repository 接口

**Files:**
- Modify: `zentray/core/repository.py`
- Modify: `zentray/repositories/file_repository.py`（已有实现则对齐签名）
- Modify: `tests/unit/test_file_repository.py`

```python
# 建议签名
def mutate_all(self, mutator: Callable[[List[Task]], bool]) -> bool:
    """锁内 read → mutator(tasks) → 若 True 则 save。返回是否有写入。"""
```

- [ ] **Step 1:** ABC 增加抽象方法。  
- [ ] **Step 2:** File 实现保持现有逻辑。  
- [ ] **Step 3:** 单测：mutator 修改后磁盘可见；返回 False 不写。  
- [ ] **Step 4:** Watcher 删除 `hasattr` 分支，直接调接口。

**验收:** `pytest tests/unit/test_file_repository.py -q`

---

### Task 2.2 TaskService 全部写路径改用 mutate/save API

**Files:**
- Modify: `zentray/services/task_service.py`
- Modify: `tests/unit/test_task_service.py`

- [ ] **Step 1:** `create_task` / `update_task` / `update_progress` / `_spawn_*` 等改为 `mutate_all` 或 `save`（单任务）在锁语义下完成。  
- [ ] **Step 2:** `mark_done` / `abandon`：archive + delete 尽量同一把锁（若 delete/archive 分文件，至少 active 文件锁内完成删除）。  
- [ ] **Step 3:** 增加「交错写入」单测：mock 或线程对同一 repo 并发 append，最终条数正确（能测则测）。

**验收:** 现有 task_service 测试全过 + 新并发语义测过。

---

### Task 2.3 周期派发单点化

**Files:**
- Modify: `zentray/services/task_service.py`（或新建 `zentray/core/periodic.py`）
- Modify: `zentray/workers/watcher.py`
- Modify: tests

- [ ] **Step 1:** 抽出 `period_prefix(periodicity, date)` 与 `spawn_due_templates(template_repo, task_repo) -> int`。  
- [ ] **Step 2:** `TaskService.create_template` 与 Watcher 均调用同一实现。  
- [ ] **Step 3:** 删除 Watcher 内重复的 Task 构造块。  
- [ ] **Step 4:** 单测：daily/weekly/monthly 前缀；同一周期不重复派发。

**验收:** 改前缀规则只改一处测试仍绿。

---

### Task 2.4 逾期惩罚迁入 Service（可选但推荐与 2.3 一起）

**Files:**
- Modify: `zentray/services/task_service.py`
- Modify: `zentray/workers/watcher.py`

- [ ] **Step 1:** `TaskService.apply_overdue_penalties() -> List[Task]`  
- [ ] **Step 2:** Watcher 只调 Service 再 emit signal。

**验收:** watcher 文件不再包含 priority 升级公式。

---

## Phase 3 — DI 与 composition root 收口

**目标:** 可测试装配；消灭 UI service locator。

### Task 3.1 单一 `bootstrap_app(app) -> AppRuntime`

**Files:**
- Modify: `zentray/dependencies.py` 或新建 `zentray/bootstrap.py`
- Modify: `zentray/main.py`

建议 `AppRuntime` 持有：

```text
controller, overlay, hotkey, watcher, nightly(optional), guard
```

- [ ] **Step 1:** 把 main 中 6–10 步装配移入 bootstrap。  
- [ ] **Step 2:** main 只负责 QApplication、日志、`app.exec()`。  
- [ ] **Step 3:** 不在模块 import 时创建难以重置的全局副作用（injector 可保留但提供 `create_injector()` 供测）。

**验收:** main.py 行数明显下降；启动行为不变。

---

### Task 3.2 Overlay / 设置注入

**Files:**
- Modify: `zentray/ui/overlay.py`
- Modify: bootstrap

- [ ] **Step 1:** `QuickAddOverlay(task_service: TaskService)` ctor 注入。  
- [ ] **Step 2:** 删除 overlay 内 `injector.get`。

**验收:** 不 import dependencies 也能构造 Overlay（单测可给 fake service）。

---

### Task 3.3 Settings 可注入

**Files:**
- Modify: `zentray/services/settings_manager.py`
- Modify: `task_service`, `pomodoro_service`, providers

- [ ] **Step 1:** 保留单例亦可，但 Service 构造函数接受可选 `settings` / 调用方传入。  
- [ ] **Step 2:** `PomodoroService` 初始 duration 来自 settings，而非仅 config 常量。  
- [ ] **Step 3:** AppModule provider 读取 settings 构造 PomodoroService。

**验收:** 改 settings.json duration 后冷启动即生效。

---

### Task 3.4 收窄或删除 `di.py` 回退

**Files:**
- Modify: `zentray/di.py`, `dependencies.py`, `pyproject.toml`

- [ ] **Step 1:** 因正式依赖已含 injector，文档标明 dev 必须装 injector。  
- [ ] **Step 2:** 删除回退 **或** 保留但加 warning 日志。  
- [ ] **Step 3:** `init_tray_renderer` 用正式 `InstanceProvider` 绑定，去掉吞异常空 pass（失败应 log）。

**验收:** `test_injector.py` 仍过。

---

### Task 3.5 Controller 不穿透 scheduler

**Files:**
- Modify: `zentray/services/task_service.py`
- Modify: `zentray/ui/controller.py`

- [ ] **Step 1:** 增加 `TaskService.advance_rotation() -> Optional[Task]`。  
- [ ] **Step 2:** Controller 只调 Service API。

**验收:** controller 无 `task_service.scheduler` 属性访问。

---

## Phase 4 — 主题功能补全

### Task 4.1 ScriptService 真执行 + 示例扩展

**Files:**
- Modify: `zentray/services/script_service.py`
- Create: `extensions/sample_echo.py`（或 `extensions/README` + sample）
- Modify: loader 默认路径文档

- [ ] **Step 1:** `execute` 使用 `subprocess`（timeout、捕获 stdout/stderr、信号回传）。  
- [ ] **Step 2:** 安全默认：仅允许 settings 白名单目录或显式注册命令。  
- [ ] **Step 3:** Sample extension 实现 `StatusBarExtension`，菜单可点。  
- [ ] **Step 4:** README 写清插件约定。

**验收:** 放置 sample 后托盘出现按钮，点击有通知/日志。

---

### Task 4.2 闪电添加快捷语法与热键热更新

**Files:**
- Modify: `zentray/ui/overlay.py`
- New: `zentray/core/quick_add_parser.py`（纯函数，易测）
- Modify: settings + bootstrap 热键 restart

- [ ] **Step 1:** 解析规则（建议）：  
  - `!高` / `!中` / `!低` 或 `!h`/`!m`/`!l` → priority  
  - `#分类名` → category  
  - 剩余为 title  
- [ ] **Step 2:** 单测解析器。  
- [ ] **Step 3:** 设置修改快捷键后 `hotkey.stop(); start(new)`。

**验收:** 输入 `!高 #生活 买菜` → 正确字段入库。

---

### Task 4.3 AI 复盘可在无推送时本地落盘

**Files:**
- Modify: `zentray/workers/nightly_job.py`
- Modify: settings（可选 `nightly.save_local`）

- [ ] **Step 1:** 复盘 Markdown 写入 `DATA_DIR/reviews/YYYY-MM-DD.md`。  
- [ ] **Step 2:** 推送失败仍保留本地文件；通知文案区分。  
- [ ] **Step 3:** 允许「仅 AI / 仅本地」策略与 Phase 1.5 生命周期一致。

**验收:** 无 WxPusher 时仍生成本地 review 文件（若启用 AI）。

---

### Task 4.4 菜单与硬编码清理

**Files:**
- Modify: `zentray/ui/menu_builder.py`

- [ ] **Step 1:** `_last_items` 改为实例属性。  
- [ ] **Step 2:** 所有时长文案来自 settings。

**验收:** 两实例 MenuBuilder 缓存互不污染（单测可选）。

---

## Phase 5 — 测试、覆盖率与构建诚实化

### Task 5.1 补关键单测

**Files (new):**
- `tests/unit/test_watcher_logic.py`（测抽离后的纯函数/Service 方法，不必跑 QThread）  
- `tests/unit/test_nightly_review.py`（mock requests）  
- `tests/unit/test_settings_manager.py`  
- `tests/unit/test_quick_add_parser.py`  
- `tests/unit/test_menu_builder.py`

- [ ] **Step 1:** 覆盖 P0/P1 行为，不追求 UI 像素。  
- [ ] **Step 2:** `pip install pytest-cov` 或 `pip install -e ".[dev]"`。  
- [ ] **Step 3:** 目标：core + services 行覆盖 ≥ 60%（对齐旧重构约束）。

```bash
venv/bin/pip install -e ".[dev]"
venv/bin/pytest tests/ -q --cov=zentray --cov-report=term-missing
```

**验收:** CI 本地命令可重复；覆盖率达标或列出豁免模块（ui/tray）。

---

### Task 5.2 构建与依赖对齐

**Files:**
- Modify: `requirements.txt`, `pyproject.toml`, `zentray.spec`, `run.sh`

- [ ] **Step 1:** `requirements.txt` 与 pyproject 主依赖一致；openai 移 optional。  
- [ ] **Step 2:** spec `hiddenimports` 补 settings/wizard/wxpusher/system_utils。  
- [ ] **Step 3:** `run.sh` 删除或隔离 legacy `notification_service` 启动。  
- [ ] **Step 4:** `./scripts/build_local.sh --clean` 成功。

**验收:** 干净 venv 按 README 可 install + build。

---

### Task 5.3（可选）单一发布物文档

- [ ] 仅维护一种 Linux 产物（tar.gz 或 AppImage 二选一），写清安装步骤。  
- [ ] 不在本 Phase 强制 GitHub Actions，除非有发布需求。

---

## Phase 6 — 可选远期（单独立项）

| 项 | 说明 |
|----|------|
| MySQLTaskRepository | 真有多端同步需求再做；需迁移与连接配置 UX |
| 独立看板窗口 | 真・GTD Board；与托盘模式并存 |
| 完整跨平台安装包矩阵 | AppImage + dmg + NSIS + CI 签名 |
| 锁屏/空闲检测 | `system_utils` 中桩函数的多平台实现 |

---

## Phase 7 — 功能扩展与体验优化（v3.8）

**目标:** 交付用户明确要求的三项能力：二级任务分类体系、任务弹窗提醒、AI 教练风格可选/可编辑。  
**前置:** 建议 M1 完成；展示链路依赖 `get_task_display_title` / settings 持久化可靠。  
**版本建议:** 功能合入后 bump `VERSION` → `3.8.0`。

### 7.0 产品规格摘要

#### F1 — 二级任务分类

| 规则 | 说明 |
|------|------|
| 一级分类 | **仅**在设置页维护（增删改排序）；任务编辑页只能**选择**已有一级，不能新建一级 |
| 二级分类 | 设置页可维护；**任务新建/编辑页也可即时添加**新二级（写入分类库，归属当前一级） |
| 启用开关 | 设置：是否开启二级分类体系；关闭时行为兼容 v3.7（仅 `category` 字符串） |
| 标题展示 | 设置：二级是否加入托盘标题前缀；一/二级之间的**分隔符**（如 `·` `/` `\|`） |
| 一级修饰符 | 设置：为一级分类选择前缀/后缀括号风格，如 `【】`、`<>`、`[]`、`（）` 或自定义左右字符 |
| 托盘示例 | 开启且展示二级时：`【工作】·需求评审 写 PRD`；仅一级：`【工作】写 PRD`；关闭二级：`工作 写 PRD` 或沿用现有 |

**数据模型建议:**

```text
# settings / categories.json（二选一，推荐独立 categories.json 便于体积）
CategorySettings:
  enabled_secondary: bool = True
  show_secondary_in_title: bool = True
  level_separator: str = "·"          # 一二级之间
  title_category_title_sep: str = " " # 分类块与任务标题之间
  primary_list: List[PrimaryCategory]

PrimaryCategory:
  id: str
  name: str                           # 如「工作」
  wrap_left: str = "【"               # 可空
  wrap_right: str = "】"
  secondaries: List[SecondaryCategory]

SecondaryCategory:
  id: str
  name: str                           # 如「需求评审」

# Task / PeriodicTemplate 字段演进
# 兼容：保留 category: str（一级显示名或 legacy）
# 新增：
#   category_primary_id: Optional[str]
#   category_secondary_id: Optional[str]
# from_dict 兼容：仅有 category 时映射到同名一级，二级为空
```

#### F2 — 弹窗提醒

| 规则 | 说明 |
|------|------|
| 任务级开关 | 新建/编辑：是否启用弹窗提醒 |
| 默认时间 | 默认 `17:00`（本地时区）；可改 HH:mm |
| 触发 | 到点后**前台弹窗**（非仅托盘气泡）；置顶模态或可操作对话框 |
| 用户操作 | 至少：更新状态（完成/进度/打开编辑）、先忽略（稍后/贪睡）、关闭本次提醒 |
| 一次性 / 每日周期 | 单次时间点即可（日期+时间 或 每天 HH:mm） |
| 非每日周期 | **可配置多次提醒**；每周任务：每个提醒可选「周几 + 时间」；每月任务：每个提醒可选「几号 + 时间」 |
| 状态持久化 | 记录 `last_fired_at` / `snooze_until`，避免同一触发窗口重复狂弹 |

**数据模型建议:**

```text
TaskReminder:
  enabled: bool = False
  # one-time / daily 简化：
  time_of_day: str = "17:00"          # HH:mm
  # 非 daily 周期多条：
  slots: List[ReminderSlot] = []      # 空则回退 time_of_day

ReminderSlot:
  # weekly: weekday 0=周一..6=周日；monthly: day_of_month 1..31
  weekday: Optional[int] = None
  day_of_month: Optional[int] = None
  time_of_day: str = "17:00"
  # 运行时
  last_fired_key: Optional[str] = None  # 如 "2026-07-17|17:00" 防重

# Task / PeriodicTemplate
#   reminder: Optional[TaskReminder]  # to_dict 嵌套
```

**运行时:** 新建 `ReminderWorker`（QTimer 每 30–60s 扫一次，或对齐整分），主线程弹 `ReminderDialog`；禁止在 worker 线程直接建窗。

#### F3 — AI 教练风格

| 规则 | 说明 |
|------|------|
| 预设风格 | 至少：`toxic` 毒舌、`gentle` 温柔、`crisp` 干练（内置 system prompt） |
| 自定义风格 | 用户可新建风格：名称 + system prompt |
| 可编辑 | 预设与自定义的 **system 提示词均可在设置中编辑**（预设可「恢复默认」） |
| 生效点 | `AIReviewService.generate_summary` 使用当前选中风格的 prompt，替换硬编码毒舌文案 |
| 存储 | `settings.json` → `ai.active_style_id` + `ai.styles: List[AIStyle]` |

```text
AIStyle:
  id: str                    # toxic / gentle / crisp / uuid
  name: str
  is_builtin: bool
  system_prompt: str

AISettings 扩展:
  active_style_id: str = "toxic"
  styles: List[AIStyle]      # 启动时 merge 内置默认（用户改过的保留）
```

---

### Task 7.1 分类领域模型与存储

**Files:**
- Create: `zentray/core/categories.py`（纯函数：校验、展示串组装、legacy 迁移）
- Modify: `zentray/core/models.py`（Task / PeriodicTemplate 字段）
- Modify: `zentray/services/settings_manager.py` 或 Create: `zentray/services/category_store.py`
- Create: `tests/unit/test_categories.py`

- [ ] **Step 1:** 定义 `PrimaryCategory` / `SecondaryCategory` / `CategorySettings` dataclass。  
- [ ] **Step 2:** 默认一级：工作、生活、学习（可调）；二级可先空或示例。  
- [ ] **Step 3:** 持久化到 `DATA_DIR/settings.json` 的 `categories` 节 **或** `DATA_DIR/categories.json`。  
- [ ] **Step 4:** `Task.category` 兼容：读写时同步 `category` 显示名 = 一级 name（归档日志仍可读）。  
- [ ] **Step 5:** 实现 `format_category_prefix(task, category_settings) -> str`：  
  - 未启用二级 → 仅一级 plain 或带 wrap  
  - 启用且 `show_secondary_in_title` → `{wrap_l}{一级}{wrap_r}{level_sep}{二级}`  
  - 二级为空 → 仅一级块  
- [ ] **Step 6:** 单测：迁移旧任务、各种开关组合下的展示串。

**验收:** 纯函数测试覆盖修饰符 `【】`/`<>`/`[]`、分隔符、关闭二级。

---

### Task 7.2 设置页：一级/二级分类管理 UI

**Files:**
- Modify: `zentray/ui/settings_dialog.py`
- Modify: `zentray/services/settings_manager.py`

- [ ] **Step 1:** 新增「分类」Tab/分组：  
  - 总开关：启用二级分类  
  - 开关：二级加入标题展示  
  - 输入：一二级分隔符、分类块与标题分隔符  
- [ ] **Step 2:** 一级列表：增删改、排序；每项可编辑 `wrap_left` / `wrap_right`（下拉预设 + 自定义）。  
  - 预设：`【】` `<>` `[]` `（）` `无`  
- [ ] **Step 3:** 选中一级后编辑其二级列表（增删改）。  
- [ ] **Step 4:** 删除一级时：确认；已引用任务的回退策略（保留 name 字符串 / 改默认一级）。  
- [ ] **Step 5:** 保存写入 store；`apply_settings` 后托盘标题立即刷新。

**验收:** 手工改修饰符与分隔符，托盘轮播标题即时变化。

---

### Task 7.3 任务对话框：选一级 + 选/加二级

**Files:**
- Modify: `zentray/ui/dialogs.py` (`TaskDialog`)
- Modify: `zentray/services/task_service.py`（create/update 传 id）
- Modify: `zentray/ui/overlay.py` / quick_add（可选：默认一级）

- [ ] **Step 1:** 一级 `QComboBox`：仅 settings 中的一级列表。  
- [ ] **Step 2:** 二级 `QComboBox`：随一级联动；若未启用二级则隐藏。  
- [ ] **Step 3:** 「添加二级…」：弹输入框 → 写入当前一级的 secondaries → 选中新建项（**不**允许在此新建一级）。  
- [ ] **Step 4:** `get_data()` 输出 `category`（一级名）+ primary/secondary id。  
- [ ] **Step 5:** 编辑已有任务时回填 id；legacy 仅 category 时按 name 匹配。

**验收:** 任务编辑可加二级；设置中可见新二级；一级无法在任务页新增。

---

### Task 7.4 托盘标题展示接入分类前缀

**Files:**
- Modify: `zentray/core/scheduler.py` 或 `task_service.get_task_display_title`
- Modify: `zentray/ui/controller.py`（确保走统一 API）

- [ ] **Step 1:** 展示标题 = `category_prefix + title_sep + (overdue_prefix?) + raw_title`。  
- [ ] **Step 2:** **禁止**把展示前缀写回 `Task.title`（沿用现有逾期前缀原则）。  
- [ ] **Step 3:** 菜单任务列表可选缩短显示（完整前缀或仅 title，产品默认：列表用短 title，托盘用完整）。  
- [ ] **Step 4:** 单测 `get_task_display_title` / format 函数。

**验收:** 轮播文本含配置的修饰符与二级；完成任务后 archive 日志仍是干净 title。

---

### Task 7.5 提醒数据模型与对话框字段

**Files:**
- Modify: `zentray/core/models.py`
- Create: `zentray/core/reminder.py`（解析、下次触发、防重 key）
- Modify: `zentray/ui/dialogs.py`
- Create: `tests/unit/test_reminder.py`

- [ ] **Step 1:** `TaskReminder` / `ReminderSlot` + Task/Template 字段；`from_dict` 缺省兼容。  
- [ ] **Step 2:** TaskDialog：Checkbox「弹窗提醒」；TimeEdit 默认 17:00。  
- [ ] **Step 3:** 周期且 `periodicity in (weekly, monthly)` 时显示「提醒计划」列表：添加多条 slot（周几/几号 + 时间）。  
- [ ] **Step 4:** `periodicity == daily` 或 one-time：单时间即可（one-time 用 deadline 日 + time，无 deadline 则仅按 clock 每天直到完成——**产品默认：one-time 在 deadline 当天或每天直到 done，需在 UI 注明**；推荐 **每天 HH:mm 直到任务消失**，实现简单）。  
- [ ] **Step 5:** 纯函数：`due_slots(now, task) -> List[slot]`、`fire_key(date, time)`。

**验收:** 单测覆盖 weekly 周三 17:00、monthly 1 号 09:00、防重。

---

### Task 7.6 ReminderWorker + 提醒弹窗交互

**Files:**
- Create: `zentray/workers/reminder_job.py`
- Create: `zentray/ui/reminder_dialog.py`
- Modify: `zentray/main.py` / bootstrap
- Modify: `zentray/ui/commands.py`（可选 action）
- Modify: `zentray/dependencies.py`（若注入 repo）

- [ ] **Step 1:** Worker 每 30–60s（或整分）扫描 `task_repo.find_active()` 中 `reminder.enabled`。  
- [ ] **Step 2:** 命中则 `Signal(task_id)` → 主线程打开 `ReminderDialog`（单实例队列：同时多任务排队）。  
- [ ] **Step 3:** 弹窗选项：  
  - **更新状态** → 打开 Progress / TaskAction / 完成  
  - **先忽略（贪睡）** → 默认 +10 / +30 / 自定义分钟，写 `snooze_until`  
  - **关闭本次** → 仅写 `last_fired_key`，本日此时段不再弹  
  - **废弃/完成**（可选快捷）  
- [ ] **Step 4:** 锁屏时策略：仍排队，解锁后展示（或跳过，settings 可选；默认排队）。  
- [ ] **Step 5:** 与番茄钟并存：提醒弹窗不强制暂停番茄，但应置顶可点。  
- [ ] **Step 6:** 设置中途改系统时间/时区：依赖本地 `datetime.now()`，文档说明。

**验收:** 改系统时间或把提醒设为下一分钟，弹窗出现且操作生效；重启后防重不连弹。

---

### Task 7.7 AI 风格预设、自定义与提示词编辑

**Files:**
- Modify: `zentray/services/settings_manager.py` (`AISettings`)
- Modify: `zentray/services/ai_review.py`
- Modify: `zentray/ui/settings_dialog.py`
- Modify: `zentray/workers/nightly_job.py`（若需展示风格名）
- Create: `zentray/services/ai_styles.py`（内置默认 prompt 常量）
- Create: `tests/unit/test_ai_styles.py`

- [ ] **Step 1:** 内置三套 prompt（毒舌 / 温柔 / 干练），id 固定。  
- [ ] **Step 2:** 启动 merge：内置缺省补齐；用户改过的同 id 不覆盖。  
- [ ] **Step 3:** 设置页 AI 区：  
  - 下拉选择当前风格  
  - 列表管理：新建自定义、删除自定义（内置不可删）  
  - 多行编辑 system prompt  
  - 「恢复此预设默认文案」按钮（仅 builtin）  
- [ ] **Step 4:** `AIReviewService.generate_summary` 使用 `active_style` 的 `system_prompt`。  
- [ ] **Step 5:** 可选：复盘报告标题带风格名（如「温柔教练锐评」）。  
- [ ] **Step 6:** mock API 单测：请求 body 含选定 system 文案。

**验收:** 切换温柔后夜间/手动触发的 API system 内容变化；自定义风格可保存重启仍在。

---

### Task 7.8 功能扩展集成测试与文档

**Files:**
- Modify: `README.md` 功能表  
- Modify: `docs/architecture-review-2026-07-17.md`（已规划节可勾选）  
- Create: `tests/unit/test_feature_migration_v38.py`（旧 json 任务/设置加载）

- [ ] **Step 1:** 旧 `active_tasks.json`（仅 category 字符串）可加载不崩。  
- [ ] **Step 2:** 旧 settings 无 categories/styles 时写入默认。  
- [ ] **Step 3:** README：二级分类、弹窗提醒、AI 风格三节简短说明。  
- [ ] **Step 4:** `VERSION = 3.8.0`；`pytest` + 可选 `build_local.sh`。

**验收:** 迁移用例 + 全量单测绿；README 与行为一致。

---

### Phase 7 建议实施顺序（功能内）

```
7.1 分类模型 ─┬─► 7.2 设置 UI ─► 7.3 任务对话框 ─► 7.4 托盘标题
              │
7.5 提醒模型 ─┴─► 7.6 ReminderWorker + 弹窗
7.7 AI 风格（可与分类并行）
7.8 迁移/文档/版本号
```

---

## 建议执行顺序与里程碑

| 里程碑 | 包含 | 可交付价值 |
|--------|------|------------|
| **M1** | Phase 0 + Phase 1 | 路径/菜单/向导/env/热键/nightly 热启可用 |
| **M2** | Phase 2 | 数据竞争与双逻辑消除 |
| **M3** | Phase 3 | 架构可测、DI 诚实 |
| **M4** | Phase 4 + 5 | 功能补全 + 质量门禁 |
| **M5** | Phase 7（可与 M2–M4 部分交错；建议 M1 后） | **二级分类 + 弹窗提醒 + AI 风格** → v3.8 |

**推荐:** 首周 M1 → 随后可开 **M5 功能扩展分支**（用户价值高）；架构深改（M2–M3）与 M5 并行时，以 `categories` / `reminder` 纯模块减少冲突。

---

## 每任务通用完成定义（DoD）

1. 代码修改完成且无调试残留  
2. 相关单测通过；全量 `pytest tests/ -q` 绿  
3. 若触达路径/打包：手动或 `build_local.sh` 验证  
4. 本文件对应 `- [ ]` → `- [x]`  
5. 审查报告中对应问题 ID 在 PR/提交说明中引用（如 `fix P0-1`）；功能项引用 `F1/F2/F3`  

---

## 风险登记

| 风险 | 缓解 |
|------|------|
| 统一 DATA_DIR 导致用户找不到旧 icons | 选保留 `ZenTray`；迁移脚本/拷贝 |
| mutate_all 改动面大 | 先接口+File，再逐方法改 Service |
| 热键在 Wayland 无法全局 | 失败降级 + 菜单「快速添加」入口（可加） |
| bootstrap 大挪移引入启动回归 | 保持行为对照清单（向导/单例/worker/热键） |
| 分类字段迁移破坏旧任务 JSON | 保留 `category` 字符串；id 可选；from_dict 宽松 |
| 提醒弹窗打断专注/多任务连弹 | 队列 + 贪睡 + last_fired 防重；番茄中仍可关 |
| 用户编辑 AI prompt 导致空/过长 | 校验非空、长度上限、恢复默认 |
| 一级修饰符 + 逾期前缀叠加过长 | 托盘截断策略（后缀省略）；设置可关二级展示 |

---

## 快速对照：问题 / 功能 → 任务

| 审查 ID / 功能 | 任务 |
|----------------|------|
| P0-1 路径分裂 | 1.1 |
| P0-2 并发写 | 2.1, 2.2 |
| P0-3 周期双写 | 2.3 |
| P1-4 番茄钟菜单 | 1.2 |
| P1-5 安装 env | 1.4 |
| P1-6 nightly 生命周期 | 1.5 |
| P1-7 闪电添加 | 1.6, 4.2 |
| P1-8 向导跳过 | 1.3 |
| P1-9/10 图标与 tray | 1.1, 1.7 |
| P2 文档/测试/扩展 | 0.*, 4.1, 5.* |
| 架构 DI | 3.* |
| **F1 二级分类** | **7.1 – 7.4** |
| **F2 弹窗提醒** | **7.5 – 7.6** |
| **F3 AI 教练风格** | **7.7** |
| **F1–F3 收口** | **7.8** |

---

*执行时建议使用 subagent-driven-development 或按 Phase 开分支；完成 M1 后再评估 M2 与 M5 的并行策略。*
