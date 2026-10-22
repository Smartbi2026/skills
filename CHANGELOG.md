# 更新日志

## 2.2.0 — 2026-10-22

- 适配 `@smartbi/cli` 2.2.0，基线提升至 ≥2.2.0。
- 新增浏览器授权登录（`smartbi login`，OAuth2 + PKCE）与登出（`smartbi logout`）可选凭证方式；登录仅支持 keyring 型 profile，授权链接在 stderr，固定回调 `127.0.0.1:24680`。
- 明确 `call` 退出码语义：HTTP 2xx 但顶层 `success:false` 返回 `BIZ_ERROR`（exit 4），流式响应同样检查；业务错误不可重试。
- `describe` 增强：消费 `docLinks`、`requestBodyTemplate`；补充 `--schema-scope`/`--schema-budget`/`--full-schema`/`--compact-schema` 等选项与 schema 截断处理。
- 补充 `profile add --timeout-ms`/`--base-url-env`、默认超时 300000、网络超时分类。

## 2.1.0 — 2026-09-22

- 新增数据查询路由，按数据模型、指标模型和已有报表选择相应路径；模型取数支持 MQL 与只读 SQL。
- 优化首次连接、资源定位、报表元数据读取及导出结果校验。
- 完善筛选、分页、结果粒度和完整性校验；保留原有通用 API、定时任务和消息推送流程。

## 2.0.0

- 原版 SmartBI CLI 通用业务操作 Skill。

Skill 版本与 `@smartbi/cli` npm 包版本独立管理。
