---
name: smartbi-cli
description: 广州思迈特软件有限公司（思迈特）提供的 SmartBI 通用业务操作技能。当用户需要连接 SmartBI、查询数据模型或指标模型、对已有报表问数、进行 AI 问数与复杂洞察，或管理智能体、知识库与知识图谱、数据模型、数据源、定时任务与 ETL、消息推送、资源及权限时使用。通过 @smartbi/cli 发现并调用当前环境的 SmartBI API，支持模型 JSON/MQL 查询与只读 SQL 取数。
---

# SmartBI 业务操作

## 流程概览
- **入口路由**：先看用户问句是否命中第二部分的场景索引。命中则加载对应场景文件；未命中则进入第一部分通用流程。组合请求按业务步骤衔接，不让取数场景覆盖调度、推送或资源操作。
- **第一部分：通用 CLI 流程**：任何 `domain.operationId` 的发现→理解→调用→排错流程一致。
- **第二部分：场景指南**：高频业务场景的端到端说明，按需加载。
- **`references/`**：各阶段的详细流程、策略模板与文档路径索引。

目录用途、公共参考与场景参考的划分，以及辅助脚本的适用范围，见 [README.md](README.md)；该说明用于结构导航，不是每次业务执行的前置步骤。

模型取数、报表问数、白泽问数与洞察分别使用第二部分对应场景；资源未定位时先走资源发现，按需加载，不改变其他场景的通用调用流程。

命中资源发现、模型取数、报表问数或白泽问数与洞察场景后，已知 operationKey 按场景文件的最短可验证调用链执行；资源未知时按资源发现场景定位。上述场景已授权只读调用不执行下文第三阶段的逐次确认；下文第一部分的通用接口发现与写操作规则继续用于其他业务操作。

## 触发条件

当用户描述 **BI 业务动作 + 业务对象**，但未显式给出接口名/operationKey（例如"帮我训练模型资源A""基于模型资源A分析去年销售额"）时触发。

当用户问及 BI 相关业务操作（分析、训练、指标查询、报表/问句类需求、定时计划任务等）时触发本技能。触发后进行场景路由判断。

`operationKey` 格式为 `${domain}.${operationId}`（如 `demo.createOrder`、`aichat.getAgentItems`）。`list` 输出结果可直接复制作为 `describe`/`call` 的参数。

---

## 全局约定（所有路径共用）

以下规则适用于 **所有** 执行路径（第一部分通用流程和第二部分场景流程）。先读完全局约定，再进行场景路由判断。

### CLI 安装与配置

- 必须仅通过 **npm 全局安装** 获得可执行命令 `smartbi`：`npm install -g @smartbi/cli@latest`，随后 `smartbi --version` 验证版本 **≥ 2.2.0**，并执行 `smartbi profile list --help` 确认 profile 命令族可用。
- 不得使用 `yarn` / `pnpm` / `bun` / `npx` 或其它程序代替上述 `smartbi`。
- 初始化 必须：由 CLI 全参数生成配置：`smartbi init --server-type <sdk-server|smartbi> --base-url <url> --token <token> [--profile <name>]`；凭证方式按用户选择，可使用字面令牌、环境变量或钥匙串，细节见 `references/common-core/setup-and-connection.md`。
- 配置文件路径：默认 **`~/.smartbi/config.yaml`**，或用户在 init 后 **明确指定** 的 `--config <path>`。不得 在系统中猜测或套用其它文件。config.yaml 可包含多个环境（profiles），默认环境由 `profile:` 字段指定；多环境的选择、配置与错误处理见 `references/common-core/profiles.md`。

### 环境选择（多 profile）

任务开始时在内部确定本次使用的 profile：用户指定连接或客户时按 `references/common-core/profiles.md` 匹配或新建，未指定时用默认 profile（config.yaml 的 `profile:` 字段）。普通业务对话不询问或展示 `dev`、profile 名、`--profile` 等内部配置；多个连接无法区分时只按服务器地址或用户熟悉的业务名称澄清。

