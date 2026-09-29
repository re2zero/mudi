# MuDi 产品计划与会话接力协议

> 本文件是产品迭代的**唯一权威进度源**：每个工作会话开工前必读，收工前必更新。
> 背景知识（架构、坑、测试方法论沿革）在 ZCode 长期记忆中，两者互补。
> 制定于 2026-09-21，基于对全部源码与 herdr 0.9.1 CLI 的逐一复核。

## 0. 产品定位

**MuDi（牧笛）= herdr 的桌面驾驶舱**：放牧 AI agent 舰队的人，眼睛不该一直盯着终端。
她与 herdr TUI 的分工——TUI 管"操作"，MuDi 管"守望、通知、直达、更新、开箱即用"。
一切里程碑的取舍标准：**是否强化"守望 → 直达"闭环**。

**明确不做**：遥测/账号/云同步、自绘终端模拟器（qtermwidget 够用）、多窗口管理（workspace 布局归 herdr）。

---

## 1. 复核确认的缺口（附代码证据）

| # | 缺口 | 证据 | 影响 |
|---|------|------|------|
| G1 | 通知不可点击、无 action，不能跳转到对应 agent | `appcore.cpp` Notify 调用 actions 传空 `QStringList()`，未监听 Activation | 提醒止步于打扰，价值断裂 |
| G2 | 关窗即失明：无托盘常驻，窗口关闭后 agent 监控停止 | 全库无 `QSystemTrayIcon`；`main.cpp` 直接 `app->exec()` | "守望"只在窗口开着时存在 |
| G3 | server 生命周期断点：herdr 更新后协议不匹配需手动 `herdr server stop`（杀掉全部 pane 进程） | 全库无 `protocol_mismatch` 处理；设置页无 server 状态区 | 每次更新 herdr 后必然踩一次，最大流失点 |
| G4 | 无 README / 无任何 release | 仓库无 README.md；App 自更新检查至今 404 | 产品不存在于世 |
| G5 | GitHub 匿名 API 限额 60/h，每次启动自动查 2 个更新，无节流无条件请求 | `appcore.cpp autoCheckUpdates()` 每 launch 必查 | 重度用户横幅悄悄消失 |
| G6 | App 自更新策略矛盾：CI 传了裸二进制（updater 能装），UI 却只给 "View" 开网页 | `initUpdateSystem()` BANNER_APP 分支 `QDesktopServices::openUrl` | deb 用户正确，便携用户被冤枉 |
| G7 | 无单实例锁（双开=双份通知）、无文件日志（仅 stderr） | 全库无 `QLockFile`；messageHandler 仅 fprintf(stderr) | 日常粗糙感 |
| G8 | 快捷键不可发现；窗口标题无上下文；ts 行号漂移；a11y 名缺失 | 快捷键仅 `bindKey` 硬编码；标题恒 "MuDi" | 打磨欠账 |

**herdr 0.9.1 CLI 已具备的地基（复核新发现，直接决定技术路线）**：
- `herdr agent focus <id>` — **点击通知直达 agent 的现成通道**；
- `herdr status` — 输出 server status / version / `private_protocol_compatible`，M7 的检测源；
- `herdr agent wait --states …` — 事件式等待，可替代 agentmonitor 4s 轮询（备选优化）；
- `herdr pane list/focus`、`herdr api snapshot` — 状态带与标题上下文的数据源。

---

## 2. 里程碑

> 编号衔接既有路线图（M1-M3 ✅，M4 ConPTY 移植，M5 打包 CI，见长期记忆）。
> 每个里程碑独立成会话可完成；验收不过不算完成。

### M6 牧羊人闭环：通知→直达 + 托盘常驻（P0，产品灵魂）

**6a 通知升级为导航**
- 改动：`appcore.cpp onAgentAttention` — Notify 带 action（"查看"）；建立私有 DBus 连接监听 `NotificationClosed`/按 action 调用；激活时 → `QWindow raise/activate` + `herdr agent focus <paneId>`（`QProcess` 异步，失败仅 raise）。
- 验收：真实桌面：agent blocked → 通知点击 → 窗口前置且 herdr 视图切到该 pane；通知 action 按钮同效。
- 测试注意：通知激活链路 Xvfb 下无法完整模拟，需公子真实桌面验收 + 代码级 review 把关。

