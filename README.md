[README.md](https://github.com/user-attachments/files/33145718/README.md)
# lark-notify Skill 使用说明

> 版本 1.2.1 ｜ Claude Code 用户级 Skill ｜ 飞书 ⇄ Claude 单向推送

## 一、这是什么

把 **Claude Code 每轮回复的原文**（或手动模式下整理好的任务结论）自动转发到飞书，
落在你与某个飞书机器人的**私聊会话**里——手机上随时查看 AI 跑了什么、结论是什么。

两种工作模式：

| 模式 | 行为 | 触发者 |
|---|---|---|
| **auto = true（自动）** | 每轮 AI 回复结束，回复**原文一字不漏**自动推送到飞书 | Claude Code 的 **Stop hook**（硬性执行，100% 必发，不经 AI 判断） |
| **auto = false（手动，默认）** | AI 产出结论后**不主动发**；你说「把结果转发到飞书」时按固定格式（任务/结论/产物位置）发送 | AI 调用 lark-notify skill |

两种模式互补：自动模式保证「每轮都推、一字不漏」；手动模式适合只要结论汇总、不想被刷屏的场景。

## 二、环境配置要求

| 依赖 | 要求 | 检查命令 |
|---|---|---|
| 操作系统 | Windows（脚本按 Windows 路径处理，Linux/macOS 需小改） | — |
| Python | ≥ 3.8，仅标准库，无需 pip 装包 | `python --version` |
| Node.js | 任意近期 LTS（lark-cli 的运行时） | `node --version` |
| lark-cli | npm 全局安装：`npm i -g @larksuite/cli` | `lark-cli --version` |
| lark-cli 认证 | **bot 身份**就绪，且应用已开通 `im:message:send_as_bot` scope | `lark-cli auth status` |
| Claude Code | ≥ 2.x（支持 Stop hook 与用户级 skill） | `claude --version` |
| 飞书侧 | 已与目标机器人建立**私聊**（给机器人发过一条消息即可） | 手机上看会话存在 |

不需要常驻进程——推送是每轮回复结束时即时执行的短命令。

## 三、安装步骤

1. **放置 skill**：把 `SKILL.md`、`auto_forward.py`、`config.json` 三个文件放到
   `C:\Users\<你的用户名>\.claude\skills\lark-notify\`（用户级，所有项目可用）。

2. **改 config.json（两处按机器调整）**：

   ```json
   {
     "auto": false,
     "user_open_id": "ou_xxxxxxxxxxxxxxxx",
     "lark_run_js": "C:\\Users\\<你>\\AppData\\Roaming\\npm\\node_modules\\@larksuite\\cli\\scripts\\run.js"
   }
   ```

   - `user_open_id`：你的飞书 open_id（查法：`lark-cli contact +get-user --as user`，
     输出里的 `openId` 字段，`ou_` 开头）
   - `lark_run_js`：npm 全局 lark-cli 的入口脚本。**留空 `""` 则自动回退用 PATH 里的
     `lark-cli` 命令**（Git Bash 环境下通常直接可用）
   - `auto`：安装后先保持 `false`，验证手动模式没问题再开自动

3. **注册 Stop hook**（自动模式必需；只用手动模式可跳过）。在
   `C:\Users\<你>\.claude\settings.json` 的 `hooks` 对象里**合并**以下内容
   （注意保留文件里已有的其他配置，不要整个替换）：

   ```json
   "Stop": [
     {
       "hooks": [
         {
           "type": "command",
           "command": "python -X utf8 C:/Users/<你>/.claude/skills/lark-notify/auto_forward.py",
           "timeout": 180,
           "async": true
         }
       ]
     }
   ]
   ```

   改完后在 Claude Code 里输入一次 `/hooks`（或重启会话）让配置生效。

4. **验证**：
   - 手动模式：随便让 Claude 干个小活，然后说「把结果转发到飞书」，手机上看会话
   - 自动模式：`/lark-notify auto enable`，然后随便问一句，回复结束后几秒飞书应收到原文

## 四、日常使用

| 操作 | 做法 |
|---|---|
| 开自动模式 | `/lark-notify auto enable`（每轮回复原文自动推） |
| 关自动模式 | `/lark-notify auto disable`（恢复手动确认） |
| 查当前模式 | `/lark-notify auto status` |
| 手动转发结论 | 直接说「把这次的结果/结论转发到飞书」「发到坤的智能罗伯特」 |

开关状态存磁盘（skill 目录 config.json），**跨会话、跨项目生效**。

## 五、文件结构

```
~/.claude/skills/lark-notify/
├── SKILL.md            # skill 本体（触发规则、手动模式发送格式）
├── auto_forward.py     # Stop hook 脚本（自动模式执行体）
├── config.json         # 配置：auto 开关 / 收件人 open_id / lark-cli 入口
├── README.md           # 本文档
├── auto_forward.log    # 运行日志（排查用，自动生成）
├── last_forward.json   # 去重状态（自动生成）
└── tmp/                # 发送临时文件（自动生成）
```

## 六、故障排查

| 症状 | 排查 |
|---|---|
| 飞书没收到，日志也没新行 | hook 没生效：确认 settings.json 里 `hooks.Stop` 写对、JSON 合法；在 Claude Code 输入 `/hooks` 重载或重启会话 |
| 日志有「发送失败 rc=…」 | 看 auto_forward.log 里 stderr：`missing_scope` → 应用缺 `im:message:send_as_bot`，去飞书开放平台补权限；网络问题重试即可 |
| 日志有「缺少 transcript_path」 | Claude Code 版本过旧，升级 |
| 收件人不对我 | config.json 的 `user_open_id` 改错了，重新查 |
| 重装/换机后不推 | lark_run_js 路径失效且 PATH 无 lark-cli → 修正路径，或装 npm 全局 lark-cli |
| 重复收到同一条 | 去重状态被删（last_forward.json）导致重发一次，正常现象，忽略即可 |

日志位置：`~/.claude/skills/lark-notify/auto_forward.log`（格式：时间 + 动作 + 内容长度/hash）。

## 七、卸载

1. 删掉 `~/.claude/settings.json` 里 `hooks.Stop` 整段
2. 删除 `~/.claude/skills/lark-notify/` 目录
3. 输入一次 `/hooks` 或重启会话

## 八、安全与边界

- 推送目标固定为你自己的私聊（config 里的 open_id），不会发到任何群
- 自动模式会把**每轮回复原文**发到飞书——包含会话里出现的代码/路径等文本，
  敏感项目请用手动模式
- 脚本静默失败设计：任何异常只写日志，绝不阻塞 Claude 会话
- 依赖 lark-cli 的 bot 身份（tenant token），与 user token 过期无关
