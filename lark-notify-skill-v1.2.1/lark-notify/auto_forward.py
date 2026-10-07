# -*- coding: utf-8 -*-
"""lark-notify auto 转发（Claude Code Stop hook）。

每轮 Claude 回复结束时由 harness 调起：
  stdin JSON -> transcript_path -> 取最后一条 assistant 消息原文
  -> config.json 的 auto=true 时，bot 身份 p2p 原文转发到飞书。
静默失败（绝不阻塞会话），日志写 auto_forward.log 供排查。

可移植性：收件人 open_id 读 config.json 的 user_open_id；
lark-cli 调用优先用 node + run.js（npm 全局安装路径，见 config.json 的
lark_run_js），路径不存在则回退 PATH 里的 lark-cli 命令。
"""
from __future__ import annotations

import hashlib
import json
import os
import subprocess
import sys
import time
from pathlib import Path

BASE = Path(__file__).resolve().parent
DEFAULT_CONFIG = {
    "auto": False,
    "user_open_id": "ou_f9677cc0133235c8f786d99add0414af",
    "lark_run_js": (
        r"C:\Users\Administrator\AppData\Roaming\npm"
        r"\node_modules\@larksuite\cli\scripts\run.js"
    ),
}
STATE_FILE = BASE / "last_forward.json"
LOG_FILE = BASE / "auto_forward.log"
TMP_DIR = BASE / "tmp"


def log(fmt, *args):
    try:
        with open(str(LOG_FILE), "a", encoding="utf-8") as f:
            f.write(time.strftime("%Y-%m-%d %H:%M:%S ") + (fmt % args) + "\n")
    except OSError:
        pass


def load_config() -> dict:
    cfg = dict(DEFAULT_CONFIG)
    try:
        cfg.update(json.loads((BASE / "config.json").read_text(encoding="utf-8")))
    except (OSError, ValueError):
        pass
    return cfg


def lark_argv(cfg):
    """返回命令前缀。优先 node+run.js（config 的 lark_run_js），回退 PATH 里的 lark-cli。"""
    js = cfg.get("lark_run_js") or ""
    if js and os.path.exists(js):
        return ["node", js]
    return ["lark-cli"]


def last_assistant_text(transcript_path: str) -> str:
    """取 transcript JSONL 里最后一条非空的 assistant 文本。"""
    text = ""
    with open(transcript_path, "r", encoding="utf-8", errors="replace") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            try:
                rec = json.loads(line)
            except ValueError:
                continue
            if rec.get("type") != "assistant":
                continue
            content = (rec.get("message") or {}).get("content")
            if isinstance(content, list):
                parts = [b.get("text", "") for b in content
                         if isinstance(b, dict) and b.get("type") == "text"]
                t = "\n".join(p for p in parts if p)
            elif isinstance(content, str):
                t = content
            else:
                t = ""
            if t.strip():
                text = t
    return text


def send(cfg, text: str) -> bool:
    prefix = lark_argv(cfg)
    TMP_DIR.mkdir(exist_ok=True)
    reply = TMP_DIR / "reply.md"
    reply.write_text(text, encoding="utf-8")
    try:
        proc = subprocess.run(
            prefix + ["im", "+messages-send",
                      "--user-id", cfg.get("user_open_id", ""),
                      "--as", "bot", "--markdown", "@./" + reply.name],
            cwd=str(TMP_DIR), capture_output=True, timeout=180,
        )
        out = proc.stdout.decode("utf-8", "replace")
        ok = proc.returncode == 0
        if ok:
            try:
                ok = json.loads(out).get("ok") is True
            except (ValueError, AttributeError):
                pass
        if not ok:
            log("发送失败 rc=%s stderr=%s", proc.returncode,
                proc.stderr.decode("utf-8", "replace")[:300])
        return ok
    finally:
        try:
            reply.unlink()
        except OSError:
            pass


def main():
    try:
        payload = json.load(sys.stdin)
    except ValueError:
        return
    if payload.get("stop_hook_active"):
        return  # hook 链内再次触发，避免循环
    cfg = load_config()
    if not cfg.get("auto"):
        return
    tp = payload.get("transcript_path")
    if not tp or not os.path.exists(tp):
        log("缺少 transcript_path")
        return

    text = last_assistant_text(tp)
    if not text.strip():
        return

    # 去重：同会话同内容只发一次（Stop 可能重复触发）
    digest = hashlib.sha256(
        (str(payload.get("session_id", "")) + text).encode("utf-8")
    ).hexdigest()[:32]
    try:
        if json.loads(STATE_FILE.read_text(encoding="utf-8")).get("hash") == digest:
            return
    except (OSError, ValueError):
        pass

    if send(cfg, text):
        STATE_FILE.write_text(json.dumps({"hash": digest}), encoding="utf-8")
        log("已转发 %d 字符 hash=%s", len(text), digest)


if __name__ == "__main__":
    try:
        main()
    except Exception as e:  # 兜底：任何异常都不能影响会话
        log("异常 %r", e)
