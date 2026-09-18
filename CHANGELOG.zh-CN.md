# 更新日志

Skillmgmnt 的重要变更。本项目暂不打版本标签，因此按日期分组。
格式参考 [Keep a Changelog][kac]。

[kac]: https://keepachangelog.com/zh-CN/1.1.0/

---

## 2026-09-18

### 变更

- **仓库迁至 [`hcodestack/skillmgmnt`][repo]**，产品名改为 **Skillmgmnt**。
  原为 `hcodestack/skillhub` 与 *Skillhub*。

  GitHub 会重定向旧名，所以**没有任何东西会坏**：网页、`raw` 地址、tarball、
  `git clone` 全部照常解析，已克隆的仓库继续能 pull。你不需要做任何事。
  想顺手改 remote 的话：

  ```bash
  git remote set-url origin https://github.com/hcodestack/skillmgmnt.git
  ```

  该重定向只在旧名没有被重新占用时有效，这也是本仓库把规范 URL 全部更新的原因。

- **有些东西刻意保留旧名**，不要去「修」它们：Python 包 `skillhub_server`、
  配置目录 `~/.skillhub`、`skillhub.db`、`skillhub` 命令、launchd 与 systemd
  单元名、Docker 镜像/容器/卷名，以及 MCP 注册名。改动其中任何一个，
  都会让已有安装的配置或数据库变成孤儿，而用户看不到任何好处。

### 弃用

- **环境变量 `SKILLHUB_*` 改为 `SKILLMGMNT_*`。** 旧前缀仍然可用。
  每个变量先读 `SKILLMGMNT_<名>`，读不到再回落 `SKILLHUB_<名>`，
  服务端和 `skillhub` 启动脚本都是如此，所以已有的 compose 文件、
  服务单元和 shell 配置原封不动也能继续工作。

  服务器启动时会打一行提示，指出它仍在读哪些旧变量。
  该回落将来会移除，但一定会在明确写着「正在移除」的那条记录里移除。

### 新增

- **MCP 提供的技能现在可被发现并呈现。** [SEP-2640][sep] 于 2026-09-13
  把 Skills 扩展并入 MCP。这样提供的技能**从不被安装**——规范要求宿主把取到的
  内容缓存在所有技能发现路径之外——所以扫文件系统看不到它们，
  否则看板会一边报着笃定的数字，一边让 agent 跑着它不知道存在的技能。

  新增 **MCP** 页签：读出每个工具指向哪些服务器，能问的就去问，
  展示它们提供什么、以及在常驻上下文里要花多少。只发 `initialize` 和
  `skills/list`，两者都是只读。**从不读取**你 MCP 配置里的凭据，
  **从不启动** stdio 服务器，**从不探测** loopback 端点。

  把「服务端视角」与「文件系统视角」对账，得到五条治理发现：与本地技能重名、
  无法做内容绑定的条目、超出协议 512 文件 / 16 MiB 上限的技能、
  在 frontmatter 里索要更宽权限的技能，以及已配置但连不上的服务器。

- **两份 README 新增参考来源区**，引用 Skills 扩展的官方来源，
  并致谢本项目借鉴的前作——[qufei1993/skills-hub][sh] 提供了工具目录表、
  `SKILL.md` 有效性校验与内容哈希思路，[lobehub][lh] 提供了工具品牌图标。
  两者都是 MIT，此前都未被致谢。

### 修复

- **Docker 安装会得到空目录。** `deploy/Dockerfile` 设了
  `SKILLHUB_LIBRARY_INDEX`，覆盖掉「不设即直接扫描库」的默认值。
  于是每个容器都会报 *index not readable*，除非用户恰好维护着一个索引文件。
  该变量已移除，改设 `SKILLMGMNT_LIBRARY_ROOT`。
- **技能的库内路径对多数布局是错的。** 它把某个目录名写死在代码里，
  而不是通过配置的库根解析，导致抽屉里的路径、复制按钮和评估提示词
  对所有不用这一种布局的用户都是错的。

---

## 2026-09-02

### 新增

- **首次公开发布。** AI agent 技能的只读观测台：可检索的技能目录、
  横跨 47+ 工具的载入拓扑、从各工具自己的会话日志解析出的真实调用、
  治理发现、确定性安全审查、上游更新追踪，以及一个只读的 MCP 接口。
- **双语界面，默认英文。** 看板以英文打开，右上角一键切简体中文，
  **服务端拼出来的文案也跟着切**——健康发现、导出的治理报告与清理脚本。
  文案存在前后端各一份目录里，每条消息两串并排，译文不会和原文脱节。
- **领域标签多选筛选**，带每标签计数与独立的「未打标签」行。
- **卡片视图**，与总览的表格视图并列。
- **工具品牌图标**，用于 agent 标签与主机页。
- **页签计数**，健康与更新两页，数据取自总览本来就要拉的接口。

### 变更

- **主机页改为工具视图**：每个检测到的工具一张卡片，
  显示它读取全局技能的目录以及被载入的项目，未检测到的折叠收起。
- **互斥视图改用分段控件**而不是开关，外观控件新增**跟随系统**态并实时跟随。
  旧的开关一旦被碰过，就再也回不到跟随系统。
- **清理脚本不再删除散落副本。** 改为移入带日期的回收目录再重建软链，
  判断错了可以撤回而不是丢失。回收目录位置可用 `SKILLMGMNT_TRASH` 覆盖。

[repo]: https://github.com/hcodestack/skillmgmnt
[sep]: https://github.com/modelcontextprotocol/modelcontextprotocol/pull/2640
[sh]: https://github.com/qufei1993/skills-hub
[lh]: https://github.com/lobehub/lobe-icons
