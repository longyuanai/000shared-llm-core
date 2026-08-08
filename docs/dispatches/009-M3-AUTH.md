# 009-M3-AUTH：BFF 身份交换与多租户 RBAC

> **状态**：🔒 已设计、未解锁
> **解锁条件**：锁定 SHA 解析修复后的新 suite CI 全部通过，并将
> `000shared-integration/AUDIT/008-M2-OPS.md` 更新为 PASS。
> **设计依据**：[`ADR-003`](../adr/ADR-003-M3-BFF-identity-boundary.md)

## 1. 目标

把 Dashboard 的全局 Gateway 机器令牌替换为按用户、按租户、短时且可撤销的 BFF 会话，
同时保留现有机器 API Key 兼容性，并用真实 PostgreSQL、Gateway 和浏览器证明租户隔离与
viewer/analyst/admin 权限。

本派活未解锁前只允许评审文档，不得开始产品代码、迁移或依赖变更。

## 2. 范围与提交顺序

允许修改：

- `000shared-integration/migrations/versions/`
- `000shared-integration/src/shared_integration/{db_models,identity,auth,api_v1,admin_cli}.py`
- `000shared-integration/tests/` 及对应身份/RBAC 文档
- `web-ui/app/chatgpt-auth.ts`
- `web-ui/app/lib/gateway-proxy.ts`
- `web-ui/app/api/`、`web-ui/tests/`、Playwright 配置和必要文档
- 阶段收口时的 `000shared-llm-core/suite-lock.yml` 与状态文档

不得修改：

- 六个产品仓业务代码和冻结的 v0.1/v0.5 核心契约
- `003AI Agent安全靶场` 当前受保护修改
- D1 schema（ADR-003 已决定 PostgreSQL/Gateway 是授权事实源）
- 真实 OIDC、Render、GitHub、Gateway 凭据或客户身份数据
- 与身份边界无关的 UI 重构、设计系统更换或技术栈迁移

分别在对应仓形成与 5 个 ISSUE 清晰映射的 commit。跨仓 ISSUE 可以在每个受影响仓各有
一个 commit，因此不机械要求总数等于 5；某一步没有改动时不得制造空 commit。逻辑顺序：

1. `feat(identity): add bridge clients and user sessions`
2. `feat(auth): exchange bff identity for tenant session`
3. `feat(web): proxy gateway with user sessions`
4. `test(auth): cover multi-tenant browser rbac`
5. `docs(auth): record m3 rollout and rollback`

## 3. ISSUE

### ISSUE AUTH-DATA-001 · 身份桥接和用户会话持久化

**目标**：建立与租户 API Key 分离、可轮换和可撤销的身份桥接凭据及短时用户会话。

**任务**：

1. 新增 Alembic migration、SQLAlchemy 模型和 repository 操作，满足 ADR-003 的
   `identity_clients`、用户会话、唯一约束、TTL 和索引要求。
2. 随机桥接密钥沿用项目中适合长期凭据的抗暴力哈希策略；高熵短时会话只保存
   SHA-256 摘要。比较摘要使用常量时间函数。
3. admin CLI 支持创建、列出元数据、轮换和撤销 identity client；密钥只在创建/轮换时
   输出一次，列表与日志不显示明文或完整摘要。
4. 增加过期会话清理和显式撤销；不得清除审计事件。

**测试**（至少 10 个）：

- migration upgrade 与既有数据兼容；重复 upgrade 无额外副作用。
- 桥接密钥只显示一次、错误密钥失败、撤销立即生效、issuer allowlist 生效。
- 会话摘要不等于明文；到期、撤销、租户/成员停用均失效。
- 并发创建或交换不产生重复 user/session 约束泄漏。

**验收**：

- 新旧 schema 均能迁移至最新 revision。
- admin CLI 帮助、创建、轮换、撤销 smoke 通过，输出不含测试密钥。
- SQLite 单元测试与真实 PostgreSQL 集成测试均通过。

### ISSUE AUTH-HTTP-001 · 身份交换和双认证中间件

**目标**：让 Gateway 从数据库 Membership 派生用户权限，并同时兼容机器 API Key。

**任务**：

1. 实现 `POST /v1/auth/exchange` 和会话撤销端点；只接受标准化身份与
   `requested_tenant_id`，拒绝客户端 role/scopes。
2. 以 `(issuer, subject)` 幂等更新用户资料；目标 Tenant/Membership 必须已存在且 active。
3. 扩展 `Principal` 和认证中间件，区分 `igw_` machine key 与 `igs_` user session；
   每个用户请求重新读取 Membership 和角色策略。
4. 加入交换端点速率限制、通用错误响应、request ID 与 actor 审计；所有日志先经过秘密
   值过滤。
5. 保持现有 public health、机器 API Key、scope 和 RBAC 行为不变。

**测试**（至少 14 个）：

- 有效交换、未知 issuer、错误/撤销 client、无 Membership、disabled Tenant。
- viewer 只读、analyst 执行允许操作、admin 管理操作；跨租户均 403。
- 会话过期/撤销 401；成员角色变更在下一请求体现。
- 旧机器 API Key、public path、错误正文和审计字段回归。

**验收**：

- API schema 明确区分 401/403，不泄露账户枚举信息。
- 真实 PostgreSQL 下并发交换和即时撤权通过。
- `tests/test_auth.py`、`tests/test_identity.py`、`tests/test_api_v1.py` 及全量测试通过。

