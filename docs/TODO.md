# 000shared-llm-core 当前 TODO

> 2026-08-09 基线。v0.5 freeze、CLI Envelope 和 M2 运维本地门禁已完成。

## 当前

- [x] 本地执行并审计 [`dispatches/008-M2-OPS.md`](dispatches/008-M2-OPS.md)。
- [x] 更新 `dispatches/INDEX.md` 和根目录 `docs/current-status.md`。
- [x] 提交并推送 Integration 修复与 web-ui 阶段更新。
- [x] 提交并推送本仓 `suite-lock.yml` 与状态文档，触发 suite CI run `31188096745`。
- [x] 确认 run `31188096745` 因 workflow 旧默认 SHA 在锁定集合校验失败。
- [x] 本地修复 workflow，默认 refs 改由 `suite-lock.yml` 解析并校验完整 SHA。
- [ ] 提交/推送修复并取得成功 rerun；随后把 008 审计升级为 PASS。
- [ ] 2026-08-14 前按[处置 Runbook](../../docs/runbooks/render-ghcr-credential-rotation.md)
  轮换 Render 私有 GHCR 拉取凭据或下线服务。

## 后续需先决策

- [x] 起草 [`ADR-003`](adr/ADR-003-M3-BFF-identity-boundary.md) 和
  [`009-M3-AUTH`](dispatches/009-M3-AUTH.md)；保持锁定直到 008 PASS。
- [ ] 多租户 Finding、策略和审计边界 RFC。
- [ ] 契约包发布、版本兼容窗口与升级策略。
- [ ] 生产 SLO、持续流量与故障恢复验收标准。

不要直接把候选项实现进冻结的 v0.1/v0.5 契约；先走 ADR/RFC 与派活流程。
