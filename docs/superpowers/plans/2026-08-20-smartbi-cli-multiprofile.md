# Smartbi CLI Skill 多 Profile 接入实施计划

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 为 skills/smartbi-cli 技能仓库接入多 profile（多环境）能力：新建 `references/profiles.md` 承载完整规范，修订 `SKILL.md` / `init.md` / `call.md` / `discovery.md` / `describe.md` 五个文件。

**Architecture:** 规范集中在 `references/profiles.md`（单点维护），`SKILL.md` 只放简短「环境选择」全局约定小节与指针，其余文件各补一句引用。CLI 侧（@smartbi/cli）已内置 profiles 配置结构（config.yaml 的 `profile:` + `profiles:`），本次不改 CLI。

**Tech Stack:** 纯 Markdown 文档（技能文件），无代码。验证手段为 grep 断言与 git diff 检查。

**设计文档:** `docs/superpowers/specs/2026-08-20-smartbi-cli-multiprofile-design.md`（已批准并提交）

## Global Constraints

- 所有命令（`list`/`search`/`describe`/`call`/`doc`）在执行时**一律带 `--profile <name>`**，无例外、无分支判断（设计原则 3）
- 技能**永不修改** config.yaml 的 `profile:` 字段，也**不引导用户手动修改**（设计原则 4）
- 用户视角只感知一个环境：任务开始时告知一次"本次操作环境：`<name>`"，之后全程静默（设计原则 1）
- 首次配置与新增环境共用同一套三要素提问（名字/地址/令牌），唯一区别：首次设默认环境，新增追加不动默认
- 配置写入 MUST 使用 `smartbi init --tmpl` 占位模板 + 精确替换 `{{SERVER_TYPE}}`/`{{BASE_URL}}`/`{{TOKEN}}`，不得手写配置结构
- 环境名留空时默认 `dev`
- CLI 版本要求：支持全部子命令 `--profile` 的最低版本；安装后验证 `smartbi list --help` 输出包含 `--profile`；≤1.4.0 时按 profiles.md「执行规则」兜底（去掉 `--profile` 重试 + 一句提示）

---

### Task 1: 新建 `references/profiles.md`（规范主体）

**Files:**
- Create: `skills/smartbi-cli/references/profiles.md`

**Interfaces:**
- Consumes: 无（新文件）
- Produces: `profiles.md` 为后续任务（SKILL.md / init.md / call.md / discovery.md / describe.md）提供被引用的规范锚点——引用路径统一为 `references/profiles.md`

- [ ] **Step 1: 创建文件**

写入以下完整内容：

````markdown
# 多环境（Profile）规范

本文件为 **Smartbi CLI Skill** 的附属参考；流程性 MUST 以上级 `SKILL.md` 为准。

**用途**：环境（profile）的确定、告知、配置与错误处理。用户视角只感知"一个环境"；`--profile`、默认环境等是内部细节，不进入用户视野。

## 核心原则

1. **用户只感知一个环境**：任务开始时确定并告知一次，之后全程静默
2. **配置 = 三要素**：地址、令牌、名字；首次与新增共用同一套提问
3. **执行零分支**：所有 `smartbi` 命令一律带 `--profile <name>`
4. **不动默认环境**：不修改 config.yaml 的 `profile:` 字段，不引导用户修改
5. **向后兼容**：用户未指定环境时走默认环境，行为与单环境时代一致

## 环境确定

任务开始时，按以下顺序确定环境：

1. 扫描对话识别环境/客户关键词（环境名、`prod`/`qa`/`dev` 等后缀、客户名），与 config.yaml 的 `profiles` 键匹配
2. 唯一匹配 → 使用该环境
3. 多个匹配 → 问用户，不猜
4. 无匹配且用户提供了新环境的地址/令牌 → 走「配置三要素」新建
5. 未指定任何环境信息 → 默认环境（config.yaml 的 `profile:` 字段）

确定后 MUST 告知用户一次：

> 本次操作环境：`<name>`

用户中途明确"切到 Y"→ 按上述流程重新确定，并再次告知一次。

## 执行规则

