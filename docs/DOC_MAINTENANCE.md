# 文档维护约定

> 目标：代码与文档同步，避免用户手册/README 落后于实现。

## 何时必须更新文档

| 变更类型 | 必更新 |
|----------|--------|
| 用户可见功能（菜单、设置、托盘行为） | `README.md` 功能表 + `docs/USER_MANUAL.md` |
| 安装/打包/依赖 | `README.md` + 手册对应平台章节 |
| 插件规范 / 校验 / 目录 | `docs/plugins/PLUGIN_SPEC.md` + README 插件速览 + 手册「脚本与服务」 |
| 设置项增删 | 手册「设置」表 + 必要时 README |
| 仅内部重构、无行为变化 | 可不改用户文档；若架构图失效则改 README 架构节 |

## 检查清单（PR / 提交前）

- [ ] README 功能一览是否仍准确？  
- [ ] USER_MANUAL 设置/日常使用是否覆盖新入口？  
- [ ] 插件相关是否与 `PLUGIN_SPEC.md` 一致？  
- [ ] 版本号说明是否仍指向 `config.py` / VERSIONING？  
- [ ] 前端改动后是否已 `web` 构建并提交 `web/dist`（若仓库策略要求提交 dist）？

## 文档索引

| 路径 | 受众 |
|------|------|
| `README.md` | 开发者与首次接触仓库的人 |
| `docs/USER_MANUAL.md` | 终端用户 |
| `docs/plugins/PLUGIN_SPEC.md` | 插件作者 |
| `docs/FRONTEND_VUE.md` | 前端开发 |
| `docs/VERSIONING.md` | 发版 |
| `docs/superpowers/specs/*` | 设计规格（历史与决策） |

## 代理 / 协作者

实现功能时默认执行本约定：改完代码后同步改 README 与用户手册，并在提交说明中点到文档变更。
