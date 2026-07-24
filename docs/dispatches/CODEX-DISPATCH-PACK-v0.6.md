# Codex 派活 Pack · v0.6 S4/S5 6 worker 并行

> **派发方式**: 复制每个 worker 的"📋 发送给 Codex"块即可粘贴。
> **6 个 worker 同时执行,彼此无依赖,每个独立 commit**。
> **回报入口**: 用户在这里汇总,我(Claude)做 commit inspect + 5 分钟验收。

---

## 协调约束(对所有 worker 适用)

1. **路径一律用绝对路径**,Python 用 `C:\Users\15072\AppData\Local\Programs\Python\Python314\python.exe`。
2. **pytest 三件套**:`--basetemp=C:/pytest-tmp/<PROJECT>-s4 -o addopts= -q`(PROJECT 替换为 001/002/003/004/005/006)。
3. **不要**改动 `000shared-llm-core` 或 `000shared-integration` 任何文件。
4. **不要**破坏 v0.5 S3 已有测试(001: 58, 002: 68, 003: 140, 004: 55, 005: 150, 006: 93+1skip)。
5. **不要**装新依赖(003-S4 例外,授权装 `openai` 包)。
6. 详细踩坑经验:`E:\001项目\000开发\003AI+网络安全\AUDIT\EXPERIENCE.md`(经验 1+2+4, 004 加经验 3)。

---

## 📋 Worker A · 001-S4 · SOC CLI 契约 + 端到端

```
[001-S4] AI-SOC-Agent · v0.6 CLI 契约适配 + e2e 联调

## 背景
- 项目: 001 AI-SOC-Agent
- 工作目录: E:\001项目\000开发\003AI+网络安全\001AI-SOC-Agent
- 当前基线: v0.5 S3 完工,58 tests passing
- 缺口: 没适配 JSONSubprocessAdapter 的 CLI 子命令

## ⚠️ 开工前必读
1. E:\001项目\000开发\003AI+网络安全\000shared-integration\src\shared_integration\adapters\base.py
2. E:\001项目\000开发\003AI+网络安全\000shared-integration\src\shared_integration\adapters\soc.py
3. E:\001项目\000开发\003AI+网络安全\000shared-integration\src\shared_integration\gateway.py
4. E:\001项目\000开发\003AI+网络安全\000shared-llm-core\docs\v0.5-contract.md §7
5. E:\001项目\000开发\003AI+网络安全\001AI-SOC-Agent\docs\tech-spec.md
6. E:\001项目\000开发\003AI+网络安全\001AI-SOC-Agent\docs\TODO.md
7. E:\001项目\000开发\003AI+网络安全\AUDIT\EXPERIENCE.md (经验 1+2+4)

## 必须做(2 ISSUE / 2 commit)

### ISSUE 1 · SOC-CLI-001
- 查 src/ai_soc_agent/__main__.py 或 cli.py
- 新增 `python -m ai_soc_agent.cli scan --input <payload.json> --json`
- payload schema: {"source": "sshd|evtx|nginx|okta", "events": [...]}
- 输出 envelope {"findings": [{...}]},字段对齐 Finding.from_dict
- 测试(test_cli_envelope.py, ≥3 个):
  - test_scan_sshd_returns_envelope
  - test_scan_with_existing_detect_rule
  - test_cli_handles_bad_json_gracefully
- 用 JSONSubprocessAdapter end-to-end

### ISSUE 2 · SOC-LIVE-001
- tests/integration/test_soc_adapter_e2e.py:启 gateway(端口 18080)
- POST /v0.5/soc/scan body {"source":"sshd","events":[...]}
- tests/fixtures/sshd_bruteforce.log(5 失败 + 1 成功)
- src/ai_soc_agent/cli.py 加 --log-file <path>
- README 加"被 IntegrationGateway 调用方式"

## 验收
- `echo '{"source":"sshd","events":[]}' | python -m ai_soc_agent.cli scan --json` → 合法 JSON
- pytest 全过(原 58 + 新增 ≥ 6)
- curl http://localhost:8080/v0.5/health → soc ok
- 2 commit

## 不要做
- 不修改 000shared-llm-core / 000shared-integration
- 不装新依赖
- 不破坏 v0.5 58 测试

## 回报
每 ISSUE:
1. Files changed
2. Tests: X/X passed
3. CLI smoke 输出
4. curl /v0.5/health 输出
5. Deviations
最终: 2 commit hash + 总测试数
```

