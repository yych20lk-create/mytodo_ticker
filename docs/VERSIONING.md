# ZenTray 版本号规则

从 **0.1.0** 起采用语义化版本 `MAJOR.MINOR.PATCH`：

| 变更类型 | 版本怎么加 | 示例 |
|----------|------------|------|
| **优化 / 修 Bug** | `PATCH + 0.0.1` | 0.1.0 → **0.1.1** |
| **功能迭代**（新能力、交互增强） | `MINOR + 0.1.0`，PATCH 归零 | 0.1.3 → **0.2.0** |
| **项目重构 / 大改版** | `MAJOR + 1.0.0`，MINOR/PATCH 归零 | 0.3.2 → **1.0.0** |

## 唯一真相源

- 运行时版本：`zentray/config.py` 中的 `VERSION`
- 打包/元数据：`pyproject.toml` 的 `version`（应与 `VERSION` 同步）
- 安装器展示：`installer/install_wizard.py` 的 `APP_VERSION`（应与 `VERSION` 同步）

发版前检查三者一致。

## 当前版本

见 `zentray/config.py` → `VERSION`（现为 **0.1.0**）。
