# ZenTray 前端（Vue 3 + Arco Design）

对话框层使用 **Vue 3 + Arco Design**（需 `web/dist`），业务逻辑在 Python（`TaskService` / `SettingsManager` 等）。

## 架构

```
托盘菜单 (Python)
    │
    ├─ 有 web/dist + Qt WebEngine ──► VueDialog (QWebEngineView)
    │                                      │
    │                                      ▼
    │                              本机 HTTP (127.0.0.1)
    │                              ├── /api/*  → handlers → TaskService
    │                              └── /*      → Vue 静态资源
    │
    └─ 否则 / ZENTRAY_UI=qt ────────► 原 PySide6 对话框（回退）
```

| 层 | 路径 | 职责 |
|----|------|------|
| Vue 页面 | `web/src/views/*` | 任务列表/表单/进度/设置/周期 |
| API 客户端 | `web/src/api/client.js` | axios 调 `/api/*` |
| 本地 API | `zentray/api/` | 转调现有服务 |
| 宿主窗口 | `zentray/ui/web_host.py` | WebEngine 开窗 + `zentray://close` 回传 |
| 菜单桥接 | `zentray/ui/vue_commands.py` | 优先 Vue，失败回退 Qt |

## 开发

```bash
# 1) 安装前端依赖并构建
cd web
npm install
npm run build          # 产出 web/dist

# 2) 启动应用（托盘仍为 Python）
cd ..
source venv/bin/activate   # 或你的虚拟环境
python -m zentray.main
```

### 纯前端热更新（可选）

```bash
# 终端 A：先起 Python（会监听随机端口；开发时代理需对齐）
# 可临时改 LocalApiServer 固定 port=17890

# 终端 B
cd web && npm run dev    # Vite :5173，代理 /api → 17890
```

生产/打包始终使用 **构建后的 `web/dist`**，由 Python 静态托管。

## 环境变量

| 变量 | 含义 |
|------|------|
| `ZENTRAY_UI=qt` | 强制使用原生 PySide 对话框 |
| 默认 | 有 `web/dist` 且 WebEngine 可用则用 Vue |

## 页面路由（hash）

| 路由 | 功能 |
|------|------|
| `/#/tasks` | 任务列表 |
| `/#/tasks/new` | 新建 |
| `/#/tasks/:id/edit` | 编辑 |
| `/#/tasks/:id/progress` | 进度（10% 步进） |
| `/#/tasks/:id/action` | 任务操作 |
| `/#/periodic` | 周期模板 |
| `/#/settings` | 设置（含主题 light/dark/system） |
| `/#/reminder/:id` | 到点提醒 |
| `/#/quick-add` | 闪电添加（无边框） |
| `/#/setup` | 首次配置向导 |

关闭宿主窗口：前端调用 `closeHost(payload)` → `zentray://close?payload=...`。

## 主题

与原版一致，三档：

| 模式 | 含义 |
|------|------|
| `light` | 浅色（Arco 默认 + 页面 light 变量） |
| `dark` | 深色（`arco-theme=dark`） |
| `system` | 跟随系统 `prefers-color-scheme` |

- Vue：`web/src/theme.js` + 设置页即时预览  
- 宿主 Qt：保存设置后仍调用 `apply_app_theme()` 同步 QSS  
- 托盘/系统指示器：非 Web UI，保持系统原生样式

## 打包

1. `cd web && npm ci && npm run build`
2. `pyinstaller zentray.spec`（已包含 `web/dist` datas）

## 与 Qt 前端的关系

- **托盘 / AppIndicator / 轮播 / Worker**：仍为 Python（系统能力，不迁 Vue）。
- **模态业务页**：优先 Vue；无 dist 时自动回退 Qt，保证可运行。
- 后续可将更多页面迁到 `web/src/views`，API 按需扩展即可。
