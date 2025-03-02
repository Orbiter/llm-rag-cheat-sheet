import os
import logging
import requests
from langchain_ollama import ChatOllama
from langchain.chains import RetrievalQA
from langchain.vectorstores import FAISS
from langchain.retrievers import BM25Retriever
from langchain.retrievers import TFIDFRetriever
from langchain.document_loaders import TextLoader
from langchain.embeddings import HuggingFaceEmbeddings
from langchain.text_splitter import CharacterTextSplitter

# Enable logging
logging.basicConfig(level=logging.INFO)

# harvest and load example text
file_path = "pg50221.txt"
if not os.path.exists(file_path):
    url = "https://www.gutenberg.org/cache/epub/50221/pg50221.txt"
    response = requests.get(url)
    with open(file_path, "wb") as f: f.write(response.content)
loader = TextLoader(file_path)
documents = loader.load()

# Split the text into chunks
text_splitter = CharacterTextSplitter(chunk_size=512, chunk_overlap=64)
texts = text_splitter.split_documents(documents)
print(f"Number of chunks: {len(texts)}")

# Create retriever
vectorstore = FAISS.from_documents(texts, HuggingFaceEmbeddings(model_name="all-MiniLM-L6-v2"))
vector_retriever = vectorstore.as_retriever(search_kwargs={"k": 4})
tfidf_retriever = TFIDFRetriever.from_documents(texts)
bm25_retriever = BM25Retriever.from_documents(texts)

# Test the retriever
query = "Was ist eine moderne Wohnungseinrichtung und was gehört in das Wohnzimmer?"
retrieved_docs = vector_retriever.get_relevant_documents(query)
for i, doc in enumerate(retrieved_docs):
    print(f"\n\*** Vector Document {i+1}:\n{doc.page_content}\n")

retrieved_docs = tfidf_retriever.get_relevant_documents(query)
for i, doc in enumerate(retrieved_docs):
    print(f"\n*** TF*IDF Document {i+1}:\n{doc.page_content}\n")

retrieved_docs = bm25_retriever.get_relevant_documents(query)
for i, doc in enumerate(retrieved_docs):
    print(f"\n*** BM25 Document {i+1}:\n{doc.page_content}\n")

# Create LLM and QA chain
llm = ChatOllama(model = "llama3.2", temperature = 0.0, num_predict = 1024)
vector_qa_chain = RetrievalQA.from_chain_type(llm=llm, chain_type="stuff", retriever=vector_retriever)
tfidf_qa_chain = RetrievalQA.from_chain_type(llm=llm, chain_type="stuff", retriever=tfidf_retriever)
bm25_qa_chain = RetrievalQA.from_chain_type(llm=llm, chain_type="stuff", retriever=bm25_retriever)

# Query the LLM with the enriched context
print("\n\nVector QA Chain Response:")
print(vector_qa_chain.invoke(query)["result"])

print("\n\nTF*IDF QA Chain Response:")
print(tfidf_qa_chain.invoke(query)["result"])

print("\n\nBM25 QA Chain Response:")
print(bm25_qa_chain.invoke(query)["result"])