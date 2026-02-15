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


def turn(messages):
    body = json.dumps({"model": MODEL, "messages": messages, "tools": [TOOL], "stream": False})
    conn = http.client.HTTPConnection(HOST, PORT, timeout=600)
    conn.request("POST", "/v1/chat/completions", body=body, headers={"Content-Type": "application/json"})
    resp = conn.getresponse()
    if resp.status < 200 or resp.status >= 300:
        conn.close(); return "", []
    try: message = ((json.loads(resp.read().decode("utf-8")).get("choices") or [{}])[0].get("message") or {})
    except Exception: conn.close(); return "", []
    conn.close()
    out, calls = message.get("content") or "", message.get("tool_calls") or []
    reqs = []
    for i, tc in enumerate(calls):
        fn = tc.get("function") or {}
        if fn.get("name") not in (None, "bash"):
            continue
        try: cmd = json.loads(fn.get("arguments") or "{}").get("command")
        except Exception: continue
        if isinstance(cmd, str): reqs.append({"id": tc.get("id") or f"call_{i}", "command": cmd})
    return out, reqs


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
        (sys.stdout if argv else sys.stderr).write("Usage: opx-mini-nostream.px <prompt>\n")
        sys.exit(0 if argv else 1)
    prompt = " ".join(argv)
    if not sys.stdin.isatty():
        extra = sys.stdin.read()
        if extra: prompt += "\n\n```\n" + extra + "\n```"
    messages = [{"role": "system", "content": SYSTEM}, {"role": "user", "content": prompt}]

    for _ in range(24):
        text, reqs = turn(messages)
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
