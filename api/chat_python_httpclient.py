import http.client
import json

conn = http.client.HTTPConnection("localhost", 11434)
payload = {
    "model": "llama3.2",
    "temperature": 0.1,
    "max_tokens": 1024,
    "messages": [
        {"role": "system", "content": "You are a helpful assistant."},
        {"role": "user", "content": "Hello, how are you?"}
    ],
    "stream": False
}
conn.request("POST", "/v1/chat/completions", json.dumps(payload),
             {"Content-Type": "application/json"})
response_text = conn.getresponse().read().decode()
response_json = json.loads(response_text)
print(json.dumps(response_json, indent=2))
conn.close()