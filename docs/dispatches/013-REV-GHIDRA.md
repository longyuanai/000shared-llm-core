# 013-REV-GHIDRA：005 反编译接缝与 Ghidra 后端

> **状态**：🟢 已解锁
> **解锁证据**：[`ADR-004`](../adr/ADR-004-build-vs-wrap.md) 已被决策层接受
> **前置**：`011-INJECT-HARDEN` 审计 PASS；`012-STRUCT-DEBT` 与本阶段无依赖，可并行
> **预计工作量**：5 个 ISSUE，约 8 小时

## 1. 目标

按 `ADR-004` §2 执行 005 轨：给反编译加一条可插拔接缝，接入 Ghidra headless 作为
可选后端，保留现有 capstone 路径作降级层，并让每条结论都能追溯到产出它的后端。

**本阶段不做 006 轨**（CycloneDX SBOM、EMBA 报告导入）—— 那是独立主题，混做会污染
验收信号。

## 2. 三条不可绕过的环境事实（2026-08-13 核实）

写进契约，避免执行层在这上面浪费时间或做错验收：

### 2.1 本机没有 Ghidra，也没有 JVM

```
where analyzeHeadless      → 无
java -version              → command not found
```

**因此 ISSUE 2 的验收不得依赖真实 Ghidra 运行。** 后端必须把子进程调用放在**可注入
的 runner 后面**，测试用 stub / 录制输出，全套测试在无 Ghidra 环境下必须能跑通。
真实 Ghidra 的验证写成**手工步骤文档**，留待有环境时执行，不作为本阶段验收条件。

### 2.2 `decompiler.py` 是公开 API 面，不能随便改

它导出的是自由函数，被三处消费：

| 消费方 | 用到的符号 |
|---|---|
| `src/ai_reverse_agent/cli.py:27,35` | `decompile_bytes` / `format_decompilation` / `find_function_boundaries` |
| `src/ai_reverse_agent/patch_diff.py:10` | `FunctionBoundary` / `find_function_boundaries` |
| `src/ai_reverse_agent/__init__.py:32` | **包级重导出** |

`__init__.py` 的重导出意味着这些是包的对外契约。**引入接缝不得删除或改签名这些符号**
—— 它们要么保持原样，要么成为默认后端之上的薄封装。

### 2.3 当前没有任何后端溯源字段

`adapter.py` 里没有 `backend` / `provenance` / `engine` 概念。ISSUE 3 是从零加，
不是改造。

## 3. 范围与提交顺序

允许修改：`005AI-Reverse-Agent/` 全仓、`005AI-Reverse-Agent/evals/`

不得修改：

- 冻结的 v0.1 / v0.5 §7–§10 对外签名
- `010` / `011` 建立的评估与边界机制（只增不改）
- 其它五个产品仓
- `003AI Agent安全靶场` 受保护文件

提交顺序（1 阻塞 2/3；4/5 依赖 2）：

1. `refactor(reverse): extract decompiler backend protocol`
2. `feat(reverse): add ghidra headless backend`
3. `feat(reverse): record decompiler provenance in findings`
4. `test(eval): baseline golden sets per decompiler backend`
5. `fix(reverse): fence ghidra output through the untrusted boundary`

## 4. ISSUE

### ISSUE REV-SEAM-001 · 反编译后端协议（约 2h，阻塞 2/3）

**目标**：给反编译加一条与现有 `BinaryBackend` 同构的接缝。

**设计约束（不要自行更换）**：

- **新建 `DecompilerBackend` 协议，不要把 Ghidra 塞进 `BinaryBackend`。**
  后者是**加载**接缝（`supports(data)` / `load(path, data)`），职责不同。
  ADR-004 §2 已就此定论
- 协议至少包含：`name`（后端标识）、`available()`（环境是否满足）、
  `decompile(image, ...) -> tuple[DecompiledFunction, ...]`
- 现有 capstone 实现原样包成 `NativeDecompilerBackend`，`available()` 恒为 `True`
- 选择逻辑镜像 `BinaryLoader` 的回退链：按序尝试，`available()` 为假则跳过

**任务**：

1. 新增 `src/ai_reverse_agent/decompilers/base.py`（协议 + 数据类复用现有
   `DecompiledFunction`）
