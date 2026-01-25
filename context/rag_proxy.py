from flask import Flask, request, jsonify, Response, stream_with_context
from flask_cors import CORS
from langchain_community.document_loaders import TextLoader
from langchain.text_splitter import CharacterTextSplitter
from langchain_community.retrievers import TFIDFRetriever
from langchain_ollama import ChatOllama
import time, json

documents = TextLoader("pg3008.txt").load()
texts = CharacterTextSplitter(chunk_size=512, chunk_overlap=32).split_documents(documents)
retriever = TFIDFRetriever.from_documents(texts)

def retrieval(question: str) -> str:
    return "\n\n----\n\n".join(doc.page_content for doc in retriever.invoke(question)[:2])

app = Flask(__name__)
CORS(app)

def stream_response(messages: list, model: str, temperature: float, max_tokens: int):
    response = ChatOllama(model=model, temperature=temperature, num_predict=max_tokens).invoke(messages)
    content = response.content if response.content else "No response generated"
    for i in range(0, len(content), 20):
        yield f"data: {json.dumps({'choices': [{'delta': {'content': content[i:i + 20]}}]})}\n\n"
        time.sleep(0.05)
    yield "data: [DONE]\n\n"

@app.route("/v1/chat/completions", methods=["POST"])
def chat_completions():
    try:
        data = request.get_json()
        stream = data.get("stream", False)
        if not stream:
            return jsonify({"error": "proxy requires streaming"}), 400
        messages_data = data.get("messages", [])
        user_message = next((msg["content"] for msg in reversed(messages_data) if msg["role"] == "user"), "")
        context = retrieval(user_message)
        messages = [{"role": "system", "content": f"You are a helpful assistant. Use the following context if relevant:\n{context}"}]
        messages.extend(messages_data)
        def generate():
            for chunk in stream_response(messages, data.get("model", "phi4"), data.get("temperature", 0.1), data.get("max_tokens", 600)):
                yield chunk
        return Response(stream_with_context(generate()), mimetype="text/event-stream")
        
    except Exception as e:
        return jsonify({"error": str(e)}), 500

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=8010)