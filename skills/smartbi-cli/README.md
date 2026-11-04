# SmartBI 业务操作技能

广州思迈特软件有限公司提供的 SmartBI 通用业务操作技能，通过 `@smartbi/cli` 调用当前环境开放且有权限的 API。Skill 版本 **2.3.0**，CLI 最低版本 **2.2.0**；二者版本独立管理。路径使用英文，标题与正文使用中文。

2.3.0 更新：统一模型查询元数据入口与完整定义补充规则；完善模型、已有报表及白泽取数路径，校正定时任务与消息发送说明；恢复独立的智能体与工具管理模块；各场景按需加载，公共规则和必要辅助工具共享。

## 完整目录与文件职责

```text
smartbi-cli/  # 可安装、发布的单一技能
├── agents/                                    # 平台展示配置，不承担业务执行
│   └── openai.yaml                            # 技能展示名称、简介和默认调用提示
├── references/                                # 按需读取的公共规则与各业务模块详细说明
│   ├── agent-management/                      # 智能体与工具配置管理，普通问数不加载
│   │   ├── agent-workflows.md                 # 工作流读取、创建、更新、备份、哈希与回读
│   │   └── tool-providers.md                  # Provider列举、读取、解析和配置维护边界
│   ├── baize-analysis/                        # 白泽问数与洞察专用规则
│   │   ├── sessions-and-logs.md               # 白泽执行边界、训练前提、会话、SSE、日志和交付检查
│   │   └── troubleshooting.md                 # 白泽流、轮次、工具节点、沙箱和输出的分层排错
│   ├── common-core/                           # 公共操作指南；连接、API调用、资源发现、查询校验与文件处理，按需读取
│   │   ├── api-calls.md                       # 参数来源、业务缺项、请求构造、调用、子任务和重试
│   │   ├── api-contracts.md                   # 核对describe契约、请求结构与SDK文档
│   │   ├── api-discovery.md                   # 通过list/search发现API操作，区分接口与业务资源
│   │   ├── artifact-handling.md                # 可选文件读取与保真规则，按需使用公共文件工具
│   │   ├── profiles.md                        # 多环境连接选择、追加配置与切换
│   │   ├── query-results.md                   # 查询共用的授权、上下文、范围与完整性；文件细节按需另读
│   │   ├── resource-discovery.md              # 目录搜索、模型与报表类型、可见性和同名消歧
│   │   ├── sdk-doc-index.md                   # API业务域到SDK文档的路径索引
│   │   ├── setup-and-connection.md            # CLI安装、地址与令牌初始化、连接修复
│   │   └── troubleshooting.md                 # CLI、认证、权限、网络及业务失败的公共排错
│   ├── model-query/                           # 模型直接取数专用规则，不依赖白泽会话
│   │   ├── model-query.md                     # 模型类型识别、元数据及 JSON/MQL/SQL 请求、返回与分页差异
│   │   └── query-semantics.md                 # 指标、时间、粒度、关联与统计计算规则；不重复执行流程
│   ├── report-query/                          # 已有报表读取专用规则
│   │   └── report-query.md                    # 报表元数据、有效参数、查询/导出与口径核对
│   └── scheduled-tasks/                       # 定时任务实现参考
│       ├── rhino-script-template.md           # 服务端Rhino取数、分页和消息发送脚本模板
│       └── task-execution.md                  # 任务更新、目录、请求模板、脚本注入和计划状态回读
├── scenarios/                                 # 按用户业务任务选择的独立场景入口
│   ├── agent-management.md                    # 智能体工作流和工具Provider的管理入口
│   ├── baize-analysis.md                      # 白泽AI问数、归因、预测及复杂洞察
│   ├── message-delivery.md                    # 消息与附件发送，核实渠道、接收人及送达状态
│   ├── model-query.md                         # 模型字段、参数、成员与直接取数；覆盖新旧指标模型
│   ├── report-query.md                        # 读取已有报表，保留报表参数、筛选与统计口径
│   ├── resource-discovery.md                  # 列举或搜索模型与报表，核对资源身份和类型
│   └── scheduled-tasks.md                     # 管理定时任务与计划；按任务内容组合其他模块
├── scripts/                                   # 必要的可执行辅助工具，按使用模块分类
│   ├── agent-management/                      # 内部管理辅助能力，仅SDK不足且契约已确认时使用
│   │   └── smartbi_internal.py                # 六个旧版管理命令，支持预览、哈希、备份与回读
│   ├── baize-analysis/                        # 白泽会话辅助工具
│   │   └── baize_session.py                   # 运行、检查或恢复会话；启用下载时加载公共文件工具
│   ├── common-core/                           # 公共辅助工具；按需用于模型、报表或白泽的文件处理
│   │   └── artifact_io.py                     # 解析文件事件、经CLI下载、读取CSV/Excel/Parquet
│   └── scheduled-tasks/                       # 定时任务请求构造工具
│       └── inject-script.mjs                  # 将多行RhinoJS安全转义并注入JSON请求体
├── README.md                                  # 每个目录和文件的用途、场景边界及模块依赖
└── SKILL.md                                   # 统一入口：触发条件、公共规则、通用CLI流程与场景索引
```

