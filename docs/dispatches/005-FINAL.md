# Codex 派活指令 · 005-FINAL · v1.0 e2e 集成 + Demo + 商业化文档

> **派活方**: Claude
> **接收方**: Codex
> **前提**: 005-INTEG ✅ done、005-UI ⏳ must done first、6 产品 v0.6(S4/S5)✅ done
> **优先级**: 🔴 Week 13(收尾,所有派活的终点)

---

## ⚠️ 开工前必读(8 个文件)

1. `E:\001项目\000开发\003AI+网络安全\000shared-integration\README.md`
2. `E:\001项目\000开发\003AI+网络安全\000shared-integration\docker-compose.yml`(待建)
3. `E:\001项目\000开发\003AI+网络安全\web-ui\README.md`(005-UI 完工后)
4. `E:\001项目\000开发\003AI+网络安全\000shared-llm-core\docs\v0.5-contract.md` 全 §
5. `E:\001项目\000开发\003AI+网络安全\README.md`(项目根)
6. `E:\001项目\000开发\003AI+网络安全\STAGES.md`
7. `E:\001项目\000开发\003AI+网络安全\AUDIT\EXPERIENCE.md`
8. `E:\001项目\000开发\003AI+网络安全\demo-report.md`(已有)

## ⚠️ Windows 踩坑经验

`AUDIT\EXPERIENCE.md` —— **4 个经验全适用**

---

## 工作目录

```
新建仓库:E:\001项目\000开发\003AI+网络安全\longyuanai-deploy
```

或直接放在 `000shared-integration/` 下新增 `deploy/` 子目录(与 INTEG worker 协商,推荐独立仓库)。

## 本 Stage 目标(3 个 ISSUE / 3 个 commit)

### ISSUE 1 · docker-compose 全栈编排(DEPLOY-001)

**目标**: 一个 `docker-compose up` 起来 7 个服务(000 不用,6 产品 + 集成 + web-ui)。

**任务**:
1. `longyuanai-deploy/docker-compose.yml`:
```yaml
version: "3.9"
services:
  shared-integration:
    build: ../000shared-integration
    ports: ["8080:8080"]
    environment:
      - SUITE_ROOT=/suite
  web-ui:
    build: ../web-ui
    ports: ["3000:3000"]
    environment:
      - NEXT_PUBLIC_GATEWAY_URL=http://shared-integration:8080
    depends_on: [shared-integration]
  001-soc, 002-vuln, 003-lab, 004-code, 005-reverse, 006-firmware: (各自 build + 共享 volume)
```
2. 每个产品目录加 `Dockerfile`(若还没有 — 001/002/003 已 done,004/005/006 已 done;若 INTEG 派活时未加,本 ISSUE 补)
3. `longyuanai-deploy/scripts/up.sh` + `down.sh`(Windows 用 .ps1 也行)
4. `.env.example`:所有 `*_API_KEY` 占位

**测试**(≥ 3 个):
- `test_compose_up.py::test_docker_compose_config_valid`(用 `docker compose config` 验证)
- `test_compose_up.py::test_all_7_services_listed`
- `test_compose_up.py::test_health_endpoint_accessible_after_up`(集成测试,标记 @pytest.mark.integration)

**验收**:
- `docker compose config` 无错
- `docker compose up -d` 成功,`docker compose ps` 7 个服务都 running
- `curl http://localhost:8080/v0.5/health` 返回 6 个 product ok
- 1 commit

### ISSUE 2 · e2e 真实场景剧本(E2E-001)

**目标**: 一个端到端剧本跑通 —— 从"扫描"到"告警"到"Dashboard 显示"。

**任务**:
1. `longyuanai-deploy/scenarios/01_brute_force_to_dashboard/`:
   - `run.py`:触发 `POST /v0.5/soc/scan` 注入 sshd 暴力破解事件
   - 触发 `POST /v0.5/vuln/scan` 注入对应 CVE
   - 触发 `POST /v0.5/code/scan` 扫描一段有 SQLi 的代码
   - 等待 SameHostMultiSourceRule 关联出告警
   - 验证 `GET /v0.5/correlations` 返回 1 条
   - 截图 `dashboard.png`(用 playwright headless 访问 `http://localhost:3000`)
2. `scenarios/02_firmware_cve_chain/`:
   - 上传一个含已知 CVE 的小固件 → `/v0.5/firmware/scan`
   - 触发关联
   - 验证 + 截图
3. `scenarios/03_prompt_injection_lab/`:
   - 跑一个 Lab 攻击 → 关联到 SOC 上(模拟)

**测试**(≥ 3 个):
- `test_scenarios.py::test_brute_force_e2e`(或直接 `python scenarios/01.../run.py`)
- 3 个 scenario 跑通各 1 次,产出 3 张截图
- 全部进 `tests/e2e/test_scenarios.py` 用 pytest 框架

**验收**:
- 3 个 scenario 跑通
- 3 张截图存在 `docs/screenshots/`
- 1 commit

### ISSUE 3 · 商业化文档 + Demo 视频脚本(DOC-001)

**目标**: 让用户 5 分钟看懂 longyuanai 是什么、解决什么问题、怎么用。

**任务**:
1. `longyuanai-deploy/README.md`:项目总览(架构图 ASCII + 一句话定位)
2. `longyuanai-deploy/docs/QUICKSTART.md`:5 分钟上手(docker compose up → 截图)
3. `longyuanai-deploy/docs/USE-CASES.md`:3 个 use case(中英文):
   - SOC 团队:实时攻击检测 + 跨产品关联
   - 渗透测试:扫描 + 利用链分析
   - 代码审计:CI 集成 + 自动修复建议
4. `longyuanai-deploy/docs/DEMO-SCRIPT.md`:3 分钟 Demo 视频脚本(分镜 + 旁白 + 截图列表)
5. `longyuanai-deploy/docs/BUSINESS.md`:商业模式 + 目标客户 + 定价(草稿)
6. `longyuanai-deploy/docs/FAQ.md`:10 个常见问题

**验收**:
- 6 个文档齐全,中英双语
- ASCII 架构图(可用 mermaid 或 dot)
- 链接到 3 张 screenshot
- 1 commit

---

## 约束

- 不修改任何产品目录(000~006)+ 000shared-integration + web-ui(只读依赖)
- 所有命令 Windows 兼容(.ps1 脚本优先,或同时给 .sh + .ps1)
- pytest 三件套
- 不装新依赖(docker compose 是宿主命令,不进 Python venv)
- **不要**碰 GitHub Actions(各产品已有)

---

## 回报

```
1. 3 个 commit hash
2. docker compose config 输出(无错)
3. 3 个 scenario run.py 输出片段
4. 3 张截图路径
5. 6 个文档路径
6. 进入 v1.0 商业化的建议
```

## 最终验证清单(交付前)

- [ ] `docker compose up -d` → 7 服务全 running
- [ ] `curl localhost:8080/v0.5/health` → 6 ok
- [ ] `curl localhost:3000` → Dashboard 可访问
- [ ] 3 scenarios 跑通
- [ ] 6 文档齐全
- [ ] 没有 pytest 测试失败

---

## 预计工时

**5-7 天**(docker 学习曲线 + 3 scenario + 6 文档)

## 商业化 checklist(本 Stage 完成后)

- [ ] Docker 镜像推到 Docker Hub(`longyuanai/*` namespace)
- [ ] 项目录个 3 分钟 Demo 视频(可选,worker 自己录或老板录)
- [ ] 写 GitHub README(英文版商业化包装)
- [ ] 商业化路演 PPT 草稿(老板来写,worker 提供素材)