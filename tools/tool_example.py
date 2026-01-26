# -----------------------------------------------------------------------------
#  IMPORTANT NOTE ON TOOL CALLING, STREAMING, AND AGENTIC EXECUTION
# -----------------------------------------------------------------------------
#
#  This example exists to demonstrate several non-obvious but critical facts
#  about OpenAI-compatible Tool Calling when used in a *real orchestrator*,
#  especially with streaming backends such as Ollama.
#
#  The observations below are not theoretical. They were discovered by
#  instrumenting the raw HTTP streaming protocol and logging every delta event.
#  They are included here to prevent future implementations from relying on
#  incorrect assumptions.
#
#  ---------------------------------------------------------------------------
#  1. TOOL CALLS ARE NOT TOKENS
#  ---------------------------------------------------------------------------
#
#  Tool calls are *not* part of the text token stream. They are emitted via
#  structured delta events (delta.tool_calls), separate from delta.content.
#
#  Consequences:
#    - You must never try to "parse" tool calls out of text.
#    - You do not need lookahead buffers or heuristic token suppression.
#    - Text streaming and tool execution must be handled as separate channels.
#
#  What looks like "one tool call in one token" is actually client-side
#  aggregation of multiple structured deltas.
#
#
#  ---------------------------------------------------------------------------
#  2. MULTIPLE TOOL CALLS IN ONE TURN DO NOT IMPLY SEQUENTIAL EXECUTION
#  ---------------------------------------------------------------------------
#
#  The OpenAI-compatible schema allows *multiple* tool calls to be emitted
#  in a single assistant turn:
#
#      finish_reason = "tool_calls"
#      tool_calls = [call_0, call_1, call_2, ...]
#
#  This does NOT mean:
#    - that these calls are sequential
#    - that later calls depend on earlier ones
#    - that the model has waited for any tool result
#
#  In practice, many models (and Ollama’s adapter layer) interpret tool calling
#  as a *planning interface*, not an execution interface.
#
#  The model may emit an entire tool chain in one turn using *hallucinated
#  placeholder arguments* (e.g. number=42) before any tool has actually run.
#
#  This behavior is schema-compliant but NOT agentically correct.
#
#
#  ---------------------------------------------------------------------------
#  3. PARALLEL TOOL CALLS MUST BE EXPLICITLY JUSTIFIED
#  ---------------------------------------------------------------------------
#
#  Multiple tool calls in one turn should only be executed in parallel if ALL
#  of the following are true:
#
#    - The calls are logically independent
#    - No call depends on the output of another
#    - All arguments are complete and externally valid
#    - The task is inherently parallel (e.g. multiple status queries)
#
#  Data-dependent chains (A → B → C) must NEVER be treated as parallel,
#  even if the model emits them in one batch.
#
#  In an agentic system, the safe default is:
#
#      "Accept at most ONE tool call per turn."
#
#
#  ---------------------------------------------------------------------------
#  4. TOOL USAGE IS OPTIONAL UNLESS YOU FORCE IT
#  ---------------------------------------------------------------------------
#
#  By default, LLMs treat tools as *optional helpers*.
#  If the model believes it can solve a step internally (e.g. simple arithmetic),
#  it may skip the tool entirely and compute the result itself.
#
#  This is correct behavior for an assistant, but WRONG for a deterministic agent.
#
#  If you require tools to be used:
#    - You must state this explicitly (usually in the system message)
#    - You must reject or retry turns where the model bypasses tools
#
#  Example requirement that must be enforced externally:
#
#      "If a tool exists for an operation, the model must call it."
#
#
#  ---------------------------------------------------------------------------
#  5. FINISH_REASON = "tool_calls" IS A TURN BOUNDARY
#  ---------------------------------------------------------------------------
#
#  When finish_reason is "tool_calls":
#    - The current assistant turn is COMPLETE
#    - No further text or tool calls will follow in this turn
#    - The orchestrator must now decide what to execute
#
#  You must never:
#    - wait for silence
#    - infer completion heuristically
#    - continue reading tokens after the finish event
#
#
#  ---------------------------------------------------------------------------
#  6. THE ORCHESTRATOR MUST BE STRICTER THAN THE MODEL
#  ---------------------------------------------------------------------------
#
#  The OpenAI tool schema is intentionally permissive.
#  Agentic correctness is NOT guaranteed by the protocol.
#
#  A correct orchestrator must therefore:
#
#    - Treat tool calls as *requests*, not commands
#    - Validate logical dependencies between tool calls
#    - Enforce one-tool-per-turn if agentic sequencing is required
#    - Reject hallucinated or guessed arguments
#    - Decide explicitly whether parallel execution is allowed
#
#  In other words:
#
#      The model may plan.
#      The orchestrator decides.
#
#
#  ---------------------------------------------------------------------------
#  7. WHY THIS EXAMPLE LOGS EVERYTHING
#  ---------------------------------------------------------------------------
#
#  Without full delta-level logging:
#    - Batch tool planning looks like sequential reasoning
#    - Hallucinated arguments go unnoticed
#    - Tool bypass via self-computation is invisible
#
#  The logs in this example intentionally expose:
#    - raw SSE lines
#    - token-level text output
#    - structured tool call deltas
#    - finish reasons
#
#  This is the minimum level of observability required to build a correct,
#  explainable, and safe tool-using agent.
#
#
#  ---------------------------------------------------------------------------
#  8. FINAL TAKEAWAY
#  ---------------------------------------------------------------------------
#
#  OpenAI-compatible Tool Calling is a *low-level protocol*.
#  Agentic behavior is a *policy layer* on top of it.
#
#  If you want deterministic, step-by-step, causally correct execution:
#
#    - Do not trust the model to sequence itself
#    - Do not execute multiple tool calls blindly
#    - Do not assume tool usage without enforcing it
#
#  Correctness lives in the orchestrator.
#
# -----------------------------------------------------------------------------


