import http.client
import json


rag_result = {
    "query": "Explain the historical impact of the Peace of Westphalia.",
    "results": [
        {
            "document_id": "histories-1648",
            "title": "Aftermath of the Thirty Years' War",
            "snippet": (
                "The 1648 Peace of Westphalia ended the Thirty Years' War and affirmed "
                "state sovereignty across Europe, reducing papal influence and laying the "
                "groundwork for modern nation-states."
            ),
        }
    ],
}

messages = [
    {"role": "system", "content": "You are a concise historian."},
    {"role": "user",
     "content": "What lasting impact did the Peace of Westphalia have on European politics?"},
    {"role": "assistant",
     "content": "",
     "tool_calls": [
            {
                "id": "search_001",
                "type": "function",
                "function": {
                    "name": "semantic_search",
                    "arguments": json.dumps(
                        {
                            "query": "Peace of Westphalia long-term impact",
                        }
                    ),
                },
            }
        ],
    },
    {"role": "tool",
     "tool_call_id": "search_001",
     "name": "semantic_search",
     "content": json.dumps(rag_result)},
]

payload = {
    "model": "qwen3:4b-instruct-2507-q4_K_M",
    "temperature": 0.2,
    "max_tokens": 1024,
    "messages": messages,
    "stream": False,
}

conn = http.client.HTTPConnection("localhost", 11434)

try:
  conn.request(
      "POST",
      "/v1/chat/completions",
      json.dumps(payload),
      {"Content-Type": "application/json"},
  )
  response = conn.getresponse()
  response_payload = json.loads(response.read().decode())
  print(json.dumps(response_payload, indent=2))
except Exception as exc:
  print(f"Error: {exc}")
finally:
  conn.close()
