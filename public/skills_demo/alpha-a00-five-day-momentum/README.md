# 量枢院 MVP 示例 Skills

这是一个可安装到 Claude Code 的 Agent Skills 示例包，用于演示两个最小任务：

- 五日动量 Alpha
- 涨跌幅异常标记 BUILD

每个任务包含开发版和生产版两个 skill。开发版负责拉取真实数据、计算、验证和测试；生产版负责读取已落地的 `database.parquet` 结果。

详细安装方式见 `INSTALL_CLAUDE_CODE.md`。
