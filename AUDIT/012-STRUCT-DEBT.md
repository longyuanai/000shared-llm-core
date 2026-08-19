# 审计 · 012-STRUCT-DEBT

> **结论**：**FAIL**（ISSUE 2 半完成且未提交；ISSUE 1 经复核**前提有误、已撤销**）
> **修订**：2026-08-17 二次核查推翻了派活对 ISSUE 1 的事实认定，见 §2.1
> **审计日期**：2026-08-17
> **派活**：[`012-STRUCT-DEBT.md`](../docs/dispatches/012-STRUCT-DEBT.md)
> **审计方式**：以仓库实际状态为准，不采信「进行中」的口头进度。

## 1. 交付概况

派活要求 5 个 ISSUE、按 §2 的顺序各自独立 commit。实际状态：

| ISSUE | 目标仓 | 要求的 commit | 实际 | 结论 |
|---|---|---|---|---|
| 1 · CODE-DEAD-001 | 004 | `refactor(code): remove dead packages` | 不存在 | ⛔ **派活前提有误，已撤销**（§2.1）|
| 2 · CODE-MERGE-001 | 004 | `refactor(code): consolidate package trees into ai_code_audit` | **不存在**，17 项未提交改动 | ❌ **半完成且未提交** |
| 3 · CORE-VERSION-001 | core | `chore(version): adopt suite version policy` | `23cc11f` | ✅ **完成** |
| 4 · LAB-EVAL-001 | 003 | `test(eval): add lab eval gate and retire its exemption` | 未执行 | ✅ **按 §5 正确挂起** |
| 5 · SOC-SIEM-001 | 001 | `feat(soc): add elasticsearch ingest source` | `f9731f7` | ✅ **完成** |

ISSUE 1 撤销后，004 仓本阶段只欠 commit 2。但该 commit 至今不存在，004 停在一个既没提交、
也没做完的中间态，违反派活 §4「每个 ISSUE 完成后先跑该仓全量再进下一个」。

## 2. 阻塞问题（必须由执行层修）

### 2.1 CODE-DEAD-001：派活自己的事实前提是错的 —— ⛔ 撤销，非执行层责任

初审时本节记为「未开工」。**二次核查推翻了这个判断** —— 该 ISSUE 不该被执行。

派活 §3 ISSUE 1 的「已核实的事实（不需要重新统计）」表写着 `src/scanner/` 与
`src/reporter/` 的「src 内引用 0 / tests 内引用 0」。审计员复核发现，**那张表只统计了
Python import**。004 是 `pyproject.toml` 自述的 "Hybrid TypeScript/Python upgrade
layer"，这三项是它的 TypeScript 半边，全部在用：

| 项 | 实际内容 | 证据 |
|---|---|---|
| `src/scanner/` | 5 个 `.ts`，零 `.py` | `tests/test_project_setup.py:24` **显式断言 `orchestrator.ts` 存在** |
| `src/reporter/` | 5 个 `.ts`，零 `.py`（`sarif` / `json` / `github` / `text` / `index`）| SARIF 与 JSON 报告器实现 |
| `src/version.ts` | `--version`、JSON reporter、SARIF `tool.driver.version` 的单一版本源 | `CHANGELOG.md:172`、`docs/dev/TESTING.md:192` 描述其漂移守卫；`dist/index.js:2447` 是其打包产物 |

构建链真实存在：`package.json` 的 `bin.ai-codeguard → ./dist/index.js`，
`build: tsup`、`test: vitest`、`lint: eslint src/`。

**若按派活原文执行**：004 Python 全量从 183 掉到 182（`test_project_setup.py` 变红），
且破坏 npm 包 `ai-codeguard` 的构建源。派活 §3 与 §8 给了「发现仍被引用 → 不要删，
写进 Open questions」的豁免路径，但执行层既没删也没报，属于**沉默跳过**——
处置结果正确，过程记录缺失（见 §6 NIT-1）。

**已处置**：派活 §2 与 §3 ISSUE 1 已由设计层划掉并写明撤销依据，
`scanner` / `reporter` / `version.ts` 三项原地保留。若未来要收拾 004 的 TS 线，
须先写 ADR 说明双语言边界再单独派活。

### 2.2 CODE-MERGE-001 半完成，且全部改动未进 Git —— ❌

004 仓 `git status --porcelain` 有 **17 项**未提交改动：

```
 M README.md
 M pyproject.toml
 M src/ai_code_audit/__init__.py
 M src/ai_code_audit/cli.py
 D src/ai_codeguard/__init__.py
 D src/ai_codeguard/__main__.py
 D src/ai_codeguard/cli.py
 M src/codeguard/cli.py
 M tests/test_baseline_writer.py
 M tests/test_cli.py
 M tests/test_cli_diff_input.py
 M tests/test_cli_envelope.py
 M tests/test_finding_gate.py
 M tests/test_hybrid_cli.py
 M tests/test_rule_engine_taint.py
 M tests/test_static_backends.py
?? src/ai_code_audit/hybrid_cli.py
```