- 环境确定后，所有 `smartbi` 命令（`list`/`search`/`describe`/`call`/`doc`）**一律带 `--profile <name>`**，无例外、无分支判断
- 兜底（仅一条）：若当前 CLI 版本拒绝 `--profile`（未知选项错误）→ 该命令去掉 `--profile` 重试，并一句提示："接口列表/契约按默认环境 `<active>` 获取"；`call`/`doc` 保持带 `--profile`

## 配置三要素流程（首次与新增统一）

触发：首次使用（无配置文件）、用户要求配置新环境、指定的环境不存在。

按顺序提问（一次一个）：

1. **名字**：用户已提供环境线索（如"客户A的测试环境"）→ 确认名字；未提供 → 先跳过
2. **地址**：提供 Smartbi 地址 → `serverType: smartbi`；无法提供 → 问 SDK Server 地址 → `serverType: sdk-server`；均无法提供 → 暂停
3. **令牌**：Smartbi 个人令牌
4. **名字（兜底）**：仍未确定时问："这个环境叫什么名字？（不填则默认 dev）"

写入方式：执行 `smartbi init --tmpl` 取占位模板 → 替换 `{{SERVER_TYPE}}`/`{{BASE_URL}}`/`{{TOKEN}}` → 构造 `profiles.<name>` 块：

| 场景 | 写入 | `profile:` 默认环境 |
|------|------|-------------------|
| 首次（无配置文件） | 新建 `profiles.<name>` | 设为 `<name>` |
| 新增 | 追加 `profiles.<name>` | 不动 |

完成后告知："环境 `<name>` 已配置 ✓"，并按「环境确定」告知本次操作环境。

## 错误处理

| 错误 | 处理 |
|------|------|
| `PROFILE_NOT_FOUND` | 读 config.yaml 列出现有环境 → 用户选择，或走「配置三要素」新建 |
| `AUTH_FAILED` | 提示"`<name>` 环境的 token 无效或已过期"，请用户确认该环境凭证 |
| 其他 | 按 SKILL.md Phase 4 通用诊断，报告本次调用所用环境 |

## 版本约束与已知限制

- **版本要求**：CLI 需支持全部子命令的 `--profile`。安装后验证：`smartbi list --help` 输出需包含 `--profile`
- **已知限制**：当前 ≤1.4.0 的 CLI 仅 `call`/`doc` 支持 `--profile`，`list`/`search`/`describe` 不支持 →「执行规则」兜底生效
- **命名扁平**：profile 名是 config.yaml 的扁平 key，无嵌套；"环境 × 客户"维度通过命名约定 `<客户>-<环境>` 承载（如 `customerA-test`），不强制
````

- [ ] **Step 2: 验证文件内容完整**

```bash
grep -c "核心原则\|环境确定\|执行规则\|配置三要素\|错误处理\|版本约束" skills/smartbi-cli/references/profiles.md
```

Expected: 输出 6（六个章节标题全部存在），文件内容与 Step 1 一致。

- [ ] **Step 3: Commit**

```bash
git add skills/smartbi-cli/references/profiles.md
git commit -m "feat(smartbi-cli): 新增多环境（profile）规范参考 profiles.md"
```

---

### Task 2: 修订 `SKILL.md`（六处）

**Files:**
- Modify: `skills/smartbi-cli/SKILL.md`

**Interfaces:**
- Consumes: `references/profiles.md`（Task 1 产物）——本节多处引用它
- Produces: SKILL.md 的「环境选择」小节与「首次配置」小节，供后续任务（init.md 等）对齐话术

- [ ] **Step 1: 版本要求行（现第 29 行）**

原文：
```
- MUST 仅通过 **npm 全局安装** 获得可执行命令 `smartbi`：`npm install -g @smartbi/cli@latest`，随后 `smartbi --version` 验证版本 ≥ 1.2.0。
```
改为：
```
- MUST 仅通过 **npm 全局安装** 获得可执行命令 `smartbi`：`npm install -g @smartbi/cli@latest`，随后 `smartbi --version` 验证版本，并执行 `smartbi list --help` 确认输出包含 `--profile`（多环境功能的最低版本要求；低于支持版本时按 `references/profiles.md`「版本约束与已知限制」兜底）。
```

