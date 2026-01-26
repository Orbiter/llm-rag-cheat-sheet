#!/usr/bin/env python3
"""
minimal_coding_agent_test.py

This script evaluates whether a model is suitable as a *coding agent core*
(e.g. Claude Code, Codex, OpenCode) in a minimal, tool-driven environment.

It tests:
  - disciplined tool usage
  - incremental code modification
  - correct handling of test failures
  - state consistency across turns
  - resistance to "rewrite everything" behavior

The goal is NOT to test how well the model writes code,
but how well it behaves as an agent.
"""

import sys
import json
import urllib.request

OLLAMA_API = "http://localhost:11434/v1/chat/completions"

if len(sys.argv) != 2:
    print("Usage: python3 minimal_coding_agent_test.py <model_name>")
    sys.exit(1)

MODEL = sys.argv[1]

# ---------------------------------------------------------------------------
# Simulated file system (minimal, in-memory)
# ---------------------------------------------------------------------------

FILES = {}

def write_file(path, content):
    FILES[path] = content
    return "OK"

def read_file(path):
    if path not in FILES:
        return "ERROR: file does not exist"
    return FILES[path]

def run_tests():
    """
    Very small test harness.
    Expects add(2,3) == 5.
    """
    code = FILES.get("math_utils.py", "")
    if "def add" not in code:
        return "FAIL: add() not defined"
    if "return a + b" not in code:
        return "FAIL: add() implementation incorrect"
    return "PASS"

TOOLS = [
    {
        "type": "function",
        "function": {
            "name": "write_file",
            "description": "Write content to a file. Overwrites existing content.",
            "parameters": {
                "type": "object",
                "properties": {
                    "path": {"type": "string"},
                    "content": {"type": "string"},
                },
                "required": ["path", "content"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "read_file",
            "description": "Read the full content of a file.",
            "parameters": {
                "type": "object",
                "properties": {
                    "path": {"type": "string"},
                },
                "required": ["path"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "run_tests",
            "description": "Run unit tests and return PASS or FAIL.",
            "parameters": {"type": "object", "properties": {}}
        }
    },
]

TOOL_IMPL = {
    "write_file": write_file,
    "read_file": read_file,
    "run_tests": run_tests,
}

# ---------------------------------------------------------------------------
# Streaming helper (same structure as previous tests)
# ---------------------------------------------------------------------------

def stream_chat(messages):
    payload = {
        "model": MODEL,
        "messages": messages,
        "tools": TOOLS,
        "tool_choice": "auto",
        "stream": True,
    }

    req = urllib.request.Request(
        OLLAMA_API,
        data=json.dumps(payload).encode("utf-8"),
        headers={"Content-Type": "application/json"},
        method="POST",
    )

    tool_calls = {}
    text_out = []
    finish_reason = None

    with urllib.request.urlopen(req) as resp:
        for raw_line in resp:
            line = raw_line.decode("utf-8").strip()
            if not line or not line.startswith("data: "):
                continue
            data = line[6:]
            if data == "[DONE]":
                break

            event = json.loads(data)
            choice = event["choices"][0]
            delta = choice.get("delta", {})

            if "content" in delta and delta["content"]:
                text_out.append(delta["content"])

            if "tool_calls" in delta:
                for tc in delta["tool_calls"]:
                    idx = tc["index"]
                    tool_calls.setdefault(idx, {"id": None, "name": None, "arguments": ""})
                    if "id" in tc:
                        tool_calls[idx]["id"] = tc["id"]
                    if "function" in tc:
                        if "name" in tc["function"]:
                            tool_calls[idx]["name"] = tc["function"]["name"]
                        if "arguments" in tc["function"]:
                            tool_calls[idx]["arguments"] += tc["function"]["arguments"]

            if choice.get("finish_reason"):
                finish_reason = choice["finish_reason"]

    return {
        "tool_calls": [tool_calls[k] for k in sorted(tool_calls)],
        "text": "".join(text_out),
        "finish_reason": finish_reason,
    }

# ---------------------------------------------------------------------------
# TEST: Minimal coding agent loop
# ---------------------------------------------------------------------------

print("\nTEST: Minimal Coding Agent")

messages = [
    {
        "role": "system",
        "content": (
            "You are a coding agent.\n"
            "You must use tools to read and write files.\n"
            "Do not rewrite files unless necessary.\n"
            "Fix only what is broken.\n"
            "Call exactly one tool per response."
        )
    },
    {
        "role": "user",
        "content": (
            "Create a file math_utils.py with a function add(a,b).\n"
            "Then run tests.\n"
            "If tests fail, fix the code."
        )
    }
]

MAX_TURNS = 8
passed = False
violations = []

for turn in range(MAX_TURNS):
    r = stream_chat(messages)

    if r["tool_calls"]:
        tc = r["tool_calls"][0]
        name = tc["name"]
        #args = json.loads(tc["arguments"] or "{}")
        # some models attach text to the json of the tool call, we filter out the first valid json to identify that
        def parse_json_prefix(s: str):
            s = s.strip()
            if not s:
                return {}
            for i in range(1, len(s) + 1):
                try:
                    return json.loads(s[:i])
                except json.JSONDecodeError:
                    continue
            raise ValueError(f"Invalid JSON arguments: {s!r}")

        args = parse_json_prefix(tc["arguments"])
        if tc["arguments"].strip() != json.dumps(args):
            violations.append("Tool arguments not clean JSON")
        
        if name not in TOOL_IMPL:
            violations.append(f"Unknown tool {name}")
            break

        try:
            result = TOOL_IMPL[name](**args)
        except TypeError as e:
            violations.append(
                f"Invalid arguments for tool '{name}': {args}"
            )
            break

        messages.append({
            "role": "tool",
            "tool_call_id": tc["id"],
            "content": str(result)
        })

        if name == "run_tests" and result == "PASS":
            passed = True
            break

    else:
        # Text-only response is usually a failure in agent mode
        violations.append("Text output without tool call")
        break

# ---------------------------------------------------------------------------
# Final evaluation
# ---------------------------------------------------------------------------

print("\n=== RESULT ===")

if passed and not violations:
    print("PASS: Model behaves like a disciplined coding agent")
elif passed:
    print("PARTIAL PASS: Model is agent-capable but requires discipline enforcement")
    for v in violations:
        print(" -", v)
else:
    print("FAIL: Model is not suitable as a coding agent")
    for v in violations:
        print(" -", v)
        
print("\nFinal file content:")
print(FILES.get("math_utils.py", "<missing>"))