import json
import random
import urllib.request

# --- OpenAI-kompatibler HTTP-Client für Ollama ---
API_URL = "http://localhost:11434/v1/chat/completions"
MODEL = "qwen2.5:7b"

# --- Tool-Implementierungen (lokal) ---
def get_random_number():
    return random.randint(1, 100)

def is_even(number: int):
    return "even" if number % 2 == 0 else "odd"

def multiply(number: int, factor: int):
    return number * factor


TOOLS = [
    {
        "type": "function",
        "function": {
            "name": "get_random_number",
            "description": "Return a random integer between 1 and 100",
            "parameters": {"type": "object", "properties": {}}
        }
    },
    {
        "type": "function",
        "function": {
            "name": "is_even",
            "description": "Check if a number is even or odd",
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
            "name": "multiply",
            "description": "Multiply a number by a factor",
            "parameters": {
                "type": "object",
                "properties": {
                    "number": {"type": "integer"},
                    "factor": {"type": "integer"}
                },
                "required": ["number", "factor"]
            }
        }
    }
]

messages = [
    {
        "role": "user",
        "content": (
            "Get a random number. "
            "Check if it is even or odd. "
            "If even, multiply it by 10. "
            "If odd, multiply it by 7. "
            "Use tools."
        )
    }
]


def stream_chat(messages_to_send):
    payload = {
        "model": MODEL,
        "messages": messages_to_send,
        "tools": TOOLS,
        "tool_choice": "auto",
        "stream": True,
    }
    data = json.dumps(payload).encode("utf-8")
    print(f"[EVENT][CONTEXT] {messages}")
    req = urllib.request.Request(
        API_URL,
        data=data,
        headers={"Content-Type": "application/json"},
        method="POST",
    )

    tool_calls = {}
    with urllib.request.urlopen(req) as resp:
        for raw_line in resp:
            line = raw_line.decode("utf-8").strip()
            print(f"[EVENT][LINE] {line}")
            if not line: continue
            if not line.startswith("data: "): continue
            chunk = line[6:]
            if chunk == "[DONE]": break

            event = json.loads(chunk)
            choice = event["choices"][0]
            delta = choice.get("delta", {})

            if "content" in delta and delta["content"]: print(f"[TOKEN][TEXT] {delta['content']!r}")

            if "tool_calls" in delta and delta["tool_calls"]:
                for tc in delta["tool_calls"]:
                    print(f"[EVENT][TOOL_CALL_PART] {tc}")
                    idx = tc.get("index", 0)
                    existing = tool_calls.get(
                        idx,
                        {"id": None, "type": "function", "function": {"name": None, "arguments": ""}},
                    )
                    if "id" in tc: existing["id"] = tc["id"]
                    if "type" in tc: existing["type"] = tc["type"]
                    func = tc.get("function", {})
                    if "name" in func: existing["function"]["name"] = func["name"]
                    if "arguments" in func and func["arguments"]: existing["function"]["arguments"] += func["arguments"]
                    tool_calls[idx] = existing

            if choice.get("finish_reason"): print(f"[EVENT][FINISH] {choice['finish_reason']}")

    tool_call_list = [tool_calls[k] for k in sorted(tool_calls.keys())]
    return tool_call_list


# --- Event-Loop ---
while True:
    print("\n=== NEW LLM TURN ===")

    tool_call_list = stream_chat(messages)

    if not tool_call_list:
        print("=== DONE ===")
        break

    tool_call = tool_call_list[0]
    name = tool_call["function"]["name"]
    args = json.loads(tool_call["function"].get("arguments") or "{}")

    if not tool_call.get("id"): tool_call["id"] = "call_0"

    print(f"[EXECUTE][TOOL] {name}({args})")

    if name == "get_random_number": result = get_random_number()
    elif name == "is_even": result = is_even(**args)
    elif name == "multiply": result = multiply(**args)
    else: raise RuntimeError("Unknown tool")

    print(f"[RESULT][TOOL] {result}")

    messages.append({
        "role": "assistant",
        "tool_calls": [tool_call]
    })
    messages.append({
        "role": "tool",
        "tool_call_id": tool_call["id"],
        "content": str(result)
    })