对照派活 §3 ISSUE 2 的四项验收：

| 要求 | 实际 |
|---|---|
| 先迁 `ai_codeguard`（3 文件），跑全量确认绿 | 做了（工作区内 3 个文件已删），但**未提交** |
| 再迁 `codeguard`（8 文件），跑全量确认绿 | **未做** —— `src/codeguard/` 仍含 `cli.py` / `taint.py` / `dataflow.py` / `explain.py` / `v05.py` / `rules/` / `__init__.py` |
| 新增 `tests/test_package_layout.py::test_no_legacy_package_trees` | **文件不存在** |
| 附迁移前后模块对照表 | 未提供（ISSUE 未完成，无从提供）|

也就是说这个 ISSUE 只走完了派活明确要求的「分两步走」的第一步。

### 2.3 有一个 load-bearing 文件不在 Git 里 —— ❌ 高优先

`src/ai_code_audit/hybrid_cli.py` 处于 **untracked**（`??`）状态，而 004 当前的
`183 passed` 依赖它 —— `tests/test_hybrid_cli.py` 已被改为从新路径导入。

后果：任何 `git clean -fd`、任何分支切换清理、任何「回到干净状态重来」的动作都会**永久
销毁**这份工作，而 `git stash` 默认也不带 untracked 文件。这不是风格问题，是交付物随时可能
凭空消失。**执行层应立刻 `git add -N src/ai_code_audit/hybrid_cli.py` 让它进入索引，
再着手补完 ISSUE 2。**

## 3. 已完成部分的核实（这两项做得对，予以确认）

### 3.1 CORE-VERSION-001 —— ✅

core `23cc11f`：

```
docs/v0.5-contract.md           |  1 +
docs/versioning.md              | 15 ++++++++++++++
pyproject.toml                  |  2 +-
src/shared_llm_core/__init__.py |  4 ++--
src/shared_llm_core/gateway.py  |  4 ++--
tests/test_versioning.py        | 30 +++++++++++++++++++++++++++
```

- `pyproject.toml:3` 实测 `version = "0.6.0"`，符合派活 §3「core 的 version 必须等于它实现
  的契约版本」
- `docs/versioning.md` 已新增；`docs/v0.5-contract.md` 已补指向
- 硬编码版本字符串已在 `__init__.py` 与 `gateway.py` 同步更新（不是只改 pyproject 就交）
- 新增 `tests/test_versioning.py`，规定的 2 个测试到位
- core 全量 **126 passed**（派活要求 ≥ 124）

### 3.2 SOC-SIEM-001 —— ✅

001 `f9731f7`：

```
src/ai_soc_agent/cli.py              |  81 +++++
src/ai_soc_agent/sources/__init__.py |  17 ++
src/ai_soc_agent/sources/elastic.py  | 330 +++++++++++++++++++++
tests/test_cli.py                    |  11 ++
tests/test_elastic_source.py         | 131 ++++++++++
tests/test_prompt_injection.py       |  52 ++++
```

- 001 全量 **285 passed**（派活要求 ≥ 278）
- 新增子命令 `--help` 实测可用，含 `--query` / `--start` / `--end` / `--log-type`，
  形态与既有子命令一致：

  ```
  Usage: python -m ai_soc_agent.cli elastic [OPTIONS]
    Pull a bounded Elasticsearch time window and run detection rules.
  ```

- 规定的 5 个测试名到位，含 `test_prompt_injection.py::test_elastic_content_is_delimited`
  —— 新入口没有绕过 `011` 的 `wrap_untrusted` 边界
- 4 件套 Worker A **全绿**（补齐 PYTHONPATH 后，见 §5）

### 3.3 LAB-EVAL-001 的挂起处理 —— ✅ 正确

派活 §5 要求未获授权则跳过。实测：

- 003 HEAD 仍为 `3862acf`，与 `suite-lock.yml` 锁定值一致，**未离开锁**
- `git status --porcelain` 精确等于 `docs/current-status.md` §3 记录的 8 个受保护项，
  状态未变：

  ```
   M src/ai_agent_lab/api/app.py
   M src/ai_agent_lab/application/service.py
   M src/ai_agent_lab/auth.py
   M src/ai_agent_lab/domain/__init__.py
   M src/ai_agent_lab/domain/entities.py
   M src/ai_agent_lab/storage/auth_repository.py
   M src/ai_agent_lab/storage/repositories.py
  ?? tests/test_tenant_isolation.py
  ```

- 未新增 `evals/`、未改 core 的 `test_eval_coverage.py` 豁免表

**执行层没有为了「凑完整」擅自执行需授权的 ISSUE，这是对的。** 该 ISSUE 的授权仍在决策层手里。

## 4. 回归数字（当前工作区状态，非收口基线）

