# 审计 · 011-INJECT-HARDEN

> **结论**：**PASS**
> **审计日期**：2026-08-13
> **派活**：[`011-INJECT-HARDEN.md`](../docs/dispatches/011-INJECT-HARDEN.md)
> **审计方式**：四份证据全部由审计员独立复现，不采信回报自述。

## 1. 交付提交

| 仓 | HEAD | ISSUE |
|---|---|---|
| `000shared-llm-core` | `e99e080` | CORE-INJECT-002 `1e2a7a7`、CORE-EVAL-003、CORE-EVAL-004 `e99e080` |
| `002AI-Vulnerability-Agent` | `c0128bd` | VULN-INJECT-001 |
| `005AI-Reverse-Agent` | `3936354` | REV-INJECT-001 `c9c630a`、CORE-EVAL-003 |
| `006AI-Firmware-Security-Agent` | `06d6630` | FW-INJECT-001 `123c419`、CORE-EVAL-003 |
| `004AI-Code-Audit/004AI-CodeGuard-upgrade` | `374a731` | CORE-EVAL-003 |

六个 ISSUE 全部有对应 commit，七个仓工作区全部干净，无空 commit。

## 2. 四份证据（逐条独立复现）

### 2.1 CORE-INJECT-002 绕过已封堵 —— ✅

审计员用 `010` 审计时的原始攻击输入重跑，并把验收从"看一个例子"提升为**验证不变量**。
对 8 组对抗输入逐一断言"存活开标签 = 1、存活闭标签 = 1、且为首尾"：

| 输入 | 结果 |
|---|---|
| 010 审计的原始攻击输入 | PASS |
| 完整包裹形状 / 只有开标签 / 只有闭标签 | PASS |
| 嵌套两层 / 空字符串 / 普通文本 / 双重包裹 | PASS |

修复后输出中攻击者的定界符被转义为 `&lt;UNTRUSTED_DATA` / `&lt;/UNTRUSTED_DATA&gt;`，
`SYSTEM OVERRIDE` 位于外层真实栅栏之内。**不变量成立。**

### 2.2 REV-INJECT-001 关键测试 —— ✅

```
tests/test_prompt_injection.py::test_symbol_name_is_delimited            PASSED
tests/test_prompt_injection.py::test_attacker_shaped_symbol_cannot_escape PASSED
tests/test_prompt_injection.py::test_guard_prompt_present                PASSED
```

该测试正是"攻击者构造的导入名"场景，在 CORE-INJECT-002 之前必然失败，依赖关系被
证明而非声明。

### 2.3 CORE-EVAL-003 门禁具备阻断能力 —— ✅

审计员自行改坏 006 的 `firmware-critical.json`：

```
finding.severity: critical -> low
→ EvalResult(case_id='firmware-critical', passed=False,
             deviations=("severity drifted 3 level(s): expected 'critical'...
1 failed, 2 passed
```

恢复后 `3 passed`，工作区干净。

**过程记录**：首次尝试改的是 `business_impact`（自由文本字段），门禁**未**变红。
复核确认这是**正确行为** —— 评估的设计是校验字段约束而非文案原文，自由文本变化不
应触发失败。审计员的探针选错了字段，不是门禁失效。

006 采用了嵌套结构 `finding.severity` 并用点路径寻址，与 001 的扁平结构不同 ——
符合派活 §7"按产品实际字段调整，不要硬套 001 字段名"的要求。

### 2.4 CORE-EVAL-004 覆盖守卫 —— ✅

把**非豁免仓** 005 的 `tests/test_eval_gate.py` 改名后：

```
AssertionError: reverse: missing tests/test_eval_gate.py
FAILED tests/test_eval_coverage.py::test_every_llm_product_has_an_eval_gate_or_exemption
```

恢复后 `4 passed`，005 工作区干净。

豁免表按 2026-08-13 裁决实现：`lab` 条目同时带 `reason` 与 `followup: "012"`，
`_validate_exemptions` 拒绝 `suite-lock.yml` 中不存在的仓、并强制双字段非空。

## 3. 回归（审计员独立执行，全绝对 PYTHONPATH）

| 仓 | 结果 | 对比 |
|---|---|---|
| `000shared-llm-core` | **124 passed** | 117 → +7 |
| `000shared-integration` | **143 passed, 4 skipped** | 未变（本阶段未涉及）|
| `001AI-SOC-Agent` | **278 passed** | 未变 ✅ |
| `002AI-Vulnerability-Agent` | **183 passed** | 180 → +3 |
| `004AI-CodeGuard-upgrade` | **183 passed** | 179 → +4 |
| `005AI-Reverse-Agent` | **284 passed** | 无下降 |
| `006AI-Firmware-Security-Agent` | **398 passed, 2 skipped** | 无下降 |

**零失败。** 001 与 004 的既有注入测试最后一次改动仍是 `010` 的提交
（`e59652e` / `fe1f1d4`），本阶段未触碰 —— 这是"边界加固没有破坏调用方"的证据。

CI 门禁 `Run LLM evaluation gates` 现覆盖 001 / 002 / 004 / 005 / 006 五个仓，
003 按裁决豁免。

受保护仓 `003AI Agent安全靶场`：HEAD 仍 `3862acf`，仍是 7 modified + 1 untracked，
**未被触碰** ✅

## 4. 两处契约冲突的裁决执行情况

| 问题 | 裁决 | 执行 |
|---|---|---|
| `005 cli.py:105` | 接受不修改（该行是 `role="assistant"` 的离线 stub 响应，非模型输入）| ✅ 未改动 |
| `003` 缺 eval gate | 不得提交到 003；改为显式豁免表 | ✅ 豁免表实现符合规格，003 零改动 |

## 5. 无 NIT

本阶段未发现需要执行层返工的问题。

## 6. 审计过程中的附带核实（不构成 ISSUE）

`010` 审计曾记录一条观察："005 的离线 stub 把 `name` 插进 `payload["purpose"]`，
攻击者可控符号名会流入 Finding 字段，属输出侧净化问题"。本次顺带核实了输出侧的
实际风险面：

- `002AI-Vulnerability-Agent/src/ai_vuln_agent/reporter_html.py:63` 使用
  `select_autoescape(default_for_string=True, default=True)`
- `006AI-Firmware-Security-Agent/src/ai_firmware_agent/html_report.py:40` 使用
  `select_autoescape(...)`

**HTML 报告路径的注入风险已被 Jinja2 自动转义挡住**，无需单开输出净化 ISSUE。
原观察据此关闭。

## 7. 结论

**PASS。** `010` 遗留的唯一实质缺陷（NIT-1）已修复，且修复被提升为不变量级验证；
不可信内容边界已覆盖全部五个接 LLM 的产品；评估门禁从 2 个产品扩到 5 个，并有守卫
防止未来静默漏掉。

后续：

1. `003` 的 eval gate 已记入豁免表的 `followup: "012"`，需要单独处理 —— 它会让
   003 的 HEAD 离开 `suite-lock.yml` 的锁定 SHA，须连带改锁并推送受保护仓，
   **必须由决策层显式授权**
2. 本阶段不涉及推送；七个仓的提交均在本地
