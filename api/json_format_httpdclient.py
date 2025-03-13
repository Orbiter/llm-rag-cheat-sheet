import http.client
import json

format = {
    "title": "Translation",
    "type": "object",
    "properties": {
        "english": { "type": "string" }, "german": { "type": "string" },
        "spanish": { "type": "string" }, "italian": { "type": "string" },
        "french": { "type": "string" }
    },
    "required": [ "german", "spanish" ]
}
messages = [
    {"role": "system", "content": "You are a helpful translator. Translate the user sentence. Write your answer as json."},
    {"role": "user", "content": "I love programming."}
]

conn = http.client.HTTPConnection("localhost", 11434)
payload = {
    "model": "llama3.2", "temperature": 0.1, "max_tokens": 1024,
    "messages": messages, "stream": False, "format": format
}
conn.request("POST", "/api/chat", json.dumps(payload), {"Content-Type": "application/json"})
response = json.loads(conn.getresponse().read().decode())
content = json.loads(response["message"]["content"])
print(json.dumps(content, indent=2))
conn.close()