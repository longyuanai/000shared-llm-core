# longyuanai 派活索引

> 状态核验：2026-08-09。当前项目事实见仓库根目录 `docs/current-status.md`。

## 当前交付门禁

| 顺序 | 派活 | 目标仓 | 状态 | 解锁条件 |
|---|---|---|---|---|
| 1 | [`009-M3-AUTH.md`](009-M3-AUTH.md) | Integration + Web | 🟢 已解锁 | 按 ADR-003 与 ISSUE 顺序执行 |

`008-M2-OPS` 的本地备份/恢复、PostgreSQL 并发、seed 修复和全量测试已通过。初次 run
`31188096745` 暴露 workflow 旧默认 SHA；core `e900a0a` 改为直接从 suite lock 解析 refs，
替代 run `31267714152` 完成 9 仓锁校验与 `1873 passed, 5 skipped, 1 warning, 0 failed`。
Integration 审计已升级为 PASS。

M3 身份边界已固化为已接受的 [`ADR-003`](../adr/ADR-003-M3-BFF-identity-boundary.md)，
`009-M3-AUTH` 已解锁。

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
