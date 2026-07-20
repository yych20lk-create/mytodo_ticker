# ZenTray 个人禅定看板

> 跨平台（Windows / macOS / Linux）系统托盘 GTD + 番茄钟 + AI 计划/复盘。  
> 当前版本见 `zentray/config.py`（版本规则：[docs/VERSIONING.md](docs/VERSIONING.md)）。

<p align="center">
  <strong>📋 任务轮播 &nbsp;|&nbsp; 🍅 番茄专注 &nbsp;|&nbsp; 🧩 脚本与服务 &nbsp;|&nbsp; 🤖 AI 计划/复盘 &nbsp;|&nbsp; 📱 通知</strong>
</p>

> 📖 **用户手册**：[docs/USER_MANUAL.md](docs/USER_MANUAL.md)  
> 🔌 **插件规范**：[docs/plugins/PLUGIN_SPEC.md](docs/plugins/PLUGIN_SPEC.md)  
> 🖥️ **Vue 前端**：[docs/FRONTEND_VUE.md](docs/FRONTEND_VUE.md)
---

## 快速开始

### 安装包

| 平台 | 包 | 方式 |
|------|-----|------|
| Linux | `zentray_*_amd64.deb` | `sudo apt install ./zentray_*.deb` → 命令 `zentray` |
| Windows | `ZenTrayInstaller-*-x64.exe` | 双击安装向导 |
| macOS | `ZenTray-*.dmg` | 拖入 Applications |

首次启动可走配置向导（可全部跳过）。程序**无主窗口**，请看**顶栏/托盘**。

### 开发运行

```bash
git clone https://github.com/zen-geek/zentray.git
cd zentray
python -m venv venv && source venv/bin/activate   # Windows: venv\Scripts\activate
pip install -e ".[dev]"
# 前端（对话框为 Vue + Arco，需先构建）
cd web && npm install && npm run build && cd ..
python -m zentray.main
```

强制使用原生 Qt 对话框：`export ZENTRAY_UI=qt`

### 可选环境变量（`.env` 或数据目录）

```env
WXPUSHER_APP_TOKEN=...
WXPUSHER_UID=...
AI_API_KEY=...
AI_API_BASE_URL=https://api.openai.com/v1
AI_MODEL_NAME=gpt-4o
```

也可用托盘 **设置** 配置（推荐）。

---

## 功能一览

| 功能 | 说明 |
|------|------|
| **托盘轮播** | 顶栏任务标题轮播；左侧**优先级饼图**（红/黄/绿，按进度填充） |
| **番茄钟** | 左：**番茄饼图**（随倒计时填充，带绿萼）；右：倒计时或自定义文案 |
| **任务** | 新建/编辑/进度(10%步进)/完成/废弃；二级分类、截止、提醒 |
| **周期任务** | 日/周/月模板自动派发 |
| **脚本与服务** | 插件式本机脚本/服务（设置中开关）；执行时进度**抢占**任务轮播；任务可**关联插件**并在编辑/更新进度页一键运行；见 [插件规范](docs/plugins/PLUGIN_SPEC.md) |
| **闪电添加** | `Ctrl+Alt+T`（macOS：`Cmd+Alt+T`） |
| **AI** | **每日计划** + **每日复盘**；多 API 配置（同时启用一个）；毒舌/温柔/干练 + 自定义提示词 |
| **通知** | 固定渠道：应用弹窗、WxPusher（可同时开） |
| **主题** | 浅色 / 深色 / 跟随系统 |
---

## 架构（简图）

```
托盘 (AppIndicator / Qt)
  ├── 轮播 / 番茄 / 脚本进度文案
  └── 菜单 → Vue 对话框 (QWebEngineView)
                 └── 本机 HTTP API → TaskService / SettingsManager / PluginRuntime
后台：Watcher / Reminder / AI 调度 Worker
插件：bundled_plugins/ + 用户数据目录 plugins/（plugin.yaml 校验门禁）
```

业务逻辑在 **Python**；设置与业务弹窗优先 **Vue 3 + Arco Design**（无 `web/dist` 时回退 Qt）。

### 脚本与服务（插件）速览

```bash
# 1. 设置中开启「脚本与服务」
# 2. 按规范编写插件后校验
python scripts/validate_plugin.py path/to/plugin
# 3. 放入用户插件目录（Linux 示例）
mkdir -p ~/.local/share/ZenTray/plugins
cp -a path/to/plugin ~/.local/share/ZenTray/plugins/
# 4. 重启或保存设置后，托盘菜单 → 🧩 脚本与服务
```

完整约定：[docs/plugins/PLUGIN_SPEC.md](docs/plugins/PLUGIN_SPEC.md)。

内置示例插件 **网络清理**：`bundled_plugins/net-cleanup/`（刷新 DNS/路由缓存等，详见目录内 README）。

---

## 打包

```bash
cd web && npm ci && npm run build && cd ..
./scripts/build_package.sh --target linux
# 产物: dist/releases/zentray_*_amd64.deb
```

---

## 文档

| 文档 | 内容 |
|------|------|
| [docs/USER_MANUAL.md](docs/USER_MANUAL.md) | 分环境安装与使用 |
| [docs/plugins/PLUGIN_SPEC.md](docs/plugins/PLUGIN_SPEC.md) | 脚本/服务插件范式与校验 |
| [docs/FRONTEND_VUE.md](docs/FRONTEND_VUE.md) | 前端开发与路由 |
| [docs/VERSIONING.md](docs/VERSIONING.md) | 版本号规则 |
| [docs/DOC_MAINTENANCE.md](docs/DOC_MAINTENANCE.md) | **文档维护约定**（改功能必更新 README/手册） |
| [LICENSE](LICENSE) | MIT |

### 文档维护（强制）

**任何用户可见行为或开发者工作流的变更**，合并前必须自检并更新：

1. [README.md](README.md)（功能表 / 快速开始 / 架构若变化）  
2. [docs/USER_MANUAL.md](docs/USER_MANUAL.md)（安装、设置、日常使用）  
3. 若涉及插件： [docs/plugins/PLUGIN_SPEC.md](docs/plugins/PLUGIN_SPEC.md)  

细则见 [docs/DOC_MAINTENANCE.md](docs/DOC_MAINTENANCE.md)。

---

## 许可证

MIT
