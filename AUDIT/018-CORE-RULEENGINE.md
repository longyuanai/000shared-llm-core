# 审计 · 018-CORE-RULEENGINE

> **结论**：**PASS-WITH-NITS**
> **审计日期**：2026-08-19
> **ISSUE**：`CORE-RULEENGINE-001`
> **目标仓**：`000shared-llm-core`
> **提交**：`7d65d2e` / `1304af8` / `85d34bd`
> **派活**：[`018-CORE-RULEENGINE.md`](../docs/dispatches/018-CORE-RULEENGINE.md)

## 1. 最终结论

执行层严格按派活完成三个连续本地提交，代码、测试与文档边界全部匹配：

1. `7d65d2e` — `fix(core): honor an explicitly empty rule registry`
2. `1304af8` — `test(core): raise coverage on router, gateway and evaluation`
3. `85d34bd` — `docs(adr): accept ADR-006 and record the 012/014 audits`

`RuleEngine` 现在只在 `registry is None` 时加载默认 registry，显式空 registry 保持对象身份；
回归测试在旧 `or` 实现下必然失败。契约 §8.5、实现和测试一致。独立全量、版本测试、
Ruff correctness、提交边界、保护文件与未推送状态全部通过。

有两个不阻塞的 NIT：一组是 ADR/派活的事实精度（003 不存在同类空表缺陷、typing
现代化会改变原始 annotation metadata、012 的最终测试数应为 184）；另一组是 C2 新增测试
没有完全隔离调用方环境变量。它们不影响 core 运行时与规定验收，但应由审计层更正文档并将
测试隔离问题记入 backlog，不让执行层为设计层原稿错误重写三个既定提交。

018 获准收口，015 可以按更新后的派活开始，但不得混入三个 OIDC/发布保护文件。

## 2. 十项 checklist

| # | 项 | 结果 | 证据 |
|---|---|---|---|
| 1 | 接口契约 | PASS | `RuleEngine` 可调用参数与公开导出未变；typing metadata 差异见 NIT-1 |
| 2 | 技术方案 | PASS | 精确落实已接受 ADR-006；显式空 registry 保持身份，仅 `None` 回退默认 |
| 3 | 测试 | PASS | 独立全量 `150 passed in 8.35s`；定向 versioning `2 passed in 0.39s` |
| 4 | CLI smoke | N/A | 本派活不涉及 CLI；验收以 core API 测试为准 |
| 5 | 跨项目隔离 | PASS | 三个提交只修改 core 派活列出的文件；003 与其他产品仓零修改 |
| 6 | 依赖管理 | PASS | `pyproject.toml`、版本号与 `suite-lock.yml` 均未修改 |
| 7 | 代码质量 | PASS | `git diff HEAD~3 --check` 通过；Ruff `E9,F63,F7,F82` 全绿 |
| 8 | Prompt 模板 | N/A | 不涉及 prompt |
| 9 | 审计日志 | N/A | 不涉及 LLM 调用或 AuditLog |
| 10 | 回报与提交 | PASS | 回报字段完整；恰好三个连续 commit，文件边界逐项匹配，未 push |

## 3. 独立验收证据

固定使用绝对 Python、绝对 `PYTHONPATH`、ASCII basetemp 和 `-o addopts=`。

| 验收项 | 结果 |
|---|---|
| core 全量 | `150 passed in 8.35s` |
| `tests/test_versioning.py` | `2 passed in 0.39s` |
| Ruff correctness | `All checks passed!` |
| commit 数 | `1f82fd0..HEAD` 精确为 3 |
| C1 文件边界 | `rule_engine.py` + `test_rule_engine.py`，完全匹配 |
| C2 文件边界 | 7 个规定测试文件，含新增 `tests/test_demo.py` |
| C3 文件边界 | 11 个规定 ADR/契约/派活/审计文件，完全匹配 |
| whitespace | `git diff HEAD~3 --check` 退出码 0、无输出 |
| 版本与锁 | `pyproject.toml`、`suite-lock.yml`、v0.1 contract 零变更 |
| 保护文件 | ADR-005、016、017 未进入任一提交 |
| 执行提交验收时状态 | tracked clean；仅上述三个保护文件 untracked；随后审计层文件进入 015 C0 |
| 未推送 | 无远端分支包含 `85d34bd` |
| 环境隔离探针 | `LLM_PROMPTS_ROOT` 可使 demo 测试失败；`SHARED_LLM_EVAL_MODE=live` 可使 4 个 replay 测试失败 |
| 独立高强度审查 | core 正确性无 blocker；归并为 2 组非阻塞 NIT |

## 4. NIT（不阻塞）

### NIT-1 · ADR/派活的三处事实精度

`docs/adr/ADR-006-rule-engine-empty-registry.md` §5 指向
`003AI Agent安全靶场/src/ai_agent_lab/v05_compat.py:276`，称其有同类空表吞没问题。
003 的 `RuleRegistry` 没有实现真值协议，空实例仍为 truthy，因此：

```python
registry or RuleRegistry.default()
```

会保留传入实例，不会复现 core 中由 `RuleRegistry.__len__` 引起的缺陷。保留原文可能诱导
未来执行层在 003 解锁后制造无必要修改。

此外，C1 获授权的 typing 现代化把字符串前向引用改为普通 postponed annotation，并把
`typing.Mapping/Sequence` 改为 `collections.abc` 版本。可调用参数、运行时行为与
`typing.get_type_hints()` 的前向引用解析没有破坏性变化，但原始 `__annotations__` 与
`inspect.signature()` 的字符串表示可观察地不同。因此 ADR-006 中“签名未变”应收窄为
“可调用参数未变”，不能宣称所有 introspection metadata 逐字不变。

最后，`012-REWORK.md` 要求新增一个布局测试却仍写最终 `= 183 passed`；最终正确基线已经
独立验证为 184。该数字应同步，避免未来按字面重新验收时产生假失败。

上述三处均由审计层直接纠正文档，不要求产品/核心代码返工。

### NIT-2 · C2 新增测试未完全隔离合法环境变量

- `tests/test_demo.py` 断言默认 `./prompts`，但未清除 `LLM_PROMPTS_ROOT`；设置合法自定义
  prompts 路径时可稳定复现失败；
- `tests/test_evaluation.py` 的 replay 用例未固定 `SHARED_LLM_EVAL_MODE=replay`；调用者环境
  合法设置为 `live` 时可稳定复现 4 个失败；
- `tests/test_router.py::test_router_from_env_builds_default_rules` 未固定
  `LLM_LOCAL_ENABLED`；环境为 `off` 时 route 指向被禁用 provider，测试在 `resolve()` 失败。

这些是测试夹具卫生问题，不是产品行为错误；规定的干净验收环境中 150 项全绿，因此不阻塞
018。后续修复应只在测试内用 `monkeypatch.setenv/delenv` 固定前置条件，不改生产语义。

## 5. 批准与解锁

**PASS-WITH-NITS，批准。** 两组 NIT 不影响 018 的运行时行为、API 契约、规定测试门禁或
提交纪律，也不阻塞后续阶段。

下一步是 `015-OBSERVABILITY`。开始前先提交审计层预写的 018 收口文档，再执行 015 的五个
OTel ISSUE（C4 在每个实际修改的产品仓独立提交）；三个 OIDC/发布文件继续保持在 015 范围外。
