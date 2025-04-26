import base64
import http.client
import json

def add_two_numbers(a: int, b: int) -> int:
  """
  Add two numbers

  Args:
    a: The first integer number
    b: The second integer number

  Returns:
    int: The sum of the two numbers
  """
  return a + b

tools = [{
    "type": "function",
    "function": {
        "name": "get_weather",
        "description": "Get current temperature for a given location.",
        "parameters": {
            "type": "object",
            "properties": {
                "location": { "type": "string", "description": "City and country e.g. Bogotá, Colombia" }
            },
            "required": [ "location" ],
            "additionalProperties": False
        },
        "strict": True
    }
}]

payload = {
    "model": "qwen3:4b-instruct-2507-q4_K_M",
    "temperature": 0.1,
    "max_tokens": 1024,
    "messages": [
        {"role": "system", "content": "You are a helpful assistant."},
        {"role": "user", "content": "What is the weather like in Paris today?"}
    ],
    "tools": tools,
    "stream": False
}

try:
    conn = http.client.HTTPConnection("localhost", 11434)
    conn.request("POST", "/v1/chat/completions", json.dumps(payload),
                 {"Content-Type": "application/json"})
    response = conn.getresponse()
    response_text = response.read().decode()
    response_json = json.loads(response_text)
    print(json.dumps(response_json, indent=2))
except Exception as e:
    print(f"Error: {e}")
finally:
    conn.close()
