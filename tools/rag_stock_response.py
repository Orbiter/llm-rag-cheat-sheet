import http.client
import json


price_history = {
    "symbol": "ACME",
    "currency": "USD",
    "series": [
        {"date": "2024-08-16", "close": 142.35},
        {"date": "2024-08-15", "close": 141.80},
        {"date": "2024-08-14", "close": 140.92},
        {"date": "2024-08-13", "close": 139.64},
        {"date": "2024-08-12", "close": 138.77},
        {"date": "2024-08-09", "close": 137.55},
        {"date": "2024-08-08", "close": 138.10},
        {"date": "2024-08-07", "close": 136.88},
        {"date": "2024-08-06", "close": 135.41},
        {"date": "2024-08-05", "close": 134.97},
        {"date": "2024-08-02", "close": 133.52},
        {"date": "2024-08-01", "close": 134.11},
        {"date": "2024-07-31", "close": 133.84},
        {"date": "2024-07-30", "close": 132.56},
        {"date": "2024-07-29", "close": 131.73},
        {"date": "2024-07-26", "close": 130.42},
        {"date": "2024-07-25", "close": 129.88},
        {"date": "2024-07-24", "close": 128.65},
        {"date": "2024-07-23", "close": 127.90},
        {"date": "2024-07-22", "close": 127.15},
    ],
}

recent_news = {
    "symbol": "ACME",
    "articles": [
        {
            "headline": "ACME launches AI-powered logistics platform",
            "published_at": "2024-08-15",
            "summary": (
                "ACME expanded its cloud logistics suite with AI routing features, "
                "projecting a 12% reduction in fulfillment costs for pilot customers."
            ),
        },
        {
            "headline": "Analysts raise ACME outlook after strong Q2",
            "published_at": "2024-08-09",
            "summary": (
                "Following a 9% year-over-year revenue increase, several brokerages "
                "upgraded ACME citing resilient subscription growth."
            ),
        },
    ],
}

messages = [
    {"role": "system", "content": "You are a pragmatic equity analyst."},
    {
        "role": "user",
        "content": "Provide a valuation outlook for ACME Corp (ticker: ACME) based on recent performance.",
    },
    {
        "role": "assistant",
        "content": "",
        "tool_calls": [
            {
                "id": "price_history_001",
                "type": "function",
                "function": {
                    "name": "fetch_price_history",
                    "arguments": json.dumps({"symbol": "ACME", "period_days": 20}),
                },
            },
            {
                "id": "news_001",
                "type": "function",
                "function": {
                    "name": "fetch_recent_news",
                    "arguments": json.dumps({"symbol": "ACME", "limit": 3}),
                },
            },
        ],
    },
    {
        "role": "tool",
        "tool_call_id": "price_history_001",
        "name": "fetch_price_history",
        "content": json.dumps(price_history),
    },
    {
        "role": "tool",
        "tool_call_id": "news_001",
        "name": "fetch_recent_news",
        "content": json.dumps(recent_news),
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
