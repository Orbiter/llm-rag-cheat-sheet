import base64, http.client, json

tools = [{
    "type": "function",
    "function": {
        "name": "get_weather", "description": "Get current temperature for a given location.", "strict": True,
        "parameters": {
            "type": "object",
            "properties": {
                "location": { "type": "string", "description": "City and country e.g. Bogotá, Colombia" }
            },
            "required": [ "location" ], "additionalProperties": False
        }
    }
}]

payload = {
    "model": "llama3.2", "temperature": 0.1, "max_tokens": 1024, "tools": tools, "stream": False,
    "messages": [
        {"role": "system", "content": "You are a helpful assistant."},
        {"role": "user", "content": "What is the weather like in Paris today?"}
    ]
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
