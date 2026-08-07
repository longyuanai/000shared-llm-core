# 7 个产品 v0.5 升级 · 解锁顺序表

> **历史快照**：本表所述 v0.5 解锁链已经全部完成。当前任务与依赖以 [`dispatches/INDEX.md`](dispatches/INDEX.md) 和根目录 `docs/current-status.md` 为准。

> **前提**: 005-CONTRACT(§7-§10 实现)完工 = 唯一硬阻塞
> **本表用途**: 005-CONTRACT 完工后,7 个产品派活的顺序、依赖、并行安排

---

## 解锁条件

```
005-CONTRACT 完工标志(全部满足):
  [x] __version__ = "0.5.0"
  [x] §7-§10 全部实现 + 测试
  [x] v0.1 现有 24 测试仍全过
  [x] v0.5 新增 ≥ 36 测试全过
  [x] __init__.py append-only,v0.1 符号零破坏
       ↓
   Claude 二审通过
       ↓
   解锁 7 产品并行升级
```

---

## 派活顺序(7 个产品)

| 阶段 | 派活 | 派给谁 | 工时 | 并行? | 依赖 |
|------|------|--------|------|-------|------|
| **Week 9** | 005-CONTRACT | shared-llm-core | 3-4 天 | — | 无 |
| **Week 10.1** | 001-S3 | 001 SOC | 3-4 天 | ✓ A组 | 005-CONTRACT |
| **Week 10.1** | 002-S3 | 002 Vuln | 3-4 天 | ✓ A组 | 005-CONTRACT |
| **Week 10.1** | 003-S3 | 003 Lab | 3-4 天 | ✓ A组 | 005-CONTRACT |
| **Week 10.2** | 004-S3 | 004 Code | 3-4 天 | ✓ B组 | 005-CONTRACT |
| **Week 10.2** | 005-S3 | 005 Reverse | 4-5 天 | ✓ B组 | 005-CONTRACT |
| **Week 10.2** | 006-S4 | 006 Firmware | 4-5 天 | ✓ B组 | 005-CONTRACT |
| **Week 11** | 005-INTEG | shared-integration | 4-5 天 | — | 6 产品 S3/S4 |
| **Week 12** | 005-UI | web-ui | 4-5 天 | ✓ | 005-INTEG |
| **Week 13** | 005-FINAL | 所有 | 5 天 | — | 全部 |

---

## Week 10 · 6 worker 并行派活表

```
A 组(Week 10.1,前 3 天开工):
┌────────────────────────────────────────────┐
│ 001-S3 · 001 SOC · v0.5 多阶段关联          │
│ 002-S3 · 002 Vuln · v0.5 拓扑感知          │
│ 003-S3 · 003 Lab · v0.5 多 Agent 实战       │
└────────────────────────────────────────────┘
       ↓ 各自完成
B 组(Week 10.2,等 A 组完成后开工避免拥挤):
┌────────────────────────────────────────────┐
│ 004-S3 · 004 Code · v0.5 taint + 数据流     │
│ 005-S3 · 005 Reverse · v0.5 符号执行        │
│ 006-S4 · 006 Firmware · v0.5 emulation      │
└────────────────────────────────────────────┘
```

**为什么 A/B 拆**: v0.5 §7-§10 在头几天可能有 bug,A 组先吃螃蟹修 issue,B 组看到稳定版 API 再开工。

---

## 各产品 v0.5 升级要点

### 001 SOC(001-S3)
- §7 MultiAgentOrchestrator:case summary 多 Agent 协作
- §8 RuleEngine:RULE-001-A 多阶段关联(同 IP 24h 跨 ssh+http+smtp)
- §9 Finding:统一 schema 接入
- 不动:v0.1 analyzer.py + CLI

### 002 Vuln(002-S3)
- §8 RuleEngine:RULE-002-A 拓扑感知 CVSS(public +0.5 / internal -0.3)
- §9 Finding:统一 schema 替换现有 Finding
- 不动:v0.1 analyzer.py + offline mode

### 003 Lab(003-S3)
- §7 MultiAgentOrchestrator:多 Agent 实战 5 个新场景
- §8 RuleEngine:场景注册为 rule
- §9 Finding:跨场景关联报告
- 不动:v0.1 detector + target

### 004 Code(004-S3)
- §8 RuleEngine:taint + dataflow 注册为 rule
- §9 Finding:代码 Finding 接入统一 schema
- 不动:tree-sitter + upstream 572 tests

### 005 Reverse(005-S3)
- §8 RuleEngine:symbolic exec + crypto id 注册为 rule
- §9 Finding:binary Finding 接入
- 不动:capstone + 当前 analyzer

### 006 Firmware(006-S4)
- §7 MultiAgentOrchestrator:attack chain 多 Agent 编排
- §8 RuleEngine:QEMU emulation 注册
- §9 Finding:firmware Finding 接入(006 现有 ComponentNarrative 适配)
- 不动:scoring + unpack + PRisk 公式

---

## 各项目派活指令就位状态

| 项目 | 派活指令文件 | 状态 |
|------|------------|------|
| 005-CONTRACT | `000shared-llm-core/docs/005-CONTRACT-CODEX-DISPATCH.md` | ✅ 就位 |
| 001-S3 | 上文消息已给出(待整理) | ⚠️ 待补文件 |
| 002-S3 | 上文消息已给出 | ⚠️ 待补文件 |
| 003-S3 | 上文消息已给出 | ⚠️ 待补文件 |
| 004-S3 | 上文消息已给出 | ⚠️ 待补文件 |
| 005-S3 | 上文消息已给出 | ⚠️ 待补文件 |
| 006-S4 | 上文消息已给出 | ⚠️ 待补文件 |
| 005-INTEG | 上文消息已给出 | ⚠️ 待补文件 |

---

## 你(老板)的工作流

### 现在(Week 9)

1. **复制** `000shared-llm-core/docs/005-CONTRACT-CODEX-DISPATCH.md` 整块内容
2. **贴给 Codex**
3. 等 3-4 天

### Codex 完工后(Week 10 前)

1. Claude 二审(对照 §14 checklist)
2. **解锁 A 组**:复制 001-S3 / 002-S3 / 003-S3 三块给 Codex(可同时发 3 个 worker)
3. **A 组完工后**(Week 10.2):复制 004-S3 / 005-S3 / 006-S4 三块(可同时发 3 个 worker)

### Week 11

- 派 005-INTEG(共享集成层)

### Week 12

- 派 005-UI(Web dashboard)

### Week 13

- 派 005-FINAL(集成测试 + Demo + 文档)

---

## 派活指令文件整理清单(待办)

我下一步把 7 个产品各自的派活指令也整理成独立 .md 文件,放 `E:\001项目\000开发\003AI+网络安全\000shared-llm-core\docs\dispatches\` 目录下,跟 005-CONTRACT 同款格式,你直接复制即可。

要我现在就整理吗?(预计再写 7 个文件,跟 005-CONTRACT 同结构)
