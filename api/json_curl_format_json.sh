# run with ./json_curl_format_json.sh  | python3 -m json.tool
curl -X POST "http://localhost:11434/api/chat"\
     -s -H "Content-Type: application/json"\
     -d '{
    "model": "llama3.2", "temperature": 0.1, "max_tokens": 1024,
    "messages": [
      {"role": "system", "content": "You are a helpful translator. Translate the user sentence to German. Write your answer as json."},
      {"role": "user", "content": "I love programming."}
    ],
    "stream": false,
    "format": "json"
  }'