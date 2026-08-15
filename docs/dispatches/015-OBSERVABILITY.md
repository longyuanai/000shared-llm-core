# 015-OBSERVABILITY：套件级可观测性

> **状态**：🟢 已解锁
> **前置**：与 `012` / `014` 目标仓有重叠，**不要与它们并行执行**，等其收口后再开
> **预计工作量**：5 个 ISSUE，约 8 小时

## 1. 目标

套件目前**没有任何分布式追踪或指标**。当一次 Dashboard 请求经 Gateway 派发到某个
产品 CLI、再触发若干 LLM 调用时，无法回答"这次请求慢在哪、失败在哪、花了多少 token"。

本阶段补上一层最小可用的可观测性，**建立在已有的 `audit.py` 之上，而不是另起炉灶**。

## 2. 三条已核实的事实（2026-08-15）

### 2.1 OpenTelemetry 覆盖为零

```
core / integration / 001 / 006  →  opentelemetry: 0 处
```

从零开始，不存在需要兼容的既有埋点。

### 2.2 已有一条真实的 LLM 审计链路，是天然接缝

`000shared-llm-core/src/shared_llm_core/audit.py` 已记录**每一次 LLM 调用**，三种
后端（`jsonl` / `stdout` / `noop`），可追溯 prompt + response + model + cost。

**OTel span 应当包住 `audit.py` 已经在记录的同一个边界**，两者对齐而不是并列。
不要在别处另开一套 LLM 计时。

### 2.3 `structlog` 是已声明但未使用的依赖

core 的 `pyproject.toml` 声明了 `structlog = "^24.2.0"`，但 `src/` 下**零处使用**。

这是 `012` 的 `jinja2` 情形的镜像（那次是用了没声明，这次是声明了没用）。本阶段
要么用起来，要么删掉声明 —— 见 ISSUE 5。

## 3. 范围与提交顺序

允许修改：`000shared-llm-core`、`000shared-integration`、六个产品仓的埋点路径与
`pyproject.toml`

不得修改：

- 冻结的 v0.1 / v0.5 §7–§10 **对外签名**。埋点必须是**装饰/包裹式的加法**
- `010` / `011` / `013` 建立的评估、边界与后端机制
- `003AI Agent安全靶场` 受保护文件

提交顺序（1 阻塞 2/3/4）：

1. `feat(core): add optional otel tracing seam`
2. `feat(core): trace llm calls alongside the audit log`
3. `feat(integration): trace gateway request lifecycle`
4. `feat(products): trace scan entrypoints`
5. `chore(core): resolve the unused structlog dependency`

## 4. ISSUE

### ISSUE CORE-OTEL-001 · 可选追踪接缝（约 2h，阻塞 2/3/4）

**设计决定（不要自行更换）**：

- OpenTelemetry 是**可选依赖**，装了才启用。**未安装时必须完全无感降级**，
  不得抛异常、不得打印警告噪音
- 提供一个**空实现（no-op）** 作为默认，接口与真实实现一致 —— 调用方永远不需要
  写 `if tracing_enabled:`
- 开关走环境变量，默认**关闭**

**任务**：

1. 新增 `src/shared_llm_core/telemetry.py`：`get_tracer()` / `span()` 上下文管理器
2. OTel 未安装或未启用 → 返回 no-op 实现
3. `pyproject.toml` 把 OTel 放进**可选 extra**（如 `[tool.poetry.extras] otel`），
   **不进主依赖** —— 六个产品都装它会显著加重安装体积
4. 新增 `docs/observability.md`：启用方式、导出到什么、默认关闭的理由

**测试**（≥ 5 个）：
- `tests/test_telemetry.py::test_noop_tracer_when_disabled`
- `tests/test_telemetry.py::test_noop_tracer_when_otel_missing`（模拟 import 失败）
- `tests/test_telemetry.py::test_span_context_manager_never_raises`
- `tests/test_telemetry.py::test_enabled_by_environment_variable`
- `tests/test_telemetry.py::test_span_records_exception_without_reraising_differently`

**验收**：core 全量 ≥ 124 passed；**在未安装 OTel 的环境下全绿**（本机就是这种环境，
这是实际验收条件）。

---

### ISSUE CORE-OTEL-002 · LLM 调用追踪（约 1.5h）

**目标**：与 `audit.py` 对齐，不并列。

**任务**：

1. 在 `audit.py` 已经在记录的同一边界上加 span
2. span 属性至少含：model、tier（`TaskTier`）、token 用量、耗时、成功/失败
3. **绝不把 prompt 或 response 内容写进 span 属性** —— 那是审计日志的职责，
   且 span 常被导出到第三方后端。只记元数据
4. 采样与开关沿用 ISSUE 1 的机制

