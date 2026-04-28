# 企业知识整合与变更分发 Agent

面向飞书生态的企业知识助手，提供两类核心能力：

- **知识问答**：抓取飞书文档 → 本地索引 → 混合检索（BM25 + 向量 + 可选 Reranker）→ LLM 基于证据回答
- **变更分发**：定时监控目标文档 → 内容指纹比对 → LLM 摘要变更 → 元数据驱动的影响分析 → 飞书消息卡片定向推送

OpenClaw 作为**可选的弱对接渠道**（HTTP Tool），不是必需依赖；项目主链路是独立的飞书自建应用 + FastAPI 后端。

---

## 项目背景

企业知识通常分散在飞书文档、Wiki、知识库等多个位置，常见痛点：

- 想找知识时检索成本高、定位慢
- 知识更新后，受影响的人无法被及时通知

本项目目标：在员工"提问时能答对"、在知识"变化时能主动推"。

---

## 当前实现状态

### 已实现

- ✅ 飞书文档抓取（通过 `lark-cli` 子进程，`scripts/fetch_lark_doc.py`）
- ✅ 文档切片 + ChromaDB 向量索引 + BM25 关键词索引
- ✅ 混合检索：`bm25` / `vector` / `hybrid` 三种模式
- ✅ Reranker 接入（来自 MedicalGraphRAG，`backend/retrieval/reranker.py`）
- ✅ FastAPI 接口：`POST /answer`、`POST /retrieve`、`GET /health`、飞书事件回调 + Bot 问答处理
- ✅ LLM 问答：兼容 OpenAI 协议，已通过 MiniMax 真实联调
- ✅ Embedding：通过 API（默认 SiliconFlow `BAAI/bge-m3`）
- ✅ 评测脚手架：`backend/eval/`（metrics、evaluator、test_cases）+ BM25 vs Hybrid 对比脚本
- ✅ 变更分发最小骨架：`backend/distribution/`（state / watcher / differ / impact / dispatcher）
- ✅ 身份策略落代码：读文档默认 `user`、发消息默认 `bot`，**不依赖 `im:message.send_as_user`**
- ✅ 端到端 demo 脚本：`scripts/run_distribution_demo.py`（dry-run + `--send` 显式发送）
- ✅ OpenClaw 弱对接：`/api/openclaw/query`、`/api/openclaw/subscribe`、`openclaw-skills/enterprise-knowledge/SKILL.md`
- ✅ 影响分析三档示例：显式目标、规则匹配、候选目标 + LLM 选择（`backend/distribution/examples/`）

### 真实飞书验证通过

- ✅ 飞书 Bot 问答闭环：飞书私聊 / 群聊消息事件 -> `AnswerService` -> bot 回复，已完成真实回调验证
- ✅ 真实主动推送验证：`scripts/run_distribution_demo.py --watch --send` 已在测试群完成文档变更后的真实推送
- ✅ 可录屏核心链路：`权限变更公告 Demo` 已验证“飞书里提问 -> Bot 回复”与“修改文档 -> Bot 主动推送”

### 进行中 / 计划中

- ⏳ 场景案例：权限变更、项目计划、产品发布等 2-3 个可复现 demo
- ⏳ 效果验证报告：问答准确性、变更摘要准确性、触达效率对比
- ⏳ 测试集：`tests/` 单元 / 集成测试
- ⏳ 录屏 / 评估报告 / 演示稿

详细阶段划分见 [`doc/stage-roadmap.md`](./doc/stage-roadmap.md)，每日开发记录见 [`help/progress.md`](./help/progress.md)。

---

## 架构概览

```
飞书客户端 ────┐                 OpenClaw 客户端 ────┐
              │ 事件 / 消息                          │ HTTP tool（可选）
              ▼                                     │
   飞书自建应用（appId/appSecret，仅身份壳）          │
              │                                     │
              │ OpenAPI                             │
              ▼                                     ▼
  ┌──────────────────────────────────────────────────┐
  │         FastAPI 后端 = Agent 本体                │
  │  - /answer（混合检索 + LLM 回答）                 │
  │  - /retrieve（仅检索）                            │
  │  - 飞书事件回调（Bot 问答闭环已真实验证）          │
  │  - distribution watcher（APScheduler 定时）       │
  └──────────────────────────────────────────────────┘
              │
              ▼
  ChromaDB（向量）+ BM25（关键词）+ SQLite（变更状态/分发记录）+ data/raw_docs（落盘文档）
```

身份与权限策略详见 [`doc/feishu-architecture.md`](./doc/feishu-architecture.md)（**所有 AI/开发者动代码前的硬约束文件**）。

---

## 技术栈

