from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
from langchain_community.document_loaders import TextLoader
from langchain.text_splitter import CharacterTextSplitter
from langchain_community.retrievers import TFIDFRetriever
from langchain_ollama import ChatOllama
from pydantic import BaseModel
from typing import List, AsyncGenerator
import time, json, asyncio

documents = TextLoader("pg3008.txt").load()
texts = CharacterTextSplitter(chunk_size=512, chunk_overlap=32).split_documents(documents)
retriever = TFIDFRetriever.from_documents(texts)

def get_context(question: str) -> str:
    return "\n\n----\n\n".join(doc.page_content for doc in retriever.invoke(question)[:2])

app = FastAPI()
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_credentials=True, allow_methods=["*"], allow_headers=["*"])

class ChatMessage(BaseModel):
    role: str
    content: str

class ChatRequest(BaseModel):
    messages: List[ChatMessage]
    model: str = "phi4"
    temperature: float = 0.1
    max_tokens: int = 600
    stream: bool = False

async def stream_response(messages: List[dict], model: str, temperature: float, max_tokens: int) -> AsyncGenerator[str, None]:
    ollama = ChatOllama(model=model, temperature=temperature, num_predict=max_tokens)
    response = ollama.invoke(messages)
    content = response.content if response.content else "No response generated"
    for i in range(0, len(content), 20):
        yield f"data: {json.dumps({'choices': [{'delta': {'content': content[i:i + 20]}}]})}\n\n"
        await asyncio.sleep(0.05)
    yield "data: [DONE]\n\n"

@app.post("/v1/chat/completions")
async def chat_completions(request: ChatRequest):
    try:
        user_message = next((msg.content for msg in request.messages[::-1] if msg.role == "user"), "")
        context = get_context(user_message)
        messages = [{"role": "system", "content": f"You are a helpful assistant. Use the following context if relevant:\n{context}"}] + [msg.model_dump() for msg in request.messages]
        if request.stream:
            async def event_stream():
                async for chunk in stream_response(messages, request.model, request.temperature, request.max_tokens):
                    yield chunk
            return StreamingResponse(event_stream(), media_type="text/event-stream")
        else:
            ollama = ChatOllama(model=request.model, temperature=request.temperature, num_predict=request.max_tokens)
            response = ollama.invoke(messages)
            content = response.content if response.content else "No response generated"
            return {"id": f"chatcmpl-{int(time.time())}", "object": "chat.completion", "created": int(time.time()), "model": request.model, "choices": [{"index": 0, "message": {"role": "assistant", "content": content}, "finish_reason": "stop"}], "usage": {"prompt_tokens": 0, "completion_tokens": 0, "total_tokens": 0}}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