**6b 托盘常驻**
- 改动：新增 `src/tray.{h,cpp}`（QSystemTrayIcon，图标 `fromTheme("mudi")`）；tooltip = agent 摘要（`2 running, 1 blocked`）；菜单 = 显示主窗 / blocked agent 直达（复用 6a focus）/ 退出；设置项 `closeToTray`（herdr 页或外观页，默认关）；关闭窗口时若开启则 `hide()`，托盘激活恢复。`main.cpp` 退出路径相应调整（真正的退出走托盘菜单）。
- 验收：开 closeToTray → 关窗 → 托盘在、通知继续来；托盘菜单直达；退出彻底。
- 测试注意：Xvfb 无 system tray host，`QSystemTrayIcon::isAvailable()` 为 false 的分支要优雅降级（无托盘则维持现状直接退出）；真实桌面验收。

**6c（可选加餐）主窗 agent 状态带**：`m_container` 里 banner 下加一条状态 strip，数据源 `herdr agent list`（agentmonitor 已有差分，可发出全量信号）。若 6a/6b 会话余量不足，顺延独立会话。

### M7 server 生命周期闭环（P0，体验断点）

- 改动：
  - `AppCore` 增加低频（如 30s）`herdr status` 探测（YAML 文本按行解析即可，勿引依赖）；结果缓存 `serverRunning/serverVersion/protocolCompatible`。
  - `SettingsDialog::createHerdrPage` 顶部加 server 状态区：运行状态、版本、协议兼容（红字提示 + "重启 server" 按钮）。
  - `herdr` 更新安装完成后：横幅 `showNotice("herdr 已更新…", "重启 server")`（action 已有路由模式可循：仿 BANNER_RETRY/CONNECT）；点击 → 破坏性确认对话框（说明会重启各 pane 进程）→ `herdr server stop` → 复用 `ensureServerRunning` 重试链自动拉起新 server 并 attach。
  - protocol 不兼容（status 显示 `private_protocol_compatible: no` 或 client 报 protocol_mismatch）→ 同一重启引导。
- 验收：隔离环境用 PATH shim 模拟 status 各分支（running/not running/incompatible）验证 UI 路由；公子真实桌面在下次 herdr 更新时走一遍真实流程。
- 纪律：`herdr server stop` 对公子真实会话有破坏性，任何自动化测试禁止对真实 server 执行。

### M8 在世发布：README + v0.3.0 首发（P0，让产品存在）

- 改动：
  - `README.md`：一图流（主窗/设置/横幅截图）+ 是什么/为什么 + 安装（deb/AppImage 按实际）+ 构建 + 名字故事（牧笛/Mudi 牧羊犬双关）；英文为主、中文附段。
  - `CMakeLists.txt` APP_VERSION 默认 0.2.1 → 0.3.0；debian/changelog 开 0.3.0 条目。
  - 前置依赖公子：GitHub 仓库已改名 `re2zero/mudi`。
  - push tag `v0.3.0` → CI 产 assets → 发布后在一台隔离机器验证 App 自更新从 404 变为有结果（闭环上线）。
- 验收：CI 全绿；releases 页资产齐全（`mudi-linux-x86_64` 等 8 件）；自更新检查返回"已是最新"。

### M9 更新体系健壮化（P1）

- 检查节流：QSettings `updater/lastCheckAt`，默认 6h 内不重复（设置页 autoCheckUpdates 已有开关，补充"检查频率"可不加——默认值即产品决策）。
- 条件请求：`If-None-Match`/ETag 缓存，304 不计限额。
- 静态 updates.json（gh-pages 托管，元数据含版本/URL 模板/SHA-256/notes）：updater 先查静态源、API 兜底。需公子先建分支/页（一次性 10 分钟）。
- 安装方式探测：`/var/lib/dpkg/info/mudi.list` 存在 → deb 管辖，App 更新维持"View"；否则便携版 → BANNER_APP 的 action 从 "View" 变 "Update"（updater 管线已支持，纯策略层改动）。
- 验收：伪造 API 429/断网验证节流与兜底；dpkg 探测在真机正反例各一。

### M10 日常打磨包（P2）

- QLockFile 单实例：二次启动 → raise 已有窗口后退出。
- 文件日志：messageHandler 增加文件 sink（`~/.local/share/mudi/logs/mudi.log`，2×1MB 轮转）；设置页"关于"加"打开日志"。
- 快捷键帮助：设置页加只读快捷键清单（起步不做自定义）。
- 窗口标题上下文：`MuDi — <workspace/pane>`（数据源 `herdr api snapshot` 或 pane current，实现时探明）。
- `lupdate` 刷新 ts 行号；自定义控件过一遍 `setAccessibleName`。
- 验收：双开行为、日志轮转、截图对照。

### 既有 M4/M5（跨平台与打包，维持原计划）

Windows ConPTY 移植、macOS 通知补齐（`agentmonitor` 现在 `!WIN && !MAC` 直接跳过）+ 签名/公证决策（$99/年 vs tarball+手动放行）、AppImage/NSIS/dmg。M4 完成前 windows-experimental.yml 维持 allowed-to-fail。

