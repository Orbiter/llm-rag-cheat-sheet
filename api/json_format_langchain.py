import json
from pydantic import BaseModel
from langchain_ollama import ChatOllama

class TranslationFormat(BaseModel):
    german: str
    spanish: str
    english: str | None = None
    italian: str | None = None

schema = TranslationFormat.model_json_schema()
messages = [
    ("system", "Translate the user sentence in different languages."),
    ("human", "I love programming."),
]

llm = ChatOllama(base_url="http://localhost:11434", model = "llama3.2",
                 temperature = 0.1, num_predict = 1024, format = schema)
llm = llm.with_structured_output(schema = schema, include_raw = True)

response = llm.invoke(messages)
content = json.loads(response['raw'].content)
print(json.dumps(content, indent=2))