# ADR-001 · 005-UI 技术栈选型评审

**状态**: 推荐(供 Codex 写最终 ADR-001 时参照)
**日期**: 2026-07-25
**作者**: Claude(设计层)
**接收方**: Codex(写最终 ADR-001 时采纳 / 反驳)
**关联派活**: `000shared-llm-core/docs/dispatches/005-UI.md`

---

## 背景

005-UI 是 longyuanai 7 产品 v0.5 周期的 Web Dashboard:在 `web-ui/`(根目录新仓)起一个 Next.js 应用,通过 `IntegrationGateway`(端口 8080)拉取 6 个产品的 Finding 流、跨产品 Correlation、健康状态,实时刷新给安全工程师看。

005 派活文档已经定调栈:**Next.js 14 + Tailwind + shadcn/ui + SWR + Playwright**。本 ADR 不重新选,而是评审这个选型 + 评审"为什么不选其他"。

---

## 候选栈对比

| 维度 | A. Next.js 14 + shadcn/ui(**已选**) | B. Vite + React + 自写组件 | C. SvelteKit + Skeleton |
|------|--------------------------------------|----------------------------|-------------------------|
| **SSR / 首屏** | ✅ 内置,SEO 友好 | ❌ SPA,首屏慢 | ✅ 内置 |
| **生态 / 招聘池** | ★★★★★(最大) | ★★★★★ | ★★(小众) |
| **数据获取** | RSC + fetch / SWR | React Query / SWR | 内置 `load` |
| **类型安全** | TS strict 默认 | TS strict 手动配 | TS 默认 |
| **shadcn/ui 可用** | ✅ 直接复制 | ✅ 但要自己接 Tailwind | ❌ |
| **暗色模式** | `next-themes` 一行 | 自己写 | Skeleton 内置 |
| **SSE 流(关键)** | Route Handler 代理上游 + EventSource | EventSource 直连 | 同左 |
| **部署** | Vercel / Node / Docker | 任何静态托管 | Vercel / Node |
| **团队学习曲线** | 中(3 天) | 低 | 高(Svelte 语法) |
| **Playwright 集成** | 官方 `@playwright/test` | 同 | 同 |
| **长期维护成本** | 低(社区大) | 低 | 中 |

---

## 决定:**Next.js 14 + shadcn/ui + SWR + Playwright**

继承 005 派活文档的定调。

## 理由

1. **生态最厚**:shadcn/ui / Tailwind / SWR 都是 React/Next 周边最大社区;招前端最容易。
2. **SSE 简单**:Next.js Route Handler 可以直接代理上游 SSE(`text/event-stream` 直通),不需要中间层。
3. **暗色模式一行搞定**:`next-themes` + shadcn 默认 dark,派活指令里写的对。
4. **服务端组件省 JS 体积**:Dashboard 首页用 RSC 直接 `await getHealth()` 拿数据,客户端只下最小交互代码。
5. **shadcn 不是 npm 包,是源码复制** —— 意味着 UI 升级可控、不被依赖锁死、TS 类型精准。这是选它的核心理由。

## 已知折衷

- **RSC + 客户端组件边界**:`<StreamBadge>` / `<FindingCard>` 必须 `"use client"`;派活 ISSUE 4 已经标对了。
- **bundle 体积**:shadcn 全装 ≥ 200KB;若担心可用 `dynamic()` 拆分。
- **Playwright 在 Windows**:需要 `npx playwright install chromium`;`playwright.config.ts` 必须显式 `webServer.url`,否则 CI 启不来。
- **SWR vs React Query**:派活指令选了 SWR;论据是轻量(4KB)+ 与 Next.js fetch 配合好。React Query 更强但**对 6 产品 + 5 屏的体量没必要**。

---

## 关于"为什么不选其他"

### 为什么不是 Vite + React?

- 没有 SSR,Dashboard 首屏会白屏等 fetch;Vite 是 SPA,但我们没有"前端路由多到必须客户端"的需求。
- shadcn/ui 在 Vite 上要用,但要自己配 Tailwind;省不下多少工作量。
- 唯一优势:启动快 / HMR 极致。**但 Dashboard 不是 dev server 重度使用场景**,不值得。

### 为什么不是 SvelteKit?

