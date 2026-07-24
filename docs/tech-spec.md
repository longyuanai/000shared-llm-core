# 000 shared-llm-core · 技术方案

## 1. 业务问题

7 个 AI 安全产品（001-006）都要调 LLM（OpenAI / Anthropic / vLLM）。如果每个产品都自己接 API、自己管 prompt 模板、自己写审计日志，会带来：

- 重复代码 7 份
- 模型切换要改 7 处
- 审计格式不统一，合规难过
- Prompt 散在各处，无法版本化管理

需要一个**共享内核**作为 7 个产品统一的 LLM 网关。

## 2. 产品定位

`shared-llm-core` 是 **6 个 AI 安全产品的共享 Python 包**，提供：

| 模块 | 作用 |
|------|------|
| `LLMClient` | OpenAI 兼容协议的单 provider 客户端 |
| `LLMRouter` | 按 `TaskTier` 路由到不同 provider + model |
| `AuditLog` | 每次调用写 JSONL 审计 |
| `TemplateRegistry` | 版本化的 YAML prompt 模板 |

**不是产品**，没有 CLI、没有 UI——只供其他 6 个产品 `import`。

## 3. 关键能力（MoSCoW）

| 优先级 | 能力 | 说明 |
|--------|------|------|
| Must | OpenAI 兼容协议 | 单一协议覆盖 vLLM / OpenAI / Anthropic(经代理) |
| Must | Tier 路由 | CHEAP / STANDARD / PREMIUM / LOCAL 4 档 |
| Must | JSONL 审计 | 含 request_id / latency / tokens |
| Must | 版本化 prompt 模板 | YAML 文件 + Jinja2 渲染 |
| Must | 重试机制 | tenacity: 3 次指数退避 |
| Should | 流式响应 | `stream()` 方法 |
| Should | 环境变量插值 | `${OPENAI_API_KEY}` |
| Should | 多 provider 配置 | YAML 同时配 local + remote |
| Could | 自动审计 rotate | v0.5 |
| Could | Anthropic native API | v0.5 |
| Won't | 多模态 / Batch API | v1.0+ |

## 4. 总体架构

```
┌──────────────────────────────────────────┐
│  6 个产品 (001-006)                       │
└──────────────┬───────────────────────────┘
               │ import
               ▼
┌──────────────────────────────────────────┐
│  shared-llm-core                          │
│  ┌──────────┐  ┌──────────┐  ┌────────┐ │
│  │ ChatReq  │  │ Router   │  │ Audit  │ │
│  │ Client   │  │ Tier→P+M │  │ JSONL  │ │
│  └──────────┘  └──────────┘  └────────┘ │
│  ┌──────────┐                             │
│  │Templates │                             │
│  │ Versioned│                             │
│  └──────────┘                             │
└──────────────┬───────────────────────────┘
               │
               ▼
       ┌──────────────┐
       │ vLLM / Claude │
       └──────────────┘
```

## 5. 模块设计

### 5.1 `LLMClient` (client.py)

```python
@dataclass
class LLMClient:
    provider: ProviderConfig
    _http: httpx.Client
    def chat(self, req: ChatRequest) -> ChatResponse: ...   # 自动重试 3 次
    def stream(self, req: ChatRequest) -> Iterator[str]: ...
```

### 5.2 `LLMRouter` (router.py)

```python
class TaskTier(str, Enum):
    CHEAP    = "cheap"
    STANDARD = "standard"
    PREMIUM  = "premium"
    LOCAL    = "local"

class LLMRouter:
    @classmethod
    def from_env(cls, rules=None, yaml_path=None) -> "LLMRouter": ...
    def chat(self, tier: TaskTier, req: ChatRequest) -> ChatResponse: ...
```

### 5.3 `AuditLog` (audit.py)

```python
@dataclass
class AuditLog:
    cfg: AuditConfig
    def record(self, *, request, response, provider, latency_ms) -> None: ...
```

每次 `router.chat()` 自动写一条 `AuditRecord` 到 JSONL。

### 5.4 `TemplateRegistry` (templates.py)

```
prompts/
└── <name>/
    ├── 1.0.0.yml
    ├── 1.1.0.yml
    └── 2.0.0.yml
```

`registry.get(name, "latest")` 取字典序最大。

## 6. 数据与模型

无业务数据存储。LLM 调用通过外部 provider。

## 7. 安全与合规

- API key 仅在 YAML / 环境变量,不进代码
- 审计日志含完整 request / response,供合规回溯
- 重试机制不会泄露 token（httpx 默认脱敏）

## 8. 部署

作为 Python 包被 6 个产品通过 poetry `path =` 依赖。

## 9. 评估指标

| 指标 | 目标 |
|------|------|
| 测试覆盖率 | ≥ 90% |
| 重试成功率 | ≥ 99% (瞬时错误) |
| 审计日志完整率 | 100% |

## 10. 路线图

| 阶段 | 内容 |
|------|------|
| **v0.1 (当前)** | 24/24 测试通过,接口冻结 |
| **v0.5** | 流式重试 + Anthropic native + 日志 rotate |
| **v1.0** | 多模态 + Batch API + 多租户 |

## 11. 接口契约

见 `docs/v0.1-contract.md`（已冻结,不可改）。

## 12. 风险

- **OpenAI 协议差异**: Anthropic 不原生支持 → 必须用代理
- **审计日志膨胀**: 无 rotate → 外部工具负责
- **流式响应不重试**: 半成品无意义

## 13. 关键文件

- `src/shared_llm_core/client.py` — ChatRequest/Response schema
- `src/shared_llm_core/router.py` — TaskTier 路由
- `src/shared_llm_core/audit.py` — JSONL 审计
- `src/shared_llm_core/templates.py` — YAML 模板
- `docs/v0.1-contract.md` — 接口契约（必读）