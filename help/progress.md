# 开发进度记录

> 记录"做了什么、到哪一步了"。每次开发前后花 2 分钟更新。  
> 配套文件：`problem.md`（记录遇到的问题）、`../doc/project-plan-v0.md`（总方案）

---

## 🎯 总体里程碑

- [ ] **M0 前置验证**（4/24-4/25）：4 项技术通路验证
- [ ] **M1 Phase 1 保底 MVP**（4/26-4/30）：知识整合 + 精准问答 + Bot 通道
- [ ] **M2 Phase 2 核心亮点**（5/1-5/3）：变更感知 + 定向分发
- [ ] **M3 Phase 3 加分**（5/4-5/6）：精细影响分析 + 评测
- [ ] **M4 提交**（5/7）：Demo 视频 + 项目介绍 + 填问卷

## 最新校准（2026-04-25）

### 赛题判断

- ✅ 方向没有偏：当前“飞书知识整合 + 基于证据问答 + 文档变更感知 + 定向分发”贴合 `doc/subject.txt` 中“不仅能精准问答，更能主动分发与推送”的要求。
- ✅ 核心链路已具备真实飞书演示形态：用户已可在飞书私聊 / 群聊中提问并收到 bot 回复，文档变更后也可由 bot 主动推送。
- ✅ “飞书原生体验”主链路已补齐，下一步重点转向案例、评测与录屏材料。
- ✅ OpenClaw 继续作为可选 HTTP Skill / 订阅入口，不作为主链路阻塞项。

### 当前已验证

- ✅ 个人 Wiki 文档 `权限变更公告 Demo` 已完成抓取、检索、问答验证。
- ✅ 文档修改后，`scripts/run_distribution_demo.py` 检测到 `changed=1`。
- ✅ 已生成变更摘要、关键变化点、目标列表和 dry-run 飞书发送命令。
- ✅ 飞书 Bot 问答闭环已真实跑通：私聊与群聊 `@Bot` 均可触发 `im.message.receive_v1` -> `AnswerService` -> bot 回复。
- ✅ 真实主动推送已验证：`scripts/run_distribution_demo.py --watch --send` 已将 `权限变更公告 Demo` 的变更主动推送到测试群。

### 当前关键缺口

- ⚠️ 需要准备 2-3 个稳定可复现的场景案例，否则目前仍偏单点 demo。
- ⚠️ 需要补最小效果验证报告，证明“回答准确 + 主动推送提升信息流转效率”。
- ⚠️ 需要整理录屏脚本、README 和提交材料，完成比赛交付收口。

### 下一步优先级

1. **P2：演示与评测材料**
   - 准备权限变更、项目计划、产品发布 3 个案例。
   - 补最小效果验证：问答准确性、变更摘要准确性、人工查找 vs Agent 推送耗时对比。
   - 同步 README / roadmap / progress / evaluation report。
2. **P3：录屏与交付收口**
   - 固化“飞书里提问 -> Bot 回复 -> 修改文档 -> Bot 主动推送”的录屏脚本。
   - 准备演示讲解口径，突出差异化亮点。
   - 收口比赛提交材料。

---

## M0 前置验证（当前阶段）

### 比赛硬指标（今天必做）

| 任务                                   | 状态 | 备注                        |
| -------------------------------------- | ---- | --------------------------- |
| 认领 EP 接入点（Doubao 2.0 Pro）       | ⏳   |                             |
| 创建 GitHub 仓库（public）+ 填问卷     | ⚠️   | 仓库已创建并 push，问卷待填 |
| 创建个人小结飞书文档 + 开权限 + 填问卷 | ⏳   |                             |

### 技术前置验证（写代码前必过）

| #   | 验证项                        | 状态 | 结论          |
| --- | ----------------------------- | ---- | ------------- |
| V1  | OpenClaw 部署 + 集成路径确认  | ⏳   | 待定（A/B/C） |
| V2  | Lark CLI 四条命令跑通         | ⏳   |               |
| V3  | Doubao 2.0 Pro 能调通         | ⏳   |               |
| V4  | BGE Embedding + Reranker 加载 | ⏳   |               |

---

## M1 Phase 1 保底 MVP

