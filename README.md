# ZenTray 个人禅定看板 (v3.7)

> 跨平台（Windows / macOS / Linux）个人任务管理与专注效率工具。
> 系统托盘常驻，番茄钟 + GTD 看板 + AI 毒舌教练，助你高效摸鱼。

<p align="center">
  <strong>📋 GTD 任务管理 &nbsp;|&nbsp; 🍅 番茄专注 &nbsp;|&nbsp; 🤖 AI 每日复盘 &nbsp;|&nbsp; 📱 移动端推送</strong>
</p>

---

## 🚀 快速开始

### 一键安装（推荐）

```bash
pip install zentray
zentray
```

**无需任何配置即可启动！** 核心功能（任务管理、番茄钟、托盘轮播）开箱即用。

### 开发模式启动

```bash
git clone https://github.com/zen-geek/zentray.git
cd zentray
pip install -e ".[dev]"
python zentray/main.py
```

### 启用高级功能

在项目根目录创建 `.env` 文件：

```env
# 移动端推送（WxPusher）
WXPUSHER_APP_TOKEN=your_token_here
WXPUSHER_UID=your_uid_here

# AI 夜间复盘教练
AI_API_KEY=sk-your-key-here
AI_API_BASE_URL=https://api.openai.com/v1
AI_MODEL_NAME=gpt-4o
```

---

## ✨ 功能特性

| 功能 | 说明 | 配置要求 |
|------|------|---------|
| 📋 **GTD 看板** | 任务创建、分类、优先级、进度追踪 | 无 |
| 🍅 **番茄钟** | 25分钟专注计时，可延长/中止 | 无 |
| 🔄 **周期任务** | 日/周/月自动派发 | 无 |
| ⚡ **闪电添加** | `Ctrl+Alt+T` 全局快捷键快速录入 | 无 |
| 📱 **移动推送** | WxPusher 通知到微信 | 需配置凭据 |
| 🤖 **AI 复盘** | 每日 23:30 毒舌锐评 + 明日规划 | 需 API Key |
| 🔌 **扩展系统** | 自定义状态栏脚本按钮 | 无 |

---

## 🖥️ 跨平台支持

| 平台 | 托盘实现 | 状态 |
|------|---------|------|
| **Linux (GNOME)** | 原生 GTK AppIndicator 桥接，顶栏文字滚动 + 进度饼图 | ✅ 完美 |
| **Linux (其他)** | Qt 系统托盘回退 | ✅ 可用 |
| **macOS** | Qt 标准菜单栏托盘 | ✅ 可用 |
| **Windows** | Qt 系统通知区域托盘 | ✅ 可用 |

### 快捷键

| 系统 | 快捷键 |
|------|--------|
| Linux / Windows | `Ctrl + Alt + T` |
| macOS | `Cmd + Alt + T` |

> ⚠️ **macOS 用户**：首次使用需在 **系统设置 → 隐私与安全性 → 辅助功能** 中授权终端软件。

---

## 🏗️ 架构设计

```
main.py
  └── DI Container (injector)
        └── TrayController (事件协调)
              ├── TaskService        → 任务 CRUD / 进度 / 调度
              ├── PomodoroService    → 番茄钟计时状态
              ├── ScriptService      → 扩展脚本执行（预留）
              ├── TrayRenderer       → 托盘 UI 渲染
              ├── MenuBuilder        → 右键菜单构建
              └── ExtensionLoader    → 动态插件发现
                    └── StatusBarExtension（脚本按钮等）

    命令模式
    ─────────
    handle_action → dispatch() → ActionCommand.execute()
        ├── NewTaskCommand
        ├── DoneCommand
        ├── PomodoroStartCommand
        ├── ExtensionCommand
        └── ...

    存储层
    ──────
    TaskRepository (接口)
        ├── FileTaskRepository      ← 当前
        └── MySQLTaskRepository     ← 后续
```

### 核心设计原则

- **依赖注入**：所有服务通过 `injector` 容器管理，松耦合可测试
- **命令模式**：托盘菜单事件通过 `ActionCommand` 分发，易扩展
- **接口隔离**：`TaskRepository` 抽象存储，可切换 file / mysql 后端
- **零配置启动**：高级功能按需激活，核心功能始终可用

---

