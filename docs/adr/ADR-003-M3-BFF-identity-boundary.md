# ADR-003 · M3 BFF 身份交换与租户授权边界

**状态**: 候选；`008-M2-OPS` 成功 rerun 后接受并解锁实施
**日期**: 2026-08-09
**决策方**: longyuanai 设计/审计层
**关联派活**: `docs/dispatches/009-M3-AUTH.md`
**前置门禁**: run `31188096745` 的锁定 SHA 解析缺陷修复后，新 suite CI 全部通过

---

## 背景

`000shared-integration` 已有持久化 Tenant、User、Membership、API Key 和
`TenantRBACMiddleware`，但 `web-ui` 的 Gateway 代理仍使用一个服务端全局
`GATEWAY_TOKEN`。这个做法能保护令牌不进入浏览器，却会把所有 Dashboard 请求压成同一
机器身份，无法可靠回答“哪个用户以什么角色访问了哪个租户”，也无法在成员关系撤销后
立即终止该用户的权限。

当前 Web 运行时已经能从受信托的 ChatGPT Hosting 请求头获得用户身份；M3 还需要支持
标准 OIDC。Gateway 不应耦合某个具体身份提供方，也不应接受浏览器自行声明的租户、角色
或用户请求头。

## 决策目标

1. 浏览器永远接触不到长期 Gateway API Key 或 BFF 身份桥接密钥。
2. Gateway 以数据库中的 Tenant、Membership 和角色策略作为最终授权事实源。
3. 现有 `igw_...` 机器 API Key 保持向后兼容，用户流量使用独立身份类型。
4. 用户、租户、会话和请求 ID 可进入审计事件，密钥和会话明文不进入日志。
5. 身份提供方变化只影响 Web 适配器，不改变 Gateway 的用户会话契约。

## 决定

### 1. 采用 BFF 身份交换，不转发提供方令牌

```text
Browser
  │ 受信托 Hosting 身份 / OIDC code + PKCE
  ▼
web-ui BFF ── identity bridge credential ──► POST /v1/auth/exchange
  │                                             │
  │ HttpOnly 短时会话 cookie                    │ Membership 是授权事实源
  ▼                                             ▼
same-origin API routes ── igs_ session ──► IntegrationGateway
```

Web 侧定义 `WebIdentityProvider` 接口，至少包含：

- `ChatGPTHostingProvider`：读取部署平台注入且已验证的身份；普通客户端提供的同名请求头
  不得成为信任来源。
- `OidcProvider`：执行 Authorization Code + PKCE，并校验 `state`、`nonce`、issuer、
  audience 和回调地址。JWT/签名校验使用维护中的标准实现，不手写密码学代码。

两种适配器最终只向 BFF 返回标准化的 `issuer`、`subject`、`email` 和 `display_name`。
身份提供方 access token / ID token 不转发给 Gateway，也不写入项目数据库。

### 2. 身份桥接凭据与租户 API Key 分离

新增 Gateway 级 `identity_clients`（实现名可等价）持久化对象，至少包含：

- `id`、`name`、`secret_hash`、`allowed_issuers`、`active`；
- 固定能力 `auth:exchange`；
- 创建、轮换、撤销和最后使用时间。

它只允许调用身份交换与会话撤销接口，不得访问 Finding、Job 或管理 API。桥接密钥通过
admin CLI 创建和轮换，只显示一次；仓库、CI、浏览器和审计报告均不保存明文。不得把现有
租户绑定 API Key 伪装成身份桥接凭据。

### 3. 交换端点只接受身份，不接受授权结论

`POST /v1/auth/exchange` 的输入包含标准化身份与 `requested_tenant_id`。Gateway 必须：

1. 验证 identity client、`auth:exchange` 能力和允许的 issuer。
2. 以 `(issuer, subject)` 查找或幂等更新用户展示资料。
3. 要求目标 Tenant 和 Membership 已存在且处于 active 状态；不自动创建 Membership。
4. 忽略 BFF 传入的任何 `role`、`scopes` 或 tenant name，并从数据库重新派生授权。
5. 创建短时用户会话并记录不含秘密值的审计事件。

无 Membership 返回 403；身份桥接失败、会话过期或撤销返回 401。错误正文不得泄露用户、
租户或成员关系枚举信息。

### 4. 用户会话采用短时不透明令牌

Gateway 颁发高熵随机 `igs_...` 会话令牌，仅在响应中出现一次。数据库只保存令牌的
SHA-256 摘要，并记录 `user_id`、`tenant_id`、`identity_client_id`、创建/到期/撤销时间
和最近使用时间。