---

## 📋 Worker B · 002-S4 · Vuln CLI 契约 + 端到端

```
[002-S4] AI-Vulnerability-Agent · v0.6 CLI 契约适配 + e2e 联调

## 背景
- 项目: 002 AI-Vulnerability-Agent
- 工作目录: E:\001项目\000开发\003AI+网络安全\002AI-Vulnerability-Agent
- 当前基线: v0.5 S3 完工,68 tests passing
- 缺口: 没适配 JSONSubprocessAdapter 的 CLI 子命令

## ⚠️ 开工前必读
1. E:\001项目\000开发\003AI+网络安全\000shared-integration\src\shared_integration\adapters\base.py
2. E:\001项目\000开发\003AI+网络安全\000shared-integration\src\shared_integration\adapters\vuln.py
3. E:\001项目\000开发\003AI+网络安全\000shared-integration\src\shared_integration\gateway.py
4. E:\001项目\000开发\003AI+网络安全\000shared-llm-core\docs\v0.5-contract.md §7
5. E:\001项目\000开发\003AI+网络安全\002AI-Vulnerability-Agent\docs\tech-spec.md
6. E:\001项目\000开发\003AI+网络安全\002AI-Vulnerability-Agent\docs\TODO.md
7. E:\001项目\000开发\003AI+网络安全\AUDIT\EXPERIENCE.md (经验 1+2+4)

## 必须做(2 ISSUE / 2 commit)

### ISSUE 1 · VULN-CLI-001
- 查 src/ai_vuln_agent/__main__.py 或 cli.py
- 新增 `python -m ai_vuln_agent.cli scan --input <payload> --json`
- payload: {"scanner": "qualys|openvas|nessus", "csv_content": "..."}
- 也支持 --csv-file <path>
- 输出 envelope {"findings": [{...}]},Finding 必含字段:id/severity/confidence/title/cve/host/narrative
- 测试(test_cli_envelope.py, ≥3 个):
  - test_scan_qualys_csv
  - test_scan_openvas_csv
  - test_prisk_in_narrative

### ISSUE 2 · VULN-LIVE-001
- src/ai_vuln_agent/nvd.py 加 NVD_API_KEY env 读取,无 key 时 fallback 到 mock
- tests/integration/test_vuln_adapter_e2e.py:gateway 18080 + POST /v0.5/vuln/scan
- README 加 "NVD API key 使用" 章节

## 验收
- `echo '{"scanner":"qualys","csv_content":"..."}' | python -m ai_vuln_agent.cli scan --json` → 合法 JSON
- pytest 全过(原 68 + 新增 ≥ 6)
- 2 commit

## 不要做
- 不修改 000shared-llm-core / 000shared-integration
- 不装新依赖
- 不破坏 v0.5 68 测试

## 回报(每 ISSUE)
1. Files changed
2. Tests: X/X passed
3. CLI smoke 输出
4. curl /v0.5/health 输出
5. Deviations
最终: 2 commit hash + 总测试数
```

---

## 📋 Worker C · 003-S4 · Lab CLI 契约 + 端到端

