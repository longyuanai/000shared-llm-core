# 审计 · 019-AUDIT-TOOLING

> **结论**：**PASS**（2 个 NIT，均为低优先，不阻塞）
> **审计日期**：2026-08-18
> **派活**：[`019-AUDIT-TOOLING.md`](../docs/dispatches/019-AUDIT-TOOLING.md)
> **审计方式**：四项验收全部独立复现，不采信回报自述。

## 1. 交付

改动两个文件，均在工作区根目录 `scripts/`（无版本控制，因此**按派活 §8 没有 commit**，
这是正确的）：

| 文件 | 改动 |
|---|---|
| `scripts/inspect_worker_return.py` | `inspect()` 的 `pp_parts` 无条件加入 `000shared-integration/src`；`env_pp` 改用 `dict.fromkeys` 去重 |
| `scripts/run_all_tests.py` | `run()` 新增每项目 `PYTHONPATH` 构造并通过 `env=` 传给子进程 |

审计员逐字比对了两个文件的实际内容与回报所贴 diff —— **完全一致**，无夹带改动。
文件修改时间 `2026-08-18 22:47`。

## 2. 四项验收逐条复现

### 2.1 验收 1 · 干净环境下 A/B/D/E/F 全 PASS —— ✅

审计员清空 `PYTHONPATH` 后独立运行：

```
Worker A · 001-S4              PASS  all green
Worker B · 002-S4              PASS  all green
Worker C · 003-S4              FAIL  pytest RC=1: 1 failed, 383 passed in 17.94s
Worker D · 004-S4              PASS  all green
Worker E · 005-S4              PASS  all green
Worker F · 006-S5              PASS  all green
OVERALL                        FAIL  5/6 workers green
```

对照修复前（2026-08-17 同样干净环境）的 `0/6 workers green`、10 个假失败 ——
**根因已消除，不再需要任何环境变量绕法。**

### 2.2 验收 2 · 003 只剩既有失败 —— ✅（本派活最关键的一条）

这条是用来区分"修好了"与"把 003 的真缺陷一起盖掉了"的。审计员单独跑 003 全量确认
失败项身份：

```
FAILED tests/test_atlas_registry.py::test_pyproject_declares_all_tactics_as_entry_points
1 failed, 383 passed in 15.68s
```

**正是派活 §5 点名的那一个**，`2 failed → 1 failed`，PYTHONPATH 造成的那个已消失，
003 自己的 ATLAS 缺陷**原样保留未被掩盖**。执行层没有多做不该做的事。

### 2.3 验收 3 · `run_all_tests.py` 八仓数字 —— ✅

干净环境独立运行，与回报数字**逐行一致**，亦与派活 §6 基线表一致：

```
000shared-llm-core                OK  150 passed
000shared-integration             OK  143 passed, 4 skipped
001AI-SOC-Agent                   OK  285 passed
002AI-Vulnerability-Agent         OK  183 passed
003AI-Agent-Security-Lab        RC=1  1 failed, 383 passed
004AI-CodeGuard-upgrade           OK  183 passed, 1 warning
005AI-Reverse-Agent               OK  304 passed
006AI-Firmware-Security-Agent     OK  415 passed, 2 skipped
TOTAL                                 passed=2046  failed=1
```

`000shared-integration` 本轮首次纳入实测：`143 passed, 4 skipped`。

### 2.4 验收 4 · 环境变量绕法仍可用且不产生重复 —— ✅（审计员用路径探针独立验证）

审计员没有只看跑通与否，而是导入脚本模块、在三种环境下逐 worker 检查最终路径列表：

```
--- clean env ---
  Worker A..F   entries=3(004 为 4)  integration×1  dupes=0
--- caller preset = integration src（即旧绕法）---
  Worker A..F   entries=3(004 为 4)  integration×1  dupes=0
--- caller preset = unrelated dir ---
  Worker A..F   entries=4(004 为 5)  integration×1  dupes=0
```

三点结论：

1. 每个 worker 都**恰好**拿到一次 integration src
2. 沿用旧绕法（预设同一路径）**不会产生重复项**，`dict.fromkeys` 去重生效
3. 预设无关目录时正常追加，**调用方的既有 `PYTHONPATH` 未被吞掉**

### 2.5 Worker D 未被改动 —— ✅

`scripts/inspect_worker_return.py:59` 仍是 `"codeguard.cli"`。派活 §3.3 明令不得改，
执行到位 —— 这正是最容易"顺手改掉"的地方。

