# Smartbi CLI Skill 多 Profile 接入设计

日期：2026-08-20
状态：已批准（用户确认后生效）

## 1. 背景与现状

### 1.1 CLI 侧（@smartbi/cli，本机实测 1.4.0）

- `~/.smartbi/config.yaml` 已原生支持多 profile 结构：`profile: <默认环境名>` + `profiles: {<name>: {serverType, baseUrl, token, timeoutMs...}}`
- `smartbi init --tmpl` 占位符模板已包含该结构（`{{SERVER_TYPE}}` / `{{BASE_URL}}` / `{{TOKEN}}`）
- 各子命令 `--profile` 支持现状（实测）：

| 子命令 | --profile | 说明 |
|---|---|---|
| call | ✅ | 显式选择环境 |
| doc | ✅ | 显式选择，默认 active |
| init | ✅ | 指定默认环境名（默认 dev） |
| list / search / describe | ❌（≤1.4.0） | 仅 `--config`，只能走默认环境 |

设计**假定最新版 CLI 已支持全部子命令的 `--profile`**（见 §2 原则 3 与 §3.5 版本约束）。

### 1.2 Skill 侧（本仓库 skills/smartbi-cli/）

- `SKILL.md` 全局约定按"单 profile"假设书写：配置文件只讲 `~/.smartbi/config.yaml` 单路径，无环境选择/切换/新建流程；Phase 3 示例不带 `--profile`
- `references/call.md` 参数表已列出 `--profile <name>`（部分意识到）
- 错误速查表有 `PROFILE_NOT_FOUND` 但无处理指引
- `references/init.md` 最小可用配置示例已含 profile 结构，"生成配置文件"流程仍按单 profile 生成（active 硬编码 dev）

### 1.3 核心差距

CLI 配置层已支持多 profile，但 skill 操作层（发现→契约→执行→排错全流程）缺少"用哪个环境"的语义：无选择规则、无告知、无新建流程、无相关错误处理。

## 2. 目标与设计原则

**目标**：让 skill 支持多环境（dev/qa/prod）与多客户/多项目双维度的配置与切换，且用户心智负担最小。

**原则**（经确认的决策）：

1. **用户只感知一个环境**：任务开始时确定并告知一次，之后全程静默；`--profile`、默认环境等概念不进入用户视野
2. **配置 = 三要素**（地址、令牌、名字）：首次配置与新增环境共用同一套提问，唯一区别是落点（首次设默认，新增不动默认）
3. **执行零分支**：所有 `smartbi` 命令一律带 `--profile <name>`，不判断目标是否等于默认环境
4. **不动默认环境**：技能永不修改 config.yaml 的 `profile:` 字段，也不引导用户手动修改
5. **向后兼容**：用户未指定环境时，行为与现状完全一致（走默认环境）

## 3. 核心规范

### 3.1 环境确定与告知

- 任务开始时扫描对话，识别环境/客户关键词（环境名、`prod`/`qa`/`dev` 后缀、客户名）匹配现有 profile
- 未指定 → 默认环境（config.yaml 的 `profile:` 字段）
- 多个候选匹配 → 问用户，不猜
- 无匹配 → 走 §3.3 新建流程
- 确定后 MUST 告知一次，格式："本次操作环境：`<name>`"
- 用户中途明确"切到 Y"→ 重新确定并再次告知一次

### 3.2 执行规则

- 会话环境确定后，所有 `smartbi` 命令（`list`/`search`/`describe`/`call`/`doc`）**一律带 `--profile <name>`**
- 兜底（仅一条）：若当前 CLI 版本拒绝 `--profile`（未知选项）→ 去掉 `--profile` 重试该命令，并一句提示："接口列表/契约按默认环境 `<active>` 获取"；`call`/`doc` 保持带 `--profile`（CLI 已支持）

### 3.3 配置三要素流程（首次与新增统一）

触发：首次使用（无配置文件）或用户要求配置新环境 / 指定的环境不存在。

按顺序提问（一次一个）：

1. **名字**：用户已提供环境线索（如"客户A的测试环境"）→ 确认名字；未提供 → 先跳过，最后兜底
2. **地址**：提供 Smartbi 地址 → `serverType: smartbi`；无法提供 → 问 SDK Server 地址 → `serverType: sdk-server`；均无法提供 → 暂停
3. **令牌**：Smartbi 个人令牌
4. **名字（兜底）**：仍未确定时问："这个环境叫什么名字？（不填则默认 dev）"

写入方式（使用 `smartbi init --tmpl` 取占位模板后替换）：

| 场景 | 写入 | 默认环境（profile: 字段） |
|---|---|---|
| 首次 | 新建 `profiles.<name>` | 设为 `<name>` |
| 新增 | 追加 `profiles.<name>` | 不动 |

