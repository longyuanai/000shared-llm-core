# 000shared-llm-core 当前 TODO

> 2026-08-07 基线。v0.5 freeze、CLI Envelope 和 suite CI 已完成。

## 当前

- [x] 本地执行并审计 [`dispatches/008-M2-OPS.md`](dispatches/008-M2-OPS.md)。
- [x] 更新 `dispatches/INDEX.md` 和根目录 `docs/current-status.md`。
- [x] 提交并推送 Integration 修复与 web-ui 阶段更新。
- [ ] 提交并推送本仓 `suite-lock.yml` 与状态文档，运行远端 suite CI。
- [ ] 2026-08-14 前确认 Render 私有 GHCR 拉取凭据已轮换或服务已下线。

## 后续需先决策

- [ ] OIDC/service identity 契约 RFC。
- [ ] 多租户 Finding、策略和审计边界 RFC。
- [ ] 契约包发布、版本兼容窗口与升级策略。
- [ ] 生产 SLO、持续流量与故障恢复验收标准。

不要直接把候选项实现进冻结的 v0.1/v0.5 契约；先走 ADR/RFC 与派活流程。
