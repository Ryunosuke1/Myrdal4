# 長期記憶（例: ChromaDB, SQLite, ファイル永続化など）

import chromadb
from chromadb.config import Settings

class LongTermMemory:
    def __init__(self, collection_name="myrdal_long_term"):
        self.client = chromadb.Client(Settings())
        self.collection = self.client.get_or_create_collection(collection_name)
    async def store(self, data: dict):
        # data: {"id": str, "text": str, ...}
        self.collection.add(
            documents=[data["text"]],
            ids=[data["id"]],
            metadatas=[{k: v for k, v in data.items() if k not in ("id", "text")}]
        )
    async def search(self, query: str, n_results=3) -> list:
        results = self.collection.query(query_texts=[query], n_results=n_results)
        return results.get("documents", [])
    async def delete(self, doc_id: str):
        self.collection.delete(ids=[doc_id]) 