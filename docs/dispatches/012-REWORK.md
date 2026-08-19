# 012-REWORK：004 包树合并收口

> **状态**：🔴 待执行（012 审计 FAIL 后的唯一返工项）
> **依据**：[`AUDIT/012-STRUCT-DEBT.md`](../../AUDIT/012-STRUCT-DEBT.md) §7
> **母派活**：[`012-STRUCT-DEBT.md`](012-STRUCT-DEBT.md)（§3 ISSUE 1 已撤销、
> ISSUE 2 第 4 条已修正，**动手前先重读这两处**）
> **目标仓**：`004AI-Code-Audit/004AI-CodeGuard-upgrade` —— **只有这一个**
> **预计工作量**：约 2.5h，**一个 commit**

## 0. 先做这一步（30 秒，防丢件）

004 有一个 **untracked 但被测试依赖**的文件，任何 `git clean -fd` 都会永久销毁它：

```bash
git add -N src/ai_code_audit/hybrid_cli.py
```

先跑这条，再做别的。做完 `git status --porcelain` 确认它从 `??` 变成 ` A`。

## 1. 背景：审计层改了两处派活事实，别按旧文执行

### 1.1 ISSUE 1（删死包）**已撤销** —— 不要删任何东西

`src/scanner/`（5 个 `.ts`）、`src/reporter/`（5 个 `.ts`）、`src/version.ts`
**不是死的 Python 包，是本仓 TypeScript 半边的在用源码**：

- `package.json` → `bin.ai-codeguard = ./dist/index.js`，`build: tsup`、`test: vitest`
- `tests/test_project_setup.py:24` **显式断言 `src/scanner/orchestrator.ts` 存在**
- `src/version.ts` 是 `--version` / JSON reporter / SARIF `tool.driver.version` 的
  单一版本源，有与 `package.json` 的漂移守卫

删了 → 004 Python 全量 183 掉到 182，且断掉 npm 包构建源。**三项原地不动。**

### 1.2 `src/codeguard/cli.py` **必须保留** —— 它是集成契约入口

母派活原文写"旧包路径不留兼容 shim，这是内部包，没有外部消费者"。**这句是错的。**

`000shared-integration/src/shared_integration/adapters/code.py:12` 硬编码：

```python
module = "codeguard.cli"
```

那是 Gateway 调 004 的唯一入口，且该仓**不在你的可改范围**（已推送、已被
`suite-lock.yml` 锁在 M3 头 `2d42a87`）。删掉 `codeguard/cli.py` 会打断 Gateway 004 通路，
并让 `tests/test_cli_envelope.py` 与审计脚本 Worker D 一起红。

你在工作区里已经把它重指向了 `ai_code_audit.hybrid_cli` —— **那个判断是对的，保持。**

## 2. 任务：把 `codeguard` 的实质模块迁进 `ai_code_audit`

`ai_codeguard`（3 文件）你已经迁完了，只是没提交。本次要迁的是剩下的 `codeguard`：

| 文件 | loc | 处置 |
|---|---|---|
| `src/codeguard/taint.py` | 531 | 迁入 `ai_code_audit`（建议 `ai_code_audit/taint/`）|
| `src/codeguard/dataflow.py` | 660 | 迁入（建议 `ai_code_audit/dataflow/`）|
| `src/codeguard/explain.py` | 141 | 跟 `dataflow` 走 |
| `src/codeguard/v05.py` | 179 | 迁入；`Finding` / `RuleContext` / `RuleEngine` / `FindingSource` 在 `ai_code_audit` 内**无同名符号**，已核实无冲突 |
| `src/codeguard/rules/__init__.py` | 16 | 迁入 |
| `src/codeguard/rules/taint.py` | 35 | 迁入 |
| `src/codeguard/__init__.py` | 39 | **精简**：实质模块迁走后不再重导出它们 |
| `src/codeguard/cli.py` | 6 | **原地保留**，见 §1.2 |

子包命名你定，但要在回报里给对照表。

### 需要改 import 的调用点（已全量列出）

`src/`：

- `src/ai_code_audit/hybrid_cli.py:15-19` —— 5 条 `from codeguard...`

`tests/`：

- `tests/test_dataflow.py:1,6,7`
- `tests/test_explain.py:5,6,10`
- `tests/test_rule_engine_taint.py:8,9`
- `tests/test_taint.py:1,2`
- `tests/test_v05_contract.py:7,8`

### 硬约束

1. **只移动，不重写业务逻辑。** 只改 import 和必要的模块内相对引用。混进重构会让
   "合并是否等价"无法验证 —— 这是母派活 §3 的原话，仍然有效
