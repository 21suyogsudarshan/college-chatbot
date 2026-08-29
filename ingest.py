import os, shutil
from pathlib import Path
from langchain_community.document_loaders import DirectoryLoader, PyPDFLoader
from langchain.text_splitter import RecursiveCharacterTextSplitter
from langchain_huggingface import HuggingFaceEmbeddings
from langchain_community.vectorstores import Chroma

if Path("./chroma_db").exists():
    shutil.rmtree("./chroma_db")

print("1/3 Loading PDFs from ./data ...")
docs = DirectoryLoader("./data", glob="**/*.pdf", loader_cls=PyPDFLoader).load()
print(f"Loaded {len(docs)} pages.")

print("2/3 Chunking text ...")
chunks = RecursiveCharacterTextSplitter(chunk_size=600, chunk_overlap=100).split_documents(docs)

print("3/3 Generating local embeddings ...")
embeddings = HuggingFaceEmbeddings(model_name="sentence-transformers/all-MiniLM-L6-v2")
Chroma.from_documents(documents=chunks, embedding=embeddings, persist_directory="./chroma_db")
print("SUCCESS: Vector store created in ./chroma_db")