---

## 3. 测试方法论（每个里程碑必须遵守）

1. **隔离**：端到端测试一律 `XDG_CONFIG_HOME=/tmp/xxx`，绝不共享真实 `~/.config/herdr` 与运行中 server。
2. **防误伤**：PATH 垫 `herdr` shim 防止测试拉起/操纵真实 server；对真实 server 的破坏性操作（stop 会杀 pane 进程）仅公子本人执行或在真实验收环节说明后进行。
3. **无头**：Xvfb + `kwin_x11 --no-kactivities`（裸 Xvfb 会在几何变化时段错误）；托盘/通知等桌面集成功能标注"需真实桌面验收"。
4. **双壳**：涉及 UI 的改动，DTK 与 `MUDI_UI=generic` 各验一次。
5. **构建**：改动后 `cmake --build build-dtk` 必须零警告通过；打包相关改动用 `cmake --install --prefix /tmp/stage` + `desktop-file-validate` 验证。

## 4. 会话接力协议

**锚点原则**：`docs/plan.md`（本文件）是唯一权威进度源；长期记忆是背景与坑位知识；git 是事实。三者冲突时以 git 为准、以 plan.md 为调度。

**每个工作会话的标准流程**：
1. 读本文件「5. 当前状态」+ `git log -3` + `git status`，确认实际进度（以仓库为准，状态区可能滞后）。
2. 实施状态区指派的里程碑；只做该里程碑范围内的事，顺手重构不超 20 行。
3. 按第 3 节方法论自测；验收标准逐条过。
4. 向公子汇报结果（含证据：构建输出/截图/测试结果）。
5. 公子确认后提交（commit-submit 规范）；随后**立即**更新本文件状态区并更新长期记忆（新坑、新决策）。
6. 任何未完成/未提交的工作，必须在状态区写明"断点在哪、如何续"。

**状态区维护格式**（每次收工更新）：

