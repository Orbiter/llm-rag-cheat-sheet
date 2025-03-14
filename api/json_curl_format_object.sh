# run with ./json_curl_format_object.sh  | python3 -m json.tool
curl -X POST "http://localhost:11434/api/chat"\
     -s -H "Content-Type: application/json"\
     -d '{
    "model": "llama3.2", "temperature": 0.1, "max_tokens": 1024,
    "messages": [
      {"role": "system",
       "content": "Translate the user sentence."},
      {"role": "user",
       "content": "I love programming."}
    ],
    "stream": false,
    "format": {
      "type": "object",
      "properties": {
        "english": { "type": "string" }, "german": { "type": "string" },
        "spanish": { "type": "string" }, "italian": { "type": "string" }
      },
      "required": [ "german", "spanish" ]
    }
  }'