# `describe` 参考

本文件为 **SmartBI CLI Skill** 的附属参考；流程要求以 `SKILL.md` 为准。

**用途**：第二阶段（Contract）与 第四阶段（Diagnose）— 读取契约与诊断信息。按 Skill 要求，**默认只消费最小字段集**；其余字段仅在升级诊断时查阅。

## 命令形式

```bash
smartbi describe <operationKey> --profile <name> [--json] [--yaml] [--agent] [--include-raw-schema] [--refresh] [--config <path>]
                 [--schema-scope request|response|both] [--schema-budget <bytes>] [--full-schema] [--compact-schema]
                 [--schema-depth <n>] [--max-constraints <n>]
```


| 选项                     | 说明                                                                       |
| ---------------------- | ------------------------------------------------------------------------ |
| `--json`               | 成功时 `stdout` 单行 JSON；失败时 `stderr` 默认可为人类可读                               |
| `--yaml`               | 成功时 `stdout` 输出 YAML 文档；失败时 `stderr` 默认可为人类可读                     |
| `--agent`              | 默认成功 `stdout` 为 YAML，失败时 `stderr` 必须输出结构化 JSON；成功体可含 Agent 侧重字段（见下节） |
| `--include-raw-schema` | 附加 `requestBodySchemaRaw`、`responseSchemaRaw`（保留 OpenAPI 侧 `$ref` 等，供调试） |
| `--refresh`            | 强制刷新 registry 缓存                                                         |
| `--profile <name>`     | 环境名；**所有命令一律带**（环境选择见 `references/common-core/profiles.md`）                     |
| `--config`             | 配置文件路径                                                                   |


## 第二阶段 必读字段（与 Skill 对齐）

执行 `describe --agent` 后，消费以下字段：

- **`callParameterPlan`**：path/query/header/cookie/body 分组与 CLI 示意；无某类参数时，对应键可能省略（仅 `body`、`checklist` 恒在）。
- **`requestBodySchema`**：请求体结构（仅 body，不含 path/query/header）；与 `callParameterPlan` 共同约束如何组 `call -d` / `-F`。
- **`requestBodyTemplate` / `requestBodyTemplateMeta`**：请求骨架及深度/截断信息，可作为构造起点；占位值仍须按业务和契约补齐。
- **`docLinks`**：关联文档列表，按需取每项 path；缺失时再查description或schema中的链接。
- **`schemaDefs` / `schemaDefsMeta` / `warnings`**：引用定义与截断信息；响应侧默认预算8192字节，缺项涉及被截断定义时用 `--schema-budget 0` 或 `--full-schema`，只需一侧时用 `--schema-scope request|response`。不要把被省略的定义当作字段不存在。
- **`consumes` / `produces`**：媒体类型。
- **`suggestedCall`**：单行命令模板（占位符与示例，**不能替代**用户对未知字段的确认）。

按用户已确认的业务意图确定目标值，文档用于解释语义，当前 operation 契约用于约束结构、必填、类型与枚举；冲突时不靠示例覆盖当前契约。详细参数来源见 `references/common-core/api-calls.md`。

资源父节点、目录类型等示例值不能直接当作当前环境事实。创建前通过目录接口核实目标父节点存在、类型适用且有写权限；若示例根节点不存在，按当前环境实际目录定位，不逐个猜 ID。

若服务端报某字段必填，但当前 `describe` 的请求 schema 未声明或未提供该字段，先刷新该 operation 契约并核对业务文档与已有资源的回读结构。仍不一致时明确报告 SDK 契约与运行时不符，不通过反复猜字段或直接覆盖已有资源来试错。

## 按需加载业务文档

首次理解接口或仍有字段语义、组合约束缺项时，优先从 `docLinks` 的 path 定位文档，缺失时再查 `description`、schema 属性说明或摘要中的链接，用 `smartbi doc <path> --profile <name> --agent` 读取对应小节。已有充分且有效的契约不重复加载；只沿本次缺项所需的引用继续读取，不递归展开全部关联文档。文档不可用或未覆盖时按当前 schema 构造；业务语义仍无法确定则澄清或说明限制。

SDK 绝对路径直接传入，相对链接按当前文档目录解析；外部链接按宿主可用能力读取，不猜内容。没有链接时按业务域查下方路径索引。

文档路径索引见 `references/common-core/sdk-doc-index.md`，各 domain 的主要文档目录可从该文件快速定位。

**递归限制（必须）**：
- 递归深度 ≤ 3 层（初始文档为深度 0，最多穿透到深度 3）。
- 已加载路径（绝对路径规范化后）不重复加载，防止循环引用。
- 超出深度的链接在当前上下文中跳过，不报错。

## `--agent` 额外字段（诊断与摘要）

在 `--agent` 成功响应中，通常还包含；具体字段以当前 CLI 版本的实际输出为准，Skill 不捆绑版本固定的 schema 文件：

- `summary`、`description`（可能带 `descriptionTruncated`）、`requiredAll`、`llmBrief`、`constraintsHints`（可能带 `constraintsMeta`）
- `suggestedBodyFile` 是请求文件提示，不替代本次有效参数；`requestBodyTemplateMeta` 的截断信息也须按需核实
- 以及 `idempotent`、`deprecated`、`streaming` 等元信息；当前CLI布尔标志仅值为true时输出，缺失不视为已启用
- `--compact-schema` 去除description/example/default但保留结构；`--schema-depth` 控制请求模板深度（默认6、范围1–20），`--max-constraints` 控制约束提示数量（默认40）。`--schema-scope` 默认both；`--schema-budget 0` 取消预算，`--full-schema` 按声明顺序输出全部定义并取消scope/budget限制。这些是按缺项选用的参数，不作为每次调用前置

用于压缩上下文下的理解与排错，**不替代**完整 `requestBodySchema`。

## 第四阶段 升级

1. 先根据调用失败结构中的 `code`、`status`、`hint`、`details` 等定位（见主技能）。
2. 需要更紧凑的必填与约束提示时，使用 **`describe <operationKey> --profile <name> --agent`**。
3. 仅在仍有契约歧义时，使用 **`describe <operationKey> --profile <name> --agent --include-raw-schema`**。

## 输出契约（机器校验）

- 当前安装 CLI 的 `smartbi describe --help` 和目标 operation 的实际响应

与说明不一致时，以**当前安装的 `smartbi describe --help` 与目标 operation 的实际响应**为准。
