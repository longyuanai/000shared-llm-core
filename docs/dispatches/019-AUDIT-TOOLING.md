# 019-AUDIT-TOOLING：修复套件验收脚本的 PYTHONPATH 缺口

> **状态**：🟢 已解锁
> **依据**：[`014` 审计 §5.1](../../AUDIT/014-FW-INTEROP.md)、[`012` 审计 §5](../../AUDIT/012-STRUCT-DEBT.md)
> **目标**：`scripts/inspect_worker_return.py`、`scripts/run_all_tests.py`（工作区根目录）
> **预计工作量**：约 40 分钟

## 1. 为什么这个派活存在

`scripts/inspect_worker_return.py` 是**审计层判定"交付了没有"的唯一自动化依据**。
它当前会对**全部六个产品仓**报假 FAIL —— 同一个坑已经造成 **3 次误判**
（2026-08-13 两次、2026-08-17 一次）。

审计层 2026-08-17 用干净环境实测：

```
Worker A · 001-S4   FAIL  1 failed, 284 passed
Worker B · 002-S4   FAIL  1 failed, 182 passed
Worker C · 003-S4   FAIL  2 failed, 382 passed
Worker D · 004-S4   FAIL  2 failed, 181 passed
Worker E · 005-S4   FAIL  2 failed, 302 passed
Worker F · 006-S5   FAIL  2 failed, 413 passed, 2 skipped
OVERALL             FAIL  0/6 workers green
```

**六个仓、10 个假失败，全部同一个根因。**这比审计报告初版记录的"001/004/006"范围更大。

## 2. 根因（已定位，不必重新排查）

`inspect_worker_return.py` 的 `inspect()` 第 251–260 行这样拼 `PYTHONPATH`：

```python
pp_parts: list[str] = [
    str(project / "src"),
    str(ROOT / "000shared-llm-core" / "src"),
]
for p in extra_pp:                       # 只有 004 声明了 .python-deps
    pp_parts.append(str(ROOT / p))
current_pp = os.environ.get("PYTHONPATH", "")
if current_pp:
    pp_parts.extend(current_pp.split(os.pathsep))
```

**从不注入 `000shared-integration/src`。** 而六个产品仓都有测试会派生子进程加载
`shared_integration.adapters.worker`，子进程工作目录与 pytest 不同，于是：

```
ModuleNotFoundError: No module named 'shared_integration'
```

两种表现（[`010-AI-TRUST.md`](010-AI-TRUST.md) §4.1 原文）：完全缺 → 直接
`ModuleNotFoundError`；写成相对路径 → 被包成 `ProductCLIError`，Gateway 转 HTTP 500，
**极易误判为产品缺陷**。第二种是 2026-08-13 两次误判的形态。

**已验证的修法**：把 `000shared-integration/src` 加进 `pp_parts`。审计层用环境变量
预注入的方式实测过，六个仓里五个立刻转绿（第六个是 003 的既有缺陷，见 §5）。

## 3. 任务

### 3.1 `scripts/inspect_worker_return.py`（主要）

在 `inspect()` 构造 `pp_parts` 时**无条件加入** `ROOT / "000shared-integration" / "src"`，
位置在 `000shared-llm-core/src` 之后、`extra_pp` 之前。

约束：

1. **必须是绝对路径**（`str(ROOT / ...)`），理由见 §2 的第二种表现
2. 保留末尾"把环境里既有 `PYTHONPATH` 追加进去"的行为，不要删
3. 在该行上方留一句注释，写明**为什么**必须有它（六个产品仓派生
   `shared_integration.adapters.worker` 子进程），并注明这是 010 §4.1 记录的坑

### 3.2 `scripts/run_all_tests.py`（同类问题）

它的 `run()` 调 `subprocess.run(cmd, cwd=..., ...)` 时**完全不传 `env`**，
纯靠调用者事先设对 `PYTHONPATH`。同一族工具、同一类脆弱性。

按 `inspect_worker_return.py` 修好后的方式，给它补上等价的每项目 `PYTHONPATH` 构造
（`<项目>/src` + core `src` + integration `src`，004 另加 `.python-deps`），
同样保留对既有环境变量的追加。

### 3.3 明确不要做的事

| 事项 | 原因 |
|---|---|
| **改 Worker D 的 `codeguard.cli`** | `000shared-integration/src/shared_integration/adapters/code.py:12` 硬编码的就是它，Worker D 是在**镜像真实适配器**。审计层初版曾判定要改，**已撤回** |
| 改任何产品仓代码 | 本派活只动 `scripts/` |
| 修 003 的 ATLAS 测试 | 见 §5，属另一件事 |
| 调整 `WORKERS` 表里的 payload 或产品路径 | 现状可用，不在范围 |

