# ZenTray 插件规范（api_version = 1）

与设计文档 `docs/superpowers/specs/2026-07-20-plugin-scripts-services-design.md` 对齐。

## 目录

```text
my-plugin/
  plugin.yaml     # 必填
  <entry>         # 可执行文件（相对路径，P2）
  README.md       # 建议
```

## plugin.yaml

| 字段 | 必填 | 说明 |
|------|------|------|
| id | 是 | `[a-z0-9]+(-[a-z0-9]+)*` |
| name | 是 | 菜单名 |
| version | 是 | 版本字符串 |
| type | 是 | `script` \| `service` |
| api_version | 是 | 目前仅 `1` |
| entry | 是 | 相对插件根的可执行文件 |
| args | 否 | 追加参数 |
| workdir | 否 | 相对工作目录 |
| timeout_sec | 否 | script 默认 300 |
| env | 否 | 额外环境变量 |
| description | 否 | 说明 |

## script 进度（stdout）

```text
PROGRESS <current>/<total> <message>
LOG <message>
RESULT ok
RESULT fail <reason>
```

退出码 `0` 表示成功。

## service

```bash
./entry start
./entry stop
./entry status   # stdout 首行: running | stopped | unknown
```

## 校验

```bash
python scripts/validate_plugin.py path/to/plugin
```

不通过校验的插件不会出现在托盘菜单。

## 安装位置

| 来源 | 路径 |
|------|------|
| 内置 | 仓库 / 安装包内 `bundled_plugins/` |
| 用户 | `~/.local/share/ZenTray/plugins/`（可在设置中改） |

设置 → 开启「脚本与服务」后生效。
