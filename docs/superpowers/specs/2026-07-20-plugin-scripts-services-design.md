# 设计：托盘「脚本与服务」插件运行时

| 字段 | 值 |
|------|-----|
| 状态 | 待用户评审 |
| 日期 | 2026-07-20 |
| 分支 | `feature/plugin-scripts-services` |
| 版本目标 | 随 ZenTray 次版本功能迭代（不绑定具体版本号） |
| 已确认选项 | **C3**（菜单入口 + 预留副指示器）+ **P2**（任意可执行入口） |

## 1. 问题与目标

### 1.1 问题

用户需要在顶栏托盘中**随时**打开一个入口，选择并运行本机脚本或服务（例如网络切换、清缓存、邮箱相关操作等）。执行过程要在托盘上看到进度/日志；结束后回到任务轮播。能力可在设置中开关。脚本与服务以**插件**形式交付，项目定义范式，**测试通过后**才装入应用。

### 1.2 非目标（MVP）

- 不在核心代码中实现具体业务剧本（VPN/邮箱等属于插件内容）。
- 不做插件商店、远程下载安装。
- 不做可视化编排器。
- MVP **不实现**第二枚顶栏图标（副 Indicator）；仅在架构上预留（C3）。
- 不在插件运行时内存放或代填账号密码。

### 1.3 成功标准

1. 设置开启后，托盘菜单有固定入口「脚本与服务」，可列出已加载且通过校验的插件。
2. 执行 `script` 类型插件时，任务轮播被进度日志抢占；结束后恢复轮播并通知结果。
3. `service` 类型插件可启动/停止/查询状态（由插件入口约定实现）。
4. 插件须符合 `plugin.yaml` 规范；校验失败不得出现在菜单。
5. 设置可关闭整功能；关闭后不加载插件、不显示入口。

## 2. 用户体验

### 2.1 入口（C3）

| 阶段 | 行为 |
|------|------|
| **MVP** | 托盘主菜单固定项：**「🧩 脚本与服务」** 子菜单（可按 type 分组：脚本 / 服务）。 |
| **设置增强（MVP 建议包含）** | 「左键点击托盘」：`任务菜单`（默认）\| `脚本与服务`，便于「随时一点就进列表」。 |
| **预留（非 MVP）** | 可选第二枚 AppIndicator / 托盘图标专用于本功能（C2）；运行时通过 `TrayOpsHost` 抽象，避免写死单 indicator。 |

### 2.2 脚本执行与轮播抢占

```
空闲：任务标题轮播 + 优先级/番茄图标
  │ 用户启动 script 插件
  ▼
抢占：停止任务轮播推进；右侧文案显示进度/日志（截断）；
      左侧可用进度饼图或固定 ops 图标（实现时二选一，默认进度饼按步骤或时间粗估）
  │ 进程结束
  ▼
恢复：系统通知成功/失败；写 activity / 本地运行日志；恢复任务轮播
```

- 与**番茄钟**互斥：script 运行中不可启动番茄；番茄进行中启动 script 时提示并拒绝（或设置「允许打断番茄」，MVP 固定为拒绝）。
- 同时仅允许**一个** script 运行；服务启停可与 script 互斥（MVP：script 运行中禁用服务操作）。

### 2.3 服务交互

子菜单示例：

```
🧩 脚本与服务
  ├── 📜 脚本
  │     ├── 清网络缓存
  │     └── …
  └── 🔧 服务
        ├── 某代理服务 ▶ 启动 / ⏹ 停止 / ℹ 状态
        └── …
```

- 启停后短暂托盘提示，**不**长期抢占轮播（与 script 区分）。
- `status` 结果写入通知或子菜单标签刷新（如「运行中」）。

### 2.4 设置页（「脚本与服务」）

| 配置项 | 类型 | 默认 | 说明 |
|--------|------|------|------|
| 启用脚本与服务 | bool | `false` | 总开关 |
| 加载内置插件 | bool | `true` | `bundled_plugins/` |
| 加载用户插件目录 | bool | `true` | 默认 `DATA_DIR/plugins` |
| 用户插件目录 | path | 见上 | 可改 |
| 执行前确认 | bool | `true` | 启动 script / 危险服务操作前确认框 |
| 左键点击托盘 | enum | `task_menu` | `task_menu` \| `ops_menu` |
| （预留）启用副指示器 | bool | `false` | 非 MVP，UI 可隐藏 |

## 3. 架构

### 3.1 模块划分

