import http.client
import json
from typing import Dict


def fake_weather_service(location: str) -> Dict[str, str]:
  """Return a mock weather payload for the requested location."""
  return {
      "location": location,
      "temperature_c": 22,
      "conditions": "Partly cloudy",
      "wind_kmh": 14,
  }


tools = [{
    "type": "function",
    "function": {
        "name": "get_weather",
        "description": "Get current temperature for a given location.",
        "parameters": {
            "type": "object",
            "properties": {
                "location": {
                    "type": "string",
                    "description": "City and country e.g. Bogotá, Colombia",
                }
            },
            "required": ["location"],
            "additionalProperties": False,
        },
        "strict": True,
    },
}]

initial_messages = [
    {"role": "system", "content": "You are a helpful assistant."},
    {"role": "user", "content": "What is the weather like today in Berlin, Germany?"},
]

initial_payload = {
    "model": "qwen3:4b-instruct-2507-q4_K_M",
    "temperature": 0.1,
    "max_tokens": 1024,
    "messages": initial_messages,
    "tools": tools,
    "stream": False,
}

conn = http.client.HTTPConnection("localhost", 11434)

try:
  conn.request(
      "POST",
      "/v1/chat/completions",
      json.dumps(initial_payload),
      {"Content-Type": "application/json"},
  )
  initial_response = conn.getresponse()
  initial_payload_response = json.loads(initial_response.read().decode())
  print("Initial response:\n", json.dumps(initial_payload_response, indent=2))

  choices = initial_payload_response.get("choices", [])
  if not choices:
    print("No choices returned from the model.")
    raise SystemExit(0)

  assistant_message = choices[0].get("message", {})
  tool_calls = assistant_message.get("tool_calls", [])
  if not tool_calls:
    print("Model did not trigger a tool call.")
    raise SystemExit(0)

  follow_up_messages = initial_messages.copy()
  follow_up_messages.append({
      "role": "assistant",
      "content": assistant_message.get("content", ""),
      "tool_calls": tool_calls,
  })

  for tool_call in tool_calls:
    function_name = tool_call.get("function", {}).get("name")
    arguments_raw = tool_call.get("function", {}).get("arguments", "{}")
    try:
      arguments = json.loads(arguments_raw)
    except json.JSONDecodeError:
      print("Malformed tool arguments:", arguments_raw)
      raise

    if function_name == "get_weather":
      result = fake_weather_service(arguments.get("location", "Unknown"))
    else:
      result = {"error": f"Unhandled tool {function_name}"}

    follow_up_messages.append({
        "role": "tool",
        "tool_call_id": tool_call.get("id"),
        "name": function_name,
        "content": json.dumps(result),
    })

  follow_up_payload = {
      "model": "qwen3:4b-instruct-2507-q4_K_M",
      "temperature": 0.1,
      "max_tokens": 1024,
      "messages": follow_up_messages,
      "stream": False,
  }

  conn.request(
      "POST",
      "/v1/chat/completions",
      json.dumps(follow_up_payload),
      {"Content-Type": "application/json"},
  )
  follow_up_response = conn.getresponse()
  follow_up_payload_response = json.loads(follow_up_response.read().decode())
  print("\nFollow-up response:\n", json.dumps(follow_up_payload_response, indent=2))

except Exception as exc:
  print(f"Error: {exc}")
finally:
  conn.close()