2. `analyzer` / `parser` / `cache` / `config` / `types` / `rules` 等其它顶层包**不动**
3. `pyproject.toml` 的 `packages` 列表**保持含 `codeguard`**（因为 `cli.py` 还在）
4. 不碰 `000shared-integration`、不碰 `003AI Agent安全靶场`、不碰其它产品仓

## 3. 新增测试（1 个）

```
tests/test_package_layout.py::test_no_legacy_package_trees
```

断言两件事：

1. `src/ai_codeguard` 已不存在
2. `src/codeguard` 下**只剩** `cli.py` 与 `__init__.py`
   （即实质模块已迁走、集成契约入口仍在）

不新增其它功能测试；已有测试的 import 路径随迁移更新，不算新增。

## 4. 验收（逐条给证据）

| # | 项 | 标准 |
|---|---|---|
| 1 | 004 全量 | **= 183 passed**，不得下降 |
| 2 | `tests/test_project_setup.py` | 全绿（证明没误删 TS 源）|
| 3 | `tests/test_package_layout.py` | 新测试通过 |
| 4 | `011` 的 `test_eval_gate.py` + `test_prompt_injection.py` | **必须仍然通过**（合并没破坏行为的证据）|
| 5 | `tests/test_cli_envelope.py` | 全绿（证明 integration adapter 路径没断）|
| 6 | CLI smoke ×2 | `codeguard.cli` 与 `ai_code_audit.cli` **都**输出合法 envelope |
| 7 | 4 件套 | `inspect_worker_return.py --workers D` PASS |

### 跑测试的固定环境（照抄，别自己拼）

```powershell
$env:PYTHONPATH = "E:\001项目\000开发\003AI-Network-Security\004AI-Code-Audit\004AI-CodeGuard-upgrade\src;E:\001项目\000开发\003AI-Network-Security\000shared-llm-core\src;E:\001项目\000开发\003AI-Network-Security\000shared-integration\src;E:\001项目\000开发\003AI-Network-Security\004AI-Code-Audit\004AI-CodeGuard-upgrade\.python-deps"
C:\Users\15072\AppData\Local\Programs\Python\Python314\python.exe -m pytest tests/ --basetemp=C:/pytest-tmp/012-rework -o addopts= -q
```

跑 4 件套前先设 `$env:PYTHONPATH` 指向 `000shared-integration\src`，否则脚本会出假 FAIL
（脚本自身缺陷，见 `CLAUDE.md` §3.3.1，**不是你的 bug，别去追**）。

## 5. 提交

**一个 commit**，信息逐字：

```
refactor(code): consolidate package trees into ai_code_audit
```

包含：`ai_codeguard` 迁移（你已做的）+ `codeguard` 实质模块迁移 + `hybrid_cli.py` +
import 更新 + 新测试。ISSUE 1 撤销后 004 本阶段只需这一个提交。

**不 push。不造空 commit。**

## 6. 回报格式

```
ISSUE: CODE-MERGE-001（返工）
commit: <hash>
files: <改动文件>
baseline: 183 passed
tests: <N> passed, <M> failed
迁移对照表: <旧模块路径 → 新模块路径>，逐行
verify: 上表 7 项验收各自的命令 stdout
codeguard/ 残留: <ls src/codeguard 输出，应只有 cli.py + __init__.py>
NITs: <可选>
Open questions: <可选>
```

## 7. 卡住时怎么办

**停下来问，写进 `Open questions`。** 特别地：

- 发现两个包有**行为冲突**（同名不同义的函数）→ 停，不要自己选一个
- 发现还有别处硬编码 `codeguard.` 路径 → 停，报出来（可能又是一个像 §1.2 那样的契约点）
- 发现派活的事实前提与仓库实际不符 → **必须写进 `Open questions` 并停在那一步**。
  上一轮 ISSUE 1 你处置对了（没删）但没报，害审计层多花一轮才查清 —— 别再沉默跳过

## 8. 不在本次范围

| 事项 | 原因 |
|---|---|
| 删 `scanner` / `reporter` / `version.ts` | ISSUE 1 已撤销（§1.1）|
| 改 `000shared-integration` 的 adapter `module` | 需动锁定仓 + 重锁 suite + 跑 suite CI，另开派活 |
| 改 `scripts/inspect_worker_return.py` 的 Worker D | 它镜像的就是真实 adapter，保持 `codeguard.cli` |
| ISSUE 4 `LAB-EVAL-001` | 仍等决策层书面授权 |
| ISSUE 3 的七仓数字补测 | 优先级低于本次，收口后再补 |