### ISSUE UI-SESSION-001 · Web 身份适配器与安全 cookie

**目标**：由 BFF 验证上游身份、托管 Gateway 用户会话，并彻底移除用户路径中的全局令牌。

**任务**：

1. 定义 `WebIdentityProvider`，保留受信托 ChatGPT Hosting adapter，并实现或接入标准
   OIDC Authorization Code + PKCE adapter。OIDC 验证不得手写密码学实现。
2. 新增 same-origin 登录回调、session bootstrap、租户切换和 logout route；租户选择只是
   请求，最终授权由 Gateway Membership 决定。
3. 生产只设置 `__Host-longyuan_session`（`Path=/; HttpOnly; Secure; SameSite=Lax`）；
   本地降级 cookie 使用不同名称且生产构建必须拒绝。
4. 所有 Gateway 代理 route 移除浏览器传入的 Authorization/identity/role/tenant 头，
   服务端只附加当前 `igs_...`。
5. 写操作校验 Origin/Host、`Sec-Fetch-Site` 和 JSON content type；错误、重试和登出不把
   会话写到页面、URL 或日志。
6. 迁移完成后，面向用户的 route 不读取 `GATEWAY_TOKEN`；机器任务若保留该变量须有
   独立入口和文档。

**测试**（至少 12 个）：

- Hosting/OIDC identity normalization、PKCE/state/nonce 失败路径。
- cookie 属性、生产降级保护、logout/revoke、过期后重新交换。
- inbound Authorization/身份头被剥离；无 cookie、跨站写请求和非法 content type 失败。
- DOM、Web Storage、渲染 HTML、URL 和测试日志均无令牌。

**验收**：

- `npm run lint`、`npm run typecheck`、`npm run test` 通过。
- Node 22、Vinext 和 Cloudflare Worker 构建均通过。
- 若新增 OIDC 依赖，锁版本、许可证和安全审计结果写入回报。

### ISSUE E2E-RBAC-001 · 真实多租户浏览器门禁

**目标**：用真实 PostgreSQL + Gateway + Web 证明 UI 不是只在 mock 下隔离租户。

**任务**：

1. 仅用测试 fixture 创建 Tenant A/B、viewer/analyst/admin、成员关系和 identity client。
2. Playwright 覆盖同租户三角色、无成员、跨租户、成员撤销、会话过期和登出。
3. 浏览器网络记录确认没有 Gateway 机器 key、bridge secret 或会话明文泄漏。
4. 保留既有 Chromium/Mobile Dashboard 场景，新增用例不得用全局令牌绕过登录。

**测试**（至少 10 个真实 E2E 场景）：

- viewer 读、viewer 写拒绝、analyst 工作流、admin 管理操作。
- A 用户访问 B、无成员、成员撤销、过期、登出、刷新恢复。

**验收**：

- 两轮连续真实 E2E 全通过，无顺序依赖和残留会话。
- 测试结束后清理带明确标签的临时身份数据；不得触碰生产 Tenant。

### ISSUE DOC-AUTH-001 · 发布、轮换、回滚和审计

**目标**：让另一位执行者在不接触秘密值的情况下完成部署和回滚。

**任务**：

1. 更新 Integration/Web 架构、环境变量模板、admin CLI 和故障排查文档。
2. 写 migration 顺序、bridge secret 双密钥轮换、Web/Gateway 分阶段部署与回滚步骤。
3. 记录真实测试数量、锁定提交、suite CI run、剩余风险和偏差。
4. 设计/审计层复核后更新 `suite-lock.yml`；不得由执行层自行修改本派活或 ADR。

**测试**（文档门禁）：

- Markdown 链接、secret scan、`git diff --check`、环境变量文档与代码一致性。

**验收**：

- 另一位执行者可按文档完成创建、轮换、撤销和回滚演练。
- Integration/Web 各自提交已推送，suite lock 指向精确 SHA，远端 suite CI 全绿。

## 4. 统一验证

Windows Python 必须使用绝对路径和 ASCII basetemp：

```powershell
$env:PYTHONPATH = "src;../000shared-llm-core/src"
& 'C:\Users\15072\AppData\Local\Programs\Python\Python314\python.exe' -m pytest --basetemp=C:/pytest-tmp/m3-auth -o addopts= tests -q
```

Web：

```powershell
npm run lint
npm run typecheck
npm run test
npm run test:e2e
```

验收报告必须同时给出真实 PostgreSQL 专项结果、全量 Integration pytest、Web build/test、
两轮 Playwright、秘密值扫描和 suite CI 链接。不得用 mock-only 或本地构建替代远端门禁。

## 5. 回报格式

```text
ID: AUTH-DATA-001 / AUTH-HTTP-001 / UI-SESSION-001 / E2E-RBAC-001 / DOC-AUTH-001
Commits: <每个 ISSUE 对应 hash>
Files changed: <关键文件列表>
Tests: <专项 + 全量 + 真实 PostgreSQL + 两轮 Playwright>
Security checks: <cookie / token exposure / CSRF / dependency audit>
Migration and rollback: <revision + 实演摘要>
Suite CI: <run URL + success>
Deviations: <与 ADR/派活不一致之处和原因>
Open questions: <需设计/审计层决策的事项>
```
