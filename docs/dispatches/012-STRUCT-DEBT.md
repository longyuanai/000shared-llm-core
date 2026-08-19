# 012-STRUCT-DEBT：结构性技术债与 003 评估收口

> **状态**：🟢 已解锁（ISSUE 4 需决策层单独授权，见 §5）
> **解锁证据**：`011-INJECT-HARDEN` 审计 **PASS**，见
> [`AUDIT/011-INJECT-HARDEN.md`](../../AUDIT/011-INJECT-HARDEN.md)
> **预计工作量**：5 个 ISSUE，约 8 小时

## 1. 目标

`010` / `011` 关闭了"AI 输出可信度"这条线。本阶段处理**积压的结构性债务** ——
这些问题不影响功能，但每一个都在持续制造误判和返工：

- 004 有**三套并行包树**，是一次没做完的合并
- 套件版本号**没有任何约定**：core `0.1.0` 却实现着 v0.6 契约，integration 是
  `0.8.0`，004 是 `0.6.0`
- 003 是唯一没有评估门禁的接 LLM 产品（`011` 的豁免表 `followup: 012`）

**不在本阶段**：005 / 006 的"自建 vs 封装成熟开源"决策需要先有 ADR，相关工作一律
不做。详见 §6。

## 2. 范围与提交顺序

允许修改：

- `004AI-Code-Audit/004AI-CodeGuard-upgrade/` 全仓
- 各仓 `pyproject.toml` 的 `version` 字段
- `000shared-llm-core/docs/` 新增版本策略文档
- `003AI Agent安全靶场` **仅新增** `evals/` 与 `tests/test_eval_gate.py`（ISSUE 4，
  需授权）
- `000shared-llm-core/suite-lock.yml`、`tests/test_eval_coverage.py`（ISSUE 4 连带）
- `001AI-SOC-Agent/` 的 ingest 路径（ISSUE 5）

不得修改：

- `003AI Agent安全靶场` 的 7 个受保护已修改文件与 `tests/test_tenant_isolation.py`
- 已冻结的 v0.1 / v0.5 §7–§10 对外签名
- `010` / `011` 建立的评估与边界机制（只增不改）

提交顺序：

1. ~~`refactor(code): remove dead packages`~~ —— **已撤销，见 §3 ISSUE 1**
2. `refactor(code): consolidate package trees into ai_code_audit`
3. `chore(version): adopt suite version policy`
4. `test(eval): add lab eval gate and retire its exemption`（需授权）
5. `feat(soc): add elasticsearch ingest source`

> 撤销 commit 1 后，004 仓本阶段**只需要 commit 2 一个提交**。

## 3. ISSUE

### ~~ISSUE CODE-DEAD-001 · 清除 004 的死包~~ · ❌ 已撤销（2026-08-17）

> **本 ISSUE 作废，不要执行。** 撤销依据见
> [`AUDIT/012-STRUCT-DEBT.md`](../../AUDIT/012-STRUCT-DEBT.md) §2.1。

**撤销原因**：原表的"src 内引用 0 / tests 内引用 0"**只统计了 Python import**，
据此把三项判为死包是错的。004 是 `pyproject.toml` 自述的
"Hybrid TypeScript/Python upgrade layer"，这三项是它的 **TypeScript 半边**：

| 项 | 真实地位 |
|---|---|
| `src/scanner/` | 5 个 `.ts`（`orchestrator` / `baseline` / `diff` / `index` / `suppression`），**`tests/test_project_setup.py::test_upstream_stage1_sources_are_present_in_upgrade` 显式断言 `orchestrator.ts` 存在** |
| `src/reporter/` | 5 个 `.ts`（`sarif` / `json` / `github` / `text` / `index`），SARIF 与 JSON 报告器的实现 |
| `src/version.ts` | `--version`、JSON reporter、SARIF `tool.driver.version` 的单一版本源，有与 `package.json` 的漂移守卫测试；已进 `dist/index.js` 打包产物 |

构建链是真的：`package.json` 的 `bin.ai-codeguard → ./dist/index.js`，
`build: tsup`、`test: vitest`、`lint: eslint src/`。

