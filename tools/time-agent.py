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


def stream_turn(messages):
    body = json.dumps({"model": MODEL, "messages": messages, "tools": [TOOL], "stream": True})
    c = http.client.HTTPConnection(HOST, PORT, timeout=600)
    c.request("POST", "/v1/chat/completions", body=body, headers={"Content-Type": "application/json"})
    r = c.getresponse()
    if r.status < 200 or r.status >= 300:
        c.close(); return "", []
    out, calls = [], []
    while True:
        line = r.readline()
        if not line: break
        if not line.startswith(b"data:"): continue
        data = line[5:].strip()
        if data == b"[DONE]": break
        try: d = ((json.loads(data).get("choices") or [{}])[0].get("delta") or {})
        except json.JSONDecodeError: continue
        t = d.get("content")
        if t: out.append(t); sys.stdout.write(t); sys.stdout.flush()
        for tc in (d.get("tool_calls") or []):
            i = tc.get("index") if isinstance(tc.get("index"), int) else len(calls)
            while len(calls) <= i: calls.append({"id": None})
            if tc.get("id"): calls[i]["id"] = tc["id"]
    c.close()
    return "".join(out), [{"id": x["id"] or f"call_{i}"} for i, x in enumerate(calls)]


def main():
    argv = sys.argv[1:]
    if not argv or argv[0] in ("-h", "--help"):
        (sys.stdout if argv else sys.stderr).write("Usage: time-agent.py <prompt>\n")
        sys.exit(0 if argv else 1)
    prompt = " ".join(argv)
    if not sys.stdin.isatty():
        x = sys.stdin.read()
        if x: prompt += "\n\n```\n" + x + "\n```"
    messages = [{"role": "system", "content": SYSTEM}, {"role": "user", "content": prompt}]

    for _ in range(12):
        text, reqs = stream_turn(messages)
        if not reqs:
            if text and not text.endswith("\n"): sys.stdout.write("\n")
            return
        messages.append({"role": "assistant", "tool_calls": [
            {"id": r["id"], "type": "function", "function": {"name": "datetime", "arguments": "{}"}} for r in reqs
        ]})
        now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        res = {"tool": "datetime", "ok": True, "datetime": now}
        for r in reqs:
            messages.append({"role": "tool", "tool_call_id": r["id"], "content": json.dumps(res)})

    print("Reached max turns (12); aborting run.", file=sys.stderr)


if __name__ == "__main__":
    main()
