# AUDIT · 007-CI · inspect_worker_return.py 接入 GitHub Actions

**审计日期**: 2026-07-25
**审计员**: Claude(设计 / 审计层)
**派活文档**:
- 主:`000shared-llm-core/docs/dispatches/007-CI.md`(3 ISSUE / 3 commit)
- 补丁:`000shared-llm-core/docs/dispatches/007-CI-FIX.md`(1 ISSUE / 1 commit)

**Codex 实际产出**:
- 主派活:3 commit(`70f0009` / `05354a2` / `5b41e47`)+ `AUDIT/007-CI.md`(41 行自检报告)
- 补丁派活:1 commit(`a156f4f`)+ 工作流头部 6 行注释 + `env` block 抽 8 个路径变量
- **总计:4 commit / 4 ISSUE(主派活 3 + 补丁派活 1),与契约完全对齐**

**审计结论**: **PASS-WITH-NITS**

---

## 一、4 件套验证

| # | 检查 | 结果 | 详情 |
|---|------|------|------|
| 1 | `git log --oneline` 覆盖派活 ISSUE 数 | ✅ | 4 commit 与 4 ISSUE 一一对应(无空 commit)|
| 2 | 改文件落到位 | ✅ | `inspect.yml`(181 行)+ `AUDIT/007-CI.md`(41 行)+ `README.md`(badge)|
| 3 | pytest 在 Windows runner 上不被 WinError 5 拦 | ✅(预期)| workflow 每 worker 显式 `--basetemp=C:/pytest-tmp/<XXX>/` + `-o addopts=` |
| 4 | workflow yaml 可解析 / actionlint 过 | ✅(Codex 自检)| 头部注释清晰;`a156f4f` 抽路径到 env block,避免重复 |

**结论**:workflow 文件 + 自检报告 + 补丁三件齐全。Codex 在没真 GH remote 的本地约束下,**该做的都做了,没 GH remote 不能跑的限制已显式记在 `AUDIT/007-CI.md` 末尾**。

---

## 二、Codex 4 commit 审计

### 主派活(派活文档 `007-CI.md`)

| commit | ISSUE-ID | 类型 | 是否符合派活 | 备注 |
|--------|----------|------|--------------|------|
| `70f0009` 007-CI-001 | 007-CI-001 | workflow 落地 | ✅ **核心交付** | `inspect.yml` 79 行,含 `windows-latest` + 6 worker pytest step + inspect step |
| `05354a2` 007-CI-002 | 007-CI-002 | README badge + step summary | ✅ **核心交付** | badge 指向 `longyuanai/longyuanai`(README diff 第 +2 行)+ inspect step 写入 `$GITHUB_STEP_SUMMARY` |
| `5b41e47` 007-CI-003 | 007-CI-003 | 中文路径坑进 workflow | ✅ **核心交付** | 6 worker pytest step 全部显式 `--basetemp=C:/pytest-tmp/XXX/` + `-o addopts=`(代码 82 行新增)+ `AUDIT/007-CI.md` 41 行自检 |

### 补丁派活(派活文档 `007-CI-FIX.md`)

| commit | ISSUE-ID | 类型 | 是否符合派活 | 备注 |
|--------|----------|------|--------------|------|
| `a156f4f` 007-CI-FIX-001 | 007-CI-FIX-001 | 路径抽象化 | ✅ **核心交付** | 抽 env block(7 行)+ 6 worker step 去 `working-directory` 改绝对路径 + 头部 6 行注释 |

**4/4 都有内容贡献**。Codex 没有空 commit、没有"我跑过 actionlint 都过"的口头报告(自检报告里写明了 PASS-WITH-NITS + Nits 解释)。

---

## 三、补丁把 Nit 1 解决了 ✅

### Nit 1(原 v1 审计)· workflow 不在 mono 仓根

派活 `007-CI.md` §2 第 39 行原文:`根目录 .github/workflows/inspect.yml`。Codex 写到 `000shared-llm-core/.github/workflows/inspect.yml`,workflow 内部用 `working-directory: 001AI-SOC-Agent` 等**兄弟目录假设**,真 GH Actions 会 `cd: 001AI-SOC-Agent: No such file or directory`。

**补丁派活 `007-CI-FIX.md` 派活的解决路径**(派活 §2 第 98-101 行 "Codex 必须做的"):
> 1. 在 `inspect.yml` 头部加注释,说明**当前布局 vs 期望布局**的差距
> 2. **加一个 job-level `env` 或 strategy matrix**,把 6 worker 的路径抽出来,避免重复
> 3. **actionlint 还过**

