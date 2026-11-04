# 白泽问数与洞察

## 触发

用户明确指定白泽或 AI 问数，或要求正式分析报告、原因归因、预测、行动建议、综合大屏，以及依赖服务端业务知识或多工具协同的复杂分析。用户明确直接取数或本地分析时优先遵循；已有结果的排版、制图或文件转换继续本地处理。

## 执行

1. 核实目标资源、Agent 及其能力；资源未知时使用 [公共资源发现规则](../references/common-core/resource-discovery.md)，不把目录类型直接当作会话请求类型。
2. 按 [白泽会话与日志](../references/baize-analysis/sessions-and-logs.md) 创建或恢复会话、执行问数并处理 SSE 与多轮工具调用。
3. 核对最终状态、业务答案和工具证据；文件交付须下载、回读，预览不等于完整数据。文件处理复用 [公共文件工具](../references/common-core/artifact-handling.md)。
4. 返回结论、必要口径及交付物；查询错误不能以转白泽或换模型掩盖。

## 边界

执行步数、并发、知识优先级等复用当前部署，不固化服务端运行配置；需要理解行为时读 [洞察行为](../references/baize-analysis/sessions-and-logs.md)。白泽不能代替资源、字段、时间或指标歧义的澄清。白泽执行异常时保留会话状态和原始错误，说明受影响范围，不自动转为直接取数或本地分析。资源修改、发布、推送继续走对应操作与授权流程。

## 接口与加载条件

- 首次执行：读取会话参考中的请求契约和执行步骤；已知 Agent、资源与有效配置直接复用，仅 Agent 未知时查 `aichat.getAgentItems`。
- 新建流式执行：`aichat.createConversation` → `aichat.queryRpc`；用户指定同步时核对 `aichat.queryRpcSync` 的独立包装，不先试流式再试同步。随包会话脚本仅适用于流式路径。
- 流断开或轮次状态不明：读取会话参考的恢复与轮次小节，使用同一会话的 `queryRpcResume`、`getConversationRounds`，不创建重复会话。
- Agent 明确依赖训练、知识或向量资源：读取会话参考的训练边界，按需核实所需前提；普通直接取数不加载此流程。
- 产生文件时才加载文件处理；出现认证、流、工具或沙箱错误时才加载[白泽排障](../references/baize-analysis/troubleshooting.md)。
