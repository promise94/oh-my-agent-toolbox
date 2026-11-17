# Claude adapter

该目录承载 Claude 专用的 plugin manifest、Bootstrap 和 Stop hook。根目录的 Marketplace/plugin 入口在过渡期继续保留，根 `scripts/bootstrap.py` 和 `hooks/phase-gate.sh` 是兼容入口。

Bootstrap 只修改目标项目的 `.claude` 文件；重复执行幂等，遇到同名但不同命令的 phase gate hook 会阻止覆盖。`--uninstall` 只移除本 adapter 写入的 Stop hook 和文件，保留用户 settings 内容。
