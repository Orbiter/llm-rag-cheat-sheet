from langchain_ollama import ChatOllama

llm = ChatOllama(model = "phi4", temperature = 0.0, num_predict = 1024)

# response without stream
messages = [
    ("system", "You are a helpful translator. Translate the user sentence to French."),
    ("human", "I love programming."),
]
response = llm.invoke(messages)
print(response.content)

# stream
messages = [
    ("human", "Return the words Hello World!"),
]
for chunk in llm.stream(messages):
    print(chunk.content, end="")
print()

# json
#json_llm = ChatOllama(model = "athene-v2", format="json")
#messages = [
#    ("human", "Return a query for the weather in a random location and time of day with two keys: location and time_of_day."),
#]
#response = llm.invoke(messages)
#print(response.content)


from typing import Optional
from pydantic import BaseModel, Field

class Joke(BaseModel):
    setup: str = Field(description="The setup of the joke")
    punchline: str = Field(description="The punchline to the joke")
    rating: Optional[int] = Field(
        default=None, description="How funny the joke is, from 1 to 10"
    )


llm = ChatOllama(model = "athene-v2", temperature = 0.0, num_predict = 1024)
structured_llm = llm.with_structured_output(Joke)
response = structured_llm.invoke("Tell me a joke about cats")
print(response.setup)
print(response.punchline)
print(response.rating)