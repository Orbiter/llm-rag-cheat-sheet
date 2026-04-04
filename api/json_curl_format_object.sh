#!/usr/bin/env bash
set -euo pipefail

curl -sS http://localhost:11434/v1/chat/completions \
  -H 'Content-Type: application/json' \
  -d '{
    "model": "llama3.2:3b",
    "temperature": 0, "max_tokens": 1024,
    "think": false, "reasoning_effort": "none",
    "messages": [
      {"role": "system", "content": "Translate into Spanish, and Italian."},
      {"role": "user", "content": "I love programming."}
    ],
    "stream": false,
    "response_format": {
      "type": "json_schema",
      "json_schema": {
        "strict": true,
        "schema": {
          "type": "object",
          "properties": {
            "spanish": { "type": "string" }, "italian": { "type": "string" }
          },
          "required": ["spanish", "italian"]
        }
      }
    }
  }' \
  | jq .
