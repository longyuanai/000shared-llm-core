# 000shared-llm-core · Phase-2

> 状态基线：2026-08-07。v0.5 契约冻结、CLI Envelope、suite lock 和九仓 CI 已完成。

## 已完成

- v0.1 §1-§6 与 v0.5 §7-§10 契约冻结。
- MultiAgentOrchestrator、RuleEngine、Finding 和 IntegrationGateway 核心能力。
- v0.6 §15 CLI Envelope 契约与 6 产品真实子进程 smoke。
- `005-FINAL` 发布证据、`suite-lock.yml` 和跨仓检查脚本。
- `007-CI` / `007-CI-FIX` 九仓 GitHub Actions 闭环。
- M2.1 Render/Neon 预生产验收记录。
- `008-M2-OPS` 本地备份恢复、PostgreSQL 并发和 seed 兼容验收。

证据见 `docs/releases/v0.5-final.md`，当前派活见 `docs/dispatches/INDEX.md`。

## 当前角色

本仓在当前阶段承担契约、锁定清单、派活索引、suite CI 和最终审计入口。`008-M2-OPS` 已本地通过，Integration 与 web-ui 输入提交已推送；当前等待本仓锁定提交和远端 suite CI。

## 后续候选

以下内容必须先写 RFC/ADR 或正式派活，不能直接改冻结契约：

- 流式 correlation 与跨 Agent 调度演进。
- OIDC/service identity 的共享认证契约。
- 多租户 Finding、审计和策略边界。
- 契约包发布与依赖版本治理。
- 生产流量、SLO 和兼容性窗口。

## 变更门禁

- 不修改 v0.1 §1-§6 或 v0.5 §7-§10，除非先有 ADR/RFC。
- `suite-lock.yml` 更新必须对应已推送提交和成功 CI。
- 跨仓验证仍使用 `scripts/inspect_worker_return.py`、绝对 Python 和 ASCII pytest basetemp。
- 不在文档、workflow 或测试 fixture 中保存凭据。
