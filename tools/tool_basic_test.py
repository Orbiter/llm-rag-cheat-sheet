#!/usr/bin/env python3
"""
tool_call_conformance_test.py

This script tests whether an LLM emits *agentically correct* tool calls
when accessed via the OpenAI-compatible Ollama API.

It explicitly distinguishes between:

  1. Correct sequential tool calls (agentic, causal)
  2. Legitimate parallel tool calls (independent)
  3. Hallucinated or invalid sequential tool calls (planned, non-causal)

The test is intentionally strict. Many models will FAIL parts of it.
That is expected.

USAGE:
    python3 tool_call_conformance_test.py qwen2.5:7b

REQUIREMENTS:
    - Ollama running on http://localhost:11434
    - Model must support tool calling
"""

import sys
import json
import random
import urllib.request
from typing import List, Dict, Any

# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------

OLLAMA_API = "http://localhost:11434/v1/chat/completions"

if len(sys.argv) != 2:
    print("Usage: python3 tool_call_conformance_test.py <model_name>")
    sys.exit(1)

MODEL = sys.argv[1]

# ---------------------------------------------------------------------------
# Tool definitions
#
# These tools are intentionally simple but semantically distinct:
#
# - get_random_number(): non-deterministic, cannot be guessed
# - is_even(n): depends on prior tool output
# - add(a,b): deterministic but MUST be called when requested
# - get_time(): independent, safe for parallel execution
# ---------------------------------------------------------------------------

TOOLS = [
    {
        "type": "function",
        "function": {
            "name": "get_random_number",
            "description": "Return a random integer between 1 and 100. The value is unknown until the tool runs.",
            "parameters": {"type": "object", "properties": {}}
        }
    },
    {
        "type": "function",
        "function": {
            "name": "is_even",
            "description": "Check whether a number is even or odd. Must be called with a real number.",
            "parameters": {
                "type": "object",
                "properties": {
                    "number": {"type": "integer"}
                },
                "required": ["number"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "add",
            "description": "Add two integers. Do not compute internally.",
            "parameters": {
                "type": "object",
                "properties": {
                    "a": {"type": "integer"},
                    "b": {"type": "integer"}
                },
                "required": ["a", "b"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "get_time",
            "description": "Return the current system time.",
            "parameters": {"type": "object", "properties": {}}
        }
    },
]

# ---------------------------------------------------------------------------
# Local tool implementations (used only when executing accepted calls)
# ---------------------------------------------------------------------------

def get_random_number():
    return random.randint(1, 100)

def is_even(number: int):
    return "even" if number % 2 == 0 else "odd"

def add(a: int, b: int):
    return a + b

def get_time():
    return "12:00"  # fixed on purpose, not relevant for logic

TOOL_IMPL = {
    "get_random_number": get_random_number,
    "is_even": is_even,
    "add": add,
    "get_time": get_time,
}

# ---------------------------------------------------------------------------
# Streaming helper
# ---------------------------------------------------------------------------

def stream_chat(messages: List[Dict[str, Any]]) -> Dict[str, Any]:
    """
    Sends a streaming chat request and returns:
      - tool_calls: list of tool call objects
      - finish_reason
      - raw_text (concatenated)
    """

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
                    tool_calls.setdefault(idx, {
                        "id": None,
                        "name": None,
                        "arguments": ""
                    })
                    if "id" in tc:
                        tool_calls[idx]["id"] = tc["id"]
                    if "function" in tc:
                        if "name" in tc["function"]:
                            tool_calls[idx]["name"] = tc["function"]["name"]
                        if "arguments" in tc["function"]:
                            tool_calls[idx]["arguments"] += tc["function"]["arguments"]

            if choice.get("finish_reason"):
                finish_reason = choice["finish_reason"]

    ordered_calls = [tool_calls[k] for k in sorted(tool_calls)]
    return {
        "tool_calls": ordered_calls,
        "finish_reason": finish_reason,
        "text": "".join(text_out)
    }

# ---------------------------------------------------------------------------
# TEST 1: Sequential causality test
#
# The model MUST:
#   - call get_random_number
#   - wait for result
#   - call is_even with the REAL number
#
# Any pre-filled number is a failure.
# ---------------------------------------------------------------------------

def test_sequential_causality():
    print("\nTEST 1: Sequential causality")

    messages = [{
        "role": "system",
        "content": (
            "You are an execution agent. "
            "Call exactly one tool per message. "
            "Wait for tool results. "
            "Do not guess values."
        )
    },{
        "role": "user",
        "content": "Get a random number, then check if it is even."
    }]

    r1 = stream_chat(messages)

    if len(r1["tool_calls"]) != 1 or r1["tool_calls"][0]["name"] != "get_random_number":
        print("FAIL: Expected get_random_number as first tool call")
        return False

    value = get_random_number()
    messages.append({"role": "tool", "tool_call_id": r1["tool_calls"][0]["id"], "content": str(value)})

    r2 = stream_chat(messages)

    if len(r2["tool_calls"]) != 1 or r2["tool_calls"][0]["name"] != "is_even":
        print("FAIL: Expected is_even as second tool call")
        return False

    args = json.loads(r2["tool_calls"][0]["arguments"] or "{}")
    if args.get("number") != value:
        print("FAIL: is_even called with hallucinated value:", args)
        return False

    print("PASS")
    return True

# ---------------------------------------------------------------------------
# TEST 2: Parallel independence test
#
# The model is asked for TWO INDEPENDENT facts.
# It MAY emit parallel tool calls.
# This is allowed only if:
#   - both calls are independent
#   - no shared data
# ---------------------------------------------------------------------------

def test_parallel_independence():
    print("\nTEST 2: Parallel independence")

    messages = [{
        "role": "user",
        "content": "Get the current time and also get a random number."
    }]

    r = stream_chat(messages)

    names = [tc["name"] for tc in r["tool_calls"]]

    if set(names) == {"get_time", "get_random_number"} and len(names) == 2:
        print("PASS (parallel calls accepted)")
        return True

    if len(names) == 1:
        print("PASS (sequential but acceptable)")
        return True

    print("FAIL: Unexpected tool call pattern:", names)
    return False

# ---------------------------------------------------------------------------
# TEST 3: Tool bypass / self-computation test
#
# The model MUST use the add() tool.
# If it computes internally, it fails.
# ---------------------------------------------------------------------------

def test_tool_bypass():
    print("\nTEST 3: Tool bypass prevention")

    messages = [{
        "role": "system",
        "content": "You must use tools for all computations."
    },{
        "role": "user",
        "content": "Add 7 and 9."
    }]

    r = stream_chat(messages)

    if r["tool_calls"]:
        if r["tool_calls"][0]["name"] == "add":
            print("PASS")
            return True
        else:
            print("FAIL: Wrong tool called:", r["tool_calls"])
            return False

    print("FAIL: Model computed internally:", r["text"])
    return False

# ---------------------------------------------------------------------------
# MAIN
# ---------------------------------------------------------------------------

results = {
    "sequential": test_sequential_causality(),
    "parallel": test_parallel_independence(),
    "tool_bypass": test_tool_bypass(),
}

print("\n=== FINAL RESULT ===")
for k, v in results.items():
    print(f"{k:20s}: {'PASS' if v else 'FAIL'}")

if all(results.values()):
    print("\nOVERALL: MODEL IS TOOL-CALL CONFORMANT (AGENTIC)")
else:
    print("\nOVERALL: MODEL FAILS ONE OR MORE AGENTIC TOOL TESTS")
