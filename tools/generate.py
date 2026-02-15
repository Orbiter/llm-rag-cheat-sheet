#!/usr/bin/env python3
import argparse
import json
import http.client
from pathlib import Path

# -----------------------------
# Configuration
# -----------------------------

MODEL = "llama3.2"
OUTPUT_CONTEXT = "context.json"


# -----------------------------
# Tool Definition
# -----------------------------

TOOLS = [{
    "type": "function",
    "function": {
        "name": "file.write",
        "strict": True,
        "description": (
            "Create or overwrite a single source file with full content.\n\n"
            "Tool response format (JSON):\n"
            "{\n"
            "  \"type\": \"file.write\",\n"
            "  \"version\": 1,\n"
            "  \"ok\": true | false,\n"
            "  \"data\": {\n"
            "    \"path\": string,\n"
            "    \"bytes_written\": number\n"
            "  } | null,\n"
            "  \"error\": string | null\n"
            "}"
        ),
        "parameters": {
            "type": "object",
            "properties": {
                "path": {
                    "type": "string",
                    "description": "Target file path"
                },
                "content": {
                    "type": "string",
                    "description": "Full file content"
                }
            },
            "required": ["path", "content"],
            "additionalProperties": False
        }
    }
}]


# -----------------------------
# Main
# -----------------------------

def main():
    parser = argparse.ArgumentParser(description="Minimal one-shot coding agent")
    parser.add_argument("prompt", help="Programming task prompt")
    parser.add_argument("--output", default="output.py", help="Output file name")
    args = parser.parse_args()

    messages = [
        {
            "role": "system",
            "content": (
                "You are a coding agent. "
                "Generate a complete Python program. "
                "Use the file.write tool exactly once."
            )
        },
        {
            "role": "user",
            "content": args.prompt
        }
    ]

    payload = {
        "model": MODEL,
        "temperature": 0.1,
        "max_tokens": 2048,
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

    # Persist full context for repair agent
    Path(OUTPUT_CONTEXT).write_text(json.dumps({
        "request": payload,
        "response": response
    }, indent=2))

    # Extract tool call
    tool_call = response["choices"][0]["message"]["tool_calls"][0]
    args_obj = tool_call["function"]["arguments"]

    # Enforce deterministic output filename
    output_path = Path(args.output)
    content = args_obj["content"]

    output_path.write_text(content)

    # Tool response envelope (logged only)
    tool_response = {
        "type": "file.write",
        "version": 1,
        "ok": True,
        "data": {
            "path": str(output_path),
            "bytes_written": len(content.encode("utf-8"))
        },
        "error": None
    }

    print(json.dumps(tool_response, indent=2))


if __name__ == "__main__":
    main()