## 📁 项目结构

```
my_todo/
├── pyproject.toml              # 项目元数据与依赖声明
├── LICENSE                     # MIT License
├── requirements.txt            # 依赖列表（兼容旧工具）
├── zentray.spec                # PyInstaller 打包配置
├── README.md
│
├── zentray/
│   ├── main.py                 # 应用入口
│   ├── config.py               # 配置管理（零配置友好）
│   ├── resources.py            # 资源路径管理（dev/pyinstaller 兼容）
│   ├── dependencies.py         # DI 容器模块配置
│   ├── di.py                   # 轻量 DI 回退（injector 不可用时）
│   │
│   ├── core/
│   │   ├── models.py           # 数据模型（Task, PeriodicTemplate）
│   │   ├── scheduler.py        # 加权轮播调度算法
│   │   ├── repository.py       # Repository 抽象接口
│   │   └── storage.py          # 旧版 Storage（兼容过渡）
│   │
│   ├── repositories/
│   │   ├── file_repository.py           # JSON 文件存储实现
│   │   └── file_periodic_repository.py  # 周期模板 JSON 存储
│   │
│   ├── services/
│   │   ├── task_service.py      # 任务管理服务
│   │   ├── pomodoro_service.py  # 番茄钟服务
│   │   ├── script_service.py    # 脚本执行服务（预留）
│   │   ├── notification.py      # 通知客户端
│   │   ├── ai_review.py         # AI 复盘服务
│   │   └── system_utils.py      # 系统工具（单例锁、热键监听）
│   │
│   ├── ui/
│   │   ├── controller.py        # 托盘协调者（事件路由）
│   │   ├── renderer.py          # 托盘渲染器
│   │   ├── menu_builder.py      # 菜单构建器
│   │   ├── commands.py          # 命令模式事件处理
│   │   ├── tray.py              # 跨平台托盘底层实现
│   │   ├── dialogs.py           # UI 对话框
│   │   ├── overlay.py           # 闪电添加浮层
│   │   ├── linux_tray_bridge.py # Linux 原生 GTK 桥接
│   │   └── extensions/          # 状态栏扩展系统
│   │       ├── interface.py     # StatusBarExtension 接口
│   │       └── loader.py        # ExtensionLoader 加载器
│   │
│   └── workers/
│       ├── watcher.py           # 后台巡检（逾期惩罚 + 周期派发）
│       └── nightly_job.py       # 夜间 AI 复盘
│
├── extensions/                  # 用户插件目录
├── resources/                   # 打包资源（图标等）
├── tests/                       # 测试套件
│   ├── conftest.py
│   └── unit/
│       ├── test_task_service.py
│       ├── test_pomodoro_service.py
│       ├── test_repository.py
│       └── ...
└── docs/                        # 设计文档
```

---

## 🧪 开发指南

### 运行测试

```bash
pip install -e ".[dev]"
pytest -v
```

### 代码风格

```bash
black zentray/ tests/
```

### 构建分发包

```bash
pip install pyinstaller
pyinstaller zentray.spec
```

输出位置：
- **Linux**: `dist/ZenTray`
- **macOS**: `dist/ZenTray.app`
- **Windows**: `dist/ZenTray.exe`

---

## 🔧 配置参考

| 环境变量 | 说明 | 默认值 | 必需 |
|---------|------|--------|------|
| `WXPUSHER_APP_TOKEN` | 通知服务 Token | - | 否 |
| `WXPUSHER_UID` | 通知服务 UID | - | 否 |
| `AI_API_KEY` | AI API 密钥 | - | 否 |
| `AI_API_BASE_URL` | AI API 地址 | `https://api.openai.com/v1` | 否 |
| `AI_MODEL_NAME` | AI 模型名称 | `gpt-4o` | 否 |
| `STORAGE_BACKEND` | 存储后端 (`file`/`mysql`) | `file` | 否 |

---

## 📄 许可证

MIT License — 详见 [LICENSE](LICENSE) 文件。

---

## 🙏 致谢

- [PySide6](https://wiki.qt.io/Qt_for_Python) — Qt for Python 官方绑定
- [injector](https://github.com/alecthomas/injector) — Python 依赖注入框架
- [pynput](https://github.com/moses-palmer/pynput) — 跨平台输入监听