**删除后果**：004 Python 全量从 183 掉到 182（`test_project_setup.py` 直接红），
并破坏 npm 包 `ai-codeguard` 的构建源。

**正确处置**：三项**原地保留，不删不移**。若未来要收拾这条 TS 线，须先写 ADR
说明 004 的双语言边界，再单独派活 —— 不在本阶段。

---

### ISSUE CODE-MERGE-001 · 三套包树合并进 `ai_code_audit`（约 3h）

**背景**：仓名 `004AI-CodeGuard-upgrade` 说明这是 `AI-CodeGuard` 与 `ai_code_audit`
的融合，融合没做完，留下三套并行包树。

**已核实的规模与地位**：

| 包 | 规模 | src 引用 | tests 引用 | 地位 |
|---|---|---|---|---|
| `ai_code_audit` | 24 files / 3299 loc | 17 | 22 | **正统** —— 拥有 CLI 入口 `ai-code-audit = "ai_code_audit.cli:main"` |
| `codeguard` | 8 files / 1607 loc | 5 | 5 | 含 `taint.py` / `dataflow.py`，有实质内容 |
| `ai_codeguard` | 3 files / 470 loc | 3 | 7 | 最小，优先合并 |

**任务**：

1. 以 `ai_code_audit` 为目标包，把 `ai_codeguard` 与 `codeguard` 的模块迁入合适的
   子包（例如 `ai_code_audit/taint/`、`ai_code_audit/dataflow/`）
2. **分两步走，不要一次性大搬家**：
   - 先迁 `ai_codeguard`（3 个文件），跑全量，确认绿
   - 再迁 `codeguard`（8 个文件），跑全量，确认绿
   - 两步可以在同一个 commit 里，但**中间必须跑一次全量**
3. 迁移期间**不要重写业务逻辑**。只移动、改 import、必要时改模块内相对引用。
   逻辑重构留给以后 —— 混进来会让"合并是否等价"无法验证
4. 旧包路径**不留兼容 shim** —— **但 `src/codeguard/cli.py` 除外（2026-08-17 修正）**。

   > **修正依据**：原文"这是内部包，没有外部消费者"**不成立**。
   > `000shared-integration/src/shared_integration/adapters/code.py:12` 硬编码
   > `module = "codeguard.cli"`，是 Gateway 调 004 的唯一入口；该仓不在本派活 §2 的
   > 可改范围内，且是 `suite-lock.yml` 锁定的已推送 M3 头 `2d42a87`。
   >
   > 因此：`src/codeguard/` 的**实质模块**（`taint` / `dataflow` / `explain` / `v05` /
   > `rules`）迁入 `ai_code_audit`，**`src/codeguard/cli.py` 与最小 `__init__.py` 原地保留**，
   > 作为显式的集成契约入口（它已在工作区内被正确重指向 `ai_code_audit.hybrid_cli`）。
   > 把 adapter 的 `module` 改成 `ai_code_audit.cli` 需要动锁定仓 + 重新锁 suite +
   > 跑一次 suite CI，属**另一个派活**，不在 012 范围。
5. `analyzer` / `parser` / `cache` / `config` / `types` / `rules` 等其它顶层包
   **本次不动**，避免范围膨胀

**测试**：

- 不新增功能测试
- 已有测试的 import 路径随之更新
- 新增 `tests/test_package_layout.py::test_no_legacy_package_trees`：断言
  `src/ai_codeguard` 不再存在，且 `src/codeguard` 下**只剩** `cli.py` 与 `__init__.py`
  （即实质模块已迁走、集成契约入口仍在）

**验收**：

1. 004 全量 = 183 passed（数量不得下降；import 路径改动不算新增测试）
2. CLI smoke 输出合法 envelope
3. `011` 建立的 `tests/test_eval_gate.py` 与 `tests/test_prompt_injection.py`
   **必须仍然通过** —— 它们是合并没破坏行为的证据
4. 回报里附一份"迁移前后模块对照表"

---

### ISSUE CORE-VERSION-001 · 套件版本号约定（约 1.5h）