**测试**（≥ 4 个）：
- `tests/test_llm_tracing.py::test_span_created_per_llm_call`
- `tests/test_llm_tracing.py::test_span_carries_model_and_tier`
- `tests/test_llm_tracing.py::test_span_never_contains_prompt_or_response`
  —— **本 ISSUE 的关键测试**
- `tests/test_llm_tracing.py::test_audit_record_still_written_when_tracing_disabled`

**验收**：core 全量无下降；`010`/`011` 的评估门禁仍全绿。

---

### ISSUE INTEG-OTEL-001 · Gateway 请求链路（约 2h）

**任务**：

1. Gateway 的请求生命周期加 span：接收 → 派发到产品 CLI → 汇总
2. 传播 trace context 到子进程（W3C `traceparent` 环境变量），让产品侧 span 能挂在
   同一条 trace 上
3. span 属性含：产品 id、job id、状态、耗时。**不含租户令牌、API key 或任何凭据**
4. 现有 `request ID` 机制与 trace id 建立关联，不要互相取代

**测试**（≥ 4 个）：
- `tests/test_gateway_tracing.py::test_request_span_created`
- `tests/test_gateway_tracing.py::test_traceparent_propagated_to_subprocess`
- `tests/test_gateway_tracing.py::test_span_contains_no_credentials`
- `tests/test_gateway_tracing.py::test_disabled_tracing_does_not_change_responses`

**验收**：integration 全量 ≥ 143 passed（4 skipped）；关闭追踪时响应逐字节不变。

---

### ISSUE PROD-OTEL-001 · 产品扫描入口埋点（约 2h）

**任务**：

1. 六个产品的 scan 入口各加一个 span，消费上游传来的 `traceparent`
2. **不要逐函数埋点** —— 只在入口和 LLM 调用两处，避免噪音与维护负担
3. span 属性含产品 id 与扫描目标的**类型**，**不含目标路径、主机名或样本内容**
   （那些是攻击者可控的，且可能含客户资产信息）

**测试**（每产品 ≥ 1，共 ≥ 6）：
- 各产品 `tests/test_tracing.py::test_scan_entrypoint_creates_span`

**验收**：六个产品全量均无下降（基线：001=278、002=183、004=183、005=304、
006=398；003 见下）。

**003 特别说明**：`003AI Agent安全靶场` 有受保护的未提交修改。**若埋点需要修改
那 7 个文件中的任何一个，跳过 003 并在回报中说明**，不要为了覆盖率去碰它。

---

### ISSUE CORE-DEP-001 · 处理未使用的 structlog（约 0.5h）

**目标**：core 声明了 `structlog` 却零处使用（§2.3）。

**任务**：

1. 确认全仓确实无人使用（含动态导入）
2. **二选一并说明理由**：
   - 若 ISSUE 1–4 的实现用得上结构化日志 → 用起来，并说明用在哪
   - 否则 → 从 `pyproject.toml` 删除该声明
3. 顺带核对 core 其余依赖有无同类情况，发现即在回报中列出（**本阶段只报不改**）

**测试**（≥ 1 个）：
- `tests/test_dependencies.py::test_declared_dependencies_are_used`
  —— 断言主依赖列表中每一项在 `src/` 有实际导入。**若某项确有正当理由保留但不导入
  （如仅运行时需要），在测试内以显式白名单 + 理由注释豁免**

**验收**：core 全量无下降；`poetry check` 或等价校验通过。

## 5. 全局约束

- 绝对 Python：`C:\Users\15072\AppData\Local\Programs\Python\Python314\python.exe`
- pytest 一律 `--basetemp=C:/pytest-tmp/015-<name> -o addopts=`
- **PYTHONPATH 必须绝对路径**，表见 [`010-AI-TRUST.md`](010-AI-TRUST.md) §4.1
- **本机未安装 OpenTelemetry，且本阶段不要求安装。** 全部验收在"未安装"路径上完成；
  真实导出验证写成手工步骤文档，同 `013` 对 Ghidra 的处理
- 只提交到本地，不 push；5 个独立 commit

## 6. 回报格式

同 `013`。额外要求：

- `CORE-OTEL-002` 贴 `test_span_never_contains_prompt_or_response` 的通过输出
- `INTEG-OTEL-001` 贴"关闭追踪时响应不变"的验证输出
- `CORE-DEP-001` 说明 structlog 是用起来了还是删掉了，以及理由

## 7. 卡住时怎么办

停下来问。特别地：

- 埋点需要改 v0.5 §7–§10 的对外签名 → **停**，埋点必须是加法
- 003 的埋点需要碰受保护文件 → **跳过 003**，写进回报，不要碰
- 认为应当把 OTel 放进主依赖 → **不要**，六个产品都装会显著加重安装体积；
  有异议先说明