2. 新增 `src/ai_reverse_agent/decompilers/native.py`，包装现有逻辑
3. 新增 `src/ai_reverse_agent/decompilers/selector.py`，实现回退链
4. **保持 §2.2 列出的全部公开符号可用且签名不变**。`decompile_bytes` 等改为走
   默认后端的薄封装

**测试**（≥ 5 个）：
- `tests/test_decompiler_backends.py::test_native_backend_is_always_available`
- `tests/test_decompiler_backends.py::test_selector_skips_unavailable_backend`
- `tests/test_decompiler_backends.py::test_selector_falls_back_to_native`
- `tests/test_decompiler_backends.py::test_public_api_symbols_unchanged`
  —— 断言 `__init__.py` 重导出的符号仍可导入且签名一致
- `tests/test_decompiler_backends.py::test_native_output_matches_pre_refactor`
  —— 对一个固定输入，断言重构后输出与重构前逐字节一致

**验收**：005 全量 = 284 passed（`011` 基线，不得下降）；CLI smoke 输出合法 envelope。

---

### ISSUE REV-GHIDRA-001 · Ghidra headless 后端（约 3h）

**目标**：接入 Ghidra，但**不让本阶段的验收依赖它装没装**。

**设计约束**：

- Ghidra 以**外部进程**调用（`analyzeHeadless`），不做进程内嵌入（ADR-004 §2）
- 子进程调用必须放在**可注入的 runner** 后面，签名参考 006 的
  `binwalk_runner.py`（`CommandRunner = Callable[..., subprocess.CompletedProcess[str]]`）
  —— 该仓已有可借鉴的先例
- `available()` 用 `shutil.which` 检测 `analyzeHeadless`，**不要**靠捕获异常判断
- Ghidra 不可用时后端安静跳过，由 selector 回退到 native。**不得抛异常中断扫描**
- Ghidra 路径与超时走环境变量，**不得硬编码任何路径**

**任务**：

1. 新增 `src/ai_reverse_agent/decompilers/ghidra.py`
2. 编写 headless 脚本或使用 Ghidra 自带导出，把反编译结果解析成
   `DecompiledFunction`
3. 超时、非零退出、输出解析失败都要有明确错误类型，且**不得把 Ghidra 的原始
   stderr 直接塞进 Finding**（可能含路径等环境信息）
4. 新增 `docs/ghidra-backend.md`：安装前提、环境变量、**手工验证步骤**
   （本机无 Ghidra，真实验证留给有环境时执行）

**测试**（≥ 6 个，全部不得依赖真实 Ghidra）：
- `tests/test_ghidra_backend.py::test_unavailable_when_binary_missing`
- `tests/test_ghidra_backend.py::test_available_when_binary_on_path`（stub `which`）
- `tests/test_ghidra_backend.py::test_parses_recorded_output`
- `tests/test_ghidra_backend.py::test_timeout_raises_typed_error`
- `tests/test_ghidra_backend.py::test_nonzero_exit_raises_typed_error`
- `tests/test_ghidra_backend.py::test_selector_falls_back_when_ghidra_unavailable`

**验收**：

1. 005 全量在**无 Ghidra 环境**下全绿（这是本阶段的实际验收条件）
2. 整轮测试**零子进程真实调用、零出网**
3. `docs/ghidra-backend.md` 的手工验证步骤可读、可执行

---

### ISSUE REV-PROV-001 · 后端溯源（约 1h）

**目标**：ADR-004 §"安全与运维影响"要求"Finding 里记录本次结论来自哪个后端"。
不同后端输出质量不同，混在一起而不标注会污染评估基线。

**任务**：

1. `DecompiledFunction`（或其容器）增加 `backend: str` 字段
2. `adapter.py` 把该值透传进 Finding 的 metadata / envelope
3. **不得改变 envelope 的顶层结构** —— 只在既有的元数据位置增字段
4. 未标注来源的历史路径一律记为 `"native"`，不留空

**测试**（≥ 3 个）：
- `tests/test_provenance.py::test_native_findings_are_tagged_native`
- `tests/test_provenance.py::test_ghidra_findings_are_tagged_ghidra`（用 stub 后端）
- `tests/test_provenance.py::test_envelope_top_level_shape_unchanged`

