# 审计 · 013-REV-GHIDRA

> **结论**：**PASS**
> **审计日期**：2026-08-15
> **派活**：[`013-REV-GHIDRA.md`](../docs/dispatches/013-REV-GHIDRA.md)
> **设计依据**：[`ADR-004`](../adr/ADR-004-build-vs-wrap.md)（已接受）
> **审计方式**：关键声明逐条独立复现，不采信回报自述。

## 1. 交付

唯一目标仓 `005AI-Reverse-Agent`，五个独立 commit，工作区干净：

| ISSUE | commit |
|---|---|
| REV-SEAM-001 | `97428dd` |
| REV-GHIDRA-001 | `c5f69e7` |
| REV-PROV-001 | `7537d1a` |
| REV-EVAL-001 | `d1d4328` |
| REV-INJECT-002 | `d0fcb72` |

## 2. 逐条核实

### 2.1 公开 API 未被破坏 —— ✅（派活 §2.2 的硬约束）

审计员把重构前（`3936354`）与当前的函数定义逐字符比对：

| 符号 | 结果 |
|---|---|
| `decompile_bytes` / `find_function_boundaries` / `format_decompilation` | **SAME** |
| `decompile_function` / `identify_stack_variables` | **SAME** |

并实际导入包验证 `__init__.py` 的重导出：`decompile_bytes`、`find_function_boundaries`、
`format_decompilation`、`DecompiledFunction`、`FunctionBoundary`、`StackVariable`
**全部可导入，签名一致**。

### 2.2 接缝独立于加载后端 —— ✅

`decompilers/base.py` 定义 `class DecompilerBackend(Protocol)`，文件内**不引用**
`BinaryBackend`。符合 ADR-004 §2 的定论。

### 2.3 native 基线内容未被改动 —— ✅

`git diff 3936354..HEAD -- evals/fixtures/` 显示六个 native fixture 全部是
**纯改名**（`{旧名 => 新名}`，0 内容变更），新增六个 `ghidra-*` fixture。
声明的"native 六份内容哈希保持不变"属实。

### 2.4 Ghidra 基线诚实标注 —— ✅

`evals/README.md`：

> The Ghidra baseline was generated from synthetic, recorded exporter output.
> It is **not a real Ghidra run artifact**.

派活明确要求"不要伪装成真实运行结果"，执行到位。

### 2.5 离线保证是真的，且拦得住实际调用路径 —— ✅

`tests/test_ghidra_backend.py` 的 autouse fixture 把 `subprocess.run`、
`socket.create_connection`、`socket.socket.connect` 替换为立即抛错的函数。

**审计员额外核实了这道网是否有洞**：若后端用 `Popen` 或 `check_output`，tripwire
就会漏。检查 `decompilers/ghidra.py` 确认 —— 唯一的子进程入口是
`self._runner = runner or subprocess.run`（第 62 行），tripwire 覆盖的正是实际路径。

同时确认：`available()` 用 `shutil.which`（第 75 行）而非捕获异常；可执行文件与超时
分别由 `AI_REVERSE_GHIDRA_HEADLESS`、`AI_REVERSE_GHIDRA_TIMEOUT_SECONDS` 控制，
无硬编码路径。

### 2.6 两套基线红灯 —— ✅（审计员自行复现）

```
改坏 native-reverse-known-read  → 2 个失败
改坏 ghidra-reverse-known-read  → 1 个失败
恢复后                          → 6 passed，工作区 0 脏
```

两套基线各自独立生效，互不遮蔽。

### 2.7 Ghidra 输出进入边界 —— ✅

`analyzer.py:135-137` 使用 `wrap_untrusted(..., kind="decompiled_code")`；
`011` 建立的 `binary_symbol` 边界（第 89–90 行）保持不变，未被替换或绕过。

## 3. 回归

| 项 | 结果 |
|---|---|
| `005AI-Reverse-Agent` 全量 | **304 passed**（`011` 基线 284 → **+20**）|

## 4. 执行层发现了派活的一处错误（记录在案）

派活 §2.3 断言"当前没有任何后端溯源字段"。**该断言不准确**：审计层当时只 grep 了
`adapter.py`，而 `backend` 键早已存在于五处，含义是**二进制加载器**后端
（`image.backend`）：

```
features/extractor.py:28   "backend": image.backend
scan.py:103                "backend": image.backend
features/model.py:61 / yara_gen.py:131 / deobfuscation/base.py:34
```

执行层没有沿用这个已被占用的键，而是新增语义明确的 `decompiler_backend`，并在
`adapter.py:41` 用 `setdefault` 避免覆盖既有值。**这是正确处理，且发现了审计层遗漏的
事实。** 记录在此以免后续误判为字段冗余。

## 5. 无 NIT

未发现需要执行层返工的问题。

## 6. 工作区状态说明（非本阶段责任）

回报称"唯一修改仓为 005AI-Reverse-Agent，工作树干净"。该表述对 **013 自身的提交**
成立，但审计时工作区中另有 `012-STRUCT-DEBT` 的并行进度：

- `000shared-llm-core` `23cc11f`（012 ISSUE 3 版本策略）
- `001AI-SOC-Agent` `f9731f7`（012 ISSUE 5 Elastic 接入）
- `004AI-Code-Audit/004AI-CodeGuard-upgrade` 17 个未提交改动（012 包树合并中间态）

两个阶段并行是既定安排，不构成越界。记录于此，以免后续审计把 012 的中间态误算进
013，或据当前工作区给出"全套件回归"结论 —— **004 处于半完成合并状态，现在不适合
出具套件级数字。**

## 7. 结论

**PASS。** `ADR-004` §2 的 005 轨已按决策落地：接缝独立、capstone 路径保留为默认、
Ghidra 以外部进程 + 可注入 runner 接入且不依赖本机安装、结论可溯源到后端、基线按
后端隔离、Ghidra 产物同样受不可信边界约束。

后续：

1. 真实 Ghidra headless 验证仍待有 JVM/Ghidra 的环境执行，手工步骤已在
   `005AI-Reverse-Agent/docs/ghidra-backend.md`。**本阶段按契约不要求**
2. `ADR-004` 的 006 轨（CycloneDX SBOM、EMBA 报告导入）尚未派发
3. 本阶段不涉及推送；五个提交均在本地
