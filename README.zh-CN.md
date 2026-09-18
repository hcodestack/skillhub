<div align="center">

<picture>
  <source media="(prefers-color-scheme: dark)" srcset="docs/assets/hero-topology-dark.png">
  <img src="docs/assets/hero-topology-light.png" alt="Skillmgmnt 载入拓扑——每个技能、每个载入它的工具，按链接健康度着色" width="920">
</picture>

# Skillmgmnt

**AI agent 技能的只读观测台。**
看清你拥有的每个技能、载入它的每个工具、真实的使用情况——以及悄悄坏掉的那些。

[![License: MIT](https://img.shields.io/badge/license-MIT-blue.svg)](LICENSE)
[![Python 3.11+](https://img.shields.io/badge/python-3.11%2B-3776ab.svg)](https://www.python.org)
[![React 19](https://img.shields.io/badge/react-19-61dafb.svg)](web/)
[![可由 agent 安装](https://img.shields.io/badge/install-by%20your%20agent-8a2be2.svg)](AGENTS.md)

[English](README.md) · **简体中文**

<sub>2026-09-18 由 <code>hcodestack/skillhub</code> 改名而来。旧链接会重定向，
你不需要改动任何东西——哪些东西刻意保留了旧名、以及仍可用但已弃用的
<code>SKILLHUB_*</code> 环境变量，见[更新日志](CHANGELOG.zh-CN.md)。</sub>

</div>

---

技能（`SKILL.md` 目录）是 AI 编码工具学会你工作流的方式——而它们膨胀得飞快：
一个库、十几个工具、这里软链、那里拷贝、到处是历史遗留。Skillmgmnt 回答四个
再也没法靠人肉回答的问题：

1. **我有哪些技能？**——整个技能库的可搜索目录
2. **它们被载入到了哪？**——**47+ 个 AI 工具**（Claude Code、Codex、Cursor、
   Gemini CLI、Copilot、Cline……）里，每个技能装在哪个工具、全局还是项目级、
   软链还是实体拷贝
3. **用得多不多？**——从各工具自己的会话日志解析出的真实调用记录
4. **哪里坏了？**——断链、散落副本、内容漂移的重复、正文超标、永远触发不了的
   过短描述，以及对每个技能代码**实际行为**的确定性安全审查

## ✨ 功能

| | |
|---|---|
| 🗺 **载入拓扑** | 三级下钻桑基图——领域 → 技能 → 每一处载入——按链接健康度着色（软链 / 仓库自带 / 散落实体 / 断链），带表格视图 |
| 🔍 **47+ 工具覆盖** | 一个扫描器认识 47+ 个 AI 编码工具的入口目录；多工具共用的目录如实标注（`shared:<dir>`），绝不冒记在某一个工具头上 |
| 📈 **真实用量，不靠感觉** | 从会话日志增量解析的技能调用，分工具分技能——可排序、可筛选、带时间线 |
| 🩺 **治理发现** | 断链（带「整卷未挂载」护栏，一块离线硬盘不会把页面刷成一片红）、散落副本、内容漂移的重复、过短描述、超标正文——每类就地讲清：是什么、怎么来、怎么办 |
| 🛡 **确定性安全审查** | 12 条正则规则 + 跨行匹配窗口，扫描每个技能的全部文件：凭据访问、向外 POST、`curl \| sh`、eval/exec、sudo 等——无模型、无密钥、无网络。命中是带 file:line 证据的信号，不是判决 |
| 🔄 **上游更新** | 落后于上游的 git 型技能一键 `git pull --ff-only`（工作区脏则拒绝）；目录复制型技能报告上游动向 |
| 📋 **发现 → 行动** | 导出治理报告（贴给你的 agent 当工单）或可审阅的清理脚本——**未注释的命令只做可证明安全的事** |
| 🤖 **MCP 原生** | 七个只读工具让 Claude Code / Codex 直接查询 hub：「哪些技能没人用？」「X 安全吗？」「取清理方案」——执行在*你的* agent 里、经*你*确认、在文件所在的机器上 |
| 🖥 **哪儿都能跑** | 单机（内置自上报，零 cron）、Docker、或家用服务器/NAS 上的局域网 hub 聚合你的每台机器 |
| 🔌 **看得见 MCP 提供的技能** | MCP 提供的技能（[SEP-2640](https://github.com/modelcontextprotocol/modelcontextprotocol/pull/2640)）从不被「装」到任何地方——规范要求宿主把它缓存在所有技能发现路径之外，扫文件系统看不到。Skillmgmnt 读出你的工具指向哪些服务器，能问的就去问，报出它们提供什么、以及在上下文里要你花多少 |
| 🌍 **中英双语** | 界面默认英文，右上角一键切中文——**服务端拼的文案也跟着切**（健康发现、导出的治理报告）。前后端各一份目录、每条消息两串并排，译文不会悄悄掉队 |
| 🔒 **只读设计** | Skillmgmnt 只观测；管理仍归你既有的工作流。它永远不会和你的工具打架、不会动你的文件 |

<div align="center">
<picture>
  <source media="(prefers-color-scheme: dark)" srcset="docs/assets/overview-dark.png">
  <img src="docs/assets/overview-light.png" alt="Skillmgmnt 总览——指标磁贴与全量技能目录" width="920">
</picture>
<br><sub>总览页：问题磁贴一键直达对应明细。</sub>
</div>

## 🚀 快速开始

| 你的情况 | 形态 | 安装方式 |
|---|---|---|
| 一台电脑 | **A · 本地** | 下面的向导——无 cron、无 Docker |
| 一台电脑 + Docker | **B · Docker** | 容器 + 宿主机一个轻量 reporter |
| 多台机器 / NAS | **C · 局域网 hub** | server 放常开的机器，其余各装 reporter |

### 形态 A —— 本地（推荐）

```bash
curl -fsSL https://raw.githubusercontent.com/hcodestack/skillhub/main/install.sh | bash
```

或从克隆开始：

```bash
git clone https://github.com/hcodestack/skillmgmnt.git ~/skillhub
cd ~/skillhub && ./setup.sh
```

向导会先亮出它在你机器上检测到的 AI 工具，问清技能库在哪（任何包含
`SKILL.md` 目录的目录树——不需要清单文件、不需要命名约定），构建一次前端，
装好 `skillhub` 命令，并按需提供开机自启与一键注册 MCP 到 Claude Code。
双语、五步、能自己回答的问题绝不问你。

日常只有：

```bash
skillhub          # 启动（如未运行）并打开看板
skillhub status   # 在跑吗？盯着哪个库？
skillhub update   # 拉取最新，需要时自动重建
skillhub stop
```

内置自上报器每 15 分钟扫描一次本机 AI 工具（首轮自动回填历史调用）——
不需要再配任何定时任务。它的运行像其他后台任务一样上健康页，失败绝不静默。

*前置：Python 3.11+ 与 [uv](https://docs.astral.sh/uv)；Node + pnpm 仅首次
构建前端时需要。还没有技能库？`./quickstart.sh` 直接用自带演示库启动。*

### 🤖 不想碰命令行？让你的 agent 替你装

仓库自带一份 **agent 运行手册**（[AGENTS.md](AGENTS.md)），Claude Code、
Codex 等工具照着执行：先检查什么、用你的语言问你什么、怎么帮你找到技能库、
跑哪条非交互安装、装完如何*自证*再向你汇报。把这段贴给你的 agent：

> 在这台机器上安装 Skillmgmnt：把 `https://github.com/hcodestack/skillmgmnt`
> 克隆到 `~/skillhub`，然后阅读检出目录里的 `AGENTS.md` 并按其 Install
> 运行手册执行。只问手册要求你问我的问题。装完后，告诉我看板上显示了什么。

安装会把 hub 注册成 MCP 工具，所以装完那一刻，同一个 agent 就能回答
「哪些技能没人用？」「帮我清理断链」。

### 形态 B —— 单机 Docker

```bash
cd web && pnpm build
docker build -f deploy/Dockerfile.release -t skillhub:latest .
# 编辑 deploy/docker-compose.yml：把你的库挂到 /library
docker compose -f deploy/docker-compose.yml up -d

# 容器扫不到宿主机的 $HOME——reporter 要在宿主机上跑：
reporter/install-launchd.sh http://127.0.0.1:8787    # macOS，每 15 分钟
reporter/install-cron.sh    http://127.0.0.1:8787    # Linux，每 15 分钟
```

### 形态 C —— 局域网 hub（家用服务器 / NAS）

在常开的那台机器按形态 B 跑起来，然后在**每台**工作机上：

```bash
reporter/install-launchd.sh http://<hub-host>:8787   # 或 install-cron.sh
```

每台机器都会出现在「主机」页签；治理发现跨机聚合。不需要一键 git 更新的话，
库挂载加 `:ro`。

## 🧭 工作原理

```
任何主机（笔记本/家用服务器/NAS）                你干活的每台机器
┌──────────────────────────────┐   HTTP POST   ┌──────────────────────────────┐
│ server/  FastAPI + SQLite    │ ◄──────────── │ reporter/skillhub_report.py  │
│  · 自动扫描你的技能库          │   /api/v1/    │  · 扫描 47+ 工具的入口目录     │
│  · 后台：上游检查、安全审查、    │    report     │  · 增量解析会话日志（游标）     │
│    MCP 技能发现               │               │  · 读取 MCP 服务器配置         │
│  · web/ SPA (React 19)       │               │  · 断网 spool 暂存补传         │
└──────────────────────────────┘               │  纯 stdlib，零依赖             │
   │    ▲                                      └──────────────────────────────┘
   │    └───────────────────────────────────── ┌──────────────────────────────┐
   │          HTTP GET  /api/v1/*              │ mcp/skillhub_mcp.py          │
   │                                           │  只读，stdio ↔ 你自己的 agent  │
   │                                           └──────────────────────────────┘
   └──► 你的工具本来就指向的那些 MCP 服务器：
        只发 initialize 和 skills/list，匿名，绝不碰 stdio
```

只有 server 是必需的。技能 id 就是相对库根目录的路径——hub 自己递归扫描
`SKILL.md` 目录；已有外部目录工具的部署可选用索引文件模式。

以上全部是读。唯一向外的路径是 MCP 探测，且被限定在两个只读方法上，
见 [MCP 提供的技能](#-mcp-提供的技能)。

## ⚙️ 配置

全部走环境变量，只有第一个是必填。

| 变量 | 含义 |
|---|---|
| `SKILLMGMNT_LIBRARY_ROOT` | 技能库目录（递归扫描 `SKILL.md`） |
| `SKILLMGMNT_LIBRARY_INDEX` | *可选*：外部预生成的目录 JSON，代替扫描；文件变了自动重同步 |
| `SKILLMGMNT_LIBRARY_SUBDIRS` | *可选*，逗号分隔：只在这些一级子目录下解析技能 |
| `SKILLMGMNT_INSTALLER_SUBDIR` | *可选*：某个由安装器 CLI 管理的子目录（hub 只标注、不代更新） |
| `SKILLMGMNT_ENTITY_WHITELIST` | *可选*：`agent:entry,…`——入口目录里合法的实体目录，不计为散落 |
| `SKILLMGMNT_PROVENANCE_FILE` | *可选*：技能族 → 上游仓库映射 JSON（schema 见 `core/provenance.py`） |
| `SKILLMGMNT_LIBRARY_DISPLAY_ROOT` | 用户视角的库路径（hub 在 Docker 里时让复制出的命令可直接粘贴） |
| `SKILLMGMNT_SELF_REPORT` | `auto`(默认)/`1`/`0`——内置自上报；auto=源码运行且不在容器内时开启 |
| `SKILLMGMNT_DB` / `SKILLMGMNT_HOST` / `SKILLMGMNT_PORT` / `SKILLMGMNT_STATIC` | 存储与服务参数 |

> **注意** · 看板没有鉴权——默认只绑 `127.0.0.1`。仅在可信网络上设
> `SKILLMGMNT_HOST=0.0.0.0`。

> **从 `SKILLHUB_*` 改名而来** · 本项目原名 Skillhub，旧前缀仍然可用：
> 每个变量先读 `SKILLMGMNT_<名>`，读不到再回落 `SKILLHUB_<名>`。
> 已有的 compose 文件和 shell 配置不会断，服务器启动时会打一行提示，
> 指出它仍在读哪些旧变量。该回落已标记弃用，将在明确说明的某个版本里移除。

## 🔌 MCP 提供的技能

技能不再只住在磁盘上。[SEP-2640][sep] 于 2026-09-13 把 Skills 扩展并入 MCP，
服务器可以和 tools 并排提供技能。而规范同时要求宿主把取到的内容缓存在
**所有技能发现路径之外**——所以工具的 skills 目录里什么都不会出现，
像本项目这样的扫描器对它们是按规范失明的。

放着不管，就会变成这个项目本来要抓的那种失效：看板一边报着一个笃定的数字，
一边让 agent 跑着它根本不知道存在的技能。**MCP** 页签补的就是这个缺口。

**这些技能是「可达」不是「已载入」。** 它们没有本地落点、没有链接状态，
所以另起一套词，而不是硬塞成第五种链接。它们的成本是每一轮上下文里的名称和描述，
在真正被用到之前再没有别的——所以这个数字排在最前面，
和总览里本地技能的常驻成本对着看。

<div align="center">
<picture>
  <source media="(prefers-color-scheme: dark)" srcset="docs/assets/mcp-dark.png">
  <img src="docs/assets/mcp-light.png" alt="Skillmgmnt MCP tab — servers, the skills they serve, and the probes deliberately refused" width="920">
</picture>
<br><sub>MCP 页：每台服务器提供什么、在上下文里要花多少、以及哪些探测是刻意放弃的。</sub>
</div>

### 它做什么，以及刻意不做什么

只发 `initialize` 和 `skills/list`，两个都是只读。不调用任何工具、不取任何技能内容：
列表本身就是完整清单，规范就是按「够用」设计的。其余由三条边界兜住：

| 边界 | 为什么 |
|---|---|
| **凭据从不读取** | 你 MCP 配置里的 `env` 或 `headers` 整块压成一个布尔值。值从不离开看到它的那个函数，探测始终匿名。需要认证的服务器只被记下「它需要认证」，然后放着不动。 |
| **stdio 服务器从不启动** | 要枚举它就得把进程拉起来，而拉起进程是在你机器上跑命令，不是观测。 |
| **loopback 端点从不探测** | `localhost` 对每个读到它的人指的是不同机器。hub 连上去碰到的是它自己那台机器上某个无关服务，不是你想指的那个服务器。 |

六种端点状态，其中两种是刻意的拒绝而不是失败：

| 状态 | 含义 |
|---|---|
| **在提供** | 声明了扩展，并列出了它提供的技能 |
| **在提供但不可枚举** | 声明了扩展但不返回列表——规范允许，用于太大、按需生成、或前面挡着网关的目录 |
| **未声明 skills 扩展** | 是 MCP 服务器，但只提供 tools 和 resources |
| **需要认证** | 刻意不探测 |
| **已声明，未启动** | stdio 服务器，刻意不启动 |
| **连不上** | 本机有配置指向它，探测没能完成 |

### 它能发现什么

把「服务端视角」和「文件系统视角」对账，得到五条健康发现：

- **与本地技能重名。** 规范把这列为冒名风险并要求宿主呈现出来，
  因为一个名字绑定的只是它的来源当前提供的字节，不携带任何作者身份。
- **无法做内容绑定的条目**，因为整份是 `dynamic`，或者有文件缺摘要、缺 size。
  审批本应钉死到一组确切的文件上，这些钉不住。
- **超出协议上限的技能**，512 个文件或 16 MiB，不保证在任何合规宿主里能加载。
- **在 frontmatter 里要权限的技能。** 远程服务端写 `allowed-tools`
  是在向你的机器要访问权，不是在描述它自己。
- **已配置但连不上的服务器。**

不需要任何配置。服务器从你的工具本来就有的配置里发现，探测作为后台任务跑，
永远不在请求路径上。

> **生态现状** · 扩展已经 `final`，但还很年轻。官方 SDK 的支持还在合入，
> 消费它的宿主也不多，所以你的服务器目前大多会报「未声明 skills 扩展」。
> 本功能是对着 [Hugging Face 的 MCP 服务器][hf] 验证的，它完整实现了该扩展。

## 🌍 语言

看板**默认英文**，右上角 `EN | 中文` 一键切换。选择按浏览器记住
（`localStorage['skillhub-lang']`），`?lang=zh` / `?lang=en` 可从链接直接指定——
把同一个视图分享给读另一种语言的同事时很顺手。

切换同时覆盖**服务端拼出来的文案**：健康发现的标题与说明、后台任务名、安全规则的
理由，以及导出的治理报告和清理脚本——因为每个请求都带当前语言，而语言也进了前端的
缓存 key。

**改文案（或加第三种语言）** 只动两份目录，前后端各一份：

| | |
|---|---|
| `web/src/lib/i18n.tsx` | 浏览器里渲染的一切。每条消息两串并排：`'nav.health': ['Health', '健康']`。组件用 `const t = useT()`；key 有类型，拼错过不了 `pnpm typecheck` |
| `server/skillhub_server/core/i18n.py` | API 拼出来的文案。同样的形状：`"he.jobs.title": ("Background jobs", "后台任务")`，按请求的 `?lang=` 解析 |

两串写在同一条里是刻意的：译文就在原文下一行，改一个忘一个的漂移在这里做不到。

**落库的是 key，不是文案**——领域标签（`video`、`cn-social` …）与 `standalone` /
`unmanaged` / `external` 这三个合成族名由前端按语言渲染；安全命中的分类与理由在读取时
由 rule id 现算，所以改词或切语言**都不需要重扫**。你自己的目录名（`Cloudflare`、
`my-stuff` …）永远原样显示。

## 🛡 为什么要有安全审查

每个技能都是别人写的、由你的 agent **以你的权限**运行的代码。每次同步时
Skillmgmnt 对技能携带的全部文件跑一遍确定性红旗审查：读取 agent 记忆/凭据
文件、动浏览器会话、直连裸 IP、`curl | sh`、对外部输入 eval/exec、sudo、
写系统路径、向外 POST、未固定版本安装、base64 解码后执行。每条命中带文件、
行号、摘录与理由——供人（或你的 agent）判断的信号，绝不是无声的判决。

## 🧱 刻意不做的事

- **不内置模型评估**——技能质量评分交给专门工具；hub 只生成可直接粘贴的
  评估提示词，不内嵌 LLM 客户端（不放密钥、不产生账单）
- **数据撑不起之前不画趋势图**——日志稀疏时趋势线是表演，可排序的表格才诚实
- **不做对话记忆**——transcripts 已经躺在你各工具自己的目录里
- **不写你的技能**——hub 侧唯一写操作是可选的 git 快进按钮，MCP 面全部只读

## 📚 参考来源

版本历史见[更新日志](CHANGELOG.zh-CN.md)。

**Skills 扩展**

- [SEP-2640: Skills Extension][sep] —— 提案本身，2026-09-13 以 `final` 合入
- [modelcontextprotocol/ext-skills][ext] —— 稳定规范、设计理由，以及实现清单
- [Extension Support Matrix][matrix] —— 各 MCP 客户端支持哪些官方扩展
- [Agent Skills specification][agentskills] —— 技能格式本身，SEP-2640 选择委托给它而不是重新定义
- [Model Context Protocol][mcp] —— 基础协议

**本项目借鉴的前作**

- [qufei1993/skills-hub][skillshub]（MIT）—— 47 工具覆盖背后的目录适配表、
  `SKILL.md` 有效性校验，以及用内容哈希做重复与漂移检测的思路。
  它的 UI 规范也是本项目把互斥视图做成分段控件而不是开关的原因。
- [@lobehub/icons-static-svg][lobehub]（MIT）—— 工具品牌图标

[sep]: https://github.com/modelcontextprotocol/modelcontextprotocol/pull/2640
[ext]: https://github.com/modelcontextprotocol/ext-skills
[matrix]: https://modelcontextprotocol.io/extensions/client-matrix
[agentskills]: https://agentskills.io/specification
[mcp]: https://modelcontextprotocol.io
[hf]: https://github.com/huggingface/hf-mcp-server
[skillshub]: https://github.com/qufei1993/skills-hub
[lobehub]: https://github.com/lobehub/lobe-icons

## 📄 许可

[MIT](LICENSE) © 2026 [hcodestack](https://github.com/hcodestack)
