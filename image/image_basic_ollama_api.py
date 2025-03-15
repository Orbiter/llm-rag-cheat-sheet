import base64
import http.client
import json

image_path = "images/scalarproduct.png"
with open(image_path, "rb") as image_file:
    base64_image = base64.b64encode(image_file.read()).decode('utf-8')

payload = {
    "model": "gemma3:4b",
    "temperature": 0.1,
    "max_tokens": 1024,
    "messages": [
        {"role": "system", "content": "You are a helpful assistant."},
        {"role": "user", "content": [
            {"type": "text", "text": "Explain whats in the image: first write down the exact content of the image then explain it."},
            {"type": "image_url", "image_url": {"url": f"data:image/png;base64,{base64_image}"}}
        ]}
    ],
    "stream": False
}

try:
    conn = http.client.HTTPConnection("localhost", 11434)
    conn.request("POST", "/v1/chat/completions", json.dumps(payload),
                 {"Content-Type": "application/json"})
    response = conn.getresponse()
    response_text = response.read().decode()
    print("Response text read:" + response_text)
    response_json = json.loads(response_text)
    print(json.dumps(response_json, indent=2))
except Exception as e:
    print(f"Error: {e}")
finally:
    conn.close()