### 任务清单

- [ ] **M1.1** 知识采集：Lark CLI 拉文档 → markdown
- [ ] **M1.2** 文档索引：切片 + Chroma + BM25
- [ ] **M1.3** Hybrid 检索：BM25 + 向量 + Reranker
- [ ] **M1.4** LLM 生成：豆包 + 证据三元组
- [ ] **M1.5** Bot 通道：飞书收发消息打通
- [ ] **M1.6** 会话记忆：基于 chat_id 的短期上下文

### 里程碑

- [ ] **Day 7 (4/30)**：端到端跑通，飞书里能 @Bot 问答带证据

---

## M2 Phase 2 核心亮点

- [ ] **M2.1** 变更感知：定时拉文档 + hash 对比
- [ ] **M2.2** 变更点提取：LLM 做 v1/v2 diff 摘要
- [ ] **M2.3** 影响分析（粗）：基于文档元数据匹配
- [ ] **M2.4** 定向分发：Lark CLI 发消息卡片
- [ ] **M2.5** 分发记录：SQLite 存推送历史

---

## M3 Phase 3 加分

- [ ] **M3.1** 影响分析（精）：员工画像 + LLM 语义匹配
- [ ] **M3.2** 评测集构造：30 条问答 + 5 个分发场景
- [ ] **M3.3** 量化报告：命中率 / 准确率 / 分发精准度
- [ ] **M3.4** 前端打磨：卡片美化 + SSE 流式 + 证据交互
- [ ] **M3.5** 可观测性：日志 + 工具链追踪

---

## M4 提交

- [ ] Demo 录屏视频（5-8 分钟）
- [ ] 项目介绍文档
- [ ] README 完善
- [ ] 比赛问卷最终填报

---

## 📅 每日开发日志

### 2025-04-24（Day 1 · 项目启动）

**今日目标**：

- 完成 3 件比赛硬指标
- 完成方案 v0.1 文档
- 完成 `context.md` 工作区索引

**实际产出**：

- ✅ 方案 v0.1：`doc/project-plan-v0.md`
- ✅ 仓库初始化 + README 草稿 + 首次 push
- ✅ 工作区索引：`../../context.md`
- ✅ 个人小结模板：`../../sandbox/toChatgpt/feishu-summary-model.md`
- ✅ 最小开发骨架：`requirements.txt`、`.env.example`、`backend/app.py`、`backend/config.py`
- ✅ 前置验证脚本：`scripts/verify_ark.py`、`scripts/verify_embeddings.py`
- ✅ 可运行性校验：`python -m compileall backend scripts`
- ⚠️ 认领 EP / 填问卷 / 建个人小结飞书文档 —— 进行中

**遇到的坑**（详细记到 problem.md）：

- GitHub HTTPS 直连 push 失败，改走 7890 代理后成功
- `.env.example` 被 `.gitignore` 的 `.env.*` 规则误伤，已通过 `!.env.example` 放行

**明日计划**：

- 完成 4 项前置技术验证
- 开始造模拟数据

### 2025-04-24（Day 1 · 路线纠偏）

**今日目标**：

- 按 `doc/reuse-mapping.md` 纠偏后续实现路线
- 把“复用优先”规则写回项目文档
- 同步阶段路线图，明确阶段 3a / 3b 与 Phase 2 优先级

**实际产出**：

