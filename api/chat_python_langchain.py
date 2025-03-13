from langchain_ollama import ChatOllama

llm = ChatOllama(model = "llama3.2", temperature = 0.1, num_predict = 1024)

messages = [
    ("system", "You are a helpful assistant."),
    ("human", "Hello, how are you?"),
]
response = llm.invoke(messages)

print(response.content)
