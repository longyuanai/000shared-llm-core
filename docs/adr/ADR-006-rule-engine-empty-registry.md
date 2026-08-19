# ADR-006：`RuleEngine` 尊重显式传入的空 `RuleRegistry`

- **状态**：已接受（2026-08-17）
- **决策层**：用户
- **影响契约**：[`v0.5-contract.md`](../v0.5-contract.md) §8.5（冻结区，本 ADR 同步其文本）
- **相关**：[`ADR-002`](ADR-002-suite-repository-layout.md)、[`docs/versioning.md`](../versioning.md)
- **触发**：012/014 审计期间发现 core 工作区存在未授权的冻结组件改动，
  记录于 `docs/current-status.md` §4 P0.0；决策层审阅后认可，要求补本 ADR 并同步契约。

## 1. 背景

`RuleEngine` 是 `v0.5-contract.md` §8 冻结的四个核心组件之一，被 7 个仓消费。
契约 §8.5 原文写的构造行为是：

```python
def __init__(self, registry: RuleRegistry | None = None) -> None:
    self.registry = registry or RuleRegistry.default()
```

`RuleRegistry` 定义了 `__len__`，因此**空注册表是 falsy**。`or` 把两种语义不同的情况
合并成了一种：

| 调用 | 意图 | `or` 版实际行为 |
|---|---|---|
| `RuleEngine()` | "给我默认规则" | 加载内置规则 ✅ |
| `RuleEngine(RuleRegistry())` | "只跑我注册的规则，现在一条都没有" | **静默加载全部内置规则** ❌ |

第二行是**fail-open**：调用方以为自己精确控制了规则集，引擎却擅自塞进内置规则并产出
Finding。在一个安全产品里，"我明确说了不跑"被解释成"跑全部"是错误的方向 ——
宁可漏报也不该无声地扩大扫描面并把结果算到调用方头上。

## 2. 决策

`RuleEngine.__init__` 改为区分"未提供"与"提供了空表"：

```python
def __init__(self, registry: RuleRegistry | None = None) -> None:
    self._registry = registry if registry is not None else RuleRegistry.default()

@property
def registry(self) -> RuleRegistry:
    return self._registry
```

- 只有 `registry is None`（含不传）才回退到 `RuleRegistry.default()`
- 显式传入的 `RuleRegistry` 一律原样持有，**包括空表**

契约 §8.5 同步为上述文本。

### 2.1 顺带修正一处既有文档漂移

同步时发现契约 §8.5 写的是公开可变属性 `self.registry`，而实现**早已**是私有
`self._registry` + 只读 `@property registry`。这处漂移**不是本次改动引入的**，
但既然要同步契约，一并改为与实现一致：`registry` 是只读属性，不可赋值。

已检索全套件：无任何消费方对 `RuleEngine(...).registry` 做赋值
（`000shared-integration` 与 `003` 中的同名 `.registry =` 属它们自己的类，与本组件无关）。

## 3. 兼容性、迁移与回滚

**兼容性**：

- `__init__` 的**可调用参数未变**，`RuleEngine()` 与 `RuleEngine(非空 registry)` 行为逐字不变
- 唯一行为变化限于 `RuleEngine(空 registry)` 这一种调用
- 全套件检索未发现任何一处依赖"传空表却期待拿到内置规则"的调用

C1 同时包含派活已认可的 typing 现代化：字符串前向引用改为普通 postponed annotation，
`typing.Mapping/Sequence` 改为 `collections.abc` 版本。它不改变调用方式或上述运行时语义，
但原始 `__annotations__` / `inspect.signature()` 的字符串表示不是逐字兼容；依赖这种原始
typing metadata 的调用方应改用 `typing.get_type_hints()`，本套件未发现此类消费方。

**迁移**：调用方无需改动。若确有代码依赖旧的 fail-open 行为，显式改写为
`RuleEngine(RuleRegistry.default())` 即可拿回原语义。

**回滚**：把 `registry if registry is not None else` 改回 `registry or`，
并删除 `tests/test_rule_engine.py::test_rule_engine_registry_property`。
回滚不涉及数据迁移，也不影响 `suite-lock.yml`。

## 4. 为什么不升版本号

[`docs/versioning.md`](../versioning.md) 有两条规则在此相遇：

1. "core 的包版本等于它实现的最高契约版本" —— 当前是 v0.6 §15，故 `0.6.0`
2. "core 的**对外签名**发生变化前……至少提升次版本号"

本次**可调用参数未变**，变的是同一契约版本内一个边界情形的行为，且是把未定义/易误用的行为
收敛到唯一合理解释。因此按规则 1 保持 `0.6.0`，不升次版本号 ——
升版本会同时违反规则 1 并打掉 `tests/test_versioning.py` 里
`__version__ == "0.6.0"` 的硬断言。

本 ADR 即规则 2 要求的"先写 ADR"。**未来任何真正改变 `__all__` 中符号签名的改动，
仍必须升次版本号。**

## 5. 跨仓核验

`003AI Agent安全靶场/src/ai_agent_lab/v05_compat.py:276` 存在相同语法：

```python
self.registry = registry or RuleRegistry.default()
```

它是 003 自己的 v0.5 兼容层，但其 `RuleRegistry` 没有实现 `__len__` 或 `__bool__`，
所以空实例仍为 truthy，当前写法会保留传入实例，**不复现 core 的空表吞没缺陷**。
003 的 HEAD 被 `suite-lock.yml` 锁在 `3862acf`，且该仓有决策层保护的未提交修改；本 ADR
不修改它，也不为这处仅语法相同的代码创建待办。