## 4. 验收

**在干净环境下**（先 `Remove-Item Env:PYTHONPATH -ErrorAction SilentlyContinue`，
确认 `$env:PYTHONPATH` 为空）跑：

```powershell
$env:SUITE_PYTHON = "C:\Users\15072\AppData\Local\Programs\Python\Python314\python.exe"
C:\Users\15072\AppData\Local\Programs\Python\Python314\python.exe scripts\inspect_worker_return.py
```

| # | 项 | 标准 |
|---|---|---|
| 1 | Worker A / B / D / E / F | **五个全部 PASS**（不再需要任何环境变量绕法）|
| 2 | Worker C（003） | 仍 FAIL，但失败项**只剩** `test_atlas_registry.py::test_pyproject_declares_all_tactics_as_entry_points` 一个（`1 failed`，不是 `2 failed`）|
| 3 | `run_all_tests.py` | 干净环境下八个仓的数字与 §6 基线表一致 |
| 4 | 环境变量绕法 | 仍然可用（设了 `PYTHONPATH` 不应导致重复路径或报错）|

**验收 2 是这个派活的关键**：它证明你修的是 PYTHONPATH 缺口，而不是顺手把 003 的
既有缺陷一起盖掉了。若 Worker C 变成 PASS，说明你多做了不该做的事。

## 5. 不在范围：003 的既有缺陷（审计层另行处置）

修好 §3 后 Worker C 仍会 FAIL，这是**真缺陷**，与本派活无关：

```
tests/test_atlas_registry.py:71: KeyError: 'project'
    entries = config["project"]["entry-points"]["longyuanai.atlas_tactics"]
```

003 的 HEAD `3862acf`（提交信息 `fix: declare ATLAS tactics as Poetry plugins`）
把声明改成了 Poetry 格式：

```toml
[tool.poetry.plugins."longyuanai.atlas_tactics"]
```

但读它的测试仍按 PEP 621 的 `[project.entry-points]` 取值，**改声明时漏改了测试**。
`pyproject.toml` 与 `test_atlas_registry.py` 两个文件工作区均干净，
所以这是**锁定 HEAD 上的既有失败**，不是用户受保护改动引入的。

003 被 `suite-lock.yml` 锁定且有决策层保护的未提交修改，**本派活不得触碰**。
已记入 `docs/current-status.md`，等 003 下次获授权动工时收口。

## 6. 参考：修好后应当看到的数字

| 仓 | 全量 |
|---|---|
| `000shared-llm-core` | 150 passed（含 ADR-006 落地后）|
| `001AI-SOC-Agent` | 285 passed |
| `002AI-Vulnerability-Agent` | 183 passed |
| `003AI Agent安全靶场` | 383 passed, **1 failed**（§5 的既有缺陷）|
| `004AI-Code-Audit/004AI-CodeGuard-upgrade` | 183 passed |
| `005AI-Reverse-Agent` | 304 passed |
| `006AI-Firmware-Security-Agent` | 415 passed, 2 skipped |

## 7. 一个结构性问题（请在回报里表态，不要自行决定）

**工作区根目录的 `scripts/` 不在任何版本控制里** —— 审计层核实：根目录不是 git 仓，
且没有任何一个子仓跟踪这些文件。

这意味着套件的**验收工具本身**没有 diff、没有 review、没有回归防护。同一个坑能咬三次，
这是结构原因：改坏了没人看得见。

**本派活不迁移它**（迁走会改变所有调用路径和 `CLAUDE.md` §6.3 的引用，是 ADR 级决策）。
请在回报的 `Open questions` 里给出你的意见：是否应把 `scripts/` 收进
`000shared-llm-core/scripts/` 并加一个自测。决策层会据此判断要不要单开 ADR。

## 8. 约束

- 绝对 Python：`C:\Users\15072\AppData\Local\Programs\Python\Python314\python.exe`
- **`scripts/` 无版本控制，因此本派活没有 commit** —— 交付物是改好的文件 + §4 四项验收的
  stdout。请在回报中贴改动前后的完整 diff（`diff -u` 或等价），供审计层复核
- 不改任何产品仓、不改 `000shared-integration`、不动 `suite-lock.yml`

## 9. 回报格式

```
ISSUE: TOOL-PYTHONPATH-001
files: scripts/inspect_worker_return.py, scripts/run_all_tests.py
diff: <两个文件的完整 diff>
verify:
  - 干净环境 inspect_worker_return.py 全 6 worker 输出（A/B/D/E/F PASS，C 只剩 1 failed）
  - run_all_tests.py 八仓数字
  - 设了 PYTHONPATH 时的输出（证明绕法仍可用）
Open questions: <§7 的表态 —— 必填>
```