```
## 5. 当前状态

- 当前里程碑: **v0.4.1 已发布：CI 产出 deb/rpm 安装包（2026-09-29，公子指派）**——Linux job 新增 Package 步骤：deb 手工组装（Depends 用 alternative 兼容 noble 的 libqt6core6t64 与 deepin/Debian12 的 libqt6core6；libqt6gui6 等同名直列；本机 deepin 已验证 9 个依赖包名全部可解析）+ rpm（packaging/rpm/mudi.spec 极简 spec，库依赖由 rpmbuild 自动从 NEEDED 推导）。release 资产现为 10 件：linux 双架构 × {deb, rpm, 裸二进制, tar.gz} + macos-aarch64 × {二进制, tar.gz}，releases/latest 正确返回 v0.4.1。三次 CI 翻车与修复：①rpm 严格校验未打包文件——vendored terminalwidget 的 /usr/share/terminalwidget6/ 数据（配色/键盘布局，运行必需）不在 %files，补上（deb 不校验所以一直带对了）；②find 的 mudi_* 把 stage 树里的 .qm 当 deb 捞上 release，两份同名副本上传 422 撞车——改 mudi_*.deb 精确匹配；③删 tag 重推触发 GitHub 把已存在 release 转 draft（对外 404、latest 不算）——gh release edit --draft=false --latest=true 转正。当前链路 100% 干净，公子机器（0.3.0 deb）检查更新即提示有 v0.4.1
- 最近提交: 8d6dafd fix(ci): find 过滤；bbcd35c fix(ci): rpm 补 terminalwidget 数据；2c74509 feat(ci): deb/rpm 打包；9fc2870 chore: bump 0.4.1；5b1ff95 docs
- 断点/下一步: ①公子真机验收：0.3.0 deb 检查更新应提示 v0.4.1（View 路径）；本机试装 CI 的 mudi_0.4.1_amd64.deb（先卸载现有 deb 装通用版属公子决策——会失去 DTK 外观，或留用本地 DTK deb）；rpm 面向 fedora/openEuler 无人真机，遇依赖问题反馈即可；②gh-pages 静态 updates.json 仍待建（走 API 无回归）；③M10 日常打磨包
- 新坑与新决策: ①**QSS token 替换必须长 token 优先**——replace("%accent") 会吃掉 %accentHover 前缀产生非法色值（#0081FFHover），settingsstyle.cpp 用长度降序替换表；②**PaletteChange 事件内严禁同步 relayout**——refreshStyle 的 setIcon 触发 doItemsLayout 在 propagatePaletteChange 栈内重入，QTextEngine::itemize SIGSEGV（点开设置即崩），必须 QMetaObject::invokeMethod QueuedConnection 排队；③**QLabel 无内容时不画 QSS background**——状态点必须用 QFrame + WA_StyledBackground；QSS 属性选择器统一用字符串值（setProperty("srow","true")）；④**deepin 默认禁 qInfo**——/etc 或 QtProject logging rules 关 info 级，验收节流日志要 QT_LOGGING_RULES="*.info=true"（qDebug 同理 "*.debug=true"）；xdotool 对 QMenuBar 顶层 action 首次点击只聚焦不触发、XTest 点击 banner 按钮在 :78 会话无效（点击送达有 focus 圈但信号不触发，kwin 焦点路由怪异）；⑤lupdate 会把上下文变化的旧串标 unfinished，zh_CN 需手动补译；⑥⑦`pkill -f` 自杀坑再次确认两连：模式含同命令行其他文本（[g]db/[b]in 防不住同命令行真实调用）+ **setsid 后台启动偶发静默失败**（命令"成功"但进程没起，验收脚本必须 pgrep 复核再断言）；⑧updater/lastCheckAt 键在 M9 重设计会话已顺手铺好（每次 checkLatest 开头写入）
- 新坑与新决策: ①**冷启动竞态：探测横幅弹出后 500ms 内 launchClient 无条件 `m_banner->hide()` 会杀掉它**——横幅 hide 要判定归属；②herdr status 未运行时输出 `status: not running` 且无 version/compatible 键，exit 0，完全被动；③vendored terminalwidget 的 startShellProgram 只以 isRunning() 为闸，session finished 后可再次 run()；④**开发机装过系统 mudi 包时 DTK 壳命中 /usr/share 旧 qm**——构建树验翻译要 MUDI_UI=generic + staging 跑；⑤xprop 在 Xvfb 读不到 _NET_WM_WINDOW_TYPE，按名筛窗用 getwindowname=="MuDi"；⑥xdotool 合成 Tab 在模态对话框不可靠，用 XTest 坐标点击；⑦`pkill -f` 模式会匹配承载 shell 自杀（加 `[]`；⑯补充：pkill 必须独立成命令，同命令行内出现可匹配文本仍会自杀）；⑧脚本补丁必须断言真打上；⑨rm .X<n>-lock/socket ≠ 释放显示号——残留 Xvfb 占抽象 namespace socket，必须杀进程；⑩**产品决策：状态带与 herdr 侧边栏同屏冗余，已删**——MuDi 只守窗外（通知+托盘），「项目名 (agent)」（cwd basename，回退 agent→paneId）是托盘/通知统一标识；⑪**GitHub Actions 删推 tag 重触发时，先起的新 run 可能未注册就被 run list 清场脚本误杀**——清理脚本不要在重触发后 30s 内跑；⑫CI 修复三连见断点/下一步②，macOS Intel runner（macos-13）排队极慢（1h+），ARM runner 快得多；⑬**QSS token 替换必须长 token 优先**——replace("%accent") 会吃掉 %accentHover 前缀产生非法色值（#0081FFHover），settingsstyle.cpp 用长度降序替换表；⑭**PaletteChange 事件内严禁同步 relayout**——refreshStyle 的 setIcon 触发 doItemsLayout 在 propagatePaletteChange 栈内重入，QTextEngine::itemize SIGSEGV（点开设置即崩），必须 QMetaObject::invokeMethod QueuedConnection 排队；⑮**QLabel 无内容时不画 QSS background**——状态点必须用 QFrame + WA_StyledBackground；QSS 属性选择器统一用字符串值（setProperty("srow","true")）；⑯（并入⑦）xdotool 对 QMenuBar 顶层 action 首次点击只聚焦不触发，第二次点击才 triggered（Xvfb 验收技巧）；⑰lupdate 会把上下文变化的旧串标 unfinished，zh_CN 需手动补译（本次 61 条）
- 待公子手动项: 同断点①；前状态区遗留：M8 收尾自更新 API 真机验证（若 v0.3.0 release 资产尚未核对）

## 6. 会话提示词模板（公子直接粘贴）

**开工（最常用）：**
> 读 docs/plan.md 的「当前状态」「接力协议」「测试方法论」三节和你的长期记忆，继续状态区指派的里程碑，按标准流程实施并自测，完成后向我汇报、更新状态区。

**中断续作：**
> 上个会话可能中断了。先读 docs/plan.md 状态区，再用 git status/log 核实真实进度（以仓库为准），从断点继续，不要重做已完成的工作。

**验收审查：**
> 读 docs/plan.md，对里程碑 Mxx 做验收：对照验收标准逐条验证（代码审查 + 按测试方法论运行时验证），列出偏差并修复，最后更新状态区。
