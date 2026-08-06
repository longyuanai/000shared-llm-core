# ADR-002 · 套件仓库布局与 shared core 路径依赖

**状态**: 提议（以九仓 `suite-ci` 首次成功为接受门槛；当前受 GitHub Actions
平台事故阻塞）
**日期**: 2026-08-07
**决策方**: longyuanai 技术负责人
**关联文件**: `suite-lock.yml`、`.github/workflows/inspect.yml`

---

## 背景

longyuanai 的七个 Python 仓库通过 Poetry 可编辑路径依赖引用
`000shared-llm-core`。标准 fresh clone 与 GitHub Actions 都把各仓库检出为同一
目录下的兄弟目录，因此产品仓内统一使用：

```toml
shared-llm-core = { path = "../000shared-llm-core", develop = true }
```

004 的现有本机工作副本是历史包装布局：真正的 Git 仓根位于
`004AI-Code-Audit/004AI-CodeGuard-upgrade`，外层 `004AI-Code-Audit` 不是可用的
Git 仓库。若为适配该机器把依赖写成 `../../000shared-llm-core`，标准 fresh clone
和 CI 中的路径就会指向错误位置。

此外，pytest 从 core 仓根对其他仓库执行绝对测试路径时，004 的根级
`benchmarks` 包不会出现在导入路径中。测试命令的调用目录因此也是套件契约的一部分。

## 决定

1. `suite-lock.yml` 中的 `repositories[].path` 定义套件的标准检出布局。所有仓库在
   同一 suite 根目录下以兄弟目录存在；不得把某一产品的本机包装目录写入跨仓契约。
2. 七个 Python 产品统一以 `../000shared-llm-core` 引用 shared core。本机若采用非标准
   嵌套布局，应重新按标准布局检出，或使用仅存在于本机的目录 junction 兼容；不得因此
   提交另一层级的相对路径。
3. `suite-ci` 必须从每个仓库自己的根目录运行其测试，同时为每个仓库使用独立的
   `--basetemp`。测试可发现性不得依赖 core 仓库的当前工作目录。
4. `suite-ci` 安装七个产品并让路径依赖拉入 core，不再同时显式安装 core，避免 pip
   把同一项目识别为可编辑引用和直接文件引用两份候选。
5. 不引入按操作系统切换路径、环境变量插值或多套 `pyproject.toml`。这些方案会使锁定
   SHA 无法同时锁定安装拓扑。
6. 长期目标是把 shared core 发布到受控私有包源并以版本范围依赖；该迁移需要先定义
   版本策略、发布认证、回滚和离线开发方案，另立阶段实施，不纳入 M2.1 收尾。

## 方案比较

| 方案 | 结果 | 结论 |
|---|---|---|
| 标准兄弟目录 + 统一相对路径 | fresh clone、CI 和锁文件使用同一拓扑 | 采用 |
| 为 004 保留 `../../` | 只适配当前机器，标准 clone 失效 | 拒绝 |
| CI 临时重写 `pyproject.toml` | 被测试代码不同于锁定提交 | 拒绝 |
| M2.1 立即发布 core 包 | 可消除路径依赖，但扩大版本与凭据范围 | 延后 |

## 本机 004 迁移

首选做法是在新的 suite 根目录按 `suite-lock.yml` 重新检出全部仓库。迁移当前历史包装层
之前，允许建立以下仅本机 junction：

```text
004AI-Code-Audit/
├── 004AI-CodeGuard-upgrade/   # 当前 004 Git 仓根
└── 000shared-llm-core/        # junction -> 套件 shared core
```

这样内层仓库的 `../000shared-llm-core` 可以解析，同时不改变 Git 历史。junction 不进入
任何仓库，不属于发布产物；完成标准布局迁移后应移除。

## 影响

- 新机器和 CI 只需复现 `suite-lock.yml` 的平级目录即可安装全部 Python 项目。
- 004 当前本机目录仍可工作，但其包装层被明确标为兼容状态，不再影响仓库契约。
- 各仓测试必须能从自身仓根执行；依赖调用方 cwd 的测试属于缺陷。
- shared core 在发布为版本化包前仍是源码级耦合，跨仓提交必须继续由锁文件固定 SHA。

## 接受条件

- `suite-ci` 在 Ubuntu / Python 3.12 上检出并验证锁定的九个仓库。
- core、IntegrationGateway、001–006 的测试都从各自仓根通过。
- 004 从标准 flat checkout 成功安装，且根级 `benchmarks` 可在测试中导入。
- web-ui 保持独立 Node 22 工作流，不被 Python 路径依赖决策影响。
- 当前 004 本机仓不产生新的 tracked 或 staged 变更。

## 验证记录

- 004 锁定提交：`e500dab917ee0fe9b4c1dbbb725ba7a86c7d82b2`
- IntegrationGateway 锁定提交：`d35ea7ac676a7356ed3e545756687c5af82e2e94`
- suite-ci 候选：包含上述锁定 SHA 的当前 core 分支 head
- Run `31120786639` 已证明九仓 checkout、锁校验、安装以及 core 至 003 的测试
  通过，并发现 004 的 CPython ABI 测试夹具缺陷。
- Run `31121452216` attempt 1 在 GitHub `Set up job` 阶段、任何 checkout 之前因
  官方 Actions major outage 失败。Attempt 2 完成全部 checkout、锁校验、安装，
  再次通过 core 至 003，并使 004 达到 175 passed / 2 failed；剩余失败来自 E2E
  对本机嵌套目录层级的固定假设。
- 锁定的 `e500dab` 已改为从祖先目录发现 suite 根；本机 004 全量 177 tests 通过。
  新锁定 run 成功后将本 ADR 状态改为“接受”。