## 3. 边界与质量

| 项 | 结果 |
|---|---|
| 产品仓 001/002/005/006 | **0 项未提交**，未被触碰 |
| `000shared-integration` | **0 项未提交**，未被触碰 |
| `003AI Agent安全靶场` | 仍是 8 个受保护项，状态未变 |
| `004AI-Code-Audit/...` | 仍是 17 项（012 返工中间态），未被触碰 |
| `suite-lock.yml` | 干净，未动 |
| 语法 | 两个文件 `ast.parse` 均 OK |
| Ruff | 3 个**既有**告警（`PLW1510` ×2、`BLE001`），新增代码零新告警 —— 与回报一致 |

**分层核实**：`run_all_tests.py` 现在也给 `000shared-llm-core` 拼上了 integration src。
审计员检查 core 的 `src/` 与 `tests/` **不 import `shared_integration`**
（唯一命中是 `test_cli_envelope_contract.py:14` 的一句文档注释）。因此那是一个多余的
路径项，**不掩盖任何分层违规**，无害。

## 4. 做得好的地方

- **`dict.fromkeys` 去重不是派活字面要求的**，但它正是验收 4「设了 `PYTHONPATH` 不应导致
  重复路径」的正解。执行层自己想到了，并**写进 diff 公开**，没有夹带。
- 注释按派活 §3.1 第 3 条写明了**为什么**（六仓派生 `shared_integration.adapters.worker`）
  并引用了 010 §4.1，不是一行无声的路径追加。
- 没有碰 Worker D，也没有顺手"修"003 —— 两处最容易越界的地方都守住了。
- §7 的表态给的是**可执行的自测清单**，不是一句"建议迁移"。

## 5. NIT（不阻塞）

### NIT-1 · `run_all_tests.py` 用硬编码字符串判定 004 的 extras（low）

`scripts/run_all_tests.py:74`：

```python
if rel == "004AI-Code-Audit/004AI-CodeGuard-upgrade":
    pp_parts.append(str(ROOT / rel / ".python-deps"))
```

同一需求在 `inspect_worker_return.py` 是**声明式**的 —— `WORKERS` 表有
`extra_pythonpath` 一列。这里改成了字符串比较：若 004 的目录名变动，比较**静默失效**，
`.python-deps` 不再加入，表现为 tree-sitter import 失败，排查方向又会指向产品仓。

建议把 `PROJECTS` 从 `(label, rel)` 扩成带 extras 的三元组，与 `WORKERS` 对齐。

### NIT-2 · 去重只对完全相同的字符串生效（very low）

`dict.fromkeys` 不做路径规范化，`C:/x` 与 `C:\x`、带不带尾斜杠会被当成不同项。
`sys.path` 上有重复项本身无害，记在这里只是**防止后来者误以为它是规范化去重**。

## 6. §7 结构性问题：执行层的表态（转决策层）

执行层建议**另开 ADR**，把根目录 `scripts/` 收进 `000shared-llm-core/scripts/`，
并加自测覆盖：

1. 六产品仓的绝对 `src` / core / integration 路径
2. 004 的 `.python-deps`
3. 调用者既有 `PYTHONPATH` 的追加
4. 完全相同路径去重
5. `shared_integration.adapters.worker` 子进程导入 smoke test

**审计层意见：这个清单是对的，且第 1、2、5 条恰好能防住本次这个坑与 NIT-1。**
但迁移会改变所有调用路径与 `CLAUDE.md` §6.3、`INDEX.md` §派活流程的引用，
仍属决策层决定。本派活按约定未迁移，等决策。

## 7. 结论

**PASS。** 四项验收全部由审计层独立复现，数字与回报逐条吻合。造成 3 次误判的根因已消除：
干净环境从 `0/6 workers green` 变为 `5/6`，且第六个是 003 自己的既有缺陷 —— 这一点
经单独跑 003 确认失败项身份，证明修的是路径缺口而非盖掉真问题。边界全部守住，
两个 NIT 均为可读性/健壮性建议，不需要返工。

后续：

1. 两个 NIT 记入 backlog
2. `scripts/` 是否版本化 → 决策层依 §6 判断是否开 ADR
3. **审计工具已可信**，`018-CORE-RULEENGINE` 与 `012-REWORK` 的验收可以正常进行
4. 003 的 ATLAS 缺陷仍挂在 `docs/current-status.md` §4 P0.3，等该仓获授权时收口