`scenarios/` 选择业务路径，`references/` 提供详细规则，`scripts/` 执行必要辅助操作。公共层不反向要求安装业务模块；已明确的简单查询不必加载全部参考。

## 按需加载

主入口负责场景路由和公共调用流程，场景文件负责业务接口选路、最短步骤、补充加载条件和停止边界。参考说明具体请求与业务规则，不重新制定另一套优先级。

模型已定位、接口已选择且元数据充分时，直接组织查询；缺少身份才加载资源发现，缺少字段或参数才补元数据，涉及时间/比率/关联才加载模型语义，范围不明才读取公共结果规则，实际需要文件时才加载文件说明与工具。首次使用所选接口仍须核对必要契约，不通过连续尝试接口代替能力判断。

## 模块职责与修改位置

每个文件按所在模块维护；供多个场景使用的连接、接口调用、资源发现与结果处理规则统一归入 `common-core（公共基础）`。服务其他场景不改变文件归属，平台展示配置也不承担业务执行。

| 修改目标 | 主要位置 | 调整内容 |
|---|---|---|
| 模型取数的进入条件和执行步骤 | `scenarios/model-query.md` | 何时查询模型、如何衔接元数据和结果检查、何时停止或澄清 |
| 数据模型字段、参数、成员及 MQL/SQL/结构化查询构造 | `references/model-query/model-query.md` | 修改“模型类型与查询对象”“资源定位与查询元数据”“结构化查询（JSON）”“MQL”“SQL”等对应小节；保留模型语义和结果校验 |
| 指标算法、日期、分组及关联口径 | `references/model-query/query-semantics.md` | 修改模型业务语义；不在公共结果文件重复定义算法 |
| 默认取数范围、分页和完整性 | `references/common-core/query-results.md` | 修改公共结果规则；模型、报表和白泽仍按各自接口判断结果 |
| 业务资源的搜索和消歧 | `references/common-core/resource-discovery.md` | 修改资源类型范围、匹配及候选选择；不是 API 操作发现 |
| 连接、参数契约或调用异常 | `references/common-core/` 下相应文件 | 修改公共基础能力；不添加特定客户地址、模型 ID 或字段映射 |
| 已有报表或白泽执行 | `scenarios/report-query.md`、`scenarios/baize-analysis.md` 及同名参考目录 | 在各自模块修改；普通模型查询不依赖它们 |
| 智能体工作流与工具配置管理 | `scenarios/agent-management.md`、`references/agent-management/`、`scripts/agent-management/` | 调整管理流程和专用辅助能力，不改普通白泽问数流程 |

只调整模型查询细节时，从模型场景和模型参考入手，无需先改主入口。若要删除整个场景，则按下面“依赖与单场景使用”同步收窄 `SKILL.md`、展示信息及引用。修改文件中的查询规则不会改变 SmartBI 服务端模型定义。

## 业务入口

| 用户需求 | 场景 |
|---|---|
| 有哪些模型或报表、按名称找资源 | [资源发现](scenarios/resource-discovery.md) |
| 查询模型字段、参数、指标或明细 | [模型取数](scenarios/model-query.md) |
| 基于已有报表查看、统计或解读数据 | [报表问数](scenarios/report-query.md) |
| 明确白泽/AI问数，或归因、预测等复杂分析 | [白泽问数与洞察](scenarios/baize-analysis.md) |
| 读取、创建或修改智能体工作流和工具配置 | [智能体与工具管理](scenarios/agent-management.md) |
| 定时执行、调度任务 | [定时任务](scenarios/scheduled-tasks.md) |
| 通过站内消息、邮件、企微等渠道发送信息 | [消息发送](scenarios/message-delivery.md) |

模型取数遵循用户指定的 MQL、JSON 或 SQL 方式；未指定时明细用 JSON 结构化查询，汇总优先 MQL，MQL 无法满足且可保持口径时用 JSON 备选。SQL 不作为自动兜底；先核实模型类型，`TABULAR_DATASET` 按当前契约使用 JSON 路径，新指标模型先定位可查询对象；已知 MQL 不支持时直接选 JSON，无需先失败。

