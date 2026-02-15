#!/usr/bin/env python3
import json, subprocess, sys, http.client

HOST, PORT = "localhost", 11434
MODEL = "qwen3:30b-a3b-instruct-2507-q4_K_M"
SYSTEM = "You are a Linux operator. Use bash when needed. Keep answers short."
TOOL = {"type": "function", "function": {
    "name": "bash",
    "description": "Run a shell command via /bin/bash and return stdout/stderr.",
    "parameters": {"type": "object", "properties": {"command": {"type": "string"}}, "required": ["command"], "additionalProperties": False},
    "strict": True,
}}


def stream_turn(messages):
    body = json.dumps({"model": MODEL, "messages": messages, "tools": [TOOL], "stream": True})
    conn = http.client.HTTPConnection(HOST, PORT, timeout=600)
    conn.request("POST", "/v1/chat/completions", body=body, headers={"Content-Type": "application/json"})
    resp = conn.getresponse()
    if resp.status < 200 or resp.status >= 300:
        conn.close(); return "", []
    out, calls = [], []
    while True:
        line = resp.readline()
        if not line: break
        if not line.startswith(b"data:"): continue
        data = line[5:].strip()
        if data == b"[DONE]": break
        try: delta = ((json.loads(data).get("choices") or [{}])[0].get("delta") or {})
        except json.JSONDecodeError: continue
        c = delta.get("content")
        if c: out.append(c); sys.stdout.write(c); sys.stdout.flush()
        for tc in (delta.get("tool_calls") or []):
            i = tc.get("index") if isinstance(tc.get("index"), int) else len(calls)
            while len(calls) <= i: calls.append({"id": None, "args": ""})
            if tc.get("id"): calls[i]["id"] = tc["id"]
            a = (tc.get("function") or {}).get("arguments")
            if a: calls[i]["args"] += a
    conn.close()
    reqs = []
    for i, tc in enumerate(calls):
        try: cmd = json.loads(tc["args"] or "{}").get("command")
        except json.JSONDecodeError: continue
        if isinstance(cmd, str): reqs.append({"id": tc["id"] or f"call_{i}", "command": cmd})
    return "".join(out), reqs


def run_bash(cmd):
    try:
        p = subprocess.run(["/bin/bash", "-lc", cmd], capture_output=True, text=True, timeout=10)
        return {"tool": "bash", "ok": p.returncode == 0, "exit_code": p.returncode, "stdout": p.stdout, "stderr": p.stderr}
    except subprocess.TimeoutExpired as e:
        return {"tool": "bash", "ok": False, "exit_code": 124, "stdout": e.stdout if isinstance(e.stdout, str) else "", "stderr": "Timed out"}
    except OSError as e:
        return {"tool": "bash", "ok": False, "exit_code": 1, "stdout": "", "stderr": str(e)}


def main():
    argv = sys.argv[1:]
    if not argv or argv[0] in ("-h", "--help"):
        (sys.stdout if argv else sys.stderr).write("Usage: opx-mini.py <prompt>\n")
        sys.exit(0 if argv else 1)
    prompt = " ".join(argv)
    if not sys.stdin.isatty():
        extra = sys.stdin.read()
        if extra: prompt += "\n\n```\n" + extra + "\n```"
    messages = [{"role": "system", "content": SYSTEM}, {"role": "user", "content": prompt}]

    for _ in range(24):
        text, reqs = stream_turn(messages)
        if not reqs:
            if text and not text.endswith("\n"): sys.stdout.write("\n")
            return
        tool_calls = [{"id": r["id"], "type": "function", "function": {"name": "bash", "arguments": json.dumps({"command": r["command"]})}} for r in reqs]
        messages.append({"role": "assistant", "tool_calls": tool_calls})
        for r in reqs:
            print(f"\nApprove bash command? [y/N]\n{r['command']}")
            ok = sys.stdin.readline().strip().lower() in ("y", "yes")
            res = run_bash(r["command"]) if ok else {"tool": "bash", "ok": False, "exit_code": 1, "stdout": "", "stderr": "Rejected by user"}
            if res["stdout"]: sys.stdout.write(res["stdout"] + ("" if res["stdout"].endswith("\n") else "\n"))
            if res["stderr"]: sys.stderr.write(res["stderr"] + ("" if res["stderr"].endswith("\n") else "\n"))
            messages.append({"role": "tool", "tool_call_id": r["id"], "content": json.dumps(res)})

    print("Reached max turns (24); aborting run.", file=sys.stderr)


if __name__ == "__main__":
    main()
