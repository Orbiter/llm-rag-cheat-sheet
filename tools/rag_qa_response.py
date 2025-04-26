import http.client
import json


rag_result_with_qa = {
    "query": "Summarize the market-based mechanisms introduced by the Kyoto Protocol.",
    "results": [
        {
            "document_id": "policy-docs-kyoto-001",
            "title": "Kyoto Protocol Article 17 Explained",
            "snippet": (
                "Article 17 of the Kyoto Protocol establishes international emissions trading, "
                "allowing countries with surplus units to sell them to parties exceeding their "
                "assigned amount. It works alongside Joint Implementation and the Clean Development "
                "Mechanism to lower compliance costs."
            ),
            "qa_pairs": [
                {
                    "question": "Which flexible mechanisms help countries meet Kyoto targets?",
                    "answer": (
                        "The protocol combines international emissions trading, Joint Implementation, and the Clean "
                        "Development Mechanism so nations can offset emissions cost-effectively."
                    ),
                },
                {
                    "question": "How does emissions trading support compliance?",
                    "answer": (
                        "Parties with surplus allowances can sell them to countries above their limits, creating price "
                        "signals that incentivize overall reductions."
                    ),
                },
            ],
        }
    ],
}

messages = [
    {"role": "system", "content": "You are an environmental policy analyst."},
    {
        "role": "user",
        "content": "How did the Kyoto Protocol use market mechanisms to control emissions?",
    },
    {
        "role": "assistant",
        "content": "",
        "tool_calls": [
            {
                "id": "semantic_search_qa_001",
                "type": "function",
                "function": {
                    "name": "semantic_search",
                    "arguments": json.dumps({"query": "Kyoto Protocol market mechanisms"}),
                },
            }
        ],
    },
    {
        "role": "tool",
        "tool_call_id": "semantic_search_qa_001",
        "name": "semantic_search",
        "content": json.dumps(rag_result_with_qa),
    },
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
