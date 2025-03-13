from langchain_ollama import ChatOllama
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
    ("system", "You are a helpful translator. Translate the user sentence in different languages. Write your answer as json."),
    ("human", "I love programming."),
]

llm = ChatOllama(base_url="http://localhost:11434", model = "llama3.2", temperature = 0.1, num_predict = 1024, format = format)
llm = llm.with_structured_output(schema = format, include_raw = True)

response = llm.invoke(messages)
content = json.loads(response['raw'].content)
print(json.dumps(content, indent=2))