import json
import http.client
from pydantic import BaseModel

class TranslationFormat(BaseModel):
    german: str
    spanish: str
    english: str | None = None
    italian: str | None = None

schema = TranslationFormat.model_json_schema()
messages = [
    {"role": "system", "content": "Translate the user sentence."},
    {"role": "user", "content": "I love programming."}
]
payload = {
    "model": "llama3.2", "temperature": 0.1, "max_tokens": 1024,
    "messages": messages, "stream": False, 
    "response_format": {
        "type": "json_schema",
        "json_schema": {"strict": True, "schema": schema}
    }
}
conn = http.client.HTTPConnection("localhost", 11434)
conn.request("POST", "/v1/chat/completions", json.dumps(payload), {"Content-Type": "application/json"})
response = json.loads(conn.getresponse().read().decode())
content = json.loads(response["choices"][0]["message"]["content"])
print(json.dumps(content, indent=2))
conn.close()