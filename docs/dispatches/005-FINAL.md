# Codex 派活指令 · 005-FINAL · v0.5 形式冻结收尾

> **派活方**: Claude
> **接收方**: Codex
> **前提**: §7-§10 实现完成、§15 CLI Envelope 已接入 001~006、6 worker 四件套可运行
> **优先级**: 🔴 v0.5 收口

---

## 1. 目标

把 `000shared-llm-core` 与 001~006 六个产品从“手工验证通过”推进到可审计的
v0.5 形式冻结：

- §15 契约具备六产品真实 subprocess 测试；
- `inspect_worker_return.py` 四件套结果固化为证据；
- RFC-001 明确冻结范围与兼容规则；
- 发布最终测试数字、状态索引与剩余风险。

工作仓库：

```text
E:\001项目\000开发\003AI+网络安全\000shared-llm-core
```

001~006 产品仓只读参与验证，不提交产品改动。

---

## 2. 任务（4 ISSUE / 4 commit）

### ISSUE 1 · 005-FINAL-001 · 六产品 §15 CLI envelope smoke

新增：

```text
tests/integration/test_cli_envelope_smoke.py
```

要求：

- 001~006 各一个真实 subprocess case；
- 使用 `sys.executable -m <module> scan --input <json> --json`；
- `cwd` 指向产品根目录；
- `PYTHONPATH` 只注入产品 `src/`、core `src/` 与 004 `.python-deps/`；
- 校验退出码、UTF-8 JSON、`findings` list 与 Finding 基础字段；
- sibling 产品仓缺失时允许 skip，存在时必须真实运行。

Commit：

```text
test(final): add six-product CLI envelope smoke
```

### ISSUE 2 · 005-FINAL-002 · 固化 6-worker 四件套证据

运行：

```powershell
& 'C:\Users\15072\AppData\Local\Programs\Python\Python314\python.exe' `
  'E:\001项目\000开发\003AI+网络安全\scripts\inspect_worker_return.py'
```

新增：

```text
docs/validation/005-final-worker-return.md
```

记录每个 worker 的：

1. recent commits；
2. `HEAD~2` diffstat；
3. isolated-basetemp pytest；
4. real CLI JSON envelope。

Commit：

```text
docs(final): record six-worker four-part validation
```

### ISSUE 3 · 005-FINAL-003 · RFC-001 v0.5 freeze

新增：

```text
docs/rfcs/RFC-001-v0.5-freeze.md
```

RFC 至少包含：

- 冻结范围（§1-§10 + §15 addendum）；
- v0.5.x 允许和禁止的变更；
- CLI envelope 兼容承诺；
- 验证证据；
- 已知限制与 rollback；
- v1.0 exit criteria。

Commit：

```text
docs(final): accept RFC-001 v0.5 freeze
```

### ISSUE 4 · 005-FINAL-004 · 最终报告与状态索引

新增或更新：

```text
docs/releases/v0.5-final.md
docs/dispatches/INDEX.md
README.md
docs/dispatches/005-FINAL.md
```

要求：

- 发布 000 + 001~006 的最终测试数字；
- 链接 contract、RFC、validation evidence；
- 明确 005-UI 与 007-CI 是独立后续派活；
- 不把“手工四件套全绿”误写成“自动 CI 已完成”。

Commit：

```text
docs(final): publish v0.5 final validation report
```

---

## 3. 测试

Windows 必须使用绝对解释器：

```text
C:\Users\15072\AppData\Local\Programs\Python\Python314\python.exe
```

所有 pytest 必须使用非中文 basetemp 并清空项目 `addopts`：

```powershell
& 'C:\Users\15072\AppData\Local\Programs\Python\Python314\python.exe' `
  -m pytest tests/ `
  --basetemp=C:/pytest-tmp/005-final-core `
  -q --tb=short -o addopts=
```

六产品四件套：

```powershell
& 'C:\Users\15072\AppData\Local\Programs\Python\Python314\python.exe' `
  'E:\001项目\000开发\003AI+网络安全\scripts\inspect_worker_return.py'
```

最低要求：

- core 全量 0 failed；
- 六产品 CLI smoke 6 passed；
- inspect `OVERALL PASS 6/6 workers green`；
- `git diff --check` 无错误。

---

## 4. 验收

- [x] 4 ISSUE 对应 4 commit；
- [x] `tests/integration/test_cli_envelope_smoke.py` 六产品真子进程全绿；
- [x] `docs/validation/005-final-worker-return.md` 包含四件套明细；
- [x] RFC-001 状态为 Accepted；
- [x] final report 给出 7 仓测试合计与剩余风险；
- [x] `inspect_worker_return.py` 显示 6/6 PASS；
- [x] 产品仓没有新增 005-FINAL 修改；
- [x] 无 API Key、Token、密码、私钥或客户数据。

---

## 5. 约束

- 不修改 v0.1 §1-§6 runtime API；
- 不修改 001~006 产品代码；
- 不把产品仓现有 dirty worktree 纳入提交；
- 不新增生产依赖；
- 不修改 GitHub Actions（由 007-CI 负责）；
- 不实施 Web Dashboard（由 005-UI 负责）；
- 所有网络安全测试仅使用本地仓、样例与授权数据；
- 未实际验证的结果不得写成 PASS。

---

## 6. 回报（四件套）

```text
1. git log --oneline -4
2. git diff HEAD~4 --stat
3. core pytest 最后输出 + 7 仓测试合计
4. inspect_worker_return.py 输出（6/6 PASS）+ 已知问题
```