| 层         | 选型                             | 说明                                                         |
| ---------- | -------------------------------- | ------------------------------------------------------------ |
| 后端框架   | FastAPI + Uvicorn                | 异步 / 流式                                                  |
| LLM        | OpenAI 兼容 SDK                  | provider-neutral，通过 `LLM_BASE_URL` 切换（已联调 MiniMax） |
| Embedding  | OpenAI 兼容 API                  | 默认 SiliconFlow `BAAI/bge-m3`                               |
| Reranker   | `BAAI/bge-reranker-v2-m3`（API） | 复用自 MedicalGraphRAG                                       |
| 向量存储   | ChromaDB                         | 本地持久化                                                   |
| 关键词检索 | rank_bm25                        |                                                              |
| 状态存储   | SQLite（标准库 `sqlite3`）       | 文档指纹 / 分发历史                                          |
| 定时调度   | APScheduler                      | watcher 轮询                                                 |
| 飞书集成   | Lark CLI（`subprocess`）         | dev/低频路径；后续高频热路径可迁 SDK / httpx                 |

---

## 快速开始

### 1. 准备环境

```bash
# Python ≥ 3.10
pip install -r requirements.txt

# Lark CLI（需 Node ≥ 22）
npm install -g @larksuite/cli
lark-cli config init
lark-cli auth login --recommend
```

### 2. 配置环境变量

复制 `.env.example` 为 `.env` 并填写：

```bash
LLM_API_KEY=...
LLM_BASE_URL=https://api.minimaxi.com/v1
LLM_MODEL=MiniMax-M2.7
EMBEDDING_API_KEY=...
EMBEDDING_BASE_URL=https://api.siliconflow.cn/v1
EMBEDDING_MODEL=BAAI/bge-m3
LARK_CLI_PATH=lark-cli
LARK_DOC_IDENTITY=user           # 文档读取身份
LARK_MESSAGE_IDENTITY=bot        # 消息发送身份（不依赖 send_as_user）
DISTRIBUTION_DOCS=               # 监控的飞书文档 URL/Token，逗号分隔
```

> Windows 注意：在 PowerShell 里 Lark CLI 需用 `lark-cli.cmd`，但本仓库代码已自动解析。

### 3. 抓取并索引文档

```bash
python scripts/fetch_lark_doc.py "<飞书文档 URL>"
```

### 4. 启动后端服务

```bash
uvicorn backend.app:app --reload
# 健康检查
curl http://localhost:8000/health
```

### 5. 问答接口

```bash
curl -X POST http://localhost:8000/answer \
  -H "Content-Type: application/json" \
  -d '{"question":"差旅报销流程是什么？","retrieval_mode":"hybrid","top_k":5}'
```

### 6. 变更分发 demo

```bash
# dry-run，仅打印将要发送的命令
python scripts/run_distribution_demo.py "<飞书文档 URL 或 Token>"

# 真实发送（需 bot 已加入目标群且具备发消息权限）
python scripts/run_distribution_demo.py "<飞书文档 URL 或 Token>" --send
```

---

## 项目结构

```
backend/
  api/routes/         FastAPI 路由（answer / retrieve / feishu_events）
  clients/            外部依赖封装（lark_cli / llm / embedding）
  ingestion/          文档抓取 + 落盘
  retrieval/          切片 / BM25 / 向量 / Hybrid / Reranker
  services/           业务编排（AnswerService / LocalRetrievalService）
  distribution/       Phase 2 变更分发：state/watcher/differ/impact/dispatcher
  models/             数据模型
  eval/               评测脚手架与对比测试
scripts/              一次性脚本与 demo
data/                 本地数据（向量库、原始文档、SQLite 状态）
doc/                  方案 / 架构决策 / 阶段路线 / 复用映射
help/                 progress / problem 跨会话开发记录
```

---

## 文档导航

动代码前必读：

1. [`doc/feishu-architecture.md`](./doc/feishu-architecture.md) — 飞书生态硬约束 + 身份/应用/OpenClaw 决策（**最高优先级**）
2. [`doc/context.md`](./doc/context.md) — 项目主上下文
3. [`doc/reuse-mapping.md`](./doc/reuse-mapping.md) — "动新模块前先查"的复用边界
4. [`doc/stage-roadmap.md`](./doc/stage-roadmap.md) — 阶段路线与当前位置
5. [`help/progress.md`](./help/progress.md) — 每日开发进度
6. [`help/problem.md`](./help/problem.md) — 已遇问题与解决记录

研究类长文（事实出处）：

- [`doc/feishu-help.md`](./doc/feishu-help.md) — 飞书开放平台 / scope / OpenClaw 完整调研

---

## 比赛与项目状态

- 赛题：飞书 OpenClaw 杯 — 企业办公知识整合与分发 Agent
- 当前阶段：阶段 0~3a 已完成，阶段 4（飞书 Bot 问答）与阶段 5（变更分发）核心链路均已完成真实飞书验证，当前进入 demo 打磨与案例/评测材料收口
- Phase 2 硬死线：5/1
- 提交日：5/7

---

## 已知约束

- 当前以**单租户、企业自建应用**为前提，文档需被显式共享给 bot（或通过授权用户读）
- 不依赖飞书 `im:message.send_as_user` 权限（高敏，部分企业禁用）
- 飞书事件入口已形成完整 Bot 问答闭环；当前主要工作已转向案例、录屏与评测材料整理
- 主动分发已完成真实发送验证；继续复用 bot 权限、真实 `chat_id` 和目标群即可演示
- LLM / Embedding / Reranker 走外部 API，需要可用密钥
- `tests/` 单测尚未补齐，当前以 `eval/` + 端到端脚本验证