**问题**：版本号目前没有任何含义。

| 仓 | 当前 version |
|---|---|
| `000shared-llm-core` | `0.1.0` ← 却实现着 v0.6 §15 契约 |
| `000shared-integration` | `0.8.0` |
| `004AI-CodeGuard-upgrade` | `0.6.0` |
| 其余五个产品 | `0.1.0` |

**决策（本派活即决策依据，不要自行更改）**：

1. **core 的 version 必须等于它实现的契约版本。** core 是被 7 个仓消费的地基，
   它的版本号就是契约版本号。当前实现 v0.6 §15，因此 **core → `0.6.0`**
2. **产品仓独立版本，遵循 semver**，各自演进，不与 core 对齐
3. **部署事实源仍然是 `suite-lock.yml` 的精确 SHA**，版本号服务于人和未来的包
   分发，不承担锁定职责
4. 本次**只改 core 一个仓的版本号**。产品仓版本号维持现状，不做统一 —— 强行对齐
   会制造大量无意义的变更

**任务**：

1. `000shared-llm-core/pyproject.toml`：`version = "0.6.0"`
2. 新增 `000shared-llm-core/docs/versioning.md`，写明上述四条策略、以及"改 core
   的对外签名必须先升次版本号并写 ADR"这一规则
3. 检查是否有代码或测试硬编码了 core 的版本字符串，一并更新
4. 在 `docs/v0.5-contract.md` 补一行指向 `versioning.md`

**测试**（≥ 2 个）：
- `tests/test_versioning.py::test_core_version_matches_contract`
- `tests/test_versioning.py::test_version_is_valid_semver`

**验收**：

1. core 全量 ≥ 124 passed
2. **七个仓全部重新可安装**：因为产品都用 `path` 依赖 core，core 改版本号后
   poetry-core 生成的 metadata 会变。逐仓跑全量，**七个仓零失败**
3. 回报里贴七仓的测试数字

---

### ISSUE LAB-EVAL-001 · 003 评估门禁（约 2h）· ⚠️ 需单独授权

**⚠️ 未获得决策层明确授权前，不要执行本 ISSUE。** 见 §5。

**背景**：003 是唯一接 LLM 却没有评估门禁的产品，`011` 把它放进了豁免表。
调用点已定位：`src/ai_agent_lab/detector.py:320`、`src/ai_agent_lab/judge.py:95`。

**任务**：

1. 003 新增 `evals/fixtures/`（≥ 6 个）与 `tests/test_eval_gate.py`
2. **003 的输出形状与其它产品不同** —— 是攻击检测与裁决结果，不是
   `severity`/`confidence`。按其实际字段设计 `expected`，不要硬套
3. `000shared-llm-core/tests/test_eval_coverage.py`：从豁免表中移除 `lab` 条目
4. `inspect.yml` 的评估门禁循环加入 003
5. **连带处理锁**：003 的 HEAD 会离开 `3862acf`，必须同步更新
   `suite-lock.yml` 的 lab commit

**绝对约束**：

- **只 `git add` 你新建的文件**。7 个受保护的已修改文件与
  `tests/test_tenant_isolation.py` 一律不得进入暂存区
- 提交前后各跑一次 `git status --porcelain`，确认那 8 项仍在、状态未变，
  把两次输出都贴进回报

**验收**：

1. 003 的 eval 在 replay 模式全绿
2. 改坏一个 fixture → 门禁变红 → 恢复，贴输出
3. core 的覆盖守卫在移除豁免后仍然通过
4. `git status --porcelain` 前后对比，证明 8 个受保护项未被触碰
5. `suite-lock.yml` 的 lab commit 与 003 新 HEAD 一致

---

### ISSUE SOC-SIEM-001 · 001 接入 Elasticsearch（约 2.5h）· 可裁剪

**这是本阶段唯一的功能性 ISSUE，若前四个超时，优先砍掉它。**

**背景**：001 目前只能吃文件和 Syslog UDP（`parse_file` / `SyslogUDPReceiver`），
没有任何 SIEM 连接器，这限制了它在真实环境的可用性。