```
zentray/
  plugins/                    # 插件运行时（核心）
    models.py                 # PluginManifest, PluginType, RunResult
    manifest.py               # 解析与校验 plugin.yaml
    loader.py                 # 扫描目录、过滤未通过校验的插件
    runtime.py                # 进程执行、进度解析、互斥（取代/吸收 ScriptService）
    protocol.py               # stdout 进度协议常量
    host.py                   # TrayOpsHost：菜单/抢占/通知，便于日后副指示器
  services/
    script_service.py         # 废弃或薄封装 → 委托 runtime（保持 DI 平滑迁移）
  ui/
    menu_builder.py           # 增加「脚本与服务」子树
    controller.py             # 连接 runtime 信号与轮播抢占
bundled_plugins/              # 可选：随包分发且已过 CI 的插件（可先空）
docs/plugins/
  PLUGIN_SPEC.md              # 对外范式文档（实现时与本设计同步）
scripts/
  validate_plugin.py          # CLI：校验单个插件目录
tests/plugins/                # 规范符合性测试与 runtime 单测
```

### 3.2 数据流

```
设置启用?
  → PluginLoader.scan(bundled + user dir)
  → 每个插件: parse manifest → validate → (fail: log + skip)
  → MenuBuilder 生成子菜单
用户选择 script
  → 确认? → PluginRuntime.start_script(plugin_id)
  → QProcess/subprocess 执行 entry
  → stdout 行 → progress/log 信号 → Controller 抢占文案
  → exit → finished 信号 → 通知 + 恢复轮播
```

### 3.3 与旧代码关系

| 现有 | 处理 |
|------|------|
| `ScriptService` 桩 | 迁移逻辑到 `plugins/runtime.py`；Controller 改连 runtime；`ScriptService` 可删或 facade |
| `StatusBarExtension` / `ExtensionLoader` | **不作为本功能载体**；文档标明废弃或预留第三方 UI 扩展，避免双插件体系 |
| `activity_log` | `category=system`, `action=plugin_run` 等 |

## 4. 插件范式（规范）

### 4.1 目录结构

```text
<plugin-root>/
  plugin.yaml          # 必填
  README.md            # 建议
  # 入口由 manifest.entry 指定，可为任意可执行文件路径（相对 plugin-root）
  # 可选: tests/ 供作者自测；合入 bundled 时仓库 CI 必跑 validate
```

### 4.2 `plugin.yaml` 字段

| 字段 | 必填 | 说明 |
|------|------|------|
| `id` | 是 | 唯一 ID：`[a-z0-9]+(-[a-z0-9]+)*` |
| `name` | 是 | 菜单显示名 |
| `version` | 是 | semver 字符串 |
| `type` | 是 | `script` \| `service` |
| `api_version` | 是 | 整数；MVP 仅支持 `1` |
| `entry` | 是 | **P2**：相对插件根的可执行路径（如 `bin/run`、`run.sh`、`tool.exe`）。运行前须 `chmod` 可执行位检查（Unix） |
| `args` | 否 | 追加参数列表（字符串数组） |
| `workdir` | 否 | 工作目录；默认插件根目录 |
| `timeout_sec` | 否 | 仅 script；默认 300；`0` 表示不限制（不推荐） |
| `env` | 否 | 额外环境变量 map（禁止覆盖危险变量见安全） |
| `description` | 否 | 设置页/ tooltip |
| `service.commands` | type=service 时必填 | 见下 |

**service.commands（api_version=1）**

通过**同一 `entry`**，用首个参数区分动作（规范强制）：

```yaml
type: service
entry: ./service.sh
# 运行时调用:
#   entry start
#   entry stop
#   entry status
```

`status` 约定：

- 退出码 `0` 且 stdout 首行（trim）为 `running` \| `stopped` \| `unknown` 之一；或
- 退出码 `0` = running，`1` = stopped，`2` = unknown（二选一写进 PLUGIN_SPEC，**采用 stdout 首行优先**，无匹配再回退退出码）。

### 4.3 进度协议（script，stdout）

插件应向 **stdout** 按行输出 UTF-8 文本。运行时逐行处理：

| 行格式 | 含义 |
|--------|------|
| `PROGRESS <current>/<total> <message>` | 步骤进度；托盘优先显示 `name current/total message` |
| `LOG <message>` 或其它非空行 | 一般日志；托盘显示截断后的 message |
| `RESULT ok` / `RESULT fail <reason>` | 可选；便于明确结果文案 |

- stderr 合并采集，写入运行日志文件；默认不刷托盘（避免噪音），可设置「显示 stderr」（二期）。
- 退出码：`0` 成功，非 0 失败（即使有 `RESULT ok` 也以退出码为准，冲突时失败并打日志）。

### 4.4 校验门禁（「符合才会应用」）

**`validate_plugin(path) -> ValidationResult`**

至少检查：

