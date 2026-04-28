# 问题与解法记录

> 开发过程中遇到的所有坑。**先查这个文件，避免重复踩坑**。  
> 每次解决一个问题就记一条，包括试过的错误方案（让 AI 也知道哪些路走不通）。  
> 配套文件：`progress.md`（开发进度）

---

## 记录格式

每条问题按以下模板填写：

```
### [YYYY-MM-DD] #N 问题简短标题

**现象**：
（报错信息 / 实际表现）

**环境**：
（OS / 版本 / 相关配置）

**试过但失败的方案**：
- 方案 A：为什么不行
- 方案 B：为什么不行

**最终解法** ✅：
（具体怎么解决的，贴命令/代码）

**根因**：
（为什么会出这个问题，本质原因）

**关联**：
（相关文件、相关 commit、参考链接）
```

---

## 状态标记

- 🔴 **未解决**：还在卡着
- 🟡 **临时绕过**：有 workaround 但不是根本解
- ✅ **已解决**：找到根因并验证通过

---

## 问题记录

<!-- 新问题追加在这下面，倒序（最新在上） -->

### [2025-04-24] #002 `.env.example` 被 `.gitignore` 误忽略

**状态**：✅ 已解决

**现象**：
创建 `.env.example` 时失败，提示该路径被仓库 `.gitignore` 中的 `.env.*` 规则禁止访问。

**环境**：

- Windows 11
- `feishu-knowledge-agent/.gitignore`
- 需要创建可提交到仓库的配置模板文件

**试过但失败的方案**：

- 方案 A：直接再次创建 `.env.example` —— 仍然会被忽略规则拦截

**最终解法** ✅：

在 `.gitignore` 中追加一条例外规则：

```gitignore
!.env.example
```

然后重新创建 `.env.example`。

**根因**：
`.env.*` 会同时匹配 `.env.example`，导致本来想提交的模板文件也被忽略。

**关联**：

- `feishu-knowledge-agent/.gitignore`
- `feishu-knowledge-agent/.env.example`

---

### [2025-04-24] #001 GitHub HTTPS push 失败，需通过本地代理推送

**状态**：✅ 已解决

**现象**：
执行 `git push -u origin main` 时报错：

```text
OpenSSL SSL_connect: SSL_ERROR_SYSCALL in connection to github.com:443
```

后续直接执行 `git push` 还会提示当前分支没有 upstream。

**环境**：

- Windows 11
- Git HTTPS remote
- 本地代理端口：`127.0.0.1:7890`

**试过但失败的方案**：

- 方案 A：直接 `git push -u origin main` —— HTTPS 连接 GitHub 失败
- 方案 B：直接 `git push` —— 因上游分支未设置失败

**最终解法** ✅：

使用一次性 Git 代理配置并顺手设置 upstream：

```bash
git -c http.proxy=http://127.0.0.1:7890 -c https.proxy=http://127.0.0.1:7890 push --set-upstream origin main
```

**根因**：
本机到 GitHub 的 HTTPS 直连不可用，需要借助本地代理；首次推送还需要显式设置 `origin/main` 为上游分支。

**关联**：

- `feishu-knowledge-agent/.git`
- GitHub remote: `https://github.com/hhhhzzzj/feishu-knowledge-agent.git`

---

### [模板示例] #001 Lark CLI auth login 报 scope 不足

> 这是模板示例，实际遇到问题时替换掉或删除

**状态**：✅ 已解决

**现象**：
执行 `lark-cli docs +fetch --doc <url>` 报错：

```
Error: permission denied, scope 'docs:read' not granted
```

**环境**：

- Windows 11
- lark-cli v0.x.x
- 使用 user token 登录

**试过但失败的方案**：

- 方案 A：重新 `lark-cli auth login` —— scope 没变还是一样
- 方案 B：用 `--as bot` 切换身份 —— 报没有 bot 配置

**最终解法** ✅：

```bash
lark-cli auth login --recommend  # 加 --recommend 会一次性申请推荐 scope
```

**根因**：
默认登录只申请基础 scope，文档相关功能需要额外的 `docs:read` / `wiki:read`。

**关联**：

- `lark-cli/README.zh.md` 第 X 节
- commit xxxxx

---

<!-- 真正遇到问题时从这下面开始记录 -->
