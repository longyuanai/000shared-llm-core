# 派活指令索引 · v0.5 升级

> **位置**: `000shared-llm-core/docs/dispatches/`
> **生成日期**: 2026-07-24(2026-07-25 更新:S4/S5 全部 dispatching)
> **前提**: 005-CONTRACT 必须先完工(锁 §7-§10 实现)
> **命名规范**: 见 [`NAMING.md`](NAMING.md)
> **6 worker 并行 pack**: [`CODEX-DISPATCH-PACK-v0.6.md`](CODEX-DISPATCH-PACK-v0.6.md) — 2026-07-25 同时发车

---

## 派活文件清单(13 个)

| # | 文件 | 项目 | 工时 | 派发周 | 状态 |
|---|------|------|------|--------|------|
| 1 | [005-CONTRACT-CODEX-DISPATCH.md](../005-CONTRACT-CODEX-DISPATCH.md) | shared-llm-core | 3-4 天 | Week 9 | ✅ done |
| 2 | [dispatches/001-S3.md](dispatches/001-S3.md) | 001 AI-SOC-Agent | 3-4 天 | Week 10.1 | ✅ done |
| 3 | [dispatches/002-S3.md](dispatches/002-S3.md) | 002 AI-Vulnerability-Agent | 3-4 天 | Week 10.1 | ✅ done |
| 4 | [dispatches/003-S3.md](dispatches/003-S3.md) | 003 AI-Agent-Security-Lab | 3-4 天 | Week 10.1 | ✅ done |
| 5 | [dispatches/004-S3.md](dispatches/004-S3.md) | 004 AI-CodeGuard | 3-4 天 | Week 10.2 | ✅ done |
| 6 | [dispatches/005-S3.md](dispatches/005-S3.md) | 005 AI-Reverse-Agent | 4-5 天 | Week 10.2 | ✅ done |
| 7 | [dispatches/006-S4.md](dispatches/006-S4.md) | 006 AI-Firmware-Security-Agent | 4-5 天 | Week 10.2 | ✅ done |
| 8 | [dispatches/005-INTEG.md](dispatches/005-INTEG.md) | shared-integration(新) | 4-5 天 | Week 11 | ✅ done(4 commit) |
| 9 | [dispatches/005-UI.md](dispatches/005-UI.md) | web-ui(新) | 4-5 天 | Week 12 | ⏳ pending |
| 10 | [dispatches/001-S4.md](dispatches/001-S4.md) | 001 v0.6 IntegrationGateway adapter | 2-3 天 | Week 11 | 🚀 dispatching (2026-07-25) |
| 11 | [dispatches/002-S4.md](dispatches/002-S4.md) | 002 v0.6 adapter | 2-3 天 | Week 11 | 🚀 dispatching (2026-07-25) |
| 12 | [dispatches/003-S4.md](dispatches/003-S4.md) | 003 v0.6 adapter | 2-3 天 | Week 11 | 🚀 dispatching (2026-07-25) |
| 13 | [dispatches/004-S4.md](dispatches/004-S4.md) | 004 v0.6 adapter | 2-3 天 | Week 11 | 🚀 dispatching (2026-07-25) |
| 14 | [dispatches/005-S4.md](dispatches/005-S4.md) | 005 v0.6 adapter | 2-3 天 | Week 11 | 🚀 dispatching (2026-07-25) |
| 15 | [dispatches/006-S5.md](dispatches/006-S5.md) | 006 v0.6 adapter | 2-3 天 | Week 11 | 🚀 dispatching (2026-07-25) |
| 16 | [dispatches/005-FINAL.md](dispatches/005-FINAL.md) | longyuanai-deploy e2e + Demo + 文档 | 5-7 天 | Week 13 | ⏳ pending(待 INTEG + UI 完工) |

---

## 解锁依赖图

```
005-CONTRACT (Week 9, 硬阻塞) ✅ done
    │
    ├──> 001-S3 ─┐
    ├──> 002-S3 ─┼──> 005-INTEG (Week 11) ✅ done
    ├──> 003-S3 ─┘            │
    │                         ├──> 001-S4 ─┐
    ├──> 004-S3 ─┐            ├──> 002-S4 ─┤
    ├──> 005-S3 ─┼──> 005-INTEG             ├──> 005-FINAL (Week 13)
    └──> 006-S4 ─┘            ├──> 003-S4 ─┤
                              ├──> 004-S4 ─┤
                              ├──> 005-S4 ─┤
                              └──> 006-S5 ─┘

005-INTEG (Week 11)
    └──> 005-UI (Week 12) ──> 005-FINAL (Week 13)
```

---

## 你(老板)的工作流

### Step 1 · Week 9 Day 1(已发)✅

复制 `005-CONTRACT-CODEX-DISPATCH.md` 整块内容,贴给 Codex。
**结果**:v0.5 §7-§10 contract 全部冻结,73 tests passing。

### Step 2 · Week 10.1(已发 3 worker 并行)✅

- 复制 `dispatches/001-S3.md` → Codex worker A
- 复制 `dispatches/002-S3.md` → Codex worker B
- 复制 `dispatches/003-S3.md` → Codex worker C

**结果**:3 个产品 v0.5 升级完成,266 tests passing(58+68+140)。

### Step 3 · Week 10.2(已发 3 worker 并行)✅

