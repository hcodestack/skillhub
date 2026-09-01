<div align="center">

<picture>
  <source media="(prefers-color-scheme: dark)" srcset="docs/assets/hero-topology-dark.png">
  <img src="docs/assets/hero-topology-light.png" alt="Skillhub 载入拓扑——每个技能、每个载入它的工具，按链接健康度着色" width="920">
</picture>

# Skillhub

**AI agent 技能的只读观测台。**
看清你拥有的每个技能、载入它的每个工具、真实的使用情况——以及悄悄坏掉的那些。

[![License: MIT](https://img.shields.io/badge/license-MIT-blue.svg)](LICENSE)
[![Python 3.11+](https://img.shields.io/badge/python-3.11%2B-3776ab.svg)](https://www.python.org)
[![React 19](https://img.shields.io/badge/react-19-61dafb.svg)](web/)
[![可由 agent 安装](https://img.shields.io/badge/install-by%20your%20agent-8a2be2.svg)](AGENTS.md)

[English](README.md) · **简体中文**

</div>

---

技能（`SKILL.md` 目录）是 AI 编码工具学会你工作流的方式——而它们膨胀得飞快：
一个库、十几个工具、这里软链、那里拷贝、到处是历史遗留。Skillhub 回答四个
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
| 🔒 **只读设计** | Skillhub 只观测；管理仍归你既有的工作流。它永远不会和你的工具打架、不会动你的文件 |

<div align="center">
<picture>
  <source media="(prefers-color-scheme: dark)" srcset="docs/assets/overview-dark.png">
  <img src="docs/assets/overview-light.png" alt="Skillhub 总览——指标磁贴与全量技能目录" width="920">
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
git clone https://github.com/hcodestack/skillhub.git ~/skillhub
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

> 在这台机器上安装 Skillhub：把 `https://github.com/hcodestack/skillhub`
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
│  · 后台：上游检查、安全审查     │    report     │  · 增量解析会话日志（游标）     │
│  · web/ SPA (React 19)       │               │  · 断网 spool 暂存补传         │
└──────────────────────────────┘               │  纯 stdlib，零依赖             │
        ▲                                      └──────────────────────────────┘
        └───────────────────────────────────── ┌──────────────────────────────┐
              HTTP GET  /api/v1/*              │ mcp/skillhub_mcp.py          │
                                               │  只读，stdio ↔ 你自己的 agent  │
                                               └──────────────────────────────┘
```

只有 server 是必需的。技能 id 就是相对库根目录的路径——hub 自己递归扫描
`SKILL.md` 目录；已有外部目录工具的部署可选用索引文件模式。

## ⚙️ 配置

全部走环境变量，只有第一个是必填。

| 变量 | 含义 |
|---|---|
| `SKILLHUB_LIBRARY_ROOT` | 技能库目录（递归扫描 `SKILL.md`） |
| `SKILLHUB_LIBRARY_INDEX` | *可选*：外部预生成的目录 JSON，代替扫描；文件变了自动重同步 |
| `SKILLHUB_LIBRARY_SUBDIRS` | *可选*，逗号分隔：只在这些一级子目录下解析技能 |
| `SKILLHUB_INSTALLER_SUBDIR` | *可选*：某个由安装器 CLI 管理的子目录（hub 只标注、不代更新） |
| `SKILLHUB_ENTITY_WHITELIST` | *可选*：`agent:entry,…`——入口目录里合法的实体目录，不计为散落 |
| `SKILLHUB_PROVENANCE_FILE` | *可选*：技能族 → 上游仓库映射 JSON（schema 见 `core/provenance.py`） |
| `SKILLHUB_LIBRARY_DISPLAY_ROOT` | 用户视角的库路径（hub 在 Docker 里时让复制出的命令可直接粘贴） |
| `SKILLHUB_SELF_REPORT` | `auto`(默认)/`1`/`0`——内置自上报；auto=源码运行且不在容器内时开启 |
| `SKILLHUB_DB` / `SKILLHUB_HOST` / `SKILLHUB_PORT` / `SKILLHUB_STATIC` | 存储与服务参数 |

> **注意** · 看板没有鉴权——默认只绑 `127.0.0.1`。仅在可信网络上设
> `SKILLHUB_HOST=0.0.0.0`。看板界面目前以中文为主，欢迎 i18n 贡献。

## 🛡 为什么要有安全审查

每个技能都是别人写的、由你的 agent **以你的权限**运行的代码。每次同步时
Skillhub 对技能携带的全部文件跑一遍确定性红旗审查：读取 agent 记忆/凭据
文件、动浏览器会话、直连裸 IP、`curl | sh`、对外部输入 eval/exec、sudo、
写系统路径、向外 POST、未固定版本安装、base64 解码后执行。每条命中带文件、
行号、摘录与理由——供人（或你的 agent）判断的信号，绝不是无声的判决。

## 🧱 刻意不做的事

- **不内置模型评估**——技能质量评分交给专门工具；hub 只生成可直接粘贴的
  评估提示词，不内嵌 LLM 客户端（不放密钥、不产生账单）
- **数据撑不起之前不画趋势图**——日志稀疏时趋势线是表演，可排序的表格才诚实
- **不做对话记忆**——transcripts 已经躺在你各工具自己的目录里
- **不写你的技能**——hub 侧唯一写操作是可选的 git 快进按钮，MCP 面全部只读

## 📄 许可

[MIT](LICENSE) © 2026 [hcodestack](https://github.com/hcodestack)
