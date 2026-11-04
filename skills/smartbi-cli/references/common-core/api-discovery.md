# `list` / `search` 参考

直接取数（模型 JSON/MQL/只读 SQL、报表读取/导出）遵循主技能 的已授权只读例外：复用已确认接口，不重复发现或逐接口确认。下文确认规则用于通用业务操作；取数只对影响答案的资源、字段、筛选或口径歧义提问。

外部智能体须区分 API 发现与业务资源发现：`list/describe` 说明可调用的操作，不替代目录/资源搜索。没有预选资源时，以用户提供的名称、ID、链接或业务关键词通过已发现的只读资源接口定位；按资源类型进入模型、报表或其他业务路径。不能把内置白泽 的数据来源上下文视为已存在，也不全量读取所有候选定义。已有明确资源与充分元数据则直接复用。

数据查询场景优先使用已知目录 operationKey；只有该 operationKey 在当前环境未知或不可用时，才以 `list --domain catalogtree` 等有范围的接口发现方式回退。本页下文的注册表发现仅适用于未知操作的一般 第一部分 流程，不覆盖数据查询场景的资源定位顺序。接口发现命令失败时保留 CLI 原始错误并核对安装、连接和当前命令契约，不通过切换输出格式或扩大检索范围掩盖错误。Shell 管道或工具截断后的空匹配不是“没有目录接口”的证据；优先收窄域并检查命令退出状态和输出是否完整。通用 第一部分 确需检索全量注册表且执行工具会截断输出时，先让 CLI 的完整输出写入临时文件，再在同一环境中本地筛选和清理文件；不能把被截断的展示内容当成全集。

本文件为 **SmartBI CLI Skill** 的附属参考，仅规范 `list` / `search` 用法；流程要求以 `SKILL.md` 为准。

**用途**：第一阶段（Discover）— 在最小输出下定位唯一 `operationKey`。按需查阅，勿一次性展开全部条目。

## 共同约定

- `--json`：成功时 `stdout` 为单行 JSON；失败时 `stderr` 默认可为人类可读。
- `--yaml`：成功时 `stdout` 为 YAML 文档；失败时 `stderr` 默认可为人类可读。
- `--agent`：默认成功 `stdout` 为 YAML（`--stream` 下为 NDJSON），且失败时 `stderr` 必须输出结构化 JSON；字段以当前 CLI 版本的实际输出契约为准。
- 自动化流程默认优先使用 `--agent`；仅在下游明确要求 JSON 时使用 `--json`。
- `--verbose`：在列表项中追加较长字段（如 `description`、`tags`、`consumes`、`produces`）。
- `--with-version`：在每个结果项中附加 `apiVersion`。
- `--with-root-version`：在顶层结果中附加 `rootVersion`。
- `--refresh`：本次强制刷新 registry 缓存，优先级高于配置中的 `checkIntervalSeconds`。
- `--config <path>`：指定配置文件路径（默认 `~/.smartbi/config.yaml`）。
- 环境确定后，`list`/`search` 一律带 `--profile <name>`；CLI 版本不支持时按安装指南升级，不省略环境选择（见 `references/common-core/profiles.md`「执行规则」）。

## `smartbi list`

**用途**：枚举当前缓存中的 operation，适合浏览 domain/service 范围。

| 选项                              | 说明                      |
| ------------------------------- | ----------------------- |
| `--domain <domain>`             | 仅列出该 domain             |
| `--service <service>`           | 仅列出该 service            |
| `--verbose`                     | 输出扩展字段                  |
| `--with-version`                | 每个 item 附加 `apiVersion` |
| `--with-root-version`           | 顶层附加 `rootVersion`      |
| `--refresh`                     | 强制刷新缓存                  |
| `--json` / `--yaml` / `--agent` | 见上                      |

输出字段以当前安装 CLI 的 `smartbi list --help` 和实际 `--agent` 响应为准；Skill 不捆绑版本固定的 schema 文件。

**典型用法**：

```bash
smartbi list --profile <PROFILE> --agent
smartbi list --profile <PROFILE> --domain demo --service file --agent
smartbi list --profile <PROFILE> --verbose --with-version --with-root-version --agent
```

## `smartbi search <keyword>`

**用途**：按关键词检索 operation，适合从自然语言或片段定位 `operationKey`。

| 选项                                                                                                                  | 说明                                                                                                                               |
| ------------------------------------------------------------------------------------------------------------------- | -------------------------------------------------------------------------------------------------------------------------------- |
| `--domain` / `--service`                                                                                            | 与 list 相同，缩小范围                                                                                                                   |
| `--in <fields>`                                                                                                     | 可重复；检索字段：`operationKey`、`operationId`、`summary`、`path`、`tags`、`description`、`requestBodySchema`、`responseSchema`（逗号分隔或多次 `--in`） |
| `--fuzzy`                                                                                                           | 模糊匹配                                                                                                                             |
| `--case-sensitive`                                                                                                  | 大小写敏感                                                                                                                            |
| `--limit <n>`                                                                                                       | 最大条数（默认 20）                                                                                                                      |
| `--verbose` / `--with-version` / `--with-root-version` / `--refresh` / `--json` / `--yaml` / `--agent` / `--config` | 同 list                                                                                                                           |

输出字段以当前安装 CLI 的 `smartbi search --help` 和实际 `--agent` 响应为准；Skill 不捆绑版本固定的 schema 文件。

**典型用法**：

```bash
smartbi search getAgentItems --profile <PROFILE> --in description,operationKey,operationId --agent
smartbi search order --profile <PROFILE> --in operationKey,summary --in description,operationKey,operationId --agent
smartbi search "支付" --profile <PROFILE> --in description,tags --fuzzy --limit 10 --agent
```

## 定位与消歧

本节用于未知 API 操作的通用流程，遵循主文件阶段 1；模型、报表等资源搜索仍使用目录接口。

1. 已核实 operationKey 时直接复用。未知操作先按已知 domain/service 限定 `list`；业务域未知时才读取全量注册表。可能超量的完整输出先落临时文件筛选，不以截断输出判断接口不存在。
2. 唯一且明确匹配时进入契约阶段，不重复搜索。通用操作按主文件在执行前确认；已授权只读场景不逐接口确认。
3. 候选无法区分时，仅对相关候选使用 `search <operationKey> --verbose` 补充信息；不逐个遍历全部结果。
4. 业务含义或操作范围仍有歧义时，展示最多五个候选的用途和影响，请用户选择；不要求普通取数用户理解技术接口名。
5. 无匹配时可缩短关键词、限定业务域或按支持的选项放宽一次；仍无匹配则说明当前未找到能力，澄清业务目标，不猜操作名。

接口关键词应使用操作名或 API 业务动作；“去年华东销售额”等属于查询条件，应交给已定位模型的查询接口，而不是用于发现 API。

安装或配置缺失时按[连接指南](setup-and-connection.md)只补缺项；已有有效配置直接复用。