- [ ] **Step 2: 配置文件路径行（现第 32 行）**

原文：
```
- 配置文件路径：默认 **`~/.smartbi/config.yaml`**，或用户在 init 后 **明确指定** 的 `--config <path>`。MUST NOT 在系统中猜测或套用其它文件。
```
改为：
```
- 配置文件路径：默认 **`~/.smartbi/config.yaml`**，或用户在 init 后 **明确指定** 的 `--config <path>`。MUST NOT 在系统中猜测或套用其它文件。config.yaml 可包含多个环境（profiles），默认环境由 `profile:` 字段指定；多环境的选择、配置与错误处理见 `references/profiles.md`。
```

- [ ] **Step 3: 新增「环境选择」全局约定小节**

在 `### 自动补齐配置` 小节（现第 35 行）**之前**插入：

````markdown
### 环境选择（多 profile）

任务开始时确定本次操作环境并**告知一次**（"本次操作环境：`<name>`"）：用户指定环境/客户时按 `references/profiles.md` 匹配或新建，未指定时用默认环境（config.yaml 的 `profile:` 字段）。

环境确定后，**所有** `smartbi` 命令（`list`/`search`/`describe`/`call`/`doc`）**一律带 `--profile <name>`**；CLI 版本不支持时按 `references/profiles.md`「执行规则」兜底。

完整规范（确定/告知/配置/错误处理/版本约束）见 `references/profiles.md`。
````

- [ ] **Step 4: 「自动补齐配置」改为「首次配置」**

原文（整个小节，现第 35-43 行）：
```
### 自动补齐配置

在首次运行 `smartbi`（任意子命令）时，若检测到 `baseUrl`/`token` 缺失，MUST 分步向用户索要（一次一个问题），全部获取后后台生成配置文件：

1. **先问 Smartbi 地址**：用户提供 → `serverType: smartbi`；用户无法提供 → 询问是否用 SDK Server 地址替代（`serverType: sdk-server`）；仍无法提供 → 暂停。
2. **再问个人令牌**：用户提供后，执行 `smartbi init --tmpl` 获取占位符模板 → 替换 `{{BASE_URL}}`、`{{TOKEN}}`、`{{SERVER_TYPE}}` → 写入 `~/.smartbi/config.yaml`。仅告知用户"配置已写入"，不展示文件内容。
3. `serverType` 取值约束（MUST）：只能是 `sdk-server` 或 `smartbi`，不得使用其他变体。

详细流程与替换规则见 `references/init.md`「生成配置文件」。
```
改为：
```
### 首次配置

在首次运行 `smartbi`（任意子命令）时，若检测到无配置文件或 `baseUrl`/`token` 缺失，MUST 分步向用户索要（一次一个问题），全部获取后后台生成配置文件：

1. **先问地址**：用户提供 Smartbi 地址 → `serverType: smartbi`；用户无法提供 → 问 SDK Server 地址 → `serverType: sdk-server`；均无法提供 → 暂停。
2. **再问令牌**：用户提供后，若环境名仍未确定，最后问名字（"不填则默认 dev"）。
3. 执行 `smartbi init --tmpl` 获取占位符模板 → 替换 `{{SERVER_TYPE}}`、`{{BASE_URL}}`、`{{TOKEN}}`，并把模板中 `profile:` 字段与 `profiles` 下的键改为确认的环境名 → 写入 `~/.smartbi/config.yaml`（该环境同时为默认环境）。仅告知用户"配置已写入"，不展示文件内容。
4. 告知本次操作环境："本次操作环境：`<name>`"。

`serverType` 取值约束（MUST）：只能是 `sdk-server` 或 `smartbi`，不得使用其他变体。

新增环境（追加写入、不动默认环境）的流程见 `references/profiles.md`「配置三要素流程」。详细提问模板见 `references/init.md`。
```

- [ ] **Step 5: Phase 1/2/3 示例统一加 `--profile`**

