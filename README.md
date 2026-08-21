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

## 更新

发布新版本（更新本仓库并 push）后，已安装用户按安装方式更新：

| 安装方式 | 更新命令 |
|---|---|
| OpenSkills | `npx openskills update smartbi-cli`（更新全部：`npx openskills update`） |
| SkillsLM | `npx skillslm update Smartbi2026/skills` |
| 手动安装 | `git pull` 后重新 `cp -r skills/smartbi-cli ~/.claude/skills/` |

说明：

- `update` 从安装时记录的来源重新拉取最新内容并覆盖，无需卸载重装
- 手动复制安装的技能没有来源记录，`npx openskills update` 会跳过它——先执行一次 `npx openskills install` 即可启用后续自动更新
- `npx` 工具本身每次运行都使用 npm 最新版，无需单独更新

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
