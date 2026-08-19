# 审计 · 012-REWORK

> **结论**：**PASS**（最终重审）
> **审计日期**：2026-08-19
> **最终提交**：004 `224c7ba71f065d3d5fcf50d47c2743055959ab56`
> **提交信息**：`refactor(code): consolidate package trees into ai_code_audit`
> **派活**：[`012-REWORK.md`](../docs/dispatches/012-REWORK.md)
> **前序状态**：初审 `9126e25` 因 README Gateway 命令与 `rules` 契约不一致判 FAIL；本次 amend 已修复

## 1. 最终结论

CODE-MERGE-001 已完整收口：

- `ai_codeguard` 包树已移除；
- `codeguard` 只保留 shared-integration 固定调用所需的 `__init__.py` 与 `cli.py`；
- 实质模块迁入 `ai_code_audit`，业务逻辑保持等价；
- 原高风险未跟踪文件 `ai_code_audit/hybrid_cli.py` 已进入提交；
- README 的 IntegrationGateway 示例正确指向 `python -m codeguard.cli`；
- 规范后端与 LLM 章节继续使用 `python -m ai_code_audit`；
- 兼容入口 help 首行正确自报 `python -m codeguard.cli`；
- 全量、定向回归、显式 rules 路径、双 CLI 与 Worker D 全部通过；
- 独立高强度代码审查未发现剩余 finding。

因此，原 `012-STRUCT-DEBT` 的唯一返工项已完成，012 对 015 的阻塞解除。

## 2. 十项 checklist

| # | 项 | 结果 | 证据 |
|---|---|---|---|
| 1 | 接口契约 | PASS | `codeguard.cli` 兼容入口保留；未改 core、Integration 或冻结 schema |
| 2 | 技术方案 | PASS | README 明确区分 Gateway 兼容 CLI 与规范 CLI；前次文档契约 blocker 已消除 |
| 3 | 测试 | PASS | 独立全量 `184 passed in 13.45s`，较迁移前 183 基线净增规定的布局测试 |
| 4 | CLI smoke | PASS | 普通兼容入口、显式 rules、规范入口和 help 均通过 |
| 5 | 跨项目隔离 | PASS | 最终提交只在 004 Git 仓；未动 003 或其它产品仓 |
| 6 | 依赖管理 | PASS | 未新增依赖；`pyproject.toml` 移除已删除包声明并继续包含 `codeguard` |
| 7 | 代码质量 | PASS | `git diff HEAD^ --check` 通过；`ruff check src --select E9,F63,F7,F82` 全绿 |
| 8 | Prompt 模板 | N/A | 本返工不涉及 prompt |
| 9 | 审计日志 | N/A | 本返工不改变 LLM/AuditLog 边界 |
| 10 | 提交与证据 | PASS | 单一 amend commit、准确 36 changed paths、tracked 工作区干净、目标提交未 push |

## 3. 迁移等价性

父提交旧 blob 与最终提交新 blob 的直接比较结果：

- `ai_codeguard/cli.py` → `ai_code_audit/hybrid_cli.py`：仅包内 import 与公开 CLI `prog` 更新；
- `codeguard/dataflow.py` → `ai_code_audit/dataflow.py`：仅 2 条 import 更新；
- `codeguard/explain.py` → `ai_code_audit/explain.py`：仅 1 条 import 更新；
- `codeguard/taint.py` → `ai_code_audit/taint.py`：仅 1 条 import 更新；
- `codeguard/rules/*` 与 `codeguard/v05.py`：Git 识别为 100% rename；
- 既有测试只更新 import；唯一新增功能测试为派活指定的布局测试。

搜索未发现遗留 `ai_codeguard` import，也未发现文档继续公开内部命令
`python -m ai_code_audit.hybrid_cli`。

## 4. 最终独立验收

固定使用 Python 3.14 绝对路径、包含 004/core/integration/`.python-deps` 的绝对
`PYTHONPATH`、ASCII basetemp 与 `-o addopts=`。

| 验收项 | 结果 |
|---|---|
| 004 全量 | `184 passed in 13.45s` |
| TS 源保护 + 布局 + 011 门禁 + Integration CLI 契约 | `14 passed in 2.73s` |
| Worker D 四件套 | `PASS · all green`；`OVERALL PASS 1/1` |
| `codeguard.cli --help` | `usage: python -m codeguard.cli [-h] [--input INPUT] [--json]` |
| `codeguard.cli` 普通 smoke | `VALID_ENVELOPE findings=1 files_scanned=10 warnings=0` |
| 显式 dataflow rules smoke | `exit=0`；`rules=['004-cross-function-dataflow']`；`findings=1`；Finding rule ID 精确相同 |
| `python -m ai_code_audit` smoke | `VALID_ENVELOPE findings=0 files_scanned=19 warnings=0` |
| 布局 | `src/ai_codeguard` 不存在；`src/codeguard` 源文件仅 `__init__.py`、`cli.py` |
| Git | HEAD=`224c7ba`；36 changed paths；`diff --check` 通过；tracked status 为空；目标 commit 未推送 |
| 独立代码审查 | 高强度复核结果：0 findings |

显式 rules smoke 使用临时静态分析语料，语料中的危险调用只供解析器扫描、从未执行。
PowerShell 5.1 通过 stdin 会附加 UTF-8 BOM，因此最终验收通过子进程参数传递原始 JSON；产品 CLI
以退出码 0 返回合法 envelope。

## 5. NIT

无需要进入 backlog 的新 NIT。初审记录的文件数与 Ruff 扫描范围表述问题已由本次独立命令证据
取代，不要求为证据文字制造额外产品 commit。

## 6. 解锁与下一步

**PASS。** `012-REWORK` 完成，004 的包树中间态与 untracked 风险正式关闭。

后续顺序固定为：

1. 先执行 [`018-CORE-RULEENGINE`](../docs/dispatches/018-CORE-RULEENGINE.md)，把 core 已认可的
   工作区内容按派活分成三个 commit；
2. 018 收口后再启动 [`015-OBSERVABILITY`](../docs/dispatches/015-OBSERVABILITY.md)；
3. 018 与 015 都修改 core，不得并行或混入同一批提交。