Phase 1 示例（现第 114 行）原文：
```
smartbi list --agent
```
改为：
```
smartbi list --profile <name> --agent
```

Phase 2 示例（现第 134 行）原文：
```
smartbi describe <operationKey> --agent
```
改为：
```
smartbi describe <operationKey> --profile <name> --agent
```

Phase 3 示例（现第 164 行）原文：
```
smartbi call <operationKey> -d @body.json --agent
```
改为：
```
smartbi call <operationKey> -d @body.json --profile <name> --agent
```
（`<name>` 为本次操作环境；所有命令一律带 `--profile`，见全局约定「环境选择」）

- [ ] **Step 6: 错误速查表补 `PROFILE_NOT_FOUND` 行（现第 209-210 行间）**

在表格 `| \`Config file not found\` (INVALID_ARGUMENT) | 配置文件不存在 | → Phase 0 init 流程 |` 之后插入：
```
| `PROFILE_NOT_FOUND` | 指定的环境不存在 | 列出现有环境让用户选择，或按 `references/profiles.md` 新建 |
```

- [ ] **Step 7: 参考索引表加行（现第 233 行附近）**

在表格 `| \`references/init.md\` | 安装与配置 |` 之后插入：
```
| `references/profiles.md` | 多环境（profile）规范：确定/告知/配置/错误处理 |
```

- [ ] **Step 8: 验证六处改动全部生效**

```bash
grep -n "smartbi list --help\|环境选择\|首次配置\|--profile <name> --agent\|PROFILE_NOT_FOUND\|profiles.md" skills/smartbi-cli/SKILL.md
```

Expected: 输出 6 行以上命中，且 `PROFILE_NOT_FOUND` 行位于错误速查表、`profiles.md` 同时出现在「环境选择」小节与参考索引。

- [ ] **Step 9: Commit**

```bash
git add skills/smartbi-cli/SKILL.md
git commit -m "feat(smartbi-cli): SKILL.md 接入多环境规范（环境选择/首次配置/版本要求）"
```

---

### Task 3: 修订 `references/init.md`（生成配置文件双路径 + 提问模板）

**Files:**
- Modify: `skills/smartbi-cli/references/init.md`

**Interfaces:**
- Consumes: `references/profiles.md` 的「配置三要素流程」（Task 1）
- Produces: init.md 的「生成配置文件（首次/新增）」双路径与三要素提问模板，供执行者照做

- [ ] **Step 1: 「生成配置文件」节改为双路径**

原文（现第 47-71 行整节）：
```
## 生成配置文件

当用户已提供 `baseUrl` 和 `token`，需要生成 `~/.smartbi/config.yaml` 时，按以下流程（用户无感知中间过程）：

### 步骤 1：获取占位符模板

执行 `smartbi init --tmpl`，将 stdout 内容读取到内存（MUST NOT 展示模板内容给用户）：

### 步骤 2：替换占位符

模板使用 `{{PLACEHOLDER}}` 语法，做以下精确字符串替换：

| 占位符 | 替换为 |
|--------|--------|
| `{{SERVER_TYPE}}` | `smartbi` 或 `sdk-server` |
| `{{BASE_URL}}` | 用户提供的地址 |
| `{{TOKEN}}` | 用户提供的令牌 |

约束：
- MUST 精确匹配占位符文本（含双花括号），不做模糊搜索。
- 仅替换上述三个占位符，不修改 `timeoutMs`、`registry` 等其他配置。

### 步骤 3：写入文件

将替换后的内容写入 `~/.smartbi/config.yaml`（父目录不存在时创建）。写入后告知用户"配置已写入 `~/.smartbi/config.yaml`"，不展示文件内容。
```
改为：
```
## 生成配置文件

分「首次配置」与「新增环境」两条路径。三要素（名字/地址/令牌）的提问顺序见「缺项时固定提问模板」。

### 首次配置（无配置文件时）

1. 按「缺项时固定提问模板」收集三要素（一次一个问题）。
2. 执行 `smartbi init --tmpl`，将 stdout 内容读取到内存（MUST NOT 展示模板内容给用户）。
3. 精确替换占位符（模板使用 `{{PLACEHOLDER}}` 语法）：

   | 占位符 | 替换为 |
   |--------|--------|
   | `{{SERVER_TYPE}}` | `smartbi` 或 `sdk-server` |
   | `{{BASE_URL}}` | 用户提供的地址 |
   | `{{TOKEN}}` | 用户提供的令牌 |

   并将模板中 `profile: dev` 与 `profiles` 下的键 `dev` 一并改为确认的环境名。

   约束：
   - MUST 精确匹配占位符文本（含双花括号），不做模糊搜索。
   - 除环境名外，不修改 `timeoutMs`、`registry` 等其他配置。
4. 将替换后的内容写入 `~/.smartbi/config.yaml`（父目录不存在时创建）。该环境同时为默认环境。写入后告知用户"配置已写入 `~/.smartbi/config.yaml`"并告知本次操作环境，不展示文件内容。

### 新增环境（已有配置文件时）

1. 按「缺项时固定提问模板」收集三要素（一次一个问题）。
2. 执行 `smartbi init --tmpl` 获取占位模板，替换 `{{SERVER_TYPE}}`/`{{BASE_URL}}`/`{{TOKEN}}` 后，取出 `profiles` 下的单个环境块，键改为新环境名。
3. 将该块**追加**到现有 config.yaml 的 `profiles` 下。
4. MUST NOT 修改现有 `profile:` 字段与其他环境。
5. 写入后告知："环境 `<name>` 已配置 ✓"，不展示文件内容。
```

