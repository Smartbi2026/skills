# Smartbi Skills

Smartbi BI 业务操作技能集（[Anthropic SKILL.md](https://docs.anthropic.com/claude/docs/skills) 格式），通过 `@smartbi/cli` 发现与调用 Smartbi API。

## 技能列表

| 技能 | 说明 |
|------|------|
| [smartbi-cli](skills/smartbi-cli/SKILL.md) | Smartbi BI 业务操作入口：AI 对话分析（大模型问数、智能体、知识库/知识图谱构建与训练、数据解释）、数据查询（MQL/DuckDB 取数、指标统计、字段发现）、数据建模（维度/指标/计算成员/命名集管理）、数据源管理（JDBC连接、Schema 与表同步、元数据刷新）、定时任务与 ETL（计划调度、作业流、因果图）、消息推送（企微/钉钉/飞书/邮件/系统消息）、资源与权限管理（目录树、用户/角色/组） |

## 安装

### 方式一：OpenSkills

```bash
# 安装到当前项目（./.claude/skills）
npx openskills install Smartbi2026/skills

# 全局安装（~/.claude/skills，所有项目可用）
npx openskills install Smartbi2026/skills --global

# 多代理环境（.agent/skills，供 Cursor/Windsurf/Aider 等通过 AGENTS.md 使用）
npx openskills install Smartbi2026/skills --universal
```

安装后：

```bash
npx openskills list          # 查看已安装技能
npx openskills sync          # 更新 AGENTS.md 技能表（多代理场景）
npx openskills update        # 更新已安装技能
```

### 方式二：SkillsLM

```bash
# 交互式：选择技能、目标代理（claude-code/cursor/codex/...）、安装范围
npx skillslm install Smartbi2026/skills

# 非交互：安装 smartbi-cli 到 Claude Code 全局
npx skillslm install Smartbi2026/skills --skill smartbi-cli --agent claude-code --global --yes

# 列出仓库中的技能
npx skillslm install Smartbi2026/skills --list
```

### 方式三：手动安装

```bash
git clone https://github.com/Smartbi2026/skills.git
cp -r skills/smartbi-cli ~/.claude/skills/
```

安装后：在任何 Claude Code 会话中描述 Smartbi 业务操作（如"帮我训练模型资源A""分析去年销售额"）即会自动触发该技能。

## 仓库结构

```
skills/
└── smartbi-cli/
    ├── SKILL.md              # 技能主文件（流程骨架：Scenario Router → Discover → Contract → Execute → Diagnose）
    ├── references/           # 按需加载的参考：init（安装配置）、profiles（多环境）、call、describe、discovery、strategy 等
    ├── scenarios/            # 高频业务场景端到端模板（定时任务、消息推送）
    └── scripts/              # 辅助脚本（如 Rhino 脚本注入）
skills.json                   # 技能索引清单（浏览/工具索引用；openskills/skillslm 不读取此文件）
```

## 开发与维护

- 技能格式为 Anthropic SKILL.md：`---` frontmatter 声明 `name` / `description`，正文为执行流程
- 多环境（profile）支持：`--profile <name>` 全命令携带，规范见 `skills/smartbi-cli/references/profiles.md`
- 修改技能文件后，若本机 Claude Code 已安装旧副本，需同步：`cp -r skills/smartbi-cli ~/.claude/skills/`
- CLI 依赖：`npm install -g @smartbi/cli@latest`（要求支持全子命令 `--profile`，当前 1.4.0 仅 `call`/`doc` 支持，见 `references/profiles.md`「版本约束与已知限制」）
