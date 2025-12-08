from langchain_ollama import ChatOllama
import json

def mood_classifier(text):
    format = {
        "title": "Classifier", "type": "object",
        "properties":
        {"mood":{ "type": "literal", "enum": ["surprised", "angry", "happy"]}},
        "required": ["mood"]
    }
    messages = [
        ("system", "You are a mood classifier. Identify the mood of the request."),
        ("human", text),
    ]
    llm = ChatOllama(base_url="http://localhost:11434", model = "llama3.2:3b",
                     temperature = 0.1, num_predict = 1024, format = format)
    llm = llm.with_structured_output(schema = format, include_raw = True)
    mood = json.loads(llm.invoke(messages)['raw'].content)['mood']
    return mood

def print_mood_classifier(text):
    print(f"{text} -> {mood_classifier(text)}")

print_mood_classifier("I love programming.")
print_mood_classifier("I hate programming.")
print_mood_classifier("That worked perfectly.")