```
[003-S4] AI-Agent-Security-Lab · v0.6 CLI 契约适配 + e2e 联调

## 背景
- 项目: 003 AI-Agent-Security-Lab
- 工作目录: E:\001项目\000开发\003AI+网络安全\003AI Agent安全靶场
- 当前基线: v0.5 S3 完工,140 tests passing
- 缺口: 没适配 JSONSubprocessAdapter 的 CLI 子命令

## ⚠️ 开工前必读
1. E:\001项目\000开发\003AI+网络安全\000shared-integration\src\shared_integration\adapters\base.py
2. E:\001项目\000开发\003AI+网络安全\000shared-integration\src\shared_integration\adapters\lab.py
3. E:\001项目\000开发\003AI+网络安全\000shared-integration\src\shared_integration\gateway.py
4. E:\001项目\000开发\003AI+网络安全\000shared-llm-core\docs\v0.5-contract.md §7 + §9
5. E:\001项目\000开发\003AI+网络安全\003AI Agent安全靶场\docs\tech-spec.md
6. E:\001项目\000开发\003AI+网络安全\003AI Agent安全靶场\docs\TODO.md
7. E:\001项目\000开发\003AI+网络安全\AUDIT\EXPERIENCE.md (经验 1+2+4)

## 必须做(2 ISSUE / 2 commit)

### ISSUE 1 · LAB-CLI-001
- 查 src/ai_agent_lab/__main__.py / cli.py
- 新增 `python -m ai_agent_lab.cli scan --input <payload> --json`
- payload: {"agent": "sql_assistant|email_assistant|file_rag|web_browser|code_act",
           "attack": "indirect_inj|token_steal|shell_escape|...",
           "iterations": 1}
- 输出 envelope:每个 attack 触发后 detector 命中 → 1 个 finding
- 测试(test_cli_envelope.py, ≥3 个):
  - test_scan_runs_attack_returns_finding
  - test_scan_handles_blocked_attack_gracefully
  - test_scan_invalid_attack_returns_empty_findings

### ISSUE 2 · LAB-LIVE-001
- src/ai_agent_lab/orchestrator.py 加 env 读取(LLM_PROVIDER=openai|anthropic|fake)
- 无 key / fake 模式:用现有 fake LLM(已有)
- **本 ISSUE 授权 pip install openai**
- tests/integration/test_lab_adapter_e2e.py:gateway 18080 + POST /v0.5/lab/scan
- README 加 "LLM provider 切换" 章节

## 验收
- `echo '{"agent":"sql_assistant","attack":"indirect_injection"}' | python -m ai_agent_lab.cli scan --json` → 合法 JSON
- pytest 全过(原 140 + 新增 ≥ 6)
- 2 commit

## 不要做
- 不修改 000shared-llm-core / 000shared-integration
- 不破坏 v0.5 140 测试
- openai 之外的依赖不装

## 回报(每 ISSUE)
1. Files changed
2. Tests: X/X passed
3. CLI smoke 输出
4. curl /v0.5/health 输出
5. Deviations
最终: 2 commit hash + 总测试数
```

---

## 📋 Worker D · 004-S4 · Code CLI 契约 + 端到端

```
[004-S4] AI-CodeGuard-upgrade · v0.6 CLI 契约适配 + e2e 联调

## 背景
- 项目: 004 AI-CodeGuard-upgrade
- 工作目录: E:\001项目\000开发\003AI+网络安全\004AI代码审计\004AI-CodeGuard-upgrade
- 当前基线: v0.5 S3 完工,55 tests passing(AI-CodeGuard-main 上游 572 测试不破)
- 缺口: 没适配 JSONSubprocessAdapter 的 CLI 子命令

## ⚠️ 开工前必读
1. E:\001项目\000开发\003AI+网络安全\000shared-integration\src\shared_integration\adapters\base.py
2. E:\001项目\000开发\003AI+网络安全\000shared-integration\src\shared_integration\adapters\code.py
3. E:\001项目\000开发\003AI+网络安全\000shared-integration\src\shared_integration\gateway.py
4. E:\001项目\000开发\003AI+网络安全\000shared-llm-core\docs\v0.5-contract.md §7
5. E:\001项目\000开发\003AI+网络安全\004AI代码审计\004AI-CodeGuard-upgrade\docs\tech-spec.md
6. E:\001项目\000开发\003AI+网络安全\004AI代码审计\004AI-CodeGuard-upgrade\docs\TODO.md
7. E:\001项目\000开发\003AI+网络安全\AUDIT\EXPERIENCE.md (经验 1+2+3 — 经验 3 关键)

## ⚠️ 004 特殊提示
- **重要**: conftest.py 已被 Claude 加了 autouse fixture `_ensure_python_deps_in_pythonpath`
  和 pyproject.toml 的 `cache_dir = "C:/pytest-cache/004"`。先读这两个文件, 别重写环境变量逻辑。
- 跑测试前必先 verify:`python -c "import tree_sitter._binding; print('OK')"`
- PYTHONPATH 已自动注入 .python-deps,任何 import tree_sitter_python 都应工作。

## 必须做(2 ISSUE / 2 commit)

### ISSUE 1 · CODE-CLI-001
- 查 src/ai_codeguard/cli.py 现状(大概率已存在,只是补 --input --json + envelope)
- 新增/扩展 `python -m ai_codeguard.cli scan --input <payload> --json`
- payload: {"repo_path": "<absolute path>", "languages": ["python","go","java"], "rules": [...]}
          或 {"git_url": "..."}
- 输出 envelope(必含字段:id/severity/confidence/title/host/narrative)
- 测试(test_cli_envelope.py, ≥3 个):
  - test_scan_local_repo
  - test_scan_with_rules_filter
  - test_scan_unsupported_language_graceful
- 每个测试都先 verify import tree_sitter._binding OK

### ISSUE 2 · CODE-LIVE-001
- src/ai_codeguard/cli.py 加 --git-url <url> 参数(git clone --depth 1 到临时目录)
- 离线/网络失败 fallback 到 --repo-path
- tests/integration/test_code_adapter_e2e.py:gateway 18080 + POST /v0.5/code/scan
- README 加 "扫描本地仓库 / Git URL" 章节

## 验收
- `echo '{"repo_path":"samples/mini_repo"}' | python -m ai_codeguard.cli scan --json` → 合法 JSON
- pytest 全过(原 55 + 新增 ≥ 6, AI-CodeGuard-main 上游 572 不破)
- 2 commit

## 不要做
- 不碰 004AI代码审计\AI-CodeGuard-main(上游 572 测试绝不能破)
- 不修改 000shared-llm-core / 000shared-integration
- 不重写 conftest.py 里 _ensure_python_deps_in_pythonpath fixture
- 不破坏 v0.5 55 测试

## 回报(每 ISSUE)
1. Files changed
2. Tests: X/X passed
3. CLI smoke 输出
4. curl /v0.5/health 输出
5. Deviations
最终: 2 commit hash + 总测试数(含上游 572 不破的证据)
```