环境确定后，**所有** `smartbi` 命令（`list`/`search`/`describe`/`call`/`doc`）**一律带 `--profile <name>`**。

完整规范（确定/告知/配置/错误处理/版本约束）见 `references/common-core/profiles.md`。

### 首次配置

仅补齐所选环境缺失的信息，复用已有地址和有效凭证，不覆盖其他连接。普通业务用户无需理解 profile 名称。

- 未提供地址且无可用配置时，先问：“是否连接 SmartBI 官网体验中心 https://cloud.smartbi.com.cn/smartbi？如果要连接自己的环境，请提供地址。”确认前不写入配置或连接；已有地址或配置时不重复推荐。
- 缺少令牌时说明：登录 SmartBI，在「个人中心 → 我的设置 → 个人访问令牌」中新建。按用户选择使用配置、环境变量或系统钥匙串存储；不主动推荐浏览器授权登录。仅用户明确要求时，按连接指南使用 `smartbi login`，超时或失败不盲目重试。
- 使用 CLI 初始化；`serverType` 仅为 `smartbi` 或 `sdk-server`。准确命令、存储方式及修复流程按需读取 `references/common-core/setup-and-connection.md`，多连接使用 `references/common-core/profiles.md`。

### 参数构造规范

按用户已确认意图和当前接口契约构造请求。SDK 文档用于业务语义；结构、必填、类型、枚举及外层包装以当前 operation 契约为准。`suggestedCall` 仅是模板，不复用占位值。必要技术值自行核实，业务歧义才澄清。

Skill 负责场景、数据口径、接口选择与参数构造。符合契约的请求仍报错或结果异常时，保留错误及影响范围，不通过改写用户条件、更换资源或调用方式掩盖接口问题。

JSON 请求使用临时 UTF-8 文件和 `-d @<绝对路径>`，不使用内联 JSON。请求体生命周期、其他传参方式见 `references/common-core/api-calls.md`；不删除用户已有文件，不把请求或业务结果写入 Skill 目录。多行 Rhino 脚本的请求注入使用 `scripts/scheduled-tasks/inject-script.mjs`。

### 子任务机制

必需的资源 ID 等技术值由当前智能体通过已授权前置操作取得，继承已选场景与已核实接口，不重新路由或重复发现。默认在当前任务内顺序完成；宿主支持且确有收益时才委派子任务，不依赖独立子智能体能力。业务歧义才向用户澄清。

前置操作的依赖、去重及停止规则统一见 `references/common-core/api-calls.md`「前置操作与依赖」；写操作仍须在用户授权范围内。

### 重试与幂等

- **写请求**（POST / PUT / PATCH / DELETE）：仅当 `--idempotent` 指定或 describe 元数据 `idempotent === true` 时才可自动重试，否则最多尝试 1 次
- **可触发的 HTTP 状态重试**（在剩余次数内）：429 / 502 / 503
- **最大尝试次数**：允许重试时最多 3 次（含指数退避与抖动）

### 输出格式

每次调用完成后，按以下固定顺序输出：
1. `operationKey`
2. 最终执行命令
3. 关键结果（`status`/`tid`/核心业务字段）
4. 若失败：原始错误及影响范围；有明确修正依据时才给出下一条命令，不编造接口修复办法

直接取数路径对用户优先展示业务答案、口径与结果范围；上述技术明细仅在排错、审计或用户要求时展示，不逐接口打断业务流程。

### 参考文件按需加载

默认只使用 SKILL.md 本摘要。需要模板/字段映射/检查清单/异常分支时，以及需要加载接口关联文档时，才读取 `references/` 下的对应文件或执行 `smartbi doc`。

# 第一部分：CLI 通用流程

