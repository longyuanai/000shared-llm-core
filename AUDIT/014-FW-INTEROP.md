# 审计 · 014-FW-INTEROP

> **结论**：**PASS-WITH-NITS**（2 个 NIT，均不阻塞 015）
> **审计日期**：2026-08-17
> **派活**：[`014-FW-INTEROP.md`](../docs/dispatches/014-FW-INTEROP.md)
> **设计依据**：[`ADR-004`](../adr/ADR-004-build-vs-wrap.md) §3 的 006 轨
> **审计方式**：关键声明逐条独立复现，不采信回报自述。

## 1. 交付

唯一目标仓 `006AI-Firmware-Security-Agent`，四个独立 commit，提交信息与派活 §3 逐字一致，
工作区干净（审计前后均为 `ahead 6`、零脏文件）：

| ISSUE | commit | 提交信息 |
|---|---|---|
| FW-EMBA-001 | `3281db1` | `feat(firmware): import emba analysis reports` |
| FW-PROV-001 | `a7cce60` | `feat(firmware): record finding source provenance` |
| FW-EVAL-001 | `dc69440` | `test(eval): baseline golden sets per finding source` |
| FW-INJECT-002 | `c1ef321` | `fix(firmware): fence imported report content` |

未 push，符合派活 §5。无空 commit：四个 commit 分别改动 5 / 3 / 14 / 2 个文件。

## 2. 逐条核实

### 2.1 SBOM 零改动 —— ✅（派活 §2.1 的硬约束）

`git diff HEAD~4 --stat` 的 23 个条目中**没有任何 `src/ai_firmware_agent/sbom/` 路径**，
四个 SBOM 测试文件同样未出现。派活最强的一条禁令执行到位。

### 2.2 许可证边界 —— ✅（派活 §4 FW-EMBA-001 硬约束）

- `git diff HEAD~4 -- pyproject.toml poetry.lock requirements.txt` **为空** —— 没有新增依赖，
  EMBA 未被声明为依赖
- `providers/emba.py` 全文无子进程、无 socket、无 EMBA 脚本片段；`load_emba_report` 只做
  `path.read_bytes()`
- `docs/emba-import.md` §License boundary 明确写出「EMBA is GPL-3.0. This MIT-licensed
  product does not include or distribute EMBA, does not depend on it, and does not execute
  it.」
- 文档措辞是「If you already have that EMBA report」，没有引导用户安装 EMBA

### 2.3 fail-closed 且不猜 schema —— ✅

先校验后取值，五级类型化错误：`EmbaImportError` 基类下分
`EmbaParseError` / `EmbaMissingFieldError` / `EmbaUnsupportedVersionError` / `EmbaSchemaError`。

硬校验的 marker：`$schema` 精确匹配 CycloneDX 1.5 schema URL、`bomFormat == "CycloneDX"`、
`specVersion == "1.5"`、文档 `version` 必须是 `int` 且为 `1`（`type(x) is not int` 排除了
`bool`）、`metadata.tools.components` 必须标识 `EMBA binary analysis environment` 且
`author == "EMBA community"`、`bom-ref` 重复即拒。

**最值得肯定的一处**：`vulnerabilities` 非空即拒（`emba.py:188`），并在注释里写明理由 ——
官方 F15 当前固定输出 `[]`，接受猜出来的漏洞记录等于声称支持 EMBA 并不产出的格式。
这是派活 §4「不要编造 schema」的正确执行，而不是绕过。

### 2.4 006 全量与基线 —— ✅

| 项 | 结果 |
|---|---|
| 006 全量（完整 PYTHONPATH） | **415 passed, 2 skipped**（`011` 基线 398 → **+17**）|
| 派活要求的 14 个测试名 | **14/14 存在且通过**（逐个 `def` 匹配核对）|
| `011` 已建立的注入测试 | 仍全绿（`test_prompt_injection` 等四文件 23 passed）|
| core 覆盖守卫 | `test_eval_coverage.py` **4 passed**，006 未掉出覆盖 |
| Ruff | `All checks passed!` |
| 4 件套（Worker F） | **PASS** —— commits / diffstat / pytest / CLI envelope 全绿 |

回报自述的 `415 passed, 2 skipped` **属实**。

**关于 mypy**：回报称本机未安装、遵守约束不装新工具。审计员核实
`python -m mypy --version` → `No module named mypy`。**声明属实**，不是回避。

### 2.5 native 六份基线内容未被改动 —— ✅（审计员独立核对）

`git diff HEAD~4 --stat` 中六个 native fixture 全部显示为
`{旧名 => native-新名}` 且改动量为 **0**：

```
...critical.json => native-firmware-critical.json}   | 0
...gh-epss.json => native-firmware-high-epss.json}   | 0
...irmware-high.json => native-firmware-high.json}   | 0
...e-kev-hit.json => native-firmware-kev-hit.json}   | 0
...are-medium.json => native-firmware-medium.json}   | 0
...are-no-cve.json => native-firmware-no-cve.json}   | 0
```