- 复制 `dispatches/004-S3.md` → Codex worker D
- 复制 `dispatches/005-S3.md` → Codex worker E
- 复制 `dispatches/006-S4.md` → Codex worker F

**结果**:3 个产品 v0.5 升级完成,298 tests passing(55+150+93)。

### Step 4 · Week 11(现在派)

复制 `dispatches/005-INTEG.md` → Codex(单 worker,**新建 `000shared-integration/` 仓库**)。
**等 4-5 天**。

### Step 5 · Week 12(005-INTEG 完工后派)

复制 `dispatches/005-UI.md` → Codex(单 worker,**新建 `web-ui/` 仓库**)。
**等 4-5 天**。

### Step 6 · Week 13

派 `005-FINAL`(集成测试 + Demo + 商业化文档)—— 待 `005-FINAL.md` 起草。

---

## 派活指令文件清单(绝对路径)

```
E:\001项目\000开发\003AI+网络安全\000shared-llm-core\docs\
├── 005-CONTRACT-CODEX-DISPATCH.md  (Week 9)  ✅ done
├── 7-PRODUCT-UNLOCK-ORDER.md        (解锁顺序总览)
├── STAGES-v0.5.md                    (4 周节奏)
└── dispatches\
    ├── INDEX.md                      (本文件)
    ├── 001-S3.md                     (Week 10.1) ✅ done
    ├── 002-S3.md                     (Week 10.1) ✅ done
    ├── 003-S3.md                     (Week 10.1) ✅ done
    ├── 004-S3.md                     (Week 10.2) ✅ done
    ├── 005-S3.md                     (Week 10.2) ✅ done
    ├── 006-S4.md                     (Week 10.2) ✅ done
    ├── 005-INTEG.md                  (Week 11) ✅ done
    ├── 005-UI.md                     (Week 12) ⏳ pending
    ├── 001-S4.md                     (Week 11) ⏳ pending — v0.6 adapter
    ├── 002-S4.md                     (Week 11) ⏳ pending — v0.6 adapter
    ├── 003-S4.md                     (Week 11) ⏳ pending — v0.6 adapter
    ├── 004-S4.md                     (Week 11) ⏳ pending — v0.6 adapter
    ├── 005-S4.md                     (Week 11) ⏳ pending — v0.6 adapter
    ├── 006-S5.md                     (Week 11) ⏳ pending — v0.6 adapter
    └── 005-FINAL.md                  (Week 13) ⏳ pending — e2e + Demo + 商业化
```

---

## 总工时估算

| 周 | 同时跑的 worker | 累计产出 | 状态 |
|----|----------------|---------|------|
| Week 9 | 1 (005-CONTRACT) | v0.5 §7-§10 就位 | ✅ done |
| Week 10.1 | 3 (001/002/003 并行) | 3 个产品 v0.5 升级 | ✅ done |
| Week 10.2 | 3 (004/005/006 并行) | 3 个产品 v0.5 升级 | ✅ done |
| Week 11 | 1 (005-INTEG) | 集成层 + FastAPI | ⏳ pending |
| Week 12 | 1 (005-UI) | Web dashboard | ⏳ pending |
| Week 13 | 1 (005-FINAL) | e2e + Demo + 文档 | ⏳ pending(待起草) |

**已完成工时**:约 3 周(Week 9-11.2)
**剩余工时**:约 3 周(Week 11.3 - Week 13)
**总墙钟**:约 6 周(原估 5 周,新增 005-FINAL 起稿)

---

## 全量回归实测(2026-07-24,7 项目合计)

```
000 shared-llm-core              OK  73 passed
001 AI-SOC-Agent                 OK  58 passed
002 AI-Vulnerability-Agent       OK  68 passed, 1 warning
003 AI-Agent-Security-Lab        OK  140 passed
004 AI-CodeGuard-upgrade         OK  55 passed, 1 warning
005 AI-Reverse-Agent             OK  150 passed, 1 warning
006 AI-Firmware-Security-Agent   OK  93 passed, 1 skipped
TOTAL: passed=637  failed=0
```

回归脚本:`E:\001项目\000开发\003AI+网络安全\scripts\run_all_tests.py`

---

## 验证检查表(每次 Codex 完工后跑)

```bash
# 在对应项目目录下(注意:必须 -o addopts= 绕开中文路径 basetemp):
python -m pytest tests/ \
    --basetemp=C:/pytest-tmp/<project> \
    -q --tb=no \
    -o addopts=

# 期望(2026-07-24 实际值):
# - shared-llm-core:  73 passed
# - 001:              58 passed
# - 002:              68 passed
# - 003:             140 passed
# - 004:              55 passed
# - 005:             150 passed
# - 006:              93 passed + 1 skipped
# - shared-integration: ≥ 30 passed(全 v0.5,待派活)
# - web-ui:           ≥ 5 Playwright E2E(待派活)
```

> **⚠️ Windows 中文路径关键 trick**:`pyproject.toml` 里硬编码的 `addopts = "--basetemp=.pytest-tmp"` 会在中文路径下报 `WinError 5`。必须在命令行用 `-o addopts=` 覆盖,详见 `AUDIT/EXPERIENCE.md`(2026-07-24 修复记录)。

如果某个项目未达标,在回报里说明 NIT,不要忽略。