---

## 📋 Worker E · 005-S4 · Reverse CLI 契约 + 端到端

```
[005-S4] AI-Reverse-Agent · v0.6 CLI 契约适配 + e2e 联调

## 背景
- 项目: 005 AI-Reverse-Agent
- 工作目录: E:\001项目\000开发\003AI+网络安全\005AI逆向Agent
- 当前基线: v0.5 S3 完工,150 tests passing
- 缺口: 没适配 JSONSubprocessAdapter 的 CLI 子命令

## ⚠️ 开工前必读
1. E:\001项目\000开发\003AI+网络安全\000shared-integration\src\shared_integration\adapters\base.py
2. E:\001项目\000开发\003AI+网络安全\000shared-integration\src\shared_integration\adapters\reverse.py
3. E:\001项目\000开发\003AI+网络安全\000shared-integration\src\shared_integration\gateway.py
4. E:\001项目\000开发\003AI+网络安全\000shared-llm-core\docs\v0.5-contract.md §7
5. E:\001项目\000开发\003AI+网络安全\005AI逆向Agent\docs\tech-spec.md
6. E:\001项目\000开发\003AI+网络安全\005AI逆向Agent\docs\TODO.md
7. E:\001项目\000开发\003AI+网络安全\AUDIT\EXPERIENCE.md (经验 1+2+4)

## 必须做(2 ISSUE / 2 commit)

### ISSUE 1 · REV-CLI-001
- 查 src/ai_reverse_agent/__main__.py / cli.py
- 新增 `python -m ai_reverse_agent.cli scan --input <payload> --json`
- payload: {"binary_path": "<absolute path>", "arch": "x86|x64|arm|aarch64|mips|riscv"}
- 输出 envelope {"findings": [{...}]},host 字段填 binary path
- 测试(test_cli_envelope.py, ≥3 个):
  - test_scan_x64_binary
  - test_scan_arm_binary
  - test_scan_handles_unsupported_arch_gracefully

### ISSUE 2 · REV-LIVE-001
- 新增 samples/mini_binaries/(≥3 真实小二进制,< 1 MB):x64 PE / ARM ELF / MIPS ELF
- tests/integration/test_reverse_adapter_e2e.py:gateway 18080 + POST /v0.5/reverse/scan
- README 加 "扫描二进制" 章节

## 验收
- `echo '{"binary_path":"samples/mini_pe.exe","arch":"x64"}' | python -m ai_reverse_agent.cli scan --json` → 合法 JSON
- pytest 全过(原 150 + 新增 ≥ 6)
- 2 commit

## 不要做
- 不修改 000shared-llm-core / 000shared-integration
- 不装新依赖(capstone 已装)
- samples/ 二进制总和 ≤ 5 MB
- 不破坏 v0.5 150 测试

## 回报(每 ISSUE)
1. Files changed
2. Tests: X/X passed
3. CLI smoke 输出
4. curl /v0.5/health 输出
5. Deviations
最终: 2 commit hash + 总测试数
```

---

## 📋 Worker F · 006-S5 · Firmware CLI 契约 + 端到端