1. 存在 `plugin.yaml` 且 YAML/字段合法。  
2. `id`/`type`/`api_version`/`entry` 合法。  
3. `entry` 路径在插件根内（禁止 `..` 逃逸），文件存在。  
4. Unix：文件有可执行权限（或 shebang 脚本可被解释器执行——P2 下要求 `os.access(X_OK)` 或对 `.py` 等允许「解释器+路径」扩展；**MVP：要求 entry 本身可执行**，作者用 `#!/usr/bin/env bash` 包装任意逻辑）。  
5. `type=service` 时文档化 commands 约定存在（无需探测 start/stop 真执行）。  
6. `id` 在一次加载中不与其它插件冲突（后扫描覆盖策略：用户目录覆盖同 id 内置，并打警告）。

**应用到程序的路径：**

| 路径 | 门禁 |
|------|------|
| 合入 `bundled_plugins/` | PR/CI 必须 `validate_plugin` + 可选 smoke（不强制真跑 VPN） |
| 用户目录插件 | 启动/刷新时校验；失败不进菜单，设置页可列「未通过：原因」 |
| 开发中 | `python scripts/validate_plugin.py path/to/plugin` |

### 4.5 安全（P2 收紧）

- 仅从配置的插件根扫描，不执行清单外路径。  
- `entry` 必须解析为插件目录**之内**的绝对路径。  
- 不默认 `shell=True`；使用 argv 列表执行。  
- `env` 禁止覆盖：`PATH` 可追加策略二期；MVP 允许插件自定义 env 但记录审计日志。  
- 执行前确认（默认真）降低误点风险。  
- 不提升权限；需要 root 的插件自行 pkexec/sudo（规范说明，应用不代调密码）。

## 5. 运行时行为细节

### 5.1 执行

- 使用 Qt `QProcess`（主线程信号）或 `subprocess` + 信号桥；优先 **QProcess** 便于杀进程与读通道。  
- 超时：发送 terminate，宽限后 kill。  
- 工作目录：`workdir` 或插件根。  
- 环境：继承当前用户环境 + manifest `env`。

### 5.2 日志落盘

- `DATA_DIR/ops_runs/<timestamp>_<plugin_id>.log`  
- `DATA_DIR/ops_runs/last.json`：上次结果摘要（id、成功、结束时间、日志路径）  
- 菜单可提供「打开上次运行日志」（MVP 可选，建议做）。

### 5.3 菜单 action id 约定

- `ops.script.<plugin_id>`  
- `ops.service.<plugin_id>.start|stop|status`  
- `ops.open_last_log`（可选）

Controller `handle_action` 分发到 runtime。

## 6. 测试策略

| 层级 | 内容 |
|------|------|
| 单元 | manifest 解析、路径逃逸拒绝、进度行解析、互斥状态机 |
| 规范 | 对 `tests/fixtures/plugins/*` 样例：合法 script、合法 service、坏 manifest、entry 逃逸 |
| 集成（可选） | fixture script 打印 PROGRESS 后退出 0，断言 runtime 信号顺序 |

样例 fixture 插件（仓库内）：

- `tests/fixtures/plugins/sample-script`：echo PROGRESS 后 exit 0  
- `tests/fixtures/plugins/sample-service`：根据 start/stop/status 参数响应  

**不**把用户真实 VPN 脚本放进仓库。

## 7. 实现分期

| 阶段 | 交付 |
|------|------|
| **MVP** | 规范文档 + validate CLI；loader/runtime；菜单入口；轮播抢占；设置开关与左键行为；样例 fixture；单测 |
| **+1** | 设置页插件列表（启用/禁用单插件、校验错误展示）；上次日志入口 |
| **+2** | 副指示器（C2）；服务状态刷新到菜单标签；stderr 可选展示 |

## 8. 风险与缓解

| 风险 | 缓解 |
|------|------|
| P2 任意可执行文件攻击面大 | 路径限制在插件根；校验门禁；默认执行确认；用户目录自担风险说明 |
| AppIndicator 文案长度有限 | 截断 + 完整内容写日志文件 |
| 与番茄/轮播状态机耦合 | 单一 `display_mode`: `tasks` \| `pomodoro` \| `ops`，优先级 pomodoro/ops 互斥 |
| Windows 可执行位 | Windows 上跳过 Unix X_OK，检查文件存在即可 |

## 9. 决议记录

| 决议 | 选择 | 说明 |
|------|------|------|
| 入口形态 | **C3** | MVP 菜单 + 可配左键；预留副指示器 |
| 入口可执行类型 | **P2** | 任意可执行文件（插件根内） |
| 业务剧本 | 插件内容 | 核心不实现 VPN/邮箱 |
| 旧 Extension 体系 | 不承载本功能 | 避免双轨 |

## 10. 开放问题（实现前默认值）

若实现时用户未再指定，采用：

1. 总开关默认 **关闭**（避免空菜单惊吓新用户）。  
2. 抢占文案最大长度 **50** 字符（与现 `ScriptService` 日志截断一致）。  
3. 同 id 冲突时 **用户插件覆盖内置**。