纯改名，声明属实。派活 §4 FW-EVAL-001 第 3 条满足。

### 2.6 两套基线红灯 —— ✅（审计员自行复现，未采信回报）

审计员没有改动仓内 fixture，而是把 `evals/fixtures/` 复制到临时目录、翻转录制的
`severity`、直接调 `run_eval`：

```
[native] clean copy : all passed = True
[native] corrupted   : failing cases = ['native-firmware-critical']
             deviations = ("severity drifted 3 level(s): expected 'critical', got 'low', maximum 0",)

[emba] clean copy : all passed = True
[emba] corrupted   : failing cases = ['emba-firmware-critical']
             deviations = ("severity drifted 3 level(s): expected 'critical', got 'low', maximum 0",)
```

两套基线各自变红，**且污染 native 不牵连 emba 用例、反之亦然** —— 来源隔离是真的生效，
不是靠共享一个门禁蒙过去。006 工作区在整个复验过程中零脏。

### 2.7 EMBA 基线诚实标注 —— ✅

`evals/README.md`：

> `emba-*` fixtures are synthetic recordings for the EMBA-import path. They were
> not produced by running EMBA and are not claimed to represent a captured EMBA
> execution.

与 `013` 对 Ghidra 基线的处理一致，未伪装成真实运行产物。`docs/emba-import.md` 同样注明
「The tests use a synthetic recording of that documented shape, not output captured from a
real EMBA run.」

### 2.8 命名避让 —— ✅（派活 §4 FW-PROV-001 的 `013` 教训）

`grep new_finding\(|finding_origin src/` 确认 `finding_origin` 是新增的唯一键，与既有的
`source`（冻结 Finding 顶层字段，值 `FindingSource.FIRMWARE`）和 `provider`
（inventory / CVE / LLM / CLI 已占用）都不冲突。选择理由与回报一致，且审计员核实了
被占用的那两个键确实已被占用 —— 这是按 `013` 教训做过检索的证据，不是事后补的说法。

### 2.9 导入内容进入既有边界 —— ✅

`analyzer.py` 新增 `_component_evidence_kind()`，在既有的 `wrap_untrusted` 调用点上把
`kind` 从固定 `"firmware_component"` 改为按来源取值，EMBA 走 `"imported_report"`。
**复用 `011` 的边界，没有新造一套**；system message 仍是
`INJECTION_GUARD_SYSTEM_PROMPT`。`cves_json` 保持原 kind 是正确的 —— 那份数据来自 CVE 库
而非导入报告，且同样在包裹内。

### 2.10 envelope 顶层结构未变 —— ✅

`test_provenance.py::test_envelope_top_level_shape_unchanged` 对 native 与 imported 两条
路径同时断言 `{"findings", "errors", "summary"}`。CLI smoke 实测输出：

```json
{"findings": [], "errors": [...], "summary": {"component_count": 0, "finding_count": 0, "status": "warning"}}
```

### 2.11 零真实子进程 / 零出网 —— ✅

`tests/test_emba_import.py` 的 autouse tripwire 封死
`asyncio.create_subprocess_exec`、`subprocess.run/Popen`、
`socket.create_connection/getaddrinfo`。

**审计员核实这道网是否有洞**（`013` 同类检查）：`providers/emba.py` 全文无任何子进程或
socket 入口，唯一 I/O 是 `path.read_bytes()`，因此 tripwire 覆盖范围大于实际路径。
另核实新代码无硬编码密钥、无硬编码绝对路径（`path=""` 是刻意不复制客户文件系统路径，
已在代码注释说明）。

## 3. 10 项 checklist

| # | 项 | 结果 | 备注 |
|---|----|------|------|
| 1 | 接口契约 | PASS | 未改 core；`shared_llm_core.untrusted` 公开符号；Finding 顶层字段未动 |
| 2 | 技术方案 | PASS | 严格在 ADR-004 §3 006 轨范围内；SBOM 未触碰 |
| 3 | 测试 | PASS | 415 passed, 2 skipped；14/14 规定测试名到位 |
| 4 | CLI smoke | PASS | 4 件套 Worker F 全绿；`--emba-report` 与 `--input/--demo/--sbom` 互斥有校验 |
| 5 | 跨项目隔离 | PASS | 仅 006 一仓 4 个 commit |
| 6 | 依赖管理 | PASS | 依赖清单零改动；core 仍为 path 依赖 |
| 7 | 代码质量 | PASS | Ruff 全绿；无密钥/绝对路径/print 日志 |
| 8 | Prompt 模板 | N-A | 未新增 prompt，复用既有边界 |
| 9 | 审计日志 | N-A | 导入路径不触发新的 LLM 调用类型 |
| 10 | 回报格式 | PASS | 四件套齐全；三条额外要求（零子进程佐证 / 键名检索说明 / 两套红灯 + 改名佐证）全部提供且核实属实 |

## 4. NIT（不阻塞，记入 backlog）

### NIT-1 · `finding_origin` 的默认值对未来的导入路径是静默陷阱（low）

