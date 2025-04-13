import http.client
import json

# Step 1: Define the function the model can call
tools = [{
    "type": "function",
    "name": "get_weather",
    "description": "Get current temperature for a given location.",
    "parameters": {
        "type": "object",
        "properties": {
            "location": {
                "type": "string",
                "description": "City and country e.g. Bogotá, Colombia"
            }
        },
        "required": ["location"],
        "additionalProperties": False
    }
}]

# Step 2: Create the payload with function specs and a user question
payload = {
    "model": "llama3.1:8b", "temperature": 0.1, "max_tokens": 1024, "stream": False,
    "messages": [
        {"role": "system", "content": "You are a helpful assistant."},
        {"role": "user", "content": "What's the weather like in Berlin?"}
    ],
    "tools": tools
}

# Step 3: Send the request
conn = http.client.HTTPConnection("localhost", 11434)
conn.request("POST", "/v1/chat/completions", json.dumps(payload), {
    "Content-Type": "application/json"
})

# Step 4: Get and print the response
response_text = conn.getresponse().read().decode()
response_json = json.loads(response_text)
print(json.dumps(response_json, indent=2))

conn.close()
