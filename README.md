# LLM-RAG-Cheat-Sheet

A collection of practical examples and tools for building LLM (Large Language Model) applications, focusing on RAG (Retrieval-Augmented Generation) patterns. Created for the talk "Open Data / Freie Daten in KI Chatbots nutzen" (Open Data in AI Chatbots).

## Requirements

- **Ollama** running on `localhost:11434` (or configure alternative API endpoint)
- **Python 3.x** for Python scripts
- **Models**: Tested with `llama3.2`, `gemma3:4b`, `qwen3`, `phi4`

## Quick Start

### Terminal Chat
```bash
cd simple_shell_chat
pip install -r requirements.txt
python llm_shell.py --model llama3.2 --api http://localhost:11434
```

Commands:
- `clear` - Reset conversation context
- `model` - Show current model
- `model <name>` - Switch to different model
- `ollama ls` - List available models
- `ollama ps` - Show running models
- `bye` - Exit

### Web Chat
```bash
cd simple_web_chat
./run_server.sh
# Open browser to http://localhost:8000
```

## Directory Structure

### `/tools/` - Function/Tool Calling
Demonstrates how to implement and use tool calling with LLMs:

**Function Calling Example**:
```python
# tools/function_calling.py
tools = [{
    "type": "function",
    "function": {
        "name": "get_weather",
        "description": "Get current temperature for a given location.",
        "parameters": {
            "type": "object",
            "properties": {
                "location": { "type": "string" }
            },
            "required": ["location"]
        }
    }
}]

payload = {
    "model": "llama3.2",
    "tools": tools,
    "messages": [{"role": "user", "content": "What is the weather in Paris?"}]
}
```

**Key Files**:
- `function_calling.py` - Basic tool calling with weather API
- `bash-agent.py` - LLM agents that execute shell commands
- `rag_response.py` - RAG pattern examples
- `tool_example.py` - Various tool integration tests

### `/api/` - API Clients & Response Formatting
Multi-language API client implementations and structured output:

**Structured JSON with Pydantic**:
```python
# api/json_format_pydantic.py
class TranslationFormat(BaseModel):
    german: str
    spanish: str
    english: str | None = None

schema = TranslationFormat.model_json_schema()
payload = {
    "model": "llama3.2",
    "response_format": {
        "type": "json_schema",
        "json_schema": {"strict": True, "schema": schema}
    }
}
```

**Key Files**:
- `chat_python_httpclient.py` / `chat_python_langchain.py` - Python HTTP clients
- `json_format_pydantic.py` / `json_format_langchain.py` - Structured JSON output
- `chat_curl.sh` / `chat_curl_stream.sh` - Curl-based API examples
- `mood_classifier.py` - Sentiment/mood classification
- Java examples: `json_format_java.java`, `chat_java_simplejson.java`

### `/context/` - RAG Context Management
Text retrieval and context management for RAG systems:

**Vector Index with Multiple Retrievers**:
```python
# context/vectorindex.py
from langchain.vectorstores import FAISS
from langchain.retrievers import BM25Retriever, TFIDFRetriever

# Split text into chunks
text_splitter = CharacterTextSplitter(chunk_size=512, chunk_overlap=64)
texts = text_splitter.split_documents(documents)

# Create multiple retrievers
vectorstore = FAISS.from_documents(texts, HuggingFaceEmbeddings(model_name="all-MiniLM-L6-v2"))
vector_retriever = vectorstore.as_retriever(search_kwargs={"k": 4})
tfidf_retriever = TFIDFRetriever.from_documents(texts)
bm25_retriever = BM25Retriever.from_documents(texts)
```

**Key Files**:
- `context_provider.py` - Document loading and TF-IDF retrieval
- `vectorindex.py` - FAISS, BM25, TF-IDF vector index implementation
- `wikipedia_news.py` / `wikipedia_news_de.py` - Wikipedia revision tracking
- `rag_proxy.py` - RAG proxy implementation
- Sample texts: `pg50221.txt`, `pg3008.txt` (Project Gutenberg)

### `/image/` - Multimodal Vision Examples
Image analysis with vision-capable LLMs:

**Image Analysis**:
```python
# image/image_basic_openai_api.py
with open("images/scalarproduct.png", "rb") as image_file:
    base64_image = base64.b64encode(image_file.read()).decode('utf-8')

payload = {
    "model": "gemma3:4b",
    "messages": [{
        "role": "user",
        "content": [
            {"type": "text", "text": "Explain the image"},
            {"type": "image_url", "image_url": {"url": f"data:image/png;base64,{base64_image}"}}
        ]
    }]
}
```

**Key Files**:
- `image_basic_ollama_api.py` - Basic image analysis with Ollama
- `image_basic_openai_api.py` - OpenAI-compatible API for image analysis
- `image_catalog.py` - Image cataloging utilities
- `image_fetch.sh` - Fetch images from URLs

### `/simple_web_chat/` - Web Chat Interface
Terminal-style browser-based chat client:

**Features**:
- Streaming token-by-token output
- Model switching (`model <name>`)
- Host configuration (`host <url>`)
- LocalStorage persistence
- Markdown rendering
- RAG context injection (via `chat.html`)

**Run**:
```bash
cd simple_web_chat
./run_server.sh
# Or manually: python -m http.server 8000
```

**Commands**:
- `reset` - Clear conversation
- `model` - Show current model
- `model <name>` - Switch model
- `host <url>` - Change API endpoint
- `ollama ls` - List available models

### `/simple_shell_chat/` - Terminal Chat Interface
Command-line chat client for terminal interaction:

**Features**:
- Streaming token-by-token output
- Model management (switch, list, show)
- Context persistence
- Multi-line input (triple quote `"""`)
- Custom system prompts via config

## Common Patterns

### RAG with Context Injection
```python
# Retrieve relevant documents
retrieved_docs = vector_retriever.get_relevant_documents(query)
context_text = "\n\n".join([doc.page_content for doc in retrieved_docs])

# Inject into prompt
messages = [{
    "role": "system",
    "content": f"Answer using this context:\n{context_text}"
}, {
    "role": "user",
    "content": query
}]
```

### Streaming Responses
```python
# API request with streaming
body = {
    "model": "llama3.2",
    "stream": True,
    "messages": messages,
    "max_tokens": 8192
}
conn.request("POST", "/v1/chat/completions", json.dumps(body))

# Process SSE stream
for line in response:
    if "data: [DONE]" in line: break
    data = json.loads(line[6:])
    token = data["choices"][0]["delta"].get("content", "")
    print(token, end="", flush=True)
```

## Configuration

### Ollama Setup
```bash
# Install and start Ollama
brew install ollama  # macOS
ollama pull llama3.2
ollama serve
```

### Environment
- Default Ollama endpoint: `http://localhost:11434`
- Use `--api` flag or `host` command to change endpoint
- Default model configurable in scripts

## License

MIT License - see LICENSE.txt for details

---

**Repository**: https://github.com/orbiter/llm-rag-cheat-sheet
