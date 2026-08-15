# 014-FW-INTEROP：006 第三方报告互操作

> **状态**：🟢 已解锁
> **解锁证据**：[`ADR-004`](../adr/ADR-004-build-vs-wrap.md) 已接受；`013` 审计 PASS
> **前置**：与 `012` 并行不冲突（目标仓不同）
> **预计工作量**：4 个 ISSUE，约 6 小时

## 1. 目标

执行 `ADR-004` §3 的 006 轨：**不捆绑 EMBA**（GPL-3.0），改为**导入客户自行运行的
EMBA 报告**，由 006 接管 LLM 分析。这条路径完全不涉及分发，规避许可证问题。

结构上照搬 `013` 已验证有效的形状：导入 → 溯源标注 → 按来源隔离基线 → 外部内容过
不可信边界。

## 2. 两条必须先知道的事实（2026-08-15 核实）

### 2.1 CycloneDX SBOM 已经做完了，不要再做

`ADR-004` 原文第 3 条写着"自建 CycloneDX SBOM 输出"。**那一条已作废并在 ADR 中划掉。**

006 已有 `src/ai_firmware_agent/sbom/cyclonedx.py`（226 行）：CycloneDX 1.5 JSON、
EPSS/KEV 以 properties 承载、VEX 风格 `vulnerabilities` 数组，四个专门测试文件，
CLI `--sbom` 可用。

**本阶段不得触碰 SBOM 相关代码。**

### 2.2 仓内已有第三方工具导入的现成范式

006 已经在做同类事情，直接照搬，不要另起炉灶：

| 现有实现 | 位置 |
|---|---|
| `parse_syft_inventory(payload) -> list[Component]` | `src/ai_firmware_agent/providers/inventory.py:53` |
| `parse_cve_bin_inventory(payload) -> list[Component]` | `src/ai_firmware_agent/providers/inventory.py:104` |
| 外部 CLI 封装（可注入 runner 的范式） | `src/ai_firmware_agent/binwalk_runner.py` |

EMBA 导入应当是这一系列的第三个成员，风格与错误处理保持一致。

## 3. 范围与提交顺序

允许修改：`006AI-Firmware-Security-Agent/` 全仓、其 `evals/`

不得修改：

- `src/ai_firmware_agent/sbom/` 及其四个测试文件（见 §2.1）
- 冻结的 v0.1 / v0.5 §7–§10 对外签名
- `010` / `011` 建立的评估与边界机制（只增不改）
- 其它产品仓

提交顺序：

1. `feat(firmware): import emba analysis reports`
2. `feat(firmware): record finding source provenance`
3. `test(eval): baseline golden sets per finding source`
4. `fix(firmware): fence imported report content`

## 4. ISSUE

### ISSUE FW-EMBA-001 · EMBA 报告导入（约 2.5h）

**目标**：006 能读取客户自行运行 EMBA 产出的报告，转成内部 `Component` /
`Finding`，接上既有的 CVE 匹配与 LLM 分析。

**许可证边界（硬约束，不得越过）**：

- **不得**把 EMBA 本体、其脚本、其任何代码片段加入本仓或依赖清单
- **不得**在代码或文档中引导用户"我们帮你装 EMBA" —— 只描述"如果你已有 EMBA 报告"
- 只读取 EMBA 的**输出产物**，不调用 EMBA、不分发 EMBA

**关于 EMBA 报告格式**：审计层**没有 EMBA 样本可供核对**。因此：

- 解析必须**先做 schema 校验再取值**，遇到未知结构 **fail-closed 并给出明确错误**，
  不要"尽力而为"地猜字段
- 支持的 EMBA 版本/格式在 `docs/emba-import.md` 中写清楚，**写你实际实现并测试过的
  那一种**，不要声称支持没验证过的版本
- 若你在实现中发现无法确定真实 EMBA 输出结构 → **停下来问**，不要编造一个 schema

**任务**：

1. 新增 `src/ai_firmware_agent/providers/emba.py`，风格对齐 §2.2 的两个既有 parser
2. CLI 增加导入子命令/选项，形态与既有选项一致
3. 新增 `docs/emba-import.md`：适用前提、支持的格式、许可证说明
   （**明确写出 EMBA 是 GPL-3.0，本产品不分发它**）
4. 解析失败、字段缺失、版本不支持各有明确错误类型

**测试**（≥ 6 个，全部用合成样本，不得依赖真实 EMBA）：
- `tests/test_emba_import.py::test_parses_recorded_report`
- `tests/test_emba_import.py::test_unknown_schema_fails_closed`
- `tests/test_emba_import.py::test_missing_required_field_raises_typed_error`
- `tests/test_emba_import.py::test_components_map_to_internal_model`
- `tests/test_emba_import.py::test_import_does_not_invoke_any_subprocess`
- `tests/test_emba_import.py::test_cli_import_produces_valid_envelope`

