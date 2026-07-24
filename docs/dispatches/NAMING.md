# 派活指令命名规范 · v0.5 / v0.6

> **位置**: `000shared-llm-core/docs/dispatches/`
> **适用**: 所有派活文档(001-S3、002-S3、...、006-S5、005-FINAL)
> **生成日期**: 2026-07-24

---

## 1. 文件名格式

```
<STAGE>-<SCODE>.md
```

| 段 | 含义 | 取值 |
|----|------|------|
| `STAGE` | v0.5 阶段号 | `005` (基础契约) / `001~006` (产品升级) |
| `SCODE` | 子阶段代码 | `S3` / `S4` / `S5` / `INTEG` / `UI` / `FINAL` |

**示例**:
- `005-CONTRACT-CODEX-DISPATCH.md` — Week 9,锁 v0.5 §7-§10 契约
- `001-S3.md` — Week 10.1,001 AI-SOC-Agent v0.5 升级
- `001-S4.md` — Week 11,001 v0.6 IntegrationGateway adapter
- `002-S4.md` — Week 11,002 v0.6 adapter
- `005-INTEG.md` — Week 11,集成层新建(`000shared-integration/`)
- `005-UI.md` — Week 12,Web Dashboard(`web-ui/`)
- `005-FINAL.md` — Week 13,v1.0 收尾(docker + e2e + Demo + 文档)

⚠️ **关键陷阱**:`005-INTEG` = v0.5 第 5 阶段集成,**不是产品 005**(产品 005 是 `005AI逆向Agent`)。同样 `005-UI` / `005-FINAL` 也是 stage 005 的子阶段。

---

## 2. 派活文档内部 · ISSUE 编号

每个派活文档内的 ISSUE 编号遵循:

```
<PRODUCT>-<ROLE>-<SEQ>
```

| 段 | 含义 | 取值 |
|----|------|------|
| `PRODUCT` | 产品 ID 短名 | `SOC` / `VULN` / `LAB` / `CODE` / `REV` / `FW` / `INTEG` / `UI` / `DEPLOY` / `E2E` / `DOC` |
| `ROLE` | ISSUE 类别 | `CLI` (CLI 契约) / `LIVE` (真实样本+集成) / `ADAPT` (adapter) / `RULE` (规则) / `PAGE` (页面) 等 |
| `SEQ` | 同产品同类别内的 3 位序号 | `001` / `002` |

**示例**(Week 11 v0.6 adapter 派活):
- `SOC-CLI-001` — 001 SOC CLI envelope 契约
- `SOC-LIVE-001` — 001 SOC 真实样本+集成
- `VULN-CLI-001` / `VULN-LIVE-001`
- `LAB-CLI-001` / `LAB-LIVE-001`
- `CODE-CLI-001` / `CODE-LIVE-001`
- `REV-CLI-001` / `REV-LIVE-001`
- `FW-CLI-001` / `FW-LIVE-001`

**示例**(Week 13 FINAL 派活):
- `DEPLOY-001` — docker-compose 全栈编排
- `E2E-001` — e2e 真实场景剧本
- `DOC-001` — 商业化文档 + Demo 视频脚本

---

## 3. 派活文档 · 6 段式结构(每 ISSUE 必填)

```markdown
### ISSUE <ID> · <一句话标题>

**目标**: <一句目标>

**任务**: <编号列表,每条带文件路径>

**测试**(≥ N 个):
- <测试路径::test_xxx>

**验收**:
- <可执行的验证命令 / curl / pytest 命令>

**约束**: <可选,默认从全局继承>
```

---

## 4. 回报格式

每 ISSUE 完工后,worker 必须按下列格式回报(便于 Claude 验收):

```
ISSUE: <ID>
commit: <hash>
files: <list of touched files>
tests: <N> passed, <M> failed
verify: <paste stdout of verification command>
NITs: <optional, anything close-to-spec-but-not-exact>
```

---

## 5. 常见 NIT(由 Claude 标记,worker 接受 / 反驳)

- `addopts` 没 override → 中文路径 pytest 报 WinError 5
- 装包忘 absolute path → 触发 Windows PATH `python` → 49
- 004 忘 verify tree_sitter._binding cp314
- 大写 severity (`"CRITICAL"`) → `FindingSeverity("CRITICAL")` 失败,必须小写
- envelope 顶层非 object/array → `ProductCLIError`
- finding 单项不是 dict → `ProductCLIError`

---

## 6. 阶段编号 → 周次映射

| 周次 | Stage 文件 | 含义 |
|------|-----------|------|
| Week 9 | `005-CONTRACT` | v0.5 §7-§10 契约锁 |
| Week 10.1 | `001/002/003-S3` | 前 3 个产品 v0.5 升级 |
| Week 10.2 | `004/005/006-S3`/`004-S3` | 后 3 个产品 v0.5 升级 |
| Week 11 | `005-INTEG` + `001~006-S4/S5` | 集成层 + 6 个产品 v0.6 adapter |
| Week 12 | `005-UI` | Web Dashboard |
| Week 13 | `005-FINAL` | v1.0 收尾 |