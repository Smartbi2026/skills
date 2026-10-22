# `describe` 参考

本文件为 **SmartBI CLI Skill** 的附属参考；流程性 MUST 以上级 `SKILL.md` 为准。

**用途**：Phase 2（Contract）与 Phase 4（Diagnose）— 读取契约与诊断信息。按 Skill 要求，**默认只消费最小字段集**；其余字段仅在升级诊断时查阅。

## 命令形式

```bash
smartbi describe <operationKey> --profile <name> [--json] [--yaml] [--agent] [--include-raw-schema] [--refresh]
                    [--schema-scope request|response|both] [--schema-budget <bytes>] [--full-schema] [--compact-schema]
                    [--schema-depth <n>] [--max-constraints <n>] [--config <path>]
```


| 选项                     | 说明                                                                       |
| ---------------------- | ------------------------------------------------------------------------ |
| `--json`               | 成功时 `stdout` 单行 JSON；失败时 `stderr` 默认可为人类可读                               |
| `--yaml`               | 成功时 `stdout` 输出 YAML 文档；失败时 `stderr` 默认可为人类可读                     |
| `--agent`              | 默认成功 `stdout` 为 YAML，失败时 `stderr` 必须输出结构化 JSON；成功体可含 Agent 侧重字段（见下节） |
| `--include-raw-schema` | 附加 `requestBodySchemaRaw`、`responseSchemaRaw`（保留 OpenAPI 侧 `$ref` 等，供调试） |
| `--schema-scope <scope>` | `schemaDefs` 范围：`request` / `response` / `both`（默认 `both`） |
| `--schema-budget <bytes>` | 响应侧 `schemaDefs` 字节预算（默认 8192；`0` 表示不限） |
| `--full-schema` | 输出全部 `schemaDefs`（按声明顺序，禁用 scope/budget） |
| `--compact-schema` | 去除 `schemaDefs` 中的 description/example/default，保留结构 |
| `--schema-depth <n>` | `requestBodyTemplate` 最大深度（默认 6，范围 1–20） |
| `--max-constraints <n>` | `constraintsHints` 最大条数（默认 40） |
| `--refresh`            | 强制刷新 registry 缓存                                                         |
| `--profile <name>`     | 环境名；**所有命令一律带**（环境选择见 `references/profiles.md`）                     |
| `--config`             | 配置文件路径                                                                   |


## Phase 2 必读字段（与 Skill 对齐）

执行 `describe --agent` 后，消费以下字段：

- **`callParameterPlan`**：path/query/header/cookie/body 分组与 CLI 示意；无某类参数时，对应键可能省略（仅 `body`、`checklist` 恒在）。
- **`requestBodySchema`**：请求体结构（仅 body，不含 path/query/header）；与 `callParameterPlan` 共同约束如何组 `call -d` / `-F`。
- **`requestBodyTemplate`**（2.2.0+）：按契约生成的请求体骨架（含 `requestBodyTemplateMeta` 深度/截断信息）；优先以它为起点组装 body，再按文档与用户输入补值。
- **`docLinks`**（2.2.0+）：CLI 自动提取的关联文档列表，每项含 `title` / `path` / `source`；文档加载优先使用该字段，取每项的 `path`。
- **`schemaDefs` / `schemaDefsMeta`**：schema 组件定义。2.2.0 起默认有字节预算，被截断时 `schemaDefsMeta` 与 `warnings` 会说明；需要完整定义时追加 `--schema-budget 0` 或 `--full-schema`。
- **`consumes` / `produces`**：媒体类型。
- **`suggestedCall`**：单行命令模板（占位符与示例，**不能替代**用户对未知字段的确认）。

字段值规则仍以主 Skill 为准：**用户输入或上下文已知事实优先；其次以文档为依据，schema 兜底**（详见主 Skill「文档优先级原则」）。

## 文档加载（优先获取，不可用时兜底）

`describe` 完成后，优先使用输出中的 `docLinks` 字段识别文档来源，通过 `smartbi doc <path> --profile <name> --agent` 加载并递归穿透；`docLinks` 缺失时再按主 Skill Phase 2「文档加载」步骤 1 的其余方式扫描。文档有定义时以其为基准理解 schema；文档不可用或未覆盖的字段，直接使用 schema。

文档路径索引见 `references/doc-index.md`，各 domain 的主要文档目录可从该文件快速定位。

**递归限制（MUST）**：
- 递归深度 ≤ 3 层（初始文档为深度 0，最多穿透到深度 3）。
- 已加载路径（绝对路径规范化后）不重复加载，防止循环引用。
- 超出深度的链接在当前上下文中跳过，不报错。

## `--agent` 额外字段（诊断与摘要）

在 `--agent` 成功响应中，通常还包含；具体字段以当前 CLI 版本的实际输出为准，Skill 不捆绑版本固定的 schema 文件：

- `summary`、`description`（可能带 `descriptionTruncated`）、`requiredAll`、`llmBrief`、`constraintsHints`（含 `constraintsMeta`）
- `requestBodyTemplate`、`docLinks`、`suggestedBodyFile`
- `idempotent`、`deprecated`、`streaming` 等元信息——2.2.0 起**仅在值为 true 时出现**，缺失即视为 false

用于压缩上下文下的理解与排错，**不替代**完整 `requestBodySchema`。

## Phase 4 升级

1. 先根据调用失败结构中的 `code`、`status`、`hint`、`details` 等定位（见主 Skill）。业务错误看 `details.upstreamMessage` / `upstreamErrorCode` / `upstreamBodyPreview`。
2. 需要更紧凑的必填与约束提示时，使用 **`describe <operationKey> --profile <name> --agent`**。
3. `schemaDefs` 被预算截断（`schemaDefsMeta` 或 warnings 提示 omitted）时，追加 **`--schema-budget 0`** 或 **`--full-schema`**；只需要一侧定义时用 `--schema-scope request|response` 降噪。
4. 仅在仍有契约歧义时，使用 **`describe <operationKey> --profile <name> --agent --include-raw-schema`**。

## 输出契约（机器校验）

- 当前安装 CLI 的 `smartbi describe --help` 和目标 operation 的实际响应

与说明不一致时，以**当前安装的 `smartbi describe --help` 与目标 operation 的实际响应**为准。
