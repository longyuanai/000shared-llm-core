# M3 身份与多租户 RBAC 门禁记录

> 状态：**精确锁定门禁通过，Sites 发布待恢复访问**
> 日期：2026-08-09

## 锁定范围

本门禁关闭 `009-M3-AUTH` 的代码、真实浏览器和运维文档范围：

- Integration：`2d42a8728b55a8a541d0f6d4ed23698fae23f15d`
- Web：`a778e0b9c845083d41493f10653ccaa943839882`
- Core：本文件所在提交；`suite-lock.yml` 的 core 继续使用 `self`
- 001–006：保持 M2 已验证锁定提交不变

Integration 包含 revision `20260809_0002`、identity client、短时用户会话、HTTP 身份交换、
双认证、逐请求 Membership RBAC、E2E fixture、发布/轮换/回滚 Runbook 和审计。Web 包含
Hosting/OIDC + PKCE、HttpOnly BFF 会话、同源代理、13 场景真实 RBAC 与双轮编排。

## 候选证据

- Web CI [`31276154427`](https://github.com/longyuanai/web-ui/actions/runs/31276154427)：
  lint、两套 typecheck、Vinext build、37 个 Node tests、Chromium/Mobile 12 个 Demo E2E。
- 候选 suite CI
  [`31276172231`](https://github.com/longyuanai/000shared-llm-core/actions/runs/31276172231)：
  8 个 Python 组 `1914 passed, 7 skipped, 1 warning`；真实 PostgreSQL + Gateway + Web
  两个独立 round 各 `13 passed`，每轮 fixture 与最终 Compose 资源清理成功。
- 精确锁定 suite CI
  [`31276779035`](https://github.com/longyuanai/000shared-llm-core/actions/runs/31276779035)：
  core `60589387bebaa36c3a12873c90839dac4052ce47` 按 `suite-lock.yml` 检出 Integration
  `2d42a8728b55a8a541d0f6d4ed23698fae23f15d` 与 Web
  `a778e0b9c845083d41493f10653ccaa943839882`；九仓锁校验、八个 Python 组与真实浏览器
  双轮门禁全部成功，两轮各 `13 passed`，最终容器和网络均已移除。
- 本地 Integration：`139 passed, 4 skipped`；真实 PostgreSQL 16 专项 `4 passed`；Ruff 通过。
- 生产依赖：`openid-client 6.8.4`、Next `16.3.0`；npm production audit 为 0。

## 发布与回滚

发布顺序固定为：备份 → Alembic migration → Gateway 双认证 → identity client / Membership
准备 → Web secret 与身份配置 → 私有浏览器验收。双密钥轮换、会话处置和回滚步骤见
[Integration M3 auth Runbook](https://github.com/longyuanai/-000shared-integration/blob/master/docs/m3-auth-rollout-rollback.md)。

## 剩余项

- 现有 Sites `project_id` 在当前连接账号下不可见。恢复原项目访问、注入运行时值并完成私有
  发布之前，不创建替代项目、不宣称现网已切换。
- Render 私有 GHCR 拉取凭据须在 2026-08-14 前轮换或随服务下线撤销。
- Sites 发布完成后，将 Integration 审计从 PASS-WITH-NITS 升级为 PASS。

最终锁定 run 与 docs-head run 记录在项目根目录 `docs/current-status.md`，避免为写入自身 run
编号形成无穷提交循环。
