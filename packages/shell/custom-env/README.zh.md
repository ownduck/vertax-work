---
description: "在 Host 上合并默认环境变量与 $DSH_HOME/.env，供模型 shell 子进程继承。"
kind: "package-reference"
---

# @deepseek-ai/dsh-custom-env

加载时将包内默认 map 与 `$DSH_HOME/.env` 合并（同名键以文件为准），写入 Host 的 `process.env`，供 bash/pwsh 子进程继承。在 Windows 上还会写入当前用户的环境变量。缺少或空的 `.env` 时只保留默认值。

## Model Experience

shell 与 skill 脚本可读合并后的键（例如 `$VERTAX_COMFYUI_ENDPOINT`）。不向模型追加提示词。

## Known Limitations and Deferred Work

- 值在插件加载时固定；改 `$DSH_HOME/.env` 或源码默认 map 后重启 Host 即可。
- Windows 用户环境变量的更新只对新进程生效；已打开的终端仍保留旧值。
- 非 Windows 主机只设置当前进程环境。
- 名称命中子进程凭据清除规则（`*KEY*`、`*SECRET*`、`*TOKEN*`、`*PASSWORD*`）时，可能传不到 shell 子进程，除非在清除后再显式注入。
- 不发布 `./invariant`：本插件只写入进程与用户环境变量。