`v05_compat.py:184` 用 `setdefault("finding_origin", "native_pipeline")`。这**正是派活
§4 FW-PROV-001 第 2 条要求的行为**（未标注的历史路径一律记为本地流水线），本阶段无缺口 ——
非 JSON 的 `--emba-report` 路径产出 Markdown/HTML 报告，不产出 Finding，因此不存在错标。

隐患在**下一个导入来源**：`emba_import` 目前只在 `providers/emba.py:242` 一处标注，
未来任何新的导入路径若忘记传这个键，会拿到看似合理的 `native_pipeline` 而不是报错，
基线污染将无声发生。建议下阶段把「产出 Finding 的导入路径必须显式声明来源」变成断言或
构造期校验，而不是依赖调用方记得传。

### NIT-2 · 边界 kind 靠嗅探字符串字面量 `"emba"`（low）

`_component_evidence_kind()` 通过 `detection_sources` 里是否含字面量 `"emba"` 决定 kind，
形成 parser 与 analyzer 之间的隐式耦合。当前只有一个导入来源，可读性没问题；第二、第三个
来源进来时会长成 if 链。建议届时把「来源 → 边界 kind」收敛成一张显式映射表。

## 5. 审计工具缺口（非本阶段责任，需修）

**这两条不影响 014 的结论，但会让后续每一次审计都出假 FAIL，必须修。**

### 5.1 `scripts/inspect_worker_return.py` 缺 `000shared-integration/src`

首次运行 4 件套得到 `2 failed, 413 passed, 2 skipped`，失败项是：

```
FAILED tests/integration/test_firmware_adapter_e2e.py::test_post_scan_returns_findings
FAILED tests/test_cli_envelope.py::test_firmware_adapter_subprocess_end_to_end
ModuleNotFoundError: No module named 'shared_integration'
```

脚本的 `inspect()` 只拼 `<project>/src` + `000shared-llm-core/src` + 声明的 extras，
**从不注入 `000shared-integration/src`**。这正是
[`010-AI-TRUST.md`](../docs/dispatches/010-AI-TRUST.md) §4.1 记录的、
2026-08-13「代价是两处误判」的同一个坑。补上该路径后 006 = `415 passed, 2 skipped`，
Worker A/D/F 4 件套全绿。

**范围比本节初版记的更大（2026-08-17 补测）**：干净环境下**全部六个 worker 都 FAIL**，
共 10 个假失败（001/002 各 1，003/004/005/006 各 2），根因同一个。补齐路径后五个转绿，
003 剩的那一个是它自己的既有缺陷。修复已派活 [`019-AUDIT-TOOLING`](../docs/dispatches/019-AUDIT-TOOLING.md)。

临时绕法（本次审计所用）：脚本会把环境里的 `PYTHONPATH` 追加进去，因此
`$env:PYTHONPATH = "<R>\000shared-integration\src"` 可救。**但默认行为必须修**，
否则下一个审计员会重复第三次误判。

### 5.2 ~~Worker D 指向即将被删除的 `codeguard.cli`~~ —— 已撤回（2026-08-17）

本节初版判定 Worker D 须改为 `ai_code_audit.cli`。**复核后撤回**：
`000shared-integration/src/shared_integration/adapters/code.py:12` 硬编码
`module = "codeguard.cli"`，Worker D 是在镜像真实适配器，**应保持不变**。
需要保证的是 012 合并后 `src/codeguard/cli.py` 仍然存在 —— 该约束已写进
[`012` 派活](../docs/dispatches/012-STRUCT-DEBT.md) §3 ISSUE 2 第 4 条的修正。

因此本节只剩 §5.1 一条真缺口。

## 6. 剩余验证缺口（按契约不要求）

拿一份**真实**的 F15 `EMBA_cyclonedx_sbom.json` 做手工互操作验证仍未做。回报对此的表述
诚实：结构判断依据是官方生成脚本，文档与评估均标注为合成录制。派活 §4 明确写了
「审计层没有 EMBA 样本可供核对」，因此**本阶段不要求真实样本**，与 `013` 对真实 Ghidra
headless 的处理一致。建议在 `docs/emba-import.md` 已有说明的基础上，等有真实样本时补一次
手工验证并记录，不必阻塞 015。

## 7. 结论

**PASS-WITH-NITS。** `ADR-004` §3 的 006 轨已按决策落地：只读导入不分发、严格 schema 校验
fail-closed、不猜 EMBA 未产出的字段、来源可溯源、基线按来源隔离且互不遮蔽、导入内容同样受
`011` 的不可信边界约束、SBOM 零触碰。两个 NIT 均为面向下一阶段的可读性/防呆建议，不需要
执行层返工。

后续：

1. 两个 NIT 记入 backlog，不阻塞 015
2. **§5.1 的审计工具缺口须修** —— 它会持续制造假 FAIL；5.2 经复核已撤回
3. 015-OBSERVABILITY 的门槛**只剩 012** —— 014 侧已收口，见
   [`012-STRUCT-DEBT` 审计](012-STRUCT-DEBT.md)
4. 本阶段四个提交均在本地，未 push