```
[006-S5] AI-Firmware-Security-Agent · v0.6 CLI 契约适配 + e2e 联调

## 背景
- 项目: 006 AI-Firmware-Security-Agent
- 工作目录: E:\001项目\000开发\003AI+网络安全\006AI-Firmware-Security-Agent
- 当前基线: v0.5 S4 完工,93 tests passing + 1 skip
- 缺口: 没适配 JSONSubprocessAdapter 的 CLI 子命令

## ⚠️ 开工前必读
1. E:\001项目\000开发\003AI+网络安全\000shared-integration\src\shared_integration\adapters\base.py
2. E:\001项目\000开发\003AI+网络安全\000shared-integration\src\shared_integration\adapters\firmware.py
3. E:\001项目\000开发\003AI+网络安全\000shared-integration\src\shared_integration\gateway.py
4. E:\001项目\000开发\003AI+网络安全\000shared-llm-core\docs\v0.5-contract.md §7
5. E:\001项目\000开发\003AI+网络安全\006AI-Firmware-Security-Agent\docs\tech-spec.md
6. E:\001项目\000开发\003AI+网络安全\006AI-Firmware-Security-Agent\docs\TODO.md
7. E:\001项目\000开发\003AI+网络安全\AUDIT\EXPERIENCE.md (经验 1+2+4)

## 必须做(2 ISSUE / 2 commit)

### ISSUE 1 · FW-CLI-001
- 查 src/ai_firmware_agent/__main__.py / cli.py
- 新增 `python -m ai_firmware_agent.cli scan --input <payload> --json`
- payload: {"firmware_path": "<absolute path>"} 或 {"firmware_url": "..."}
- 输出 envelope,Finding 必含 id/severity/confidence/title/cve/host/narrative
- 测试(test_cli_envelope.py, ≥3 个):
  - test_scan_firmware_path
  - test_scan_corrupted_firmware_graceful
  - test_envelope_contains_prisk_narrative

### ISSUE 2 · FW-LIVE-001
- 新增 samples/ 加 1 个公开小固件(≤ 10 MB,如从 https://github.com/firmianay/firmwares 拉一个 demo)
- tests/integration/test_firmware_adapter_e2e.py:gateway 18080 + POST /v0.5/firmware/scan
- README 加 "扫描固件" 章节

## 验收
- `echo '{"firmware_path":"samples/mini.bin"}' | python -m ai_firmware_agent.cli scan --json` → 合法 JSON
- pytest 全过(93 + 1 skip + 新增 ≥ 6)
- 2 commit

## 不要做
- 不修改 000shared-llm-core / 000shared-integration
- 不破坏 v0.5 S4 的 93 + 1 skip
- 不装新依赖
- samples/ 固件总和 ≤ 20 MB

## 回报(每 ISSUE)
1. Files changed
2. Tests: X/X passed
3. CLI smoke 输出
4. curl /v0.5/health 输出
5. Deviations
最终: 2 commit hash + 总测试数
```

---

## 验收节奏(Claude 侧)

每个 worker 回报后,5 分钟内 commit inspect:

1. `git -C <project> log --oneline -2` — 确认 2 个新 commit
2. `git -C <project> diff HEAD~2 --stat` — 改文件清单符合上述范围
3. `pytest` 全过 → 接受
4. 失败 → 1 句话反馈具体哪步,等 worker 修

6 个全部收齐后:
- 跑 `scripts/run_all_tests.py` 全量回归
- 更新 `AUDIT/CONTRACT-COMPLIANCE.md` §7 IntegrationGateway 行
- 派 005-UI(Week 12)

---

## 派发顺序与冲突域

| Worker | 项目 | 工作目录 | 测试集基线 | 期望产出 |
|--------|------|---------|-----------|---------|
| A | 001 SOC | 001AI-SOC-Agent | 58+6 | 2 commit |
| B | 002 Vuln | 002AI-Vulnerability-Agent | 68+6 | 2 commit |
| C | 003 Lab | 003AI Agent安全靶场 | 140+6 | 2 commit |
| D | 004 Code | 004AI代码审计/004AI-CodeGuard-upgrade | 55+6 | 2 commit |
| E | 005 Reverse | 005AI逆向Agent | 150+6 | 2 commit |
| F | 006 Firmware | 006AI-Firmware-Security-Agent | 93+6 | 2 commit |

**6 worker 完全并行,无交叉写域**(各自项目独立 git tree)。