- 默认 TTL 为 5 分钟，配置上限为 15 分钟。
- Gateway 不静默续期；BFF 重新验证上游身份后才能再次交换。
- 每个请求重新读取 active Membership 与角色策略，不在会话中冻结 role/scopes。
- Tenant、Membership、identity client 或会话撤销后，下一次请求立即失效。
- 定时清理只删除已过期会话；安全审计事件按既有保留策略保存。

现有中间件同时接受 `igw_...` 机器 API Key 和 `igs_...` 用户会话。`Principal` 增加
`auth_type`、`user_id`、`session_id` 等审计上下文；用户会话的 scopes 由服务端角色策略
产生，不接收客户端声明。

### 5. 浏览器只持有 HttpOnly cookie

生产环境 cookie 固定为：

```text
__Host-longyuan_session; Path=/; HttpOnly; Secure; SameSite=Lax
```

不得设置 `Domain`，不得写入 Local Storage、Session Storage、可读 JavaScript 状态或
页面 HTML。本地 HTTP 开发使用不同名称 `longyuan_session_dev`；生产构建若出现该降级
名称或关闭 `Secure` 必须失败。

BFF 的 same-origin API route 必须移除浏览器传入的 `Authorization`、用户、角色和租户
身份头，再由服务端附加 `igs_...`。状态变更请求同时校验 `Origin`/`Host`、
`Sec-Fetch-Site` 和 JSON content type；登出调用 Gateway 撤销会话后再清 cookie。

### 6. 兼容与迁移

- 现有机器 API Key、CLI 和非浏览器客户端行为保持不变。
- `GATEWAY_TOKEN` 只允许用于明确标记的机器任务；用户请求路径完成迁移后不再读取它。
- 数据库迁移先加表和索引，再部署 Gateway 双认证，最后切换 Web；回滚时 Web 可恢复到
  已锁定版本，Gateway 仍兼容旧机器 API Key。
- 不启用当前空置的 D1 作为会话权威库；身份与授权事实继续归 PostgreSQL/Gateway 所有。

## 未采用方案

| 方案 | 结论 | 原因 |
|---|---|---|
| 全局 `GATEWAY_TOKEN` + 转发用户头 | 拒绝 | 用户头可伪造，角色撤销和逐用户审计不可靠 |
| 浏览器直接保存租户 API Key | 拒绝 | 长期秘密暴露给 DOM、扩展、XSS 和客户端日志 |
| Gateway 直接集成每个 OIDC 提供方 | 拒绝 | 将 Gateway 与 Web 登录流程、回调和供应商配置耦合 |
| BFF 签发长期自包含 JWT | 延后 | 角色撤销不即时，还需要签名密钥轮换与 JWKS 生命周期 |
| D1 保存用户授权和会话 | 拒绝 | 形成第二授权事实源，增加跨库一致性问题 |

## 安全与运维影响

- 新增 identity client 和 user session 的迁移、管理 CLI、清理任务和审计事件。
- 身份交换是新的高价值端点，必须有速率限制、失败审计和通用错误响应。
- BFF 密钥轮换应支持短暂双密钥窗口；旧密钥只在新密钥验证通过后撤销。
- OIDC provider 配置、桥接密钥和 cookie 不进入 Git；测试只使用显式 fixture 身份。
- 不新增生产依赖是默认原则；OIDC 标准实现若需新增依赖，必须锁版本并通过 Node 22、
  Vinext/Cloudflare 构建和安全审计，不能以自写验证替代。

## 接受条件

1. 两个 Tenant、viewer/analyst/admin 三角色的真实 PostgreSQL 测试通过。
2. 无 Membership 和跨租户访问均为 403；过期/撤销会话为 401。
3. Membership、Tenant 或 identity client 被停用后，下一请求立即失效。
4. 现有机器 API Key 契约与测试保持通过。
5. 审计事件包含 actor user/session/client、tenant、action 和 request ID，不含令牌明文。
6. cookie 属性正确；令牌不出现在 DOM、Web Storage、URL、浏览器日志或错误正文。
7. 真实 Gateway + PostgreSQL + Web 的 Playwright RBAC 场景通过。
8. `008-M2-OPS` 的远端 suite CI 先成功，`suite-lock.yml` 再锁定 M3 的已推送提交。

## 解锁规则

本 ADR 当前只授权设计与派活，不授权产品实现。锁定 SHA 解析修复后的新 suite CI 全部
通过后，将本 ADR 状态改为“接受”，把 `009-M3-AUTH` 标为已解锁，再交给执行层。