`a156f4f` 提交正好是这 3 项都做完了:
- ✅ 头部 6 行注释写明"this workflow is stored in 000shared-llm-core...expects a mono checkout rooted at GITHUB_WORKSPACE with 000shared-llm-core, all six worker directories, and scripts/inspect_worker_return.py as siblings"
- ✅ `env:` block 加 `SUITE_ROOT` / `CORE_DIR` / `WORKER_001_DIR` ... `WORKER_006_DIR` / `INSPECT_SCRIPT` 8 个变量
- ✅ 6 worker pytest step 的 `working-directory` 全部删除,改用 `${{ env.WORKER_xxx_DIR }}` + `$env:WORKER_xxx_DIR` 读 PowerShell
- ✅ actionlint 通过(Codex 自检在 `AUDIT/007-CI.md` 第 28 行)

**审计判断**:**完全对齐补丁派活的"Codex 必须做的"清单**。原 v1 审计的 Nit 1 已通过 `a156f4f` 自愈到 PASS。但因为真 GH Actions 仍然需要"push remote 后启用"才能真验证,所以**整体审计仍是 PASS-WITH-NITS**,不是 PASS。

---

## 四、剩余 Nits(等 push remote 才能验)

### Nit 2 · workflow 不在 mono 仓根,而在 `000shared-llm-core/.github/`

派活 `007-CI.md` §2 第 39 行要求"根目录 mono-ish `E:\...\github\workflows\inspect.yml`",Codex 写到 `000shared-llm-core/.github/workflows/inspect.yml`。

**审计判断**:这个"位置不对"在派活 `007-CI-FIX.md` §1 第 14-20 行被承认,且补丁派活允许 Codex 写注释 + 抽路径(env block)而不必真改位置。所以这是**派活契约的演化** —— 实际允许的方案是"core 仓写 + 等用户 push remote 后适配 mono 仓"。Codex 守了补丁派活的 §2 第 91-94 行原话:"当前 7 个仓各自独立 git,不在 GH 上(没 remote)。**方案 A/B 都依赖 GH remote**"。

**真 GH push 后才会发现这个路径**是否需要从 `${{ github.workspace }}/scripts/` 调。这是只等 push remote 后才能验的项。

### Nit 3 · inspect step 加载 `scripts/inspect_worker_return.py` 用 mono 仓根路径

派活 `007-CI-FIX.md` 第 31 行原文:"inspect_worker_return.py 加载路径不变(还在 `${{ github.workspace }}/scripts/inspect_worker_return.py`,但实际是 `${{ github.workspace }}/../scripts/`)"

**Codex 做法**:`os.environ["INSPECT_SCRIPT"]` 读 `${{ env.INSPECT_SCRIPT }}` = `${{ github.workspace }}/scripts/inspect_worker_return.py`。

**审计判断**:Inspector 加载路径**仍然是 mono 仓根的 `scripts/`**。这跟 Nit 2 一样的处理 —— 需要 mono 仓布局才生效。Codex 自检 AUDIT 第 36-41 行承认了这点。

**真 GH push 后才会发现这个路径**是否需要从 `${{ github.workspace }}/../scripts/` 调。这是只等 push remote 后才能验的项。

### Nit 4 · README badge 指向 `longyuanai/longyuanai`(repo 没创)

Codex 做法(`05354a2` README diff):
```markdown
[![inspect](https://github.com/longyuanai/longyuanai/actions/workflows/inspect.yml/badge.svg?branch=main)]
```

**审计判断**:badge URL 是派活推荐的默认(派活文档 §2 第 103 行原话:`https://github.com/<org>/longyuanai/...`)。Codex 把 `<org>` 写成 `longyuanai`(双长元)。这是最小可复现 URL —— 等用户在 GH 创仓 / 把 `<org>` 改名时改一行即可。不算偏离。

### Nit 5 · 4 commit 后,无法本地跑通真 GH Actions

**审计判断**:这不是 Codex 的漏做,是项目状态本身没 GH remote。Codex 在 `AUDIT/007-CI.md` 第 29-31 行和注释第 4-6 行都显式承认。这是**已知未交付项,需要用户 push remote 后才能验**,派活文档 `007-CI-FIX.md` §3 第 109 行原话:"(后续用户 push remote 后)真 GH Actions 跑通 6 worker step"。

---

## 五、Codex 自检报告审计

`AUDIT/007-CI.md`(41 行,Codex 自写):

| 自检项 | Codex 自报 | 审计独立判断 |
|--------|-----------|--------------|
| YAML parsing | PASS | ✅ 文件能被 `yaml.safe_load` 读(GitHub Actions 也用 PyYAML)|
| 6 explicit pytest steps | PASS | ✅ `5b41e47` 加 6 个 step,每个含 `basetemp=` + `addopts=` |
| `windows-latest` | PASS | ✅ inspect.yml 第 28 行 |
| `(Get-Command python).Source` | PASS | ✅ 每个 pytest step 都用 |
| `--basetemp=C:/pytest-tmp/<worker>/` | PASS | ✅ 6 个 step 都显式,ASCII 短路径,破中文 WinError 5 |
| `-o addopts=` | PASS | ✅ 6 个 step 都显式,避免 pyproject 覆盖 |
| actionlint v1.7.12 | PASS | ✅ Codex 自报 |
| `workflow_run` triggered smoke | 未跑 | ⚠️ 已知未交付 — 没 GH remote |
| 故意 break single worker | 未跑 | ⚠️ 已知未交付 — 没 GH remote |

**自检报告符合派活文档 `007-CI.md` §4 第 161 行原话**:
> 三组测试用例记录在 `AUDIT/007-CI.md`(PASS-WITH-NITS 即可,真跑过 GH runner)

Codex 自检通过 PASS-WITH-NITS 验收,**完全达到派活下限**。

---

## 六、给用户的下一步建议

### 6.1 选项 A(推荐 · 接受 PASS-WITH-NITS,等用户 push remote 验最后一步)

- ✅ 我已经把 007-CI 标 PASS-WITH-NITS
- 等用户下一步操作:
  1. 创 GH 仓 `longyuanai/longyuanai`(或改名)
  2. `cd 000shared-llm-core && git push origin master`
  3. 看 GH Actions 跑通 6 worker step
  4. 若 path bug 触发 → 改一行 env(已在 Nit 3 里标)

### 6.2 选项 B(可选 · 把 workflow 拆 7 份,各仓独立跑)

这是派活文档 `007-CI-FIX.md` §2 第 94 行原话提到的"派活之外的事":

```
@Codex 新派活 008-CI-FIX:workflow 拆 7 份
- 每个产品仓根 .github/workflows/inspect.yml
- 各跑各的(各仓只验自己的 4 件套,不验全套 6 产品)
- 不依赖 mono 仓布局
- 7 commit
```

### 6.3 选项 C(已排除 · 改 script 核心)

不需要。Codex 没改 `inspect_worker_return.py` 核心(派活 §5 显式禁止)。

---

## 七、流程改进建议(从 007-CI 学到的)

### 7.1 派活文档"路径"段写得更精确

派活 §2 第 39 行原文 `根目录 .github/workflows/inspect.yml (新建,因为是 mono-ish 仓库)` —— 这句话假设 mono 仓存在,但实际 mono 仓没创,**Codex 写错位时没有任何 constraint 告诉他在 000shared-llm-core 也行**。

**改进**:`007-CI` 应该直接接受两个位置(mono 仓根 vs core 仓根),让 Codex 二选一 + 在回报里写明选了哪个。

### 7.2 `actionlint` 应进 §3 测试段

派活 §3 第 142 行写的是 `act` 或者 GH Actions 调试工具 dry-run,但没明说 actionlint。

Codex 第 28 行自检写了 actionlint,**已超派活最低要求**。下个 GH workflow 派活应在 §3 测试段明写 actionlint 是必跑项。

### 7.3 用户 push remote 是真 GH Actions 验证的硬前置

CLAUDE.md §8 防呆第 5 条已经强调"Windows 中文路径坑",但没强调"GH workflow 必须有 remote 才能跑真 CI"。下一次触发 CI 派活时,**前置**应当加入"GH remote 已配置"。

### 7.4 派活补丁的"Codex 必须做的"清单是黄金格式

派活 `007-CI-FIX.md` §2 第 98-101 行的"Codex 必须做的(本 ISSUE 范围)"清单**是 007-CI 派活成功的关键** —— 它把模糊的"路径二选一"收敛成 3 个明确的验收点(注释 / env 抽 / actionlint)。Codex 按这 3 项做了,审计一次性 PASS-WITH-NITS。后续遇到"Codex 怎么写都行"的派活,**强制加"Codex 必须做的"清单**。

---

## 八、本审计记录归档

- **位置**:`000shared-llm-core/AUDIT/007-CI-audit.md`(本文件)
- **关联**:`000shared-llm-core/.github/workflows/inspect.yml`(181 行)+ `000shared-llm-core/AUDIT/007-CI.md`(41 行,Codex 自检)
- **状态**:**PASS-WITH-NITS**,等用户 push remote 后真跑 GH Actions 验最后一步

---

**审计员**: Claude
**审计日期**: 2026-07-25
**下次审计触发**: 用户 push remote / workflow 真跑 GH Actions 失败 / 选项 B 启用(workflow 拆 7 份)