**验收**：006 全量 ≥ 398 passed（`011` 基线）；CLI smoke 输出合法 envelope；
整轮零子进程真实调用、零出网。

---

### ISSUE FW-PROV-001 · Finding 来源溯源（约 1h）

**目标**：与 `013` 的 `REV-PROV-001` 同构 —— 不同来源的证据质量不同，混在一起而不
标注会污染评估基线。

**⚠️ 命名避让（`013` 的教训）**：005 上曾出现过 `backend` 键已被"二进制加载器"占用
的情况，执行层用 `decompiler_backend` 避让才没撞车。**动手前先 grep 006 有没有
`source` / `provider` / `origin` 这类键已被占用**，若有，选一个语义明确且不冲突的新
键名，并在回报里说明你查了什么、为什么这样命名。

**任务**：

1. Finding metadata 增加来源标识，区分「006 自身流水线」与「导入的 EMBA 报告」
2. 未标注的历史路径一律记为本地流水线，不留空
3. **不得改变 envelope 顶层结构**

**测试**（≥ 3 个）：
- `tests/test_provenance.py::test_native_pipeline_findings_are_tagged`
- `tests/test_provenance.py::test_imported_findings_are_tagged`
- `tests/test_provenance.py::test_envelope_top_level_shape_unchanged`

**验收**：006 全量无下降；envelope 顶层结构未变。

---

### ISSUE FW-EVAL-001 · 按来源隔离黄金集（约 1.5h）

**目标**：同 `013` 的 `REV-EVAL-001`。来源不同 → LLM 输入不同 → 不隔离基线就会把
"换来源"误报成"质量回归"。

**任务**：

1. `evals/fixtures/` 按来源隔离（case id 前缀即可，`013` 用的就是这个办法）
2. `tests/test_eval_gate.py` 按当前来源加载对应基线
3. **保持 `011` 已有的六份 native 基线内容不变**，只允许改名/移动
4. EMBA 那套基线由合成录制生成，`evals/README.md` **必须注明它不是真实 EMBA 运行
   产物** —— 与 `013` 对 Ghidra 基线的处理一致

**测试**（≥ 3 个）：
- `tests/test_eval_gate.py::test_native_golden_set_passes_in_replay`
- `tests/test_eval_gate.py::test_imported_golden_set_passes_in_replay`
- `tests/test_eval_gate.py::test_sources_have_separate_baselines`

**验收**：

1. 两套基线各自全绿
2. **各改坏一个 fixture → 对应门禁变红 → 恢复**，两次输出都贴进回报
3. core 的覆盖守卫仍通过（006 不得掉出覆盖）
4. 回报中说明 native 六份基线内容未被改动（可用 `git diff --stat` 佐证是纯改名）

---

### ISSUE FW-INJECT-002 · 导入内容进入边界（约 0.75h）

**目标**：`ADR-004`"安全与运维影响"明确要求 —— **导入的第三方报告同样是攻击者可
影响的内容**（攻击者控制固件 → 影响 EMBA 报告文本）。

**任务**：

1. 从 EMBA 报告导入的字符串在进入 prompt 前走
   `wrap_untrusted(..., kind="imported_report")`
2. 复用 `011` 在 006 已建立的边界调用方式，**不要新造一套**
3. system message 沿用 `INJECTION_GUARD_SYSTEM_PROMPT`

**测试**（≥ 2 个）：
- `tests/test_prompt_injection.py::test_imported_report_content_is_delimited`
- `tests/test_prompt_injection.py::test_attacker_shaped_imported_text_cannot_escape`
  —— 用 `011` 审计那段"看起来已包裹"的形状作为报告内容

**验收**：006 全量无下降；`011` 已有的四个注入测试**必须仍然通过**。

## 5. 全局约束

- 绝对 Python：`C:\Users\15072\AppData\Local\Programs\Python\Python314\python.exe`
- pytest 一律 `--basetemp=C:/pytest-tmp/014-<name> -o addopts=`
- **PYTHONPATH 必须绝对路径**，表见 [`010-AI-TRUST.md`](010-AI-TRUST.md) §4.1
- 只提交到本地，不 push；4 个独立 commit，不合并，不造空 commit
- **基线：006 = 398 passed**

## 6. 回报格式

同 `013`。额外要求：

- `FW-EMBA-001` 说明如何确认整轮零真实子进程调用
- `FW-PROV-001` 说明你 grep 了哪些既有键名、为什么选现在这个
- `FW-EVAL-001` 贴两套基线各一次的红灯输出 + native 基线未改动的佐证

## 7. 卡住时怎么办

停下来问，写进 `Open questions`。特别地：

- **无法确定真实 EMBA 输出结构** → 停，不要编造 schema
- 想顺手改进 SBOM → **不要**，见 §2.1
- 发现需要调用 EMBA 才能实现 → 停，那越过了 `ADR-004` 的许可证边界
