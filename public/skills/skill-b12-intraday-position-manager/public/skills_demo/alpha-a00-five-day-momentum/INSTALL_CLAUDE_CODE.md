# Claude Code Skill 安装说明

本包包含 4 个 Claude Code / Agent Skills 标准目录：

- `alpha-a00-five-day-momentum`：Alpha 开发版，用于重新拉数、计算、验证和回测。
- `alpha-a00-five-day-momentum-production`：Alpha 生产版，用于直接读取已生成结果。
- `build-b00-price-change-flag`：BUILD 开发版，用于重新拉数、生成工具结果和测试。
- `build-b00-price-change-flag-production`：BUILD 生产版，用于直接读取已生成结果。

## 安装到个人 Claude Code Skills

将上述 4 个目录复制到：

```text
~/.claude/skills/
```

Windows 示例：

```powershell
New-Item -ItemType Directory -Force "$HOME\.claude\skills"
Copy-Item ".\alpha-a00-five-day-momentum" "$HOME\.claude\skills\" -Recurse -Force
Copy-Item ".\alpha-a00-five-day-momentum-production" "$HOME\.claude\skills\" -Recurse -Force
Copy-Item ".\build-b00-price-change-flag" "$HOME\.claude\skills\" -Recurse -Force
Copy-Item ".\build-b00-price-change-flag-production" "$HOME\.claude\skills\" -Recurse -Force
```

安装后可在 Claude Code 中直接调用：

```text
/alpha-a00-five-day-momentum
/alpha-a00-five-day-momentum-production
/build-b00-price-change-flag
/build-b00-price-change-flag-production
```

## 运行依赖

开发版 skill 需要 Python 3.10+，并安装：

```text
pandas
pyarrow
requests
panda-data
```

生产版 skill 若需要用 Python 读取 `database.parquet`，也需要 `pandas` 和 `pyarrow`。

## 环境变量

开发版 skill 会通过 Panda data 拉取真实行情，运行前需要设置：

```text
PANDA_DATA_USERNAME
PANDA_DATA_PASSWORD
```

可选设置：

```text
PANDA_DATA_START_DATE
PANDA_DATA_END_DATE
```

不要把账号密码写入 `SKILL.md`、脚本或提交到仓库。

## 使用边界

- 开发版用于重新计算、验证、测试和回测。
- 生产版用于读取已生成的 `database.parquet`。
- 生产查询时不要重新拉数或临时重算。
- Alpha 回测必须避免未来函数、偷价和同根 K 线成交假设。
- 本包是 MVP 示例，不等同于正式策略上线结论。
