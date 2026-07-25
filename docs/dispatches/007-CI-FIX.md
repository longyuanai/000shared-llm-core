# 派活 007-CI-FIX · 修 Nit 1 workflow 路径布局

**周期**: v0.6 补丁(007-CI 收尾)
**作者**: Claude
**接收方**: Codex
**前置**: `000shared-llm-core/.github/workflows/inspect.yml` 已存在(007-CI-001/002/003 commit)
**期望 ISSUE 数**: 1
**期望 commit 数**: 1

---

## 0. 背景

007-CI 派活的 workflow 文件写在 `000shared-llm-core/.github/workflows/inspect.yml`,但 workflow 内部 6 个 pytest step 用的是:

```yaml
working-directory: 001AI-SOC-Agent
```

这是**兄弟目录**的假设。`actions/checkout@v4` 在 `000shared-llm-core` 仓里跑时,`github.workspace` = `000shared-llm-core/`,**没有** `001AI-SOC-Agent/`。真 GH Actions 跑会 `cd: 001AI-SOC-Agent: No such file or directory` → 6 worker step 全 fail。

Codex 自己在 `AUDIT/007-CI.md` 第 35-37 行承认了这点。

---

## 1. 目标(Goal)

- workflow 在 `000shared-llm-core` 仓单仓跑通,不需要兄弟目录
- 6 worker pytest step 的路径改成**绝对路径**(`${{ github.workspace }}/...`),去掉 `working-directory`
- `PYTHONPATH` 同步改成绝对路径
- inspect_worker_return.py 加载路径不变(还在 `${{ github.workspace }}/scripts/inspect_worker_return.py`,但实际是 `${{ github.workspace }}/../scripts/`)

---

## 2. 任务(Issues)

### Issue 007-CI-FIX-001 · workflow 单仓化

**位置**:`000shared-llm-core/.github/workflows/inspect.yml`(就这一个文件改)

**变更点**:

1. **去掉所有 `working-directory`**(6 个 pytest step + 1 个 inspect step),改用 `${{ github.workspace }}` 拼接
2. **`actions/checkout@v4`** 必须 checkout **父目录**,或者用 `submodules` 拉兄弟仓,但 mono 仓不是 submodule —— 必须换 checkout 方式
3. 实际**最简方案**:`actions/checkout` 改成 checkout 到 `${{ github.workspace }}/suite/`,然后 `${{ github.workspace }}/suite/000shared-llm-core/...` 是仓内容,`${{ github.workspace }}/suite/001AI-SOC-Agent/...` 是兄弟目录。但 GH Actions 默认 `${{ github.workspace }}` 是仓库根。

**改法**(Codex 二选一):

**方案 A · 推荐:把 6 worker 当成 6 个独立 job**

```yaml
jobs:
  inspect-001:
    runs-on: windows-latest
    steps:
      - uses: actions/checkout@v4
        with:
          repository: longyuanai/001AI-SOC-Agent  # 假设未来都推到 GH
          path: 001AI-SOC-Agent
      - uses: actions/setup-python@v5
        ...
      - run: |
          $py = (Get-Command python).Source
          & $py -m pytest tests/ `
            --basetemp=C:/pytest-tmp/001/ `
            -o addopts= `
            -q --tb=no
        env:
          PYTHONPATH: ${{ github.workspace }}/001AI-SOC-Agent/src
```

**方案 B · 用 `actions/checkout` 的 `path` 参数控制**

```yaml
- name: Check out suite
  uses: actions/checkout@v4
  with:
    path: suite/000shared-llm-core

- name: Check out 001 AI SOC
  uses: actions/checkout@v4
  with:
    repository: longyuanai/001AI-SOC-Agent
    path: suite/001AI-SOC-Agent
```

然后所有 step 用 `working-directory: suite/...`。

**方案 C · 用户 push 一个真正的 mono 仓**(这一步是**用户责任**,不是 Codex 的活)

**Codex 决策**:
- 当前 7 个仓各自独立 git,不在 GH 上(没 remote)。**方案 A/B 都依赖 GH remote**。
- 当前实现能做的:**至少在 workflow 里加注释 + 准备方案 A/B 模板**,让用户 push remote 后能用。
- 或者:**把 workflow 拆成 7 个文件**(每个仓根一个 `.github/workflows/inspect.yml`),各跑各的。**这是派活之外的事,留给后续派活**。

**Codex 必须做的(本 ISSUE 范围)**:

1. 在 `inspect.yml` 头部加注释,说明**当前布局 vs 期望布局**的差距
2. **加一个 job-level `env` 或 strategy matrix**,把 6 worker 的路径抽出来,避免重复
3. **actionlint 还过**
4. **不需要真 GH Actions 跑**(还是没 remote)

---

## 3. 测试(Tests)

- actionlint 通过(Codex AUDIT 自报)
- YAML parse 通过
- (后续用户 push remote 后)真 GH Actions 跑通 6 worker step

---

## 4. 验收(Acceptance)

- [ ] `inspect.yml` 头部加注释,说明 mono 仓布局假设
- [ ] 6 worker pytest step 路径抽到 `env` 或 matrix,避免 6 段重复
- [ ] actionlint 通过
- [ ] AUDIT/007-CI-audit.md 加一行说明本次补丁
- [ ] 1 commit

---

## 5. 约束(Constraints)

**禁止**:
- ❌ 删 6 worker pytest step(派活 007-CI 已绿)
- ❌ 改 inspect_worker_return.py 核心逻辑
- ❌ 假设 GH remote 存在(本地还没配)

**必须**:
- ✅ 改动局限在 `.github/workflows/inspect.yml` 一个文件
- ✅ commit message 以 `007-CI-FIX-001:` 开头
- ✅ 改动后 actionlint 通过

---

## 6. 回报格式

```
ID: 007-CI-FIX-001
Files changed:
  - .github/workflows/inspect.yml
Tests: actionlint 通过 / 本地 YAML parse 通过
CI smoke: (无法本地跑 GH Actions,留待 push remote 后验证)
Deviations: <与本派活的不一致>
Open questions: <需要 Claude 决策的模糊点>
```

---

## 7. 不要混淆

- 本派活**不**重写 inspect.yml,**只**路径抽象化 + 加注释
- 本派活**不**改派活 007-CI 的核心功能
- 真 GH Actions 跑通等用户 push remote 后再做

---

**最近修订**: 2026-07-25 · Claude
**下次回看触发**: 本 ISSUE 交付 / 用户 push remote 后真跑 GH Actions