**任务**：

1. 新增 `src/ai_soc_agent/sources/elastic.py`：按查询与时间窗从 Elasticsearch
   拉取日志，产出 `NormalizedEvent`
2. 复用现有 `normalizer` / `parsers`，**不要新写一套解析**
3. 连接参数走环境变量，**不得硬编码任何地址或凭据**；凭据缺失时 fail-closed
   并给出明确错误
4. CLI 增加对应子命令，形态与现有 `syslog` 子命令保持一致
5. **拉回的日志内容必须经过 `wrap_untrusted(..., kind="log_event")`** ——
   这是 `011` 建立的边界，新入口不得绕过

**测试**（≥ 5 个）：
- `tests/test_elastic_source.py::test_query_maps_hits_to_normalized_events`
- `tests/test_elastic_source.py::test_missing_credentials_fails_closed`
- `tests/test_elastic_source.py::test_time_window_is_applied`
- `tests/test_elastic_source.py::test_pagination_terminates`
- `tests/test_prompt_injection.py::test_elastic_content_is_delimited`

**测试中不得连接真实 Elasticsearch**，用 stub / 录制响应。

**验收**：001 全量 ≥ 278 passed；CLI smoke 仍输出合法 envelope；新增子命令
`--help` 可用。

## 4. 全局约束

- 绝对 Python：`C:\Users\15072\AppData\Local\Programs\Python\Python314\python.exe`
- pytest 一律 `--basetemp=C:/pytest-tmp/012-<name> -o addopts=`
- **PYTHONPATH 必须绝对路径**，表见 [`010-AI-TRUST.md`](010-AI-TRUST.md) §4.1
- 动工前每仓 `git status --short --branch`
- 只提交到本地，不 push
- 5 个 ISSUE 各自独立 commit，不合并，不造空 commit
- 每个 ISSUE 完成后先跑该仓全量再进下一个

## 5. ISSUE 4 的授权要求

`LAB-EVAL-001` 会在 `003AI Agent安全靶场` 建立提交，使其 HEAD 离开
`suite-lock.yml` 锁定的 `3862acf`，并连带要求更新锁。该仓有决策层明确保护的
未提交修改。

**未收到决策层书面授权前，跳过 ISSUE 4，直接做 ISSUE 5，并在回报中注明"ISSUE 4
待授权"。** 不要为了完整性擅自执行。

## 6. 本阶段**不做**的事

| 事项 | 原因 |
|---|---|
| 005 用 Ghidra headless 替换自研伪 C 反编译 | 需先有 ADR-004（自建 vs 封装），未写 |
| 006 接入 EMBA / 输出 CycloneDX SBOM | 同上 —— 若决定封装 EMBA，它自带 SBOM，现在自研会白做 |
| OpenTelemetry 可观测性 | 独立能力，另开阶段 |
| 输出侧净化 | `011` 审计已核实 002/006 的 HTML 报告器均启用 Jinja2 `select_autoescape`，风险已被覆盖，无需处理 |

## 7. 回报格式

每 ISSUE 一份：

```
ISSUE: <ID>
commit: <hash>
files: <改动文件>
baseline: <动工前该仓 pytest 数字>
tests: <N> passed, <M> failed
verify: <验收命令 stdout>
NITs: <可选>
Open questions: <可选>
```

额外要求：

- `CODE-MERGE-001` 附迁移前后模块对照表
- `CORE-VERSION-001` 附七仓测试数字
- `LAB-EVAL-001` 附 `git status --porcelain` 的提交前后对比 + 门禁红灯输出

## 8. 卡住时怎么办

停下来问，写进 `Open questions`，先做不受阻塞的 ISSUE。特别地：

- ~~发现 `scanner` / `reporter` 其实仍被引用 → 不要删，报出来~~ —— 审计层已核实它们是 TS 源，ISSUE 1 整体撤销
- 合并过程中发现两个包有**行为冲突**（同名不同义的函数）→ 停，不要自己选一个
- core 改版本号后某个产品装不上 → 停，不要改产品的依赖声明绕过
