# 番茄作家助手 MCP 服务 (Fanqie Writer Assistant MCP)

专为大语言模型（LLM / AI Agent）设计的**番茄作家助手（Fanqie Novel Author Platform）全自动 MCP 工具**。

- 📚 **全自动新建作品**：自动填写书名、作品简介、主角名、频道分类（男频/女频）、阅读标签及签约模式，一键提交创建并返回作品唯一 ID。
- 📑 **全自动分卷管理**：支持在线新建分卷、重命名分卷，完美契合番茄平台分卷规则。
- 🚀 **全自动发文**：单章发布、定时发布（指定精确到秒的未来时间）、存草稿，支持自动归属分卷、错别字弹窗自动确认与 AI 标识合规处理。
- 📦 **按分卷一键发布整本小说**：支持扫描各分卷子目录（如 `卷一_xxx`），按卷按章全自动创建分卷并发布/存入草稿箱，带实时持久化进度记录与断点续传。
- ✏️ **修改书名**：自动填报新书名及修改理由，提交平台审核。
- 🖼️ **更换书籍封面**：自动按番茄 3:4 标准比例智能校验裁剪并上传，提交平台审核。
- 🛡️ **反检测与持久化登录**：基于 Playwright Stealth 深度伪装技术，支持一键本地弹窗扫码登录，持久化存储会话，后续操作静默执行。

---

## 核心 MCP 工具一览

| 工具名称 | 功能描述 | 核心参数 |
| :--- | :--- | :--- |
| `fanqie_check_status` | 检查当前是否已登录，获取作者笔名 | 无 |
| `fanqie_login_interactive` | 弹出本地浏览器窗口供手机 App 扫码登录 | `timeout_sec: int` (默认 180s) |
| `fanqie_get_login_qrcode` | 无头截取登录二维码图片保存到本地 | 无 |
| `fanqie_list_books` | 获取作者名下所有作品详情（ID、书名、封面、字数等） | 无 |
| `fanqie_create_book` | **全自动创建新书作品** | `title`, `intro`, `protagonist`, `gender`, `category`, `sign_pattern` |
| `fanqie_create_volume` | **为作品创建或重命名分卷** | `book_id`, `volume_name` |
| `fanqie_publish_chapter` | 发布单章节（支持草稿、立即发布、定时发布、指定分卷） | `book_id`, `title`, `content`, `is_draft`, `publish_time`, `volume_name` |
| `fanqie_publish_volume_book` | **全自动按分卷结构发布整本小说** | `book_id`, `folder_path`, `mode`, `start_chapter`, `interval_hours` |
| `fanqie_batch_publish_chapters` | 一键批量自动定时发布章节 | `book_id`, `chapters_source`, `start_time`, `daily_slots`, `interval_hours` |
| `fanqie_update_book_title` | 修改作品书名并提交审核 | `book_id`, `new_title`, `reason` |
| `fanqie_update_book_cover` | 更换作品封面图片并提交审核（自动按 3:4 裁剪） | `book_id`, `image_path` |
| `fanqie_get_batch_progress` | 查看最近一次批量发布的进度与日志 | 无 |

---

## 接入配置 (Client Config)

### 1. Claude Desktop 配置示例
在 `claude_desktop_config.json` 中的 `mcpServers` 节点添加：

```json
{
  "mcpServers": {
    "fanqie-writer": {
      "command": "python",
      "args": [
        "C:\\Users\\Kupetis\\.gemini\\antigravity\\scratch\\fanqie-writer-mcp\\mcp_server.py"
      ]
    }
  }
}
```

### 2. Antigravity / Cursor / Cline 配置示例
```json
{
  "name": "fanqie-writer-assistant",
  "command": "python",
  "args": [
    "C:\\Users\\Kupetis\\.gemini\\antigravity\\scratch\\fanqie-writer-mcp\\mcp_server.py"
  ],
  "env": {
    "PYTHONIOENCODING": "utf-8"
  }
}
```

---

## 典型操作场景与提示词示例

### 场景一：首次扫码登录
> **用户指令**：“帮我登录番茄作家助手”  
> **Agent 执行**：调用 `fanqie_login_interactive()`，本地自动弹出一个 Chromium 窗口供您用番茄小说 App 或抖音扫码。登录成功后凭证永久保存在本地 `.session/` 目录。

### 场景二：查询我的书
> **用户指令**：“列出我账号里的所有小说和书籍 ID”  
> **Agent 执行**：调用 `fanqie_list_books()`，返回格式化书籍列表与对应 `book_id`。

### 场景三：一键批量定时发布（核心要求）
> **用户指令**：“把 `D:\novels\my_novel` 目录里的 50 个章节批量发到书籍 ID 7182910 下，从明天上午 10 点开始，每天两更（10:00 和 18:00）”  
> **Agent 执行**：调用：
> ```python
> fanqie_batch_publish_chapters(
>     book_id="7182910",
>     chapters_source=r"D:\novels\my_novel",
>     start_time="2026-09-22 10:00:00",
>     daily_slots=["10:00", "18:00"]
> )
> ```
> 工具将自动对目录中的章节进行自然数值排序（如第 2 章排在第 10 章前），依次计算未来每天对应时间戳，全自动排队填入番茄富文本后台并完成定时发布！

### 场景四：修改书名与更换封面
> **用户指令**：“将书籍 7182910 的名字改成《全球高武：我有一座万界商城》，封面换成 `D:\covers\new_cover.jpg`”  
> **Agent 执行**：分别调用 `fanqie_update_book_title` 和 `fanqie_update_book_cover`，自动完成规范化裁剪并提交审核。
