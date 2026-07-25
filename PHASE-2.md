# 000shared-llm-core · Phase-2 计划

> **本仓角色**: longyuanai 中心仓。提供 `LLMRouter` + v0.5 §7-§10 四个组件。
> **当前状态**: v0.5 §7-§10 已实现 + 测试;v0.5 §15 CLI Envelope 契约冻结;v0.5 §1-§6(v0.1)冻结。`inspect_worker_return.py` 6/6 worker 已绿。
> **下一阶段**: v0.6 / v1.0。

---

## 现状摘要(2026-07-25)

| 项 | 状态 | 备注 |
|----|------|------|
| v0.1 contract §1-§6 | 冻结 | `LLMRouter` + `PromptTemplate` + `AuditLog` 等 |
| v0.5 contract §7 MultiAgentOrchestrator | ✅ | 5 个 AgentRole + MissionContext + scratchpad |
| v0.5 contract §8 RuleEngine | ✅ | Rule 抽象 + 内置注册表 + 默认顺序 |
| v0.5 contract §9 Finding | ✅ | UUID4 + severity/confidence 校验 + to/from_dict |
| v0.5 contract §10 IntegrationGateway | ✅ | FastAPI app + 4 端点(/health/scan/findings/stream/correlations) |
| v0.5 contract §15 CLI Envelope | ✅ | 6 产品契约 + 字段兼容性归一化 |
| 测试 | ✅ | ≥ 60 test function 累计(含 test_contract_examples) |
| 6 worker 4 件套 | ✅ | A/B/C/D/E/F 全绿 |

---

## Phase-2 hooks(下一组派活,等用户解锁)

> 下面是 Codex 拿到可以立刻干的候选。**不是必须** — 用户可能选不同方向。

### Hook A · §15 contract 测试完全覆盖(派活 005-FINAL-001 已在做)

- **目标**:`tests/integration/test_cli_envelope_smoke.py` 跑 6 产品 e2e 子进程
- **优先级**:🟢 高(已挂)
- **解冻条件**:CLI smoke 当前是 inspect 脚本覆盖,**不算真 contract test**

### Hook B · §16 streaming correlation(新 v0.6 章节)

**目标**:让 `FindingRegistry.add` 触发 correlation rule 时**不阻塞主流程**(目前 add + correlate 是同步)。

**派活文档**:`008-CORR-STREAM.md`(待起草)

```python
# 现状
await registry.add(finding)
for rule in correlations:
    emitted = rule.correlate(finding, existing)  # 同步、阻塞
    await registry.add_correlation(corr)

# 目标
await registry.add(finding)  # 立即返回
# correlation 在后台 task 跑,不阻塞
```

**实现要点**:
- 把 correlation rule 跑变成 `asyncio.create_task(coro)`
- 加 `correlation_queue` 缓冲区,断连时缓冲不丢失
- 测试:`tests/test_streaming_correlation.py` ≥ 5 个 test function

**为什么是 Phase-2**:
- 当前同步版够用(扫描是一请求一回复)
- 大流量时 correlation 慢会阻塞 `/scan` 返回
- v0.6 真正生产流量时不能阻塞

### Hook C · §17 multi-tenant auth(v0.7+)

**目标**:`IntegrationGateway` 加 Bearer token 鉴权。

**派活文档**:`009-AUTH.md`(待起草)

- endpoint:`/v0.5/{source}/scan` + `/v0.5/findings` 都要鉴权
- token 走环境变量 `LONGLYUANAI_TOKENS`(逗号分隔)
- 401 → stdlib error,不泄露 token
- 测试:7 个 case(missing token / wrong token / valid token / expiry 不模拟)

**为什么 Phase-2**:
- v0.5/0.6 是**内网 demo**,鉴权不是核心
- v1.0 SaaS 时必须有

### Hook D · §18 persistent FindingRegistry(v0.7+)

**目标**:把 `FindingRegistry` 从 `deque(maxlen=100_000)` 换成 SQLite / Postgres backend。

**派活文档**:`010-PERSISTENCE.md`(待起草)

- 抽象 `FindingsBackend` protocol,2 个实现:`InMemoryFindings` / `SQLiteFindings`
- `IntegrationGateway(..., backend=SQLiteFindings("db.sqlite"))`
- 启动 1 次开 DB 写,finding 重启后保留
- 测试:≥ 10 test,覆盖 CRUD + 重启恢复 + 并发

**为什么 Phase-2**:
- 当前 demo 重启清空没问题
- v0.7 真用生产流量,finding 必须持久

---

## v1.0 路线图(指向,不立刻做)

```
v0.5 已冻结 (2026-07 目标)
   ↓
v0.6 (2026 Q3): §15 CLI Envelope + 007-CI + Phase-2 Hook A
   ↓
v0.7 (2026 Q4): Phase-2 Hook B (streaming correlation) + Hook D (SQLite persistence)
   ↓
v1.0 (2027 Q1): 7 产品全部 v1.0 上线 + Phase-2 Hook C (multi-tenant auth) + gateway 生产流量 30 天
   ↓
v1.0 → v2.0: 仅 breaking change,必须写迁移指南(参见 v0.5 §12)
```

---

## 不要做的事

- ❌ 不要随便删 v0.1 / v0.5 字段,即使"看起来没用"
- ❌ 不要在 §7-§10 上做新设计,先写 RFC 进 `docs/rfcs/`
- ❌ 不要新增第三方依赖除非 6 个产品都受益
- ❌ 不要在 v0.5 阶段碰 §15 CLI Envelope 兼容性归一化(那是契约)

---

## Claude 自己用(Codex 不用读)

- 派活文档统一进 `000shared-llm-core/docs/dispatches/`
- ADR 进 `docs/adr/`,命名 `ADR-NNN-<topic>.md`
- RFC 进 `docs/rfcs/`,命名 `RFC-NNN-<topic>.md`

---

**最近修订**: 2026-07-25 · Claude 起草 Phase-2 计划
**下次回看触发**: v0.6 启动 / 新 hook 出现 / v1.0 触发条件满足
