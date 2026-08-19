# 018-CORE-RULEENGINE：落定 ADR-006 与 core 文档提交

> **状态**：✅ PASS-WITH-NITS（2026-08-19；见 [`AUDIT/018`](../../AUDIT/018-CORE-RULEENGINE.md)）
> **依据**：[`ADR-006`](../adr/ADR-006-rule-engine-empty-registry.md)（已接受）
> **目标仓**：`000shared-llm-core` —— **只有这一个**
> **预计工作量**：约 20 分钟，**三个 commit**，不写新代码

## 1. 这个派活是干什么的

012/014 审计期间，core 工作区出现了一批**未经派活授权**的改动：`RuleEngine` 的构造语义
变更 + 大量测试补充。审计层把它记为 `docs/current-status.md` §4 P0.0 并交决策层判定。

**决策层已认可。** 设计层已补写 [`ADR-006`](../adr/ADR-006-rule-engine-empty-registry.md)
并同步 `docs/v0.5-contract.md` §8.5。本派活只做一件事：**把这些已经躺在工作区里的东西
按正确的边界提交掉**，不新增任何功能。

**不要重写、不要"顺手改进"任何一个文件。** 内容都已定稿并通过测试。

## 2. 已知事实（不必重新验证）

- core 全量当前 **150 passed**（改动前基线 126）
- `RuleEngine.__init__` 的语义变更与
  `tests/test_rule_engine.py::test_rule_engine_registry_property` 是配对的：
  该测试在旧的 `or` 写法下必然失败
- `docs/v0.5-contract.md` §8.5 已同步为实现的真实形态（含 `registry` 只读属性）
- 全套件已检索：无消费方对 `RuleEngine(...).registry` 赋值

## 3. 三个 commit（按此顺序，各自独立）

### C1 · `fix(core): honor an explicitly empty rule registry`

```
src/shared_llm_core/rule_engine.py
tests/test_rule_engine.py
```

`RuleEngine.__init__` 由 `registry or RuleRegistry.default()` 改为
`registry if registry is not None else RuleRegistry.default()`，
以及同文件内的 typing 现代化（`typing.Mapping/Sequence` → `collections.abc`、
去掉字符串前向引用）。这些都已在工作区，原样提交。

### C2 · `test(core): raise coverage on router, gateway and evaluation`

```
tests/test_client.py
tests/test_evaluation.py
tests/test_gateway.py
tests/test_router.py
tests/test_templates.py
tests/test_untrusted.py
tests/test_demo.py        ← 当前是 untracked，必须 git add
```

纯测试补充，无 src 改动。**注意 `tests/test_demo.py` 是未跟踪文件，别漏。**

### C3 · `docs(adr): accept ADR-006 and record the 012/014 audits`

```
docs/adr/ADR-006-rule-engine-empty-registry.md   ← untracked
docs/v0.5-contract.md                            ← §8.5 同步
docs/dispatches/012-STRUCT-DEBT.md               ← ISSUE 1 撤销 + ISSUE 2 shim 修正
docs/dispatches/012-REWORK.md                    ← untracked
docs/dispatches/018-CORE-RULEENGINE.md           ← untracked（本文件）
docs/dispatches/019-AUDIT-TOOLING.md             ← untracked
docs/dispatches/INDEX.md
AUDIT/012-STRUCT-DEBT.md                         ← untracked
AUDIT/012-REWORK.md                              ← untracked（最终 PASS）
AUDIT/014-FW-INTEROP.md                          ← untracked
AUDIT/019-AUDIT-TOOLING.md                       ← untracked
```

全部由设计/审计层写定，**逐字提交，不要编辑**。

## 4. 不属于本派活的文件（留在工作区，别碰）

以下三项是 **2026-08-15** 就存在的上一阶段产物，归 016/017 处置：

```
docs/adr/ADR-005-web-hosting-carrier-oidc.md
docs/dispatches/016-OIDC-DEPLOY.md
docs/dispatches/017-RELEASE-WINDOW.md
```

提交完 C1–C3 后，`git status --porcelain` 应当**只剩这三行**。这是本派活的收尾自检。

## 5. 验收

| # | 项 | 标准 |
|---|---|---|
| 1 | core 全量 | **150 passed**，不得下降 |
| 2 | `tests/test_versioning.py` | 全绿（`__version__` 仍是 `0.6.0`，ADR-006 §4 明确不升版本）|
| 3 | commit 数 | 恰好 3 个，各自文件清单与 §3 一致，无空 commit |
| 4 | 收尾状态 | `git status --porcelain` 只剩 §4 的三行 |

```powershell
$env:PYTHONPATH = "E:\001项目\000开发\003AI-Network-Security\000shared-llm-core\src"
C:\Users\15072\AppData\Local\Programs\Python\Python314\python.exe -m pytest tests/ --basetemp=C:/pytest-tmp/018-core -o addopts= -q
```

## 6. 约束

- 只提交到本地，**不 push**
- 不改任何产品仓
- 不动 `suite-lock.yml` —— ADR-006 不改变部署组合
- 不升 core 版本号 —— 理由见 ADR-006 §4

## 7. 回报格式

```
ISSUE: CORE-RULEENGINE-001
commits: <C1 hash> / <C2 hash> / <C3 hash>
tests: 150 passed
verify: 上表 4 项验收各自的命令 stdout
收尾 git status --porcelain: <应只剩 3 行>
Deviations: <可选>
Open questions: <可选>
```

## 8. 给执行层的一句话

这批改动本身质量不差 —— 那个 `or` 确实是 fail-open 隐患。**问题不在改动，在于它没有
派活授权就进了冻结组件。** 下次遇到"我看到 core 有个 bug 想顺手修"，正确动作是
写进 `Open questions` 让设计层判定，而不是直接改。见 `CLAUDE.md` §8。