- ✅ 更新 `doc/context.md`：新增“写任何新模块前先查 `doc/reuse-mapping.md`”硬约束
- ✅ 更新 `doc/stage-roadmap.md`：拆分阶段 3a / 3b，并标注 Phase 2 的 `5/1` 硬死线
- ✅ 确认阶段 3a 已完成，后续阶段 3b 将严格按对照表指定来源复用
- ✅ 从 `MedicalGraphRAGSystem/graphrag/reranker.py` 搬入 `backend/retrieval/reranker.py`，改动点：日志名改为 `feishu_knowledge_agent`、适配 `RetrievalHit`、复用 `EMBEDDING_API_KEY`/`EMBEDDING_BASE_URL` 并新增 `RERANKER_MODEL`
- ✅ 从 `MedicalGraphRAGSystem/evaluation/metrics.py` 搬入 `backend/eval/metrics.py`，改动点：保留原指标函数，不扩写额外框架
- ✅ 参考 `MedicalGraphRAGSystem/evaluation/evaluator.py` 改写 `backend/eval/evaluator.py` / `backend/eval/run_eval.py`，改动点：只保留单一 `/answer` 接口评测，输出 `report.md` + `report.json`
- ✅ 参考 `integration-project/zp-agent-sandbox-copy/test-rag-accuracy.py` 的分层思路，补 `backend/eval/test_cases.json` 与 `backend/eval/compare_retrieval.py`，改动点：改成企业知识问答场景，并对比 BM25 vs Hybrid
- ✅ 按 `doc/reuse-mapping.md` 开始 Phase 2：主链路原创实现 `backend/distribution/` 最小骨架（`state.py` / `watcher.py` / `differ.py` / `impact.py` / `dispatcher.py`）
- ✅ 参考 `learn-claude-code/agents/s08_background_tasks.py` 的后台任务范式，在 `watcher.py` 中补了可选调度入口；消息分发接口按 `lark-cli im +messages-send` 约束封装为可复用 dispatcher
- ✅ 增加 Phase 2 最小配置入口：在 `backend/config.py` / `.env.example` 新增 `DISTRIBUTION_DOCS`、默认接收目标和子目录配置，避免 demo 运行时手写硬编码
- ✅ 新增 `scripts/run_distribution_demo.py`：可本地执行“检查文档变化 → 输出摘要 → 预览待发送命令”，并支持显式 `--send` 触发真实发送
- ✅ 收敛 Phase 2 身份策略到代码：新增 `LARK_DOC_IDENTITY` / `LARK_MESSAGE_IDENTITY`，读取链路继续允许 `user`，分发链路默认改为 `bot`，避免被 `im:message.send_as_user` 卡住主链路
- ✅ 修复隐患：`backend/clients/lark_cli.py` 中 `LarkCLIClient.identity` 去掉默认值（原为 `"user"`），强制所有调用方显式传入身份，避免未来漏传时静默掉回 user 身份
- ✅ 重写 `README.md`：删除与现状脱节的描述（LangGraph、Doubao 2.0 Pro、"项目启动阶段"、OpenClaw 是核心入口），按 `doc/feishu-architecture.md` 决策同步真实状态、技术栈、启动命令与文档导航
- ✅ 补 `.env.example`：新增 `LARK_APP_ID` / `LARK_APP_SECRET`（落实 `doc/feishu-architecture.md` §5 P0 第 3 条要求，为后续直连飞书 OpenAPI / 事件回调签名校验预留入口）
- ✅ 修 `next.md` 中两处错误的 README 链接（cci 路径误指向 `lark-cli/README.md`，已改回 `feishu-knowledge-agent/README.md`），并把 `impact.py` 升级一项的优先级标注从"P1"改为"非 architecture.md 显式列出，来自外部代码评审 + 项目差异化诉求"，避免伪造引用源
- ✅ 新增 OpenClaw 弱对接最小链路：补 `backend/api/routes/openclaw.py` 的 `/api/openclaw/query` 与 `/api/openclaw/subscribe`，分别复用现有 `AnswerService` 与 `distribution_targets` metadata 写入
- ✅ 新增 `backend/services/openclaw_service.py` 与 `openclaw-skills/enterprise-knowledge/SKILL.md`：前者承接 OpenClaw 的薄封装服务层，后者只描述 HTTP 调用、不放业务逻辑，符合 `doc/feishu-architecture.md` 的 OpenClaw 约束

**明日计划**：

- 为 `distribution_targets` 元数据格式补一个最小示例，便于定向分发演示
- `backend/distribution/impact.py` 升级为 metadata + 规则 + 可选 LLM 三档（兑现差异化亮点）
- 评估是否把 `watcher.start()` 接入独立 runner，而不是直接挂到 FastAPI 生命周期

### 2026-04-25（Day 2 · 赛题校准与真实演示路线）

**今日目标**：

- 对照 `doc/subject.txt` 判断当前项目方向和竞争力。
- 用个人可编辑飞书 Wiki 文档跑通真实变更检测 demo。
- 明确下一阶段不再只做后台链路，而是补飞书 Bot 问答和真实主动推送。

