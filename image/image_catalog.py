import os
import json
import base64
import http.client

def image_catalog_entry(image_file):
    with open(image_file, "rb") as image_file:
        base64_image = base64.b64encode(image_file.read()).decode('utf-8')
    format = {
        "title": "Image Catalog Entry",
        "type": "object",
        "properties": {
            "description": { "type": "string" },
            "purpose": { "type": "string" },
            "size": { "type": "string" },
            "price": { "type": "string" }
        },
        "required": [ "description", "purpose", "size", "price" ]
    }
    payload = {
        "model": "gemma3:4b",
        "temperature": 0.1,
        "max_tokens": 1024,
        "messages": [
            {"role": "system", "content": "You are a helpful assistant."},
            {
                "role": "user",
                "content": "Make a catalog entry of a sales object. Describe the object in the image, its purpose, size, and price and write it as json.",
                "images": [base64_image]
            }
        ],
        "stream": False,
        "format": format
    }

    try:
        conn = http.client.HTTPConnection("localhost", 11434)
        conn.request("POST", "http://localhost:11434/api/chat", json.dumps(payload),
                    {"Content-Type": "application/json"})
        response = conn.getresponse()
        response_text = response.read().decode()
        response_json = json.loads(response_text)
        print(json.dumps(response_json, indent=2))
    except Exception as e:
        print(f"Error: {e}")
    finally:
        conn.close()

image_folder = "images"
image_files = os.listdir(image_folder)
image_files = [f"{image_folder}/{image_file}" for image_file in image_files]
for image_file in image_files:
    catalog_entry = image_catalog_entry(image_file)
    print(catalog_entry)