- [ ] **Step 2: 配置字段说明补环境名（现第 73-82 行节后）**

在「配置字段说明」列表末尾追加一条：
```
- **环境名**（`profile:` 字段与 `profiles.<name>` 键）：由用户确认；用户未提供线索时最后问（"不填则默认 dev"）。
```

- [ ] **Step 3: 提问模板补名字兜底（现第 84-108 行）**

原文最后一段：
```
**第二步——再问令牌：**

```text
已记录服务器地址。请提供 Smartbi 个人令牌（可登录 Smartbi，在个人中心申请）。
```

在你补齐前，我会先暂停，不会继续调用 smartbi 命令。
```
在其后追加：
```
**第三步——名字兜底：**

```text
这个环境叫什么名字？（不填则默认 dev）
```

- 用户提供 → 用作环境名（含 `profile:` 字段与 `profiles.<name>` 键）
- 用户留空或说"都行" → 环境名 `dev`
- 用户在对话中已给出环境线索（如"客户A的测试环境"）→ 第一步先确认名字，跳过本步
```

- [ ] **Step 4: 验证改动生效**

```bash
grep -n "首次配置\|新增环境\|名字兜底\|环境名" skills/smartbi-cli/references/init.md
```

Expected: 输出 5 行以上命中：双路径标题（首次配置/新增环境）、提问模板第三步、字段说明环境名。

- [ ] **Step 5: Commit**

```bash
git add skills/smartbi-cli/references/init.md
git commit -m "feat(smartbi-cli): init.md 支持首次配置与新增环境双路径"
```

---

### Task 4: 修订 `call.md` / `discovery.md` / `describe.md`（各补 `--profile` 引用）

**Files:**
- Modify: `skills/smartbi-cli/references/call.md`
- Modify: `skills/smartbi-cli/references/discovery.md`
- Modify: `skills/smartbi-cli/references/describe.md`

**Interfaces:**
- Consumes: `references/profiles.md`（Task 1）作为引用锚点

- [ ] **Step 1: call.md 的 `--profile` 行补充说明（现第 32 行）**

原文：
```
| `--profile <name>`      | 使用配置中的指定 profile            |
```
改为：
```
| `--profile <name>`      | 环境名；**所有命令一律带**（环境选择见 `references/profiles.md`） |
```

- [ ] **Step 2: discovery.md「共同约定」补一条（现第 17 行 `--config` 行后）**

在：
```
- `--config <path>`：指定配置文件路径（默认 `~/.smartbi/config.yaml`）。
```
之后插入：
```
- 环境确定后，`list`/`search` 一律带 `--profile <name>`；CLI 版本不支持时去掉并提示（见 `references/profiles.md`「执行规则」）。
```

- [ ] **Step 3: describe.md 命令形式与选项表补 `--profile`（现第 10 行与选项表）**

第 10 行原文：
```
smartbi describe <operationKey> [--json] [--yaml] [--agent] [--include-raw-schema] [--refresh] [--config <path>]
```
改为：
```
smartbi describe <operationKey> [--profile <name>] [--json] [--yaml] [--agent] [--include-raw-schema] [--refresh] [--config <path>]
```

选项表在 `| \`--refresh\` | 强制刷新 registry 缓存 |` 行之后插入：
```
| `--profile <name>`     | 环境名；**所有命令一律带**（环境选择见 `references/profiles.md`） |
```

- [ ] **Step 4: 验证三处改动**

```bash
grep -n "一律带\|--profile" skills/smartbi-cli/references/call.md skills/smartbi-cli/references/discovery.md skills/smartbi-cli/references/describe.md
```

Expected: call.md 命中 1 行（选项表）、discovery.md 命中 1 行（共同约定）、describe.md 命中 2 行（命令形式 + 选项表）。

- [ ] **Step 5: Commit**

```bash
git add skills/smartbi-cli/references/call.md skills/smartbi-cli/references/discovery.md skills/smartbi-cli/references/describe.md
git commit -m "feat(smartbi-cli): call/discovery/describe 参考补 --profile 规范引用"
```

---

### Task 5: 同步已安装副本 `~/.claude/skills/smartbi-cli/`

**Files:**
- Modify: `/Users/wahsonleung/.claude/skills/smartbi-cli/`（技能运行时的实际加载副本）

**Interfaces:**
- Consumes: Task 1-4 的全部产物（profiles.md 新建 + 5 个修订文件）

**注意：** 已安装副本是旧版（缺 `doc-index.md`/`rhino-template.md`/`scenarios/`），只同步本次改动的 6 个文件，不触碰副本中其他文件。

- [ ] **Step 1: 复制 6 个改动文件到已安装副本**

```bash
cp skills/smartbi-cli/references/profiles.md ~/.claude/skills/smartbi-cli/references/
cp skills/smartbi-cli/SKILL.md ~/.claude/skills/smartbi-cli/
cp skills/smartbi-cli/references/init.md ~/.claude/skills/smartbi-cli/references/
cp skills/smartbi-cli/references/call.md ~/.claude/skills/smartbi-cli/references/
cp skills/smartbi-cli/references/discovery.md ~/.claude/skills/smartbi-cli/references/
cp skills/smartbi-cli/references/describe.md ~/.claude/skills/smartbi-cli/references/
```

- [ ] **Step 2: 验证副本与仓库一致**

```bash
diff -q skills/smartbi-cli/SKILL.md ~/.claude/skills/smartbi-cli/SKILL.md
diff -q skills/smartbi-cli/references/profiles.md ~/.claude/skills/smartbi-cli/references/profiles.md
```

Expected: 两个 diff 均无输出（文件一致）。

- [ ] **Step 3: 汇总验证（全仓库交叉引用完整性）**

```bash
cd /Users/wahsonleung/dev/smartbi/skills
git grep -l "profiles.md" -- skills/smartbi-cli/
```

Expected: 输出 SKILL.md、references/init.md、references/call.md、references/discovery.md、references/describe.md（5 个文件均引用 profiles.md）。

- [ ] **Step 4: 行为验证——兜底路径与 CLI 现状一致**

本机 CLI 为 1.4.0（`list` 不支持 `--profile`）。实测兜底路径的触发形态，确认 profiles.md「执行规则」描述属实：

```bash
smartbi list --profile dev --agent 2>&1 | head -5
```

Expected: 输出包含 `unknown option` / `--profile` 相关的参数解析错误（说明 1.4.0 下 `list` 带 `--profile` 会被拒绝 → 兜底规则应触发：去掉 `--profile` 重试 + 一句提示）。

注意：本任务不改仓库内容，无需 commit（副本在仓库外）。