完成后告知："环境 `<name>` 已配置 ✓"，并告知本次操作环境。

### 3.4 错误处理

| 错误 | 处理 |
|---|---|
| `PROFILE_NOT_FOUND` | 读 config.yaml 列出现有环境 → 用户选择，或走 §3.3 新建 |
| `AUTH_FAILED` | 提示"`<name>` 环境的 token 无效或已过期"，让用户确认该环境凭证 |
| 其他 | Phase 4 通用诊断，报告本次调用所用环境 |

### 3.5 版本约束

- CLI 版本要求：支持全部子命令 `--profile` 的最低版本（当前最新 1.4.0 仅 call/doc 支持，list/search/describe 待上游补全）
- 安装后验证：`smartbi list --help` 输出需包含 `--profile`
- 版本不满足 → §3.2 兜底规则生效，并在输出中说明差异

## 4. 用户旅程（验收场景）

### 场景 1：第一次安装使用

```
用户：帮我分析去年的销售额
Claude：需要先完成首次配置。请提供您的 Smartbi 地址（如 http://127.0.0.1:8080/smartbi）
用户：http://10.10.201.210:8080/smartbi
Claude：请提供您的个人令牌（Smartbi 个人中心可申请）
用户：（粘贴令牌）
Claude：这个环境叫什么名字？（不填则默认 dev）
用户：就叫 prod
Claude：配置已写入 ✓
       本次操作环境：prod
       开始分析去年销售额…（list → describe → call，均带 --profile prod）
```

### 场景 2：使用中新增环境并继续使用

```
用户：帮我配置一个客户A的测试环境，然后在上面分析销售额
Claude：好的。新环境叫什么名字？
用户：customerA-test
Claude：请提供该环境的服务器地址
用户：http://192.168.1.50:8086
Claude：请提供该环境的令牌
用户：（粘贴令牌）
Claude：环境 customerA-test 已配置 ✓
       本次操作环境：customerA-test
       开始分析销售额…（list → describe → call，均带 --profile customerA-test）
```

验收标准：两个场景中，用户全程不接触"profile"、"默认环境"、"active"等概念；执行阶段无环境相关打扰。

## 5. 文件改动清单

| 文件 | 改动 |
|---|---|
| `skills/smartbi-cli/references/profiles.md` | **新建**：完整规范（§3 全部内容 + 版本约束 + 已知限制） |
| `skills/smartbi-cli/SKILL.md` | ①「CLI 安装与配置」补一句：config.yaml 可含多个环境（profiles），默认环境由 `profile:` 字段指定；② 新增「环境选择」全局约定小节（约 10 行，原则 + 指向 profiles.md）；③「自动补齐配置」改为「首次配置」三要素流程；④ Phase 3 示例加注：命令一律带 `--profile <name>`；⑤ 错误速查表补 `PROFILE_NOT_FOUND` 行；⑥ 参考索引加 profiles.md 行 |
| `skills/smartbi-cli/references/init.md` | 「生成配置文件」改为三要素提问；新增"新增环境"分支（追加不动默认） |
| `skills/smartbi-cli/references/call.md` | `--profile` 行补充：所有命令一律带 |
| `skills/smartbi-cli/references/discovery.md` / `describe.md` | 各补一句：命令带 `--profile <name>` |
| `~/.claude/skills/smartbi-cli/` | 已安装副本同步（当前为旧版，缺 doc-index/rhino-template/scenarios，需按发布机制同步） |

## 6. 已知限制与 CLI 待办

- **≤1.4.0 CLI**：`list`/`search`/`describe` 不支持 `--profile`，只能走默认环境（§3.2 兜底生效）
- **上游待办**：补全 `list`/`search`/`describe` 的 `--profile` 支持（本设计的前提假定）
- **命名扁平**：profile 名是 config.yaml 的扁平 key，无嵌套；"环境 × 客户"维度通过命名约定 `<客户>-<环境>` 承载，不强制

## 7. 决策记录

| 决策 | 选择 | 理由 |
|---|---|---|
| 文档组织 | 新建 profiles.md 集中承载 | 单点维护不漂移；SKILL.md 摘要不膨胀；符合"参考文件按需加载" |
| 切换语义 | 显式传参 + 环境告知 | 不动全局 active，无副作用；用户已确认不引导改 active |
| 执行规则 | 全命令一律带 --profile | 零分支、不易错；"契约按默认、执行按目标"的双轨不外露 |
| 首次命名 | 引导用户起名，留空默认 dev | 首次与新增体验统一；命名体系一致 |
| 告知时机 | 任务开始一次 | 避免逐 Phase 播报噪音 |
