# run with ./chat_curl_tool_response.sh  | python3 -m json.tool
curl -X POST "http://localhost:11434/v1/chat/completions"\
     -s -H "Content-Type: application/json"\
     -d '{
    "model": "llama3.2", "temperature": 0.1, "max_tokens": 1024,
    "messages": [
      {"role": "system", "content": "You are a home assistant."},
      {"role": "user", "content": "Switch on the light"},
      {"role": "tool", "tool_call_id": "0", "name":"lightswitch", "content": "The light was switched on"}
    ],
    "tools": [{
      "type": "function",
      "function": {
        "name": "lightswitch",
        "description": "With this tool you can switch on the light",
        "parameters": {
          "type": "object",
          "properties": {
            "switch": { "type": "boolean", "description": "true for on, false for off" }
          },
          "required": [ "switch" ],
          "additionalProperties": false
        },
        "strict": true
      }
     }],
    "stream": false
  }'
