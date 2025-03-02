import os
import json
import requests
from langchain.schema import Document
from fastapi import FastAPI, HTTPException
from fastapi.responses import StreamingResponse
from langchain.retrievers import TFIDFRetriever
from langchain.document_loaders import TextLoader
from langchain.text_splitter import CharacterTextSplitter

# load the text for RAG
file_path = "pg50221.txt"
if not os.path.exists(file_path):
    url = "https://www.gutenberg.org/cache/epub/50221/pg50221.txt"
    response = requests.get(url)
    with open(file_path, "wb") as f: f.write(response.content)
loader = TextLoader(file_path)
documents = loader.load()
text_splitter = CharacterTextSplitter(chunk_size=512, chunk_overlap=64)
texts = text_splitter.split_documents(documents)
tfidf_retriever = TFIDFRetriever.from_documents(texts)

# Step 2: Set up FastAPI
app = FastAPI()

# Step 3: Define the OpenAI Chat API endpoint
@app.post("/v1/chat/completions")
async def chat_completions(request: dict):
    try:
        # Extract the user's message from the request
        user_message = request["messages"][-1]["content"]

        # Step 4: Augment the prompt with retrieved documents
        retrieved_docs = tfidf_retriever.get_relevant_documents(user_message)
        context = "\n\n".join([doc.page_content for doc in retrieved_docs])
        augmented_prompt = f"Context:\n{context}\n\nQuestion: {user_message}\nAnswer:"

        # Step 5: Forward the augmented prompt to Ollama
        ollama_url = "http://localhost:11434/api/generate"  # Ollama's API endpoint
        ollama_payload = {
            "model": "llama2",  # Replace with your Ollama model
            "prompt": augmented_prompt,
            "stream": True,  # Enable streaming
        }

        # Step 6: Stream the response from Ollama back to the client
        def generate():
            with requests.post(ollama_url, json=ollama_payload, stream=True) as response:
                for chunk in response.iter_lines():
                    if chunk:
                        chunk_data = json.loads(chunk.decode("utf-8"))
                        yield f"data: {json.dumps({'choices': [{'delta': {'content': chunk_data['response']}}])}\n\n"

        return StreamingResponse(generate(), media_type="text/event-stream")
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

# Step 7: Run the FastAPI server
if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)