**实际产出**：

- ✅ 阅读 `doc/subject.txt`，确认赛题要求“精准问答 + 主动分发与推送 + 至少一种主动触发方式”。
- ✅ 确认项目方向不偏：企业知识变更感知与定向分发是当前项目的差异化主线。
- ✅ 用个人 Wiki 文档 `权限变更公告 Demo` 完成端到端后台验证：
  - 抓取飞书文档到 `data/raw_docs/lark_docs/`
  - `/retrieve` 命中文档 chunk
  - `/answer` 基于证据回答
  - 建立 baseline
  - 修改飞书文档
  - 再次运行分发 demo，检测到 `changed=1`
  - 输出变更摘要、关键变化和 dry-run 发送命令
- ✅ 确认当前最大短板：演示还偏后台，飞书事件入口尚未形成真实 Bot 问答闭环。
- ✅ 更新 `doc/stage-roadmap.md`：将下一阶段最高优先级调整为“飞书 Bot 问答 + 真实主动推送验证”。

**遇到的坑**（详细记到 problem.md）：

- 当前可读飞书文档不一定可编辑，变更检测演示必须使用用户可编辑的个人文档。
- `feishu_events.py` 目前只 ACK 事件，不处理消息正文和 bot 回复。
- 真实主动发送仍依赖 bot 权限、真实 `chat_id` 和应用配置，不能只靠 dry-run 代表最终效果。

**明日计划**：

- 实现飞书 Bot 问答闭环：消息事件解析 -> `AnswerService` -> bot 回复。
- 准备公网回调方案，完成飞书事件订阅验证。
- 验证 bot 身份真实发消息到测试群。
- 将 watcher 的 `--watch` / `--send` 跑成可录屏的主动推送链路。

---

### 2026-04-26（Day 3 · 真实飞书闭环验证完成）

**今日目标**：

- 跑通飞书私聊 / 群聊 Bot 问答真实链路。
- 跑通文档变更后的真实主动推送链路。
- 按验证结果同步 README / roadmap / progress 状态。

**实际产出**：

- ✅ 启动本地 FastAPI 后端到 `127.0.0.1:5000`，复用公网隧道完成飞书事件回调。
- ✅ 完成飞书私聊真实问答验证：用户发问 -> `/feishu/events` -> `AnswerService` -> bot 回复。
- ✅ 完成飞书群聊真实问答验证：在测试群 `@Bot` 后可正常回复。
- ✅ 修复飞书回复显示问题：将多行回答压平成单行文本，避免只显示前缀。
- ✅ 修复 webhook 触发时的 Pydantic `schema` warning：移除未使用字段。
- ✅ 定位测试群 `chat_id`，并对 `权限变更公告 Demo` 运行 `scripts/run_distribution_demo.py --watch --send`。
- ✅ 文档二次修改后成功检测到 `changed=1`，生成变更摘要与关键变化，并由 bot 主动推送到测试群。
- ✅ 同步 `README.md` 与 `doc/stage-roadmap.md` 状态口径，进入 demo 材料收口阶段。

**遇到的坑**（详细记到 problem.md）：

- P1 主动推送验证必须使用 bot 已加入的真实测试群，不能只停留在私聊场景。
- 如果文档当前状态已经被 watcher 记录为最新，再次 dry-run 会出现 `changed=0`，需要继续修改文档才能触发新一轮推送。
- 飞书群聊场景下优先使用 `@Bot` 触发，验证更稳定。

**明日计划**：

- 准备 2-3 个稳定可复现的场景案例。
- 补最小效果验证报告与录屏脚本。
- 继续收口 README、评估报告和比赛提交材料。

---

<!-- 每天按下面格式追加

### YYYY-MM-DD（Day N · 阶段）

**今日目标**：
-

**实际产出**：
-

**遇到的坑**（详细记到 problem.md）：
-

**明日计划**：
-

-->

---

## 状态说明

- ⏳ 未开始 / 进行中
- ✅ 已完成
- ⚠️ 遇到问题（详见 `problem.md`）
- ❌ 已放弃 / 降级
