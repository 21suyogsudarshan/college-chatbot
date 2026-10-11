import json
import os
import chromadb

docs = []
try:
    client = chromadb.PersistentClient(path="./chroma_db")
    for col_info in client.list_collections():
        col = client.get_collection(col_info.name)
        result = col.get()
        if result and "documents" in result and result["documents"]:
            docs.extend(result["documents"])
    print(f"Extracted {len(docs)} chunks from ChromaDB.")
except Exception as e:
    print("ChromaDB read error:", e)

if not docs:
    docs = ["ABV-IIITM Gwalior institutional knowledge base."]

with open("knowledge.json", "w", encoding="utf-8") as f:
    json.dump(docs, f, ensure_ascii=False, indent=2)

print("knowledge.json saved successfully.")