- 团队没人会 Svelte(假设);学习曲线 2-3 周,超过项目剩余时间。
- 招聘池小(国内 Svelte 后端 / 前端少)。
- shadcn/ui 不可用,要换 Skeleton 或自己写组件,**与 005 派活指令冲突**。

### 为什么不是 Remix?

- 派活指令写的是 Next.js;如果想换 Remix,要从头改 005-UI 派活文档,**不划算**。
- Remix v2 与 Next 14 App Router 概念高度重叠(loader / action vs RSC + Server Actions);选哪个都行,但**已有指令就别动**。

### 为什么不是 Nuxt / Vue 系?

- 国内 React 招聘池比 Vue 略大(安全产品技术栈偏好)。
- shadcn/ui 是 React-only。
- 整个 longyuanai 6 个 Python 项目**没有前端代码**,不存在"和已有 Vue 仓对齐"的需求。

### 为什么不是纯 HTML + HTMX?

- 体量太小。Dashboard 6 屏 + 实时流 + 暗色 + 多视图,**HTMX 写起来反而更累**。
- 没有类型安全,Python 后端 ↔ 前端契约靠口头,违背 v0.5 §10 的精神。

---

## 我(Claude)的额外建议

派活指令写得已经够细,我只补 3 点:

### 1. TypeScript strict 必须开

`tsconfig.json` 显式:

```json
{
  "compilerOptions": {
    "strict": true,
    "noUncheckedIndexedAccess": true,
    "exactOptionalPropertyTypes": true
  }
}
```

`noUncheckedIndexedAccess` 会强迫处理 `findings[0]?.id` 这种 —— 与 Python 端 Pydantic 严校验对位。

### 2. SWR fallback 用 `fallbackData` 而不是 `revalidateOnMount`

派活 ISSUE 3 的 RSC 写法已经把首屏数据拉好,客户端 SWR 应避免重复 fetch:

```typescript
const { data } = useSWR("findings", () => listFindings({ limit: 50 }), {
  fallbackData: initialFindings,
  revalidateOnMount: false,
});
```

### 3. SSE 客户端要节流

每条 finding 都 `setCount(c => c + 1)` 会触发 React 渲染,高频时会卡。派活 ISSUE 4 应该加 `requestAnimationFrame` 合并:

```typescript
const queue = useRef<Finding[]>([]);
const [, force] = useReducer(x => x + 1, 0);

useEffect(() => {
  const es = new EventSource("/api/stream");
  es.addEventListener("finding", (e) => {
    queue.current.push(JSON.parse(e.data));
    requestAnimationFrame(() => {
      flush(queue.current.splice(0));
      force();
    });
  });
  return () => es.close();
}, []);
```

派活指令没写这一层 —— **Codex 实施时必须补**,否则生产环境会卡死。

---

## 验收硬约束(继承自 005-UI 派活)

| # | 约束 | 验证方法 |
|---|------|----------|
| 1 | 不修改任何产品目录(000~006) | `git diff` 验证 |
| 2 | 不修改 000shared-integration | `git diff` 验证 |
| 3 | 只通过 IntegrationGateway 取数据 | `grep -r "fetch.*localhost:80" src/` |
| 4 | dark mode 默认 | 截图 |
| 5 | 6 个产品 tab 都能路由 | Playwright |
| 6 | ≥ 5 个 Playwright E2E | `npx playwright test` |
| 7 | `npm run build` 通过 | CI |
| 8 | 5 个 ISSUE = 5 个 commit | `git log` |
| 9 | 集成层未就绪也能跑 | Playwright fixture |

---

## 给 Codex 写最终 ADR-001 的对照表

如果 Codex 同意本评审,**直接采纳**(本文件就是 ADR-001 草稿)。

如果 Codex 想反驳某条,在最终 ADR-001 里写:
- 反驳点(本文件某条)
- 替代方案
- 反驳理由

我会看你的反驳,不会机械执行派活指令。

---

## 决策记录

**评审日期**: 2026-07-25
**评审结果**: ✅ 维持 005 派活文档栈定调(Next.js 14 + Tailwind + shadcn/ui + SWR + Playwright),补 3 条建议(TS strict / SWR fallbackData / SSE 节流)
**Codex 采纳状态**: 待回