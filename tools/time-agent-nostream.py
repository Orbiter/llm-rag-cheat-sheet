#!/usr/bin/env python3
import json, sys, http.client
from datetime import datetime

HOST, PORT = "localhost", 11434
MODEL = "qwen3:30b-a3b-instruct-2507-q4_K_M"
SYSTEM = "You are a concise assistant. Use the datetime tool when needed."
TOOL = {"type": "function", "function": {
    "name": "datetime",
    "description": "Return current local date and time.",
    "parameters": {"type": "object", "properties": {}, "required": [], "additionalProperties": False},
    "strict": True,
}}


def turn(messages):
    body = json.dumps({"model": MODEL, "messages": messages, "tools": [TOOL], "stream": False})
    c = http.client.HTTPConnection(HOST, PORT, timeout=600)
    c.request("POST", "/v1/chat/completions", body=body, headers={"Content-Type": "application/json"})
    r = c.getresponse()
    if r.status < 200 or r.status >= 300:
        c.close(); return "", []
    try: d = json.loads(r.read().decode("utf-8"))
    except Exception: c.close(); return "", []
    c.close()
    m = ((d.get("choices") or [{}])[0].get("message") or {})
    text = m.get("content") or ""
    calls = m.get("tool_calls") or []
    reqs = [{"id": tc.get("id") or f"call_{i}"} for i, tc in enumerate(calls)]
    return text, reqs


def main():
    argv = sys.argv[1:]
    if not argv or argv[0] in ("-h", "--help"):
        (sys.stdout if argv else sys.stderr).write("Usage: time-agent-nostream.py <prompt>\n")
        sys.exit(0 if argv else 1)
    prompt = " ".join(argv)
    if not sys.stdin.isatty():
        x = sys.stdin.read()
        if x: prompt += "\n\n```\n" + x + "\n```"
    messages = [{"role": "system", "content": SYSTEM}, {"role": "user", "content": prompt}]

    for _ in range(12):
        text, reqs = turn(messages)
        if text:
            sys.stdout.write(text + ("" if text.endswith("\n") else "\n"))
            sys.stdout.flush()
        if not reqs:
            return
        messages.append({"role": "assistant", "tool_calls": [
            {"id": r["id"], "type": "function", "function": {"name": "datetime", "arguments": "{}"}} for r in reqs
        ]})
        res = {"tool": "datetime", "ok": True, "datetime": datetime.now().strftime("%Y-%m-%d %H:%M:%S")}
        for r in reqs:
            messages.append({"role": "tool", "tool_call_id": r["id"], "content": json.dumps(res)})

    print("Reached max turns (12); aborting run.", file=sys.stderr)


if __name__ == "__main__":
    main()
