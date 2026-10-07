---
name: lark-notify
version: 1.2.1
description: "把当前 AI 会话跑出的结论/结果通过 lark-cli 转发到飞书「坤的智能罗伯特」机器人会话（即用户与机器人的私聊，手机端可直接查看）。当用户说把结果/结论发到飞书、转发给机器人、跑完后通知我、发到坤的智能罗伯特，或要求切换自动/手动转发模式（lark-notify auto enable/disable/status）时使用。不负责一般性的发消息/群聊需求（走 lark-im）。"
metadata:
  requires:
    bins: ["lark-cli"]
---


# lark-notify：转发 AI 结论到飞书机器人会话

> **前置条件：** 先阅读 [`../lark-shared/SKILL.md`](../lark-shared/SKILL.md)。

## 用途

AI 会话（Claude Code 等）跑完任务后，把结论/结果文本送到用户飞书里与机器人
「坤的智能罗伯特」的私聊会话，用户在手机/客户端上即可查看。

**固定收件人**：`ou_f9677cc0133235c8f786d99add0414af`（机器人主人熊坤）。
**固定身份**：`--as bot`（bot 身份发给用户 → 消息落在该用户与机器人的私聊里；
不要用 `--as user` 发给机器人——下游桥接进程会把消息当新指令再跑一轮 Claude）。

## 模式开关（auto enable / disable）

模式状态存在本 skill 目录的 [`config.json`](config.json)（`{"auto": true|false}`）。
用户通过 `/lark-notify auto <子命令>` 切换，AI 直接编辑该文件并回显结果：

| 用户输入 | 动作 |
|---|---|
| `/lark-notify auto enable` | 把 config.json 的 `auto` 写为 `true`，回复「自动转发已开启（每轮回复原文由 Stop hook 自动推送）」 |
| `/lark-notify auto disable` | 把 `auto` 写为 `false`，回复「自动转发已关闭，之后发送前会先确认」 |
| `/lark-notify auto status` | 读 config.json，报告当前模式 |

切换立即生效，对所有会话生效（状态在磁盘上，非会话内存）。

### 两种模式下的发送规则

- **auto = true（自动）**：**由 Claude Code 的 Stop hook 硬性执行**（脚本
  [`auto_forward.py`](auto_forward.py)，已注册在 `~/.claude/settings.json`）：每轮 AI 回复结束时，
  脚本自动把该轮回复的**原文**（最后一条 assistant 消息）bot 身份 p2p 转发到飞书，一字不漏，
  无需 AI 参与、无需用户确认。AI 在此模式下**不要**再手动调用本 skill 重复发送。
  脚本自带去重（同会话同内容只发一次），日志见 [`auto_forward.log`](auto_forward.log)。
- **auto = false（手动，默认）**：仅在用户明确要求转发时，按下方「消息内容组织」结构化发送；
  其他情况要发必须先把草稿贴给用户确认。

## 消息内容组织

发送前把结论整理成一份 Markdown，结构固定：

```
🤖 AI 任务结论（{时间}）

## 任务
{一句话说明这是什么任务/哪个会话的结论}

## 结论
{AI 产出的结论/结果正文，保持原文，不要自行缩写删减}

## 产物位置（如有）
{本地文件/代码改动位置，路径原样}
```

## 命令

```bash
# 短内容（< 2000 字符）：直接内联发送
lark-cli im +messages-send \
  --user-id ou_f9677cc0133235c8f786d99add0414af \
  --as bot \
  --markdown $'🤖 AI 任务结论（2026-10-07 14:00）\n\n## 任务\n...\n\n## 结论\n...'

# 长内容：先写入 cwd 下临时文件，用 @file 发送（lark-cli 只接受 cwd 相对路径）
# 发送成功后删除临时文件
lark-cli im +messages-send \
  --user-id ou_f9677cc0133235c8f786d99add0414af \
  --as bot \
  --markdown @./.lark-notify-result.md
rm ./.lark-notify-result.md   # Windows Git Bash
```

## 判断成功

按 lark-shared 输出契约：stdout JSON 的 `ok == true`（或退出码 0）即成功，
返回 `message_id`。失败时 stderr 是 JSON error envelope，按 `error.hint` 处理；
`missing_scope` 说明 bot 缺 `im:message:send_as_bot`，走 lark-shared 授权流程补齐。

## 使用规则

1. auto = true 时，产出任务结论即发送许可；auto = false 时，用户明确要求转发即发送许可。
2. auto = false 时**不要**在用户没要求时主动把会话内容发出去；拿不准就先把草稿贴给用户看。
3. 需要预览请求而不实际发送时加 `--dry-run`。
4. 结论正文保持 AI 原文，不截断、不改写；只允许补充「任务/产物位置」两个框架字段。
5. 每次任务转发一条汇总消息，不要把中间步骤逐条轰炸。
6. 开头若没有明确模式线索（用户既没要求转发也没说不推），且 config.json 不可读，按 auto = false 处理。

## 权限

| 操作 | 所需 scope |
|------|-----------|
| `+messages-send --as bot`（p2p 发给用户） | `im:message:send_as_bot`（bot 身份） |

## 关联

- 结果落地的会话由「飞书 ⇄ Claude 桥接」（`E:\AI开发工具\9_LarkClaudeBridge\bridge.py`）维护；
  本 skill 只单向推送，不经过桥接，不产生循环。
- 一般性的发消息/群聊/回复场景不走本 skill，用 [`../lark-im/SKILL.md`](../lark-im/SKILL.md)。
- 模式开关状态文件：[`config.json`](config.json)；全局触发规则见用户 `~/.claude/CLAUDE.md` 的
  「lark-notify 自动转发」一节。