模型取数不依赖训练、白泽会话或Python；已有报表保留自身筛选和计算口径。资源发现只核实身份与可见性，不证明已经取到数据。智能体和工具配置管理走独立管理场景，优先SDK，缺少能力且内部契约已确认时才用管理辅助脚本；其他建模、数据源和资源权限操作使用通用CLI流程。

## 依赖与单场景使用

| 保留模块 | 必要内容 | 可选组合 |
|---|---|---|
| 资源发现 | 资源发现场景与共享资源发现规则、公共连接/API规则 | 定位后由主入口选择保留的执行场景 |
| 模型取数 | 模型场景、模型参考、共享资源发现/查询规则和公共连接/API规则 | 文件读取按需使用公共文件工具 |
| 报表问数 | 报表场景与参考、共享发现/查询规则及文件处理 | 用户另行要求底层模型分析时保留模型取数，并核实口径 |
| 白泽问数与洞察 | 白泽场景、参考、会话工具及共享发现/查询规则 | 下载文件时保留公共文件工具；用户另行要求模型分析时需模型模块 |
| 智能体与工具管理 | 管理场景、同名参考和专用脚本，公共连接/API规则 | 用户要求运行验收时再组合白泽模块 |
| 消息发送 | 消息场景与公共连接/API规则 | 附件读取、定时发送按实际需要增加 |
| 定时任务 | 定时场景、参考、注入脚本与公共连接/API规则 | 取数需模型或报表模块，发送需消息模块 |

各模块只引用自身和公共文件；跨场景属于可选组合，由主入口核实当前保留能力后调度。未保留的能力应明确说明，不能继续加载缺失文件或伪称已经执行。

裁剪时保留目标模块和必要公共文件，调整 `SKILL.md` 的能力描述、场景索引、组合声明和专用工具入口，更新README及平台提示。保留模块的正文不需要改写。模型仅返回接口数据时无需Python或任何专用辅助脚本；需要本地文件读取时才增加对应工具。

## 安装与运行

```bash
npm install -g @smartbi/cli@latest
smartbi --version
```

将完整目录放入目标智能体支持的技能目录，加载 `SKILL.md`。桌面智能体需要命令执行和文件读写能力。连接配置按共享安装指南处理；无地址时可确认连接 SmartBI 官网体验中心 `https://cloud.smartbi.com.cn/smartbi`，个人访问令牌在「个人中心 → 我的设置 → 个人访问令牌」创建，已有配置直接复用。

Python仅用于可选辅助脚本；Excel、Parquet等格式依赖按需安装。脚本支持 `--help`，会话和文件下载支持 `--config` 指定CLI配置。不依赖其他Skill。

发布目录只包含技能说明、平台配置、场景、参考与必要辅助代码。请求、令牌、业务数据、日志、测试与过程材料均放在技能目录外；字节码缓存不属于发布文件。实际接口与渠道能力取决于部署、模型和账号权限。

## 旧版辅助脚本迁移

原平铺脚本 smartbi_internal.py 迁至 scripts/agent-management/smartbi_internal.py，保留六个子命令和原参数，调用方更新路径即可。内部认证仍由显式环境变量提供，不等同CLI profile；创建与更新默认预览。Provider执行、写入和定义上传下载保留契约说明，不宣称已有自动化命令。此模块可整体裁剪，普通模型/报表取数和白泽执行不依赖它。

其他原平铺脚本现位于对应模块目录：白泽会话工具为 `scripts/baize-analysis/baize_session.py`，文件工具为 `scripts/common-core/artifact_io.py`，任务注入工具为 `scripts/scheduled-tasks/inject-script.mjs`。外部程序若固定了旧路径，应同步更新。

白泽会话工具的调用变化：

- `run` 默认不拉取日志；需要时增加 `--collect-logs`，或单独执行 `logs`。
- `run` 退出码 `0` 表示传输成功且本轮 `NORMAL`，业务答案仍需校验；`1` 表示传输失败或本轮失败／中断；`2` 表示本轮仍在运行、缺失或状态未知，不得当作成功。
- 已核实存在的会话用 `run --conv-id` 提交新一轮问题；恢复上次断开的流用 `resume`，不重新提交问句。每轮使用独立输出目录保存证据。

具体参数见各脚本 `--help`，白泽运行与状态处理见[会话参考](references/baize-analysis/sessions-and-logs.md)。
