#!/usr/bin/env python3
import argparse
import json
import http.client
import subprocess
import tempfile
from pathlib import Path


# -----------------------------
# Configuration
# -----------------------------

MODEL = "llama3.2"
CONTEXT_FILE = "context.json"


# -----------------------------
# Tool Definition
# -----------------------------

TOOLS = [{
    "type": "function",
    "function": {
        "name": "file.patch",
        "strict": True,
        "description": (
            "Apply a unified diff to an existing file.\n\n"
            "Tool response format (JSON):\n"
            "{\n"
            "  \"type\": \"file.patch\",\n"
            "  \"version\": 1,\n"
            "  \"ok\": true | false,\n"
            "  \"data\": {\n"
            "    \"path\": string,\n"
            "    \"lines_added\": number,\n"
            "    \"lines_removed\": number\n"
            "  } | null,\n"
            "  \"error\": string | null\n"
            "}"
        ),
        "parameters": {
            "type": "object",
            "properties": {
                "path": {
                    "type": "string",
                    "description": "Path of file to patch"
                },
                "diff": {
                    "type": "string",
                    "description": "Unified diff"
                }
            },
            "required": ["path", "diff"],
            "additionalProperties": False
        }
    }
}]


# -----------------------------
# Helpers
# -----------------------------

def apply_patch(diff: str) -> dict:
    with tempfile.NamedTemporaryFile("w+", delete=False) as f:
        f.write(diff)
        f.flush()
        result = subprocess.run(
            ["patch", "-p1"],
            stdin=open(f.name),
            capture_output=True,
            text=True
        )

    if result.returncode != 0:
        return {
            "ok": False,
            "error": result.stderr.strip()
        }

    added = sum(1 for l in diff.splitlines() if l.startswith("+") and not l.startswith("+++"))
    removed = sum(1 for l in diff.splitlines() if l.startswith("-") and not l.startswith("---"))

    return {
        "ok": True,
        "lines_added": added,
        "lines_removed": removed
    }


# -----------------------------
# Main
# -----------------------------

def main():
    parser = argparse.ArgumentParser(description="Repair agent using diffs")
    parser.add_argument("error", help="Runtime error message")
    args = parser.parse_args()

    context = json.loads(Path(CONTEXT_FILE).read_text())

    messages = context["request"]["messages"] + [
        {
            "role": "user",
            "content": (
                "The program failed with the following error:\n\n"
                f"{args.error}\n\n"
                "Fix the program by applying a minimal unified diff."
            )
        }
    ]

    payload = {
        "model": MODEL,
        "temperature": 0.1,
        "max_tokens": 1024,
        "tools": TOOLS,
        "messages": messages,
        "stream": False
    }

    conn = http.client.HTTPConnection("localhost", 11434)
    conn.request(
        "POST",
        "/v1/chat/completions",
        json.dumps(payload),
        {"Content-Type": "application/json"}
    )

    response = json.loads(conn.getresponse().read())
    conn.close()

    tool_call = response["choices"][0]["message"]["tool_calls"][0]
    args_obj = tool_call["function"]["arguments"]

    patch_result = apply_patch(args_obj["diff"])

    if not patch_result["ok"]:
        print(json.dumps({
            "type": "file.patch",
            "version": 1,
            "ok": False,
            "data": None,
            "error": patch_result["error"]
        }, indent=2))
        return

    tool_response = {
        "type": "file.patch",
        "version": 1,
        "ok": True,
        "data": {
            "path": args_obj["path"],
            "lines_added": patch_result["lines_added"],
            "lines_removed": patch_result["lines_removed"]
        },
        "error": None
    }

    print(json.dumps(tool_response, indent=2))


if __name__ == "__main__":
    main()