以下阶段定义了从用户意图到 API 调用的完整流程。
通用参数构造、子任务等底层规则在 [全局约定](#全局约定所有路径共用) 中定义，这里只描述各阶段的执行顺序。

## 阶段 0 — 惰性预检

默认不强制在每个新会话先检查安装/配置。按已选场景或通用流程继续；已核实操作不重新发现。

当**任意一次**实际执行 `smartbi`（任意子命令）时，若出现下列情况，才按 [全局约定 · CLI 安装与配置](#cli-安装与配置) 补齐与排查：

- **CLI 不存在**（`command not found` / 退出码 127 等）→ 立即停止，按标准安装流程处理
- **鉴权/凭证**：`AUTH_FAILED` / `FORBIDDEN` / `PROFILE_NOT_FOUND`
- **服务不可达**：`NETWORK_TIMEOUT` / `NETWORK_ERROR` / `UPSTREAM_UNAVAILABLE`
- **配置缺失或不合法**：`INVALID_ARGUMENT` 且 hint 指向 `Config file not found`

其余错误跳过惰性预检，由 第四阶段 诊断处理。

## 阶段 1 — 发现操作

```
smartbi list --profile <name> --agent
```

1. 已核实 operationKey 时直接进入契约阶段，不重新发现。未知操作但业务域已知时，先用 `list --domain <domain>`，必要时再限定 service；业务域未知时才列出注册表。
2. 输出可能过大时先限定范围，仍需完整注册表时落临时文件筛选，不把截断输出当作全集。
3. 若候选唯一且语义明确匹配（用户意图与接口 summary 高度一致，无歧义）→ 直接进入 第二阶段，在 第三阶段 `call` 前向用户展示"准备调用 `<operationKey>`，参数如下…"做一次性确认。不要继续 search，也不要单独停下来等用户确认 operationKey。
4. 若候选唯一但语义匹配度存疑（摘要与意图不完全对应）→ 展示该候选给用户，等用户明确确认后进入 第二阶段。
5. 若存在多条疑似候选无法区分 → 仅对难以区分的候选调用 `smartbi search <operationKey> --profile <name> --verbose --agent` 获取详细信息以消歧。不得 对所有 Top-N 逐个 search。
6. `search` 的关键词检索仅作为补充回退手段（例如用户提供了明确关键词锚点时），不作为默认第一步。

第一阶段 定位约束（必须）：
- 未知操作使用有范围的 `list` 定位；已核实接口直接复用，`search` 用于候选消歧。
- `search --verbose` 仅用于消歧，不得对每个候选盲目执行。
- 存在多候选时 必须 等在候选阶段让用户选择，不得替用户拍板。唯一且明确匹配时可直接进入 第二阶段（在 第三阶段 call 前做一次性确认）。

细节见 `references/common-core/api-discovery.md`。

## 阶段 2 — 核对契约

```
smartbi describe <operationKey> --profile <name> --agent
```

消费字段：`callParameterPlan`、`requestBodySchema`、`requestBodyTemplate`、`docLinks`、`consumes/produces`、`suggestedCall`。按需处理 schema 截断，具体见契约参考。

### 文档加载

需要理解字段语义或组合约束时，优先按 `describe.docLinks` 中的路径加载对应 SDK 说明；已有充分且有效的契约直接复用。文档来源、引用解析和加载边界统一见 `references/common-core/api-contracts.md`，按业务域查文档路径时用 `references/common-core/sdk-doc-index.md`。不加载无关文档或猜测内容。

## 阶段 3 — 执行

```
smartbi call <operationKey> -d @body.json --profile <name> --agent
```
（`<name>` 为本次操作环境；所有命令一律带 `--profile`，见全局约定「环境选择」）

- 参数构造、请求体格式、临时文件清理等底层规则见 [全局约定 · 参数构造规范](#参数构造规范)
- 前置参数依赖机制见 [全局约定 · 子任务机制](#子任务机制)
- 重试策略与幂等门控见 [全局约定 · 重试与幂等](#重试与幂等)

细节见 `references/common-core/api-calls.md`。

## 阶段 4 — 诊断

先核对请求与已取得的当前契约；仅契约缺失或有歧义时执行 `smartbi describe <operationKey> --profile <name> --agent`，必要时加 `--include-raw-schema`。符合契约仍失败时报告接口异常，不变更业务条件试错。
诊断策略参考 `references/common-core/api-calls.md`。

# 第二部分：场景索引

**入口先进行场景路由。** 将业务操作问句与下表比对：
- 命中 → 加载对应场景文件，按场景流程执行
- 未命中 → 第一部分 通用流程
- 加载后场景判定不适用 → 回退 第一部分

| 场景 | 关键触发词 | 场景文件 |
|------|-----------|---------|
| 定时计划任务 | 每天/每周/定时/cron + 查询/统计/推送/ETL | `scenarios/scheduled-tasks.md` |
| 消息推送 | 发送/推送/通知 + 站内消息/企微/钉钉/飞书/邮件 | `scenarios/message-delivery.md` |
| 资源发现 | 列出/查找可用模型或报表，或查询对象未定位 | [资源发现](scenarios/resource-discovery.md) |
| 模型取数 | 数据模型/指标模型字段、参数、取数、统计与比较 | [模型取数](scenarios/model-query.md) |
| 已有报表问数 | 基于已有报表、电子表格、仪表盘、即席查询或透视分析读取数据 | [报表问数](scenarios/report-query.md) |
| 白泽问数与洞察 | 明确白泽/AI问数，或归因、预测、正式报告等复杂洞察 | [白泽问数与洞察](scenarios/baize-analysis.md) |
| 智能体与工具管理 | 明确读取、创建或修改智能体工作流、管理工具 Provider | [智能体与工具管理](scenarios/agent-management.md) |

触发词仅用于快速匹配；精确判定由场景文件 `## 触发` 节负责。仅命中时加载对应文件；执行路径由场景入口确定，参考仅按当前信息缺口读取。已知接口不重新搜索，不顺序尝试多个接口来判断选路。

查询路径优先遵循用户指定的执行方式和已核实资源类型：已有报表优先按报表口径读取；模型聚合、筛选和两期比较直接取数。用户明确白泽或需要归因、预测、正式分析报告、综合大屏时进入白泽场景；已有数据排版、制图或文件转换继续本地处理。范围或口径不明先澄清，不以白泽代替确认，也不因查询失败自动切换场景。

场景按业务步骤组合，不互相加载全部内容。用户另行要求基于报表底层模型分析时需同时保留模型模块并核实口径；定时取数或发送需相应模块；用户另行要求其他分析方式时重新选择场景；白泽执行异常不自动转为直接取数。未包含的模块不声明支持；裁剪版本只调整入口、展示信息和组合能力声明，保留模块的正文无需改写。


场景随 OpenAPI 的扩展可持续追加；新增场景按类型完成端到端验证后才可声明支持，尚未验收的分支须标明边界。

> **开发者**：扩展场景在 `scenarios/` 中声明触发条件与执行路径，通过本表挂接；复用 第一部分 和现有参考，不复制安装、鉴权或接口调用框架。

---

## 常见错误速查

### CLI / 连接类

| 错误 | 原因 | 处理 |
|------|------|------|
| `command not found` (127) / `is not recognized` | 未安装 CLI | → 第零阶段 标准安装 |
| `AUTH_FAILED` (401) | 目标地址、凭证来源、令牌有效性或服务端鉴权不匹配 | 先核对所选环境与 token/env/keyring 来源；仅缺失或失效时补凭证，不修改查询参数或覆盖其他连接 |
| `BIZ_ERROR` (exit 4) | CLI 已识别 HTTP 成功下的业务失败，流式响应同样适用 | 检查 details 中的上游错误；不作为网络错误重试，仍须核对业务结果与轮次状态 |
| `FORBIDDEN` (403) | 用户无权限执行该 operation | 检查 `x-funcPerm` 要求，确认用户角色 |
| `Plain token is disabled by allowPlainToken=false`（AUTH_FAILED） | 字面量 token 被 `allowPlainToken: false` 拦截 | 按 `references/common-core/setup-and-connection.md` 修复凭证来源；保留该 profile 的其他设置和其他环境，不擅自改为明文或覆盖初始化 |
| `KEYRING_UNAVAILABLE` | 配置了 `tokenKeyring: true` 但系统钥匙串不可用（无头/无桌面会话） | 恢复钥匙串可用性，或按用户选择更换凭证来源；遵循 `references/common-core/setup-and-connection.md` 保留现有配置 |
| `NETWORK_TIMEOUT` / `NETWORK_ERROR` | 连接失败或处理超时 | 核实地址、连接和请求耗时，不能仅凭超时认定服务不可达 |
| `UPSTREAM_UNAVAILABLE` (503) | SmartBI 服务未启动或过载 | 确认服务状态后重试 |
| `Config file not found` (INVALID_ARGUMENT) | 配置文件不存在 | → 第零阶段 init 流程 |
| `Config file is invalid`（INVALID_ARGUMENT，附逐条 `- 路径: 原因`） | 配置内容不合法 | 按逐条摘要修正字段，保留现有环境和自定义设置，不用重新 init 覆盖 |
| `PROFILE_NOT_FOUND` | 指定的环境不存在 | `smartbi profile list` 列出现有环境让用户选择，或按 `references/common-core/profiles.md` 新建 |
| `SpecRejected` / `path not in spec` | sdk-server 路径前缀错误 | 确认 `serverType` 与 `baseUrl` 配置一致 |

### API 业务类

| 错误 | 原因 | 处理 |
|------|------|------|
| `getDataModelTrees` 的空 `modelIds` 返回 `[]` | 空数组不是“列出全部模型” | 用目录枚举或搜索找到实际模型 ID，再取字段树 |
| MQL `没有找到层次字段` | `dims` 可能用了技术名或缺少模型要求的层级路径 | 对照当前字段树/模型契约，使用已核实的维度层级标识；不猜英文 `refColumn` |
| MQL `表未找到` / SQL `DAO_ID_IS_NULL` | `from`/`FROM` 可能用了物理表名，或模型视图未解析 | 按模型取数场景的统一元数据规则核实逻辑视图别名，必要时读完整定义的 `views`；不盲改字段或切换查询方式 |
| `选择字段不能为空` | dims/metrics 空或不匹配 | 按模型取数场景的统一元数据规则核对字段、指标和层级标识，不猜字段 |
| HTTP 500 / `Internal Server Error` | 服务端执行失败 | 保留 `tid` 与原始错误；仅请求与当前契约不一致时修正参数 |

---

## 参考（按需加载）

| 文件 | 内容 |
|------|------|
| `references/common-core/setup-and-connection.md` | 安装与配置 |
| `references/common-core/artifact-handling.md` | 仅实际需要下载/读取文件且保留公共文件能力时加载；纯接口查询无需此项 |
| `references/common-core/profiles.md` | 多环境（profile）规范：确定/告知/配置/错误处理 |
| `references/common-core/api-discovery.md` | 第一阶段 接口发现 |
| `references/common-core/api-contracts.md` | 第二阶段 契约理解 |
| `references/common-core/api-calls.md` | 请求构造、参数缺项、执行及重试；仅当前步骤有需要时加载 |
| `references/scheduled-tasks/rhino-script-template.md` | MQL 取数 Rhino JS 模板（定时任务场景共用） |
| `references/common-core/sdk-doc-index.md` | domain → 文档路径索引（第二阶段 文档加载时参照） |
| `scenarios/scheduled-tasks.md` | 定时计划任务 |
| `scripts/scheduled-tasks/inject-script.mjs` | 脚本注入工具：将多行 JS 文件自动 JSON 转义后注入请求体 |
