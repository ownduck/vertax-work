---
name: windows-mcp
description: 接管 Windows computer use 与桌面控制。用户询问 Windows 控制、桌面控制、电脑操作、computer use 是否可用，或要求截图、点击、移动鼠标、键盘输入、滚动、快捷键、切换或启动窗口时，先加载本 skill。键鼠走 windows-mcp，不要用沙箱里的 pwsh 调用 SendInput、SetCursorPos，也不要在沙箱里启动 open-computer-use。
---

# Windows MCP

接管本机 Windows 桌面控制：截图、点击、移动鼠标、键盘输入、滚动、快捷键、切换和启动窗口。用户问「Windows 控制可用吗」「能不能操作桌面」「computer use」时，用本 skill 回答并完成操作。

点击、移动、打字和快捷键只走本 skill 拉起的 `mcp__windows-mcp__*`。不要用沙箱中的 `pwsh` 调用 `SendInput`、`SetCursorPos`、`keybd_event`，也不要在沙箱里启动 `open-computer-use`。那些进程带着低完整性令牌，读屏幕可以，注入键鼠会被系统丢掉。文件、命令、注册表仍用 DSH 自己的工具。

这个 skill 不会在启动时自己执行。模型先加载本文，完成下面的可用性检查，再操作桌面。检查和后续操作都留在用户这一轮里：工具返回后自动进入下一步，用户不需要再发一条消息。

## 放置位置

打包后的桌面版会扫描这份 skill。`apps/desktop/scripts/electron-builder-config.mjs` 把仓库 `skills/` 拷进安装资源的 `skills/`，`apps/desktop/src/main.ts` 在打包态把 `DSH_BUNDLED_SKILL_DIR` 指到 `resources/skills`。`skill-filesystem` 会扫描这个目录。

未打包的开发进程没有这段赋值。那里要让它出现，把整个 `windows-mcp` 目录放到下面任一位置，或自行设置 `DSH_BUNDLED_SKILL_DIR`：

- `$DSH_HOME/skills/windows-mcp`
- 工作区 `.agents/skills/windows-mcp`
- 工作区 `.dsh/skills/windows-mcp`

## 执行顺序

脚本会安装程序并写入 `$DSH_HOME`。这两处都在会话工作区外面。默认的 `workspace-write` 会拒绝写入。运行前把这次命令升到 `danger-full-access`，并取得用户批准。

在本 skill 目录中执行：

```powershell
npm install
powershell -NoProfile -File scripts/init-env.ps1
node scripts/init-mcp-client.mjs
```

`init-env.ps1` 只在缺少 uv 或 `windows-mcp.exe` 时安装，并把最终 exe 的绝对路径打到 stdout。不检查、不安装系统 Python。`uv tool install windows-mcp` 自带 Python 3.14。

`init-mcp-client.mjs` 读取 `DSH_HOME`。变量未设置时直接失败。家目录补丁 `$DSH_HOME/cordis.patch.yml` 不存在时，从空数组创建。文件里还没有 `id: mcp-windows-mcp` 时，插入一条已启用的 `@deepseek-ai/dsh-mcp-client`。已有同 id 时不改文件。

可执行文件优先用 `%USERPROFILE%\.local\bin\windows-mcp.exe`。那里没有时，才用 `where.exe windows-mcp` 的第一个结果。不要把 `where` 的第一行直接当成 uv 安装的程序，本机上它可能先命中别的虚拟环境。

## 可用性

每一轮模型请求开始时，才会读取当时已经注册的工具。写补丁的那一步里还没有 `mcp__windows-mcp__*`。client 可用的唯一标志，是下一步的工具名单里出现这些名字，例如 `mcp__windows-mcp__Screenshot`、`mcp__windows-mcp__Click`、`mcp__windows-mcp__Type`、`mcp__windows-mcp__App`。

按这个顺序做，并且一直留在同一轮：

1. 当前这一步已经能调用 `mcp__windows-mcp__Screenshot` 时，client 已可用。直接使用，不必再跑初始化。
2. 否则先跑上面的初始化命令，并且不要和等待并行。`init-mcp-client.mjs` 在真正写入后会自己等 10 秒再返回，用来盖过文件监视的稳定时间和 `windows-mcp.exe` 的启动。补丁里已经有这条 client 时，脚本不等待。
3. 脚本返回后的下一步重新读取工具名单。名单里有 `mcp__windows-mcp__Screenshot`，检查通过，开始操作桌面。
4. 名单里还没有，就用 `pwsh` 执行 `Start-Sleep -Seconds 10`，`timeoutMs` 设为 `20000`。这次调用只等待。它返回后的下一步再看名单。同一轮里最多再等 3 次。
5. 3 次之后仍然没有，向用户说明 client 没有挂上，并停止。headless、sdk、acp 关闭了这份热更新，等待不会在当前进程里生效；写入之后告诉用户下次启动才会挂上，不要空等。

`plugin_manager` 里这条插件变成 active，不能当作可用。连接失败时插件仍可能激活，工具却还没注册。

Web 和桌面版监视 `$DSH_HOME/cordis.patch.yml` 的新增、修改和删除。写入稳定后才重载，大约要 2 秒，然后再启动 client 并拉取工具列表。

这条 client 不提供 `PowerShell`、`FileSystem`、`Registry`。截图要能进对话，当前模型路由必须声明支持图像。

## 使用

可用性检查通过之后再操作。先看屏幕，优先 `Screenshot` 或 `Snapshot`，用返回的坐标或元素调用 `Click`、`Type`、`Scroll`、`Move`、`Shortcut`。切换或启动应用用 `App`。文件和命令仍用 DSH 自己的工具。