**验收**：005 全量无下降；CLI smoke 的 envelope 仍合法且顶层结构未变。

---

### ISSUE REV-EVAL-001 · 按后端分别录制黄金集（约 1.5h）

**目标**：ADR-004 明确指出，换后端会改变 LLM 输入，**若黄金集不分后端，切换后端会
被误报成质量回归**。

**任务**：

1. `evals/fixtures/` 按后端分目录（如 `native/` 与 `ghidra/`），或在 case id 中
   编码后端。二选一，但必须能区分
2. `tests/test_eval_gate.py` 按当前选中的后端加载对应基线
3. Ghidra 基线**用录制输出生成**（本机无 Ghidra），并在
   `evals/README.md` 注明"该基线由录制输出生成，非真实 Ghidra 运行产物"——
   **不要伪装成真实运行结果**
4. 保持 `011` 已有的 native 基线内容不变，只是移动位置

**测试**（≥ 3 个）：
- `tests/test_eval_gate.py::test_native_golden_set_passes_in_replay`
- `tests/test_eval_gate.py::test_ghidra_golden_set_passes_in_replay`
- `tests/test_eval_gate.py::test_backends_have_separate_baselines`

**验收**：

1. 两套基线在 replay 模式各自全绿
2. **改坏任一套的一个 fixture → 对应门禁变红 → 恢复**，两次输出都贴进回报
3. core 的覆盖守卫仍然通过（005 不得掉出覆盖）

---

### ISSUE REV-INJECT-002 · Ghidra 输出进入边界（约 0.75h）

**目标**：ADR-004 明确要求 —— **反编译产物不因为来自 Ghidra 就可信**。它同样是
攻击者可影响的内容（攻击者构造样本 → 影响反编译文本）。

**任务**：

1. Ghidra 后端产出的伪代码/符号在进入 prompt 前，走
   `wrap_untrusted(..., kind="decompiled_code")`
2. 复用 `011` 已在 `analyzer.py` 建立的边界调用方式，**不要新造一套**
3. system message 沿用 `INJECTION_GUARD_SYSTEM_PROMPT`

**测试**（≥ 2 个）：
- `tests/test_prompt_injection.py::test_ghidra_output_is_delimited`
- `tests/test_prompt_injection.py::test_attacker_shaped_decompiled_text_cannot_escape`
  —— 用 `011` 审计里那段"看起来已包裹"的形状作为反编译文本

**验收**：005 全量无下降；`011` 已有的三个注入测试**必须仍然通过**。

## 5. 全局约束

- 绝对 Python：`C:\Users\15072\AppData\Local\Programs\Python\Python314\python.exe`
- pytest 一律 `--basetemp=C:/pytest-tmp/013-<name> -o addopts=`
- **PYTHONPATH 必须绝对路径**，表见 [`010-AI-TRUST.md`](010-AI-TRUST.md) §4.1
- 动工前 `git status --short --branch`
- 只提交到本地，不 push
- 5 个 ISSUE 各自独立 commit，不合并，不造空 commit
- **基线：005 = 284 passed**（`011` 审计），任何 ISSUE 完成后不得低于此数

## 6. 回报格式

```
ISSUE: <ID>
commit: <hash>
files: <改动文件>
baseline: <动工前 005 的 pytest 数字>
tests: <N> passed, <M> failed
verify: <验收命令 stdout>
NITs / Open questions: <可选>
```

额外要求：

- `REV-SEAM-001` 贴 `test_native_output_matches_pre_refactor` 的通过输出
- `REV-GHIDRA-001` 说明如何确认整轮测试零真实子进程调用
- `REV-EVAL-001` 贴两套基线各一次的红灯输出

## 7. 卡住时怎么办

停下来问，写进 `Open questions`。特别地：

- 若发现无法在不改 §2.2 公开符号签名的前提下引入接缝 → **停**，不要擅自改签名，
  那是包的对外契约
- 若 Ghidra 的输出格式无法稳定解析成 `DecompiledFunction` → **停**，不要为了跑通
  而放宽 `DecompiledFunction` 的字段约束
- 若认为应当把 006 轨（SBOM / EMBA 导入）一并做掉 → **不要**，那是独立阶段