| 仓 | 结果 | 备注 |
|---|---|---|
| `000shared-llm-core` | **126 passed** | ISSUE 3 已提交 |
| `001AI-SOC-Agent` | **285 passed** | ISSUE 5 已提交 |
| `002AI-Vulnerability-Agent` | **183 passed** | 未受本阶段影响 |
| `004AI-Code-Audit/004AI-CodeGuard-upgrade` | **183 passed** | ⚠️ **依赖 untracked 的 `hybrid_cli.py`**，见 §2.3 |
| `005AI-Reverse-Agent` | **304 passed** | 013 收口后基线 |
| `006AI-Firmware-Security-Agent` | **415 passed, 2 skipped** | 014 收口后基线 |

004 达到派活要求的 183，但那是**半完成合并 + 未提交 + 有 untracked 依赖**状态下的数字，
不能作为收口证据。

**ISSUE 3 的「七仓全部重新可安装」验收未完整核实**：上表覆盖 6 个仓，`003AI Agent安全靶场`
（受保护工作区）与 `000shared-integration` 本次未重跑。执行层的回报也未提供七仓数字。
该项验收**仍缺口**，但优先级低于 §2。

## 5. 审计工具缺口（非执行层责任）

与 [`014` 审计 §5](014-FW-INTEROP.md) 同一条：`scripts/inspect_worker_return.py` 不注入
`000shared-integration/src`，会出假 FAIL
（`ModuleNotFoundError: No module named 'shared_integration'`）。
2026-08-17 干净环境补测确认影响面是**全部六个产品仓、10 个假失败**，非初记的三个。
修复已派活 [`019-AUDIT-TOOLING`](../docs/dispatches/019-AUDIT-TOOLING.md)。

**本阶段额外一条（2026-08-17 修正）**：初审曾判定脚本 Worker D 的 `codeguard.cli` 会被
CODE-MERGE-001 删掉、须改为 `ai_code_audit.cli`。**该判定是错的，已撤回。**
`000shared-integration/src/shared_integration/adapters/code.py:12` 硬编码
`module = "codeguard.cli"`，Worker D 正是在镜像真实适配器的调用方式 ——
**保持 `codeguard.cli` 不动才是对的**。真正要保证的是 `src/codeguard/cli.py` 在合并后
继续存在，见 §2.2 与派活 §3 ISSUE 2 第 4 条的修正。

## 6. NIT（不阻塞）

### NIT-1 · 遇到派活与事实冲突时沉默跳过（medium）

ISSUE 1 的正确处置就是不执行（§2.1），执行层的**结果**是对的。但派活 §3 第 3 条与 §8
都写明了「发现仍被引用 → 不要删，写进 Open questions」，回报里既没有这一条，也没有任何
说明。审计层因此在初审时把它记成「未开工」，多花了一轮才查清真相。

**要求**：今后遇到派活的事实前提与仓库实际不符，**必须写进 `Open questions` 并停在那一步**，
不要沉默略过 —— 派活文档是契约，契约与事实冲突时的裁决权在设计层，不在执行层的沉默里。

## 7. 需要执行层做的事（按顺序）

1. **立刻** `git add -N src/ai_code_audit/hybrid_cli.py`，消除交付物丢失风险（§2.3）
2. ~~补 CODE-DEAD-001~~ —— **已撤销，不要执行**（§2.1）。`scanner` / `reporter` /
   `version.ts` 原地保留
3. 补完 CODE-MERGE-001：迁 `src/codeguard/` 的 8 个文件，不留 shim；新增
   `tests/test_package_layout.py::test_no_legacy_package_trees`；附迁移前后模块对照表
4. 以上并入**一个** commit `refactor(code): consolidate package trees into ai_code_audit`
   （ISSUE 1 撤销后 004 本阶段只需这一个提交；不造空 commit）
5. ~~改 `inspect_worker_return.py` 的 Worker D~~ —— **已撤回，保持 `codeguard.cli`**（§5）
6. 补 ISSUE 3 的七仓测试数字（含 003 与 000shared-integration）
7. ISSUE 4 保持挂起，等决策层书面授权

## 8. 结论

**FAIL。** ISSUE 3 与 ISSUE 5 的实现质量没有问题，已逐条核实通过；ISSUE 4 的挂起处理正确，
003 的 8 个受保护项完好无损；ISSUE 1 经复核属派活前提有误，已撤销，不计执行层责任。
但本阶段的**主线** —— 004 的包树合并 —— 只走完第一步，
且全部改动停留在工作区外，其中还有一个 untracked 却被测试依赖的文件。这既不满足派活 §3 的
验收，也不满足 §4 的提交约定。

**对 015-OBSERVABILITY 的影响**：015 的门槛是 012 与 014 双双收口。
[`014` 已 PASS-WITH-NITS](014-FW-INTEROP.md)，因此 **015 现在只被 012 卡住**。
执行层完成 §7 的 1、3、4 项后重审 012，通过即可解锁 015。

**不建议**为了赶 015 而放宽 012 —— 004 的包树债正是「拖着不做会持续制造误判和返工」的那类
问题，半完成状态比未开工更危险：它让 `git clean` 变成破坏性操作。
