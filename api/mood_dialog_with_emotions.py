from langchain_ollama import ChatOllama
import json

def mood_classifier(text):
    format = {
        "title": "Classifier", "type": "object",
        "properties": { "mood": { "type": "literal", "enum": ["surprised", "angry", "happy"]} }
    }
    messages = [
        ("system", "You are a mood classifier. Identify the mood of the request. Write your answer as json."),
        ("human", text),
    ]
    llm = ChatOllama(base_url="http://localhost:11434", model = "llama3.2", temperature = 0.1, num_predict = 1024, format = format)
    llm = llm.with_structured_output(schema = format, include_raw = True)
    mood = json.loads(llm.invoke(messages)['raw'].content)['mood']
    return mood

def emotional_response(text):
    mood = mood_classifier(text)
    prompts = {
        "happy": "Reflect enthusiasm in the most positive way. Be extremely excited!",
        "surprised": "Have extreme positive expectations. Now anything may happen!",
        "angry": "Team up with the user to eliminate the problem. Destroy the source of anger!"
    }
    messages = [("system", f"You are a very emotional assistant which makes short answers. {prompts.get(mood, '')}"), ("human", text)]
    llm = ChatOllama(base_url="http://localhost:11434", model = "llama3.2", temperature = 0.1, num_predict = 1024)
    return llm.invoke(messages).content

def print_emotional_answer(text):
    print(f"\n---\n\nUser:      {text}\nAssistant: {emotional_response(text)}\n")

print_emotional_answer("I love programming.")
print_emotional_answer("I hate programming.")
print_emotional_answer("I lost all my data.")