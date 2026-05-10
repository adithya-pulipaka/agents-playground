import os
import uuid
from datetime import datetime, timezone
from pathlib import Path

import chromadb
from chromadb.utils.embedding_functions import OpenAIEmbeddingFunction

_CHROMA_DIR = Path(__file__).parent.parent / "chroma_data"
_collection = None


def _get_collection():
    """Lazily initialise ChromaDB so env vars are loaded before first use."""
    global _collection
    if _collection is None:
        client = chromadb.PersistentClient(path=str(_CHROMA_DIR))
        ef = OpenAIEmbeddingFunction(
            api_key=os.environ["OPENAI_API_KEY"],
            model_name="text-embedding-3-small",
        )
        _collection = client.get_or_create_collection(
            name="personal_assistant",
            embedding_function=ef,
            metadata={"hnsw:space": "cosine"},
        )
    return _collection


def memory_store(content: str, memory_type: str = "fact") -> dict:
    """Store a fact, preference, or conversation summary in long-term memory.

    Args:
        content: The text to remember. Be specific and self-contained.
        memory_type: Category of memory — one of 'fact', 'preference', 'summary'.

    Returns:
        A dict with 'status' and the 'id' of the stored memory.
    """
    collection = _get_collection()
    memory_id = str(uuid.uuid4())
    timestamp = datetime.now(timezone.utc).isoformat()

    collection.add(
        documents=[content],
        metadatas=[{"memory_type": memory_type, "timestamp": timestamp}],
        ids=[memory_id],
    )

    return {"status": "stored", "id": memory_id, "memory_type": memory_type}


def memory_recall(query: str, n_results: int = 5) -> dict:
    """Search long-term memory for information relevant to a query.

    Args:
        query: What to search for. Uses semantic similarity — natural language works best.
        n_results: Maximum number of memories to return. Defaults to 5.

    Returns:
        A dict with a 'memories' list, each containing content, memory_type, timestamp,
        and relevance_score. Returns empty list if nothing relevant is found.
    """
    collection = _get_collection()

    if collection.count() == 0:
        return {"memories": []}

    results = collection.query(
        query_texts=[query],
        n_results=min(n_results, collection.count()),
        include=["documents", "metadatas", "distances"],
    )

    memories = []
    for doc, meta, distance in zip(
        results["documents"][0],
        results["metadatas"][0],
        results["distances"][0],
    ):
        memories.append({
            "content": doc,
            "memory_type": meta.get("memory_type", "unknown"),
            "timestamp": meta.get("timestamp", ""),
            "relevance_score": round(1 - distance, 3),  # cosine distance → similarity
        })

    return {"memories": memories}
