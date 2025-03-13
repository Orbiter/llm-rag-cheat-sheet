# this requires a text file named pg50221.txt to be present in the same directory
# download it with: wget https://www.gutenberg.org/cache/epub/3008/pg3008.txt
from langchain_community.document_loaders import TextLoader
from langchain.text_splitter import CharacterTextSplitter
from langchain_community.retrievers import TFIDFRetriever


documents = TextLoader("pg3008.txt").load() # Jargon File
texts = CharacterTextSplitter(chunk_size=512, chunk_overlap=32, separator="\n"
        ).split_documents(documents)
retriever = TFIDFRetriever.from_documents(texts)

def get_context(question: str) -> str:
    return "\n\n----\n\n".join(doc.page_content for doc in retriever.invoke(question)[:2])

question = "What does 'wombat' mean?"
print("\033c") # clear the terminal
print(get_context(question))