# longyuanai 派活索引

> 状态核验：2026-08-09。当前项目事实见仓库根目录 `docs/current-status.md`。

## 当前交付门禁

| 顺序 | 派活 | 目标仓 | 状态 | 解锁条件 |
|---|---|---|---|---|
| 1 | [`009-M3-AUTH.md`](009-M3-AUTH.md) | Integration + Web | 🟠 精确锁定门禁通过，Sites 发布待办 | 五个 ISSUE、文档与 suite lock 已交付；恢复既有 Sites 项目访问后完成私有发布 |

`008-M2-OPS` 的本地备份/恢复、PostgreSQL 并发、seed 修复和全量测试已通过。初次 run
`31188096745` 暴露 workflow 旧默认 SHA；core `e900a0a` 改为直接从 suite lock 解析 refs，
替代 run `31267714152` 完成 9 仓锁校验与 `1873 passed, 5 skipped, 1 warning, 0 failed`。
Integration 审计已升级为 PASS。

M3 身份边界已固化为已接受的 [`ADR-003`](../adr/ADR-003-M3-BFF-identity-boundary.md)。
Integration `15a905b`、Web `3dbc361` 与 Core `d41bfea` 的候选 suite run `31276172231`
成功：八个 Python 组 `1914 passed, 7 skipped, 1 warning`，真实 PostgreSQL/Gateway/Web
两轮各 `13 passed`。运维 Runbook 与 PASS-WITH-NITS 审计已进入 Integration `2d42a87`，
Web 阶段文档为 `a778e0b`，并已写入精确 suite lock。剩余 nit 是恢复既有 Sites 项目访问并
完成私有发布，不得新建替代项目覆盖事实源。

精确锁定头 core `6058938` 的 suite run `31276779035` 已成功：九仓锁校验、八个 Python
测试组和真实 PostgreSQL/Gateway/Web 双轮门禁全部通过，两轮各 `13 passed`，最终容器与
网络清理完成。身份/RBAC 的代码、E2E、发布文档和精确锁已收口；当前只保留既有 Sites
项目访问恢复与私有发布这一部署项。

## 已完成派活

### 产品与集成

| 派活 | 范围 | 状态 |
|---|---|---|
| [`001-S3.md`](001-S3.md) / [`001-S4.md`](001-S4.md) | AI SOC | ✅ complete |
| [`002-S3.md`](002-S3.md) / [`002-S4.md`](002-S4.md) | Vulnerability Agent | ✅ complete |
| [`003-S3.md`](003-S3.md) / [`003-S4.md`](003-S4.md) | Agent Security Lab | ✅ complete |
| [`004-S3.md`](004-S3.md) / [`004-S4.md`](004-S4.md) | CodeGuard | ✅ complete |
| [`005-S3.md`](005-S3.md) / [`005-S4.md`](005-S4.md) | Reverse Agent | ✅ complete |
| [`006-S4.md`](006-S4.md) / [`006-S5.md`](006-S5.md) | Firmware Agent | ✅ complete |
| [`005-INTEG.md`](005-INTEG.md) | Integration Gateway | ✅ complete |

### 套件闭环

| 派活 | 范围 | 状态 |
|---|---|---|
| [`005-UI.md`](005-UI.md) | Web Dashboard | ✅ complete |
| [`005-FINAL.md`](005-FINAL.md) | v0.5 freeze / E2E / docs | ✅ complete |
| [`007-CI.md`](007-CI.md) | suite CI | ✅ complete |
| [`007-CI-FIX.md`](007-CI-FIX.md) | 发布后 CI 修复 | ✅ complete |
| [`008-M2-OPS.md`](008-M2-OPS.md) | M2 备份、并发、seed 与发布门禁 | ✅ complete |
| [`009-M3-AUTH.md`](009-M3-AUTH.md) | M3 身份、会话、多租户 RBAC 与发布文档 | ✅ locked gate; Sites publish pending |
| [`010-AI-TRUST.md`](010-AI-TRUST.md) | LLM 输出评估门禁、不可信内容边界、`api-key-list` | ✅ PASS-WITH-NITS（[审计](../../AUDIT/010-AI-TRUST.md)）|
| [`011-INJECT-HARDEN.md`](011-INJECT-HARDEN.md) | 边界加固 + 六产品铺开边界与评估门禁（含 010 NIT-1）| 🟢 已解锁，未开工 |

历史 6-worker 并行包保留在 [`CODEX-DISPATCH-PACK-v0.6.md`](CODEX-DISPATCH-PACK-v0.6.md)，不再重复派发。

## 派活流程

1. 阅读根目录 `AGENTS.md`、`docs/current-status.md` 和目标仓 README。
2. 检查目标仓 `git status --short --branch`，保护现有修改。
3. 将已解锁派活交给执行层；执行层不得改派活文档或范围外仓库。
4. 执行层按派活要求提交 commit、测试、CLI smoke、偏差和问题。
5. 设计/审计层运行 `scripts/inspect_worker_return.py --project <project>` 并写 `<project>/AUDIT/<stage-id>.md`。
6. 审计 PASS 后，更新本索引和 `docs/current-status.md`，再解锁下一任务。

## Windows 验证约束

- 使用绝对 Python：`C:\Users\15072\AppData\Local\Programs\Python\Python314\python.exe`。
- pytest 显式使用 `--basetemp=C:/pytest-tmp/ -o addopts=`。
- `004AI-Code-Audit/004AI-CodeGuard-upgrade` 是实际 Git 仓；不要把外层包装目录当仓库。
- `000shared-integration` 的 `PYTHONPATH` 同时包含自身 `src` 和 `../000shared-llm-core/src`。

命名和回报约定见 [`NAMING.md`](NAMING.md)。
