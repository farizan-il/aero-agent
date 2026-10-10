import os
import re
from pathlib import Path
from typing import List, Dict, Any
import numpy as np

from src import config

try:
    from langchain_google_genai import GoogleGenerativeAIEmbeddings
except ImportError:
    GoogleGenerativeAIEmbeddings = None


class KnowledgeBaseRAG:
    """Robust RAG knowledge retrieval engine.
    Supports semantic vector search using Gemini embeddings, with automatic
    keyword-based fallback.
    """

    def __init__(self, docs_dir: Path = None):
        self.docs_dir = docs_dir or config.KNOWLEDGE_BASE_DIR
        self.documents: List[Dict[str, Any]] = []
        self.embeddings_model = None
        self.doc_embeddings: List[np.ndarray] = []
        self._is_initialized = False

    def load_documents(self) -> int:
        """Reads markdown and text files from the knowledge base directory and chunks them."""
        self.documents = []
        if not self.docs_dir.exists():
            return 0

        for file_path in self.docs_dir.glob("**/*"):
            if file_path.suffix.lower() in [".md", ".txt"]:
                try:
                    content = file_path.read_text(encoding="utf-8")
                    chunks = self._chunk_content(content, file_path.name)
                    self.documents.extend(chunks)
                except Exception as e:
                    print(f"Warning: Failed to read {file_path.name}: {e}")

        return len(self.documents)

    def _chunk_content(self, text: str, source: str, max_chunk_len: int = 400) -> List[Dict[str, Any]]:
        """Splits text by markdown sections or paragraphs for meaningful chunks."""
        raw_sections = re.split(r"(?=\n#{1,3}\s)", text)
        chunks = []

        for sec in raw_sections:
            sec_clean = sec.strip()
            if not sec_clean:
                continue

            # If section is very long, split further by paragraphs
            if len(sec_clean) > max_chunk_len * 2:
                paragraphs = sec_clean.split("\n\n")
                current = ""
                for p in paragraphs:
                    if len(current) + len(p) < max_chunk_len * 2:
                        current += ("\n\n" if current else "") + p
                    else:
                        if current:
                            chunks.append({"text": current, "source": source})
                        current = p
                if current:
                    chunks.append({"text": current, "source": source})
            else:
                chunks.append({"text": sec_clean, "source": source})

        return chunks

    def initialize_embeddings(self) -> bool:
        """Computes embeddings for all chunks using Google GenAI."""
        if self._is_initialized:
            return True

        self.load_documents()
        if not self.documents:
            return False

        cache_file = self.docs_dir / ".embeddings_cache.npz"

        # Check local cache first for instant startup
        if cache_file.exists():
            try:
                data = np.load(cache_file, allow_pickle=True)
                cached_vecs = data["embeddings"]
                if len(cached_vecs) == len(self.documents):
                    self.doc_embeddings = [np.array(v, dtype=np.float32) for v in cached_vecs]
                    if config.GEMINI_API_KEY and GoogleGenerativeAIEmbeddings:
                        self.embeddings_model = GoogleGenerativeAIEmbeddings(
                            model=config.EMBEDDING_MODEL,
                            google_api_key=config.GEMINI_API_KEY,
                        )
                    self._is_initialized = True
                    return True
            except Exception:
                pass

        if config.GEMINI_API_KEY and GoogleGenerativeAIEmbeddings:
            try:
                self.embeddings_model = GoogleGenerativeAIEmbeddings(
                    model=config.EMBEDDING_MODEL,
                    google_api_key=config.GEMINI_API_KEY,
                )
                texts = [doc["text"] for doc in self.documents]
                vectors = self.embeddings_model.embed_documents(texts)
                self.doc_embeddings = [np.array(v, dtype=np.float32) for v in vectors]
                self._is_initialized = True

                # Save cache for instant subsequent loads
                try:
                    np.savez(cache_file, embeddings=np.array(self.doc_embeddings))
                except Exception:
                    pass

                return True
            except Exception as e:
                print(f"Vector embeddings initialization failed: {e}. Falling back to keyword search.")

        self._is_initialized = False
        return False

    def search(self, query: str, top_k: int = 3) -> List[Dict[str, Any]]:
        """Searches relevant documents using semantic cosine similarity or keyword ranking."""
        if not self.documents:
            self.load_documents()

        if not self.documents:
            return []

        # Vector search if initialized
        if self._is_initialized and self.embeddings_model and self.doc_embeddings:
            try:
                query_vec = np.array(self.embeddings_model.embed_query(query), dtype=np.float32)
                scores = []
                for idx, doc_vec in enumerate(self.doc_embeddings):
                    norm = np.linalg.norm(query_vec) * np.linalg.norm(doc_vec)
                    cos_sim = float(np.dot(query_vec, doc_vec) / (norm + 1e-8))
                    scores.append((cos_sim, idx))

                scores.sort(key=lambda x: x[0], reverse=True)
                results = []
                for score, idx in scores[:top_k]:
                    item = dict(self.documents[idx])
                    item["score"] = round(score, 4)
                    results.append(item)
                return results
            except Exception as e:
                print(f"Semantic search error: {e}. Using keyword fallback.")

        # Keyword match fallback
        query_words = set(re.findall(r"\w+", query.lower()))
        scored = []
        for doc in self.documents:
            doc_words = set(re.findall(r"\w+", doc["text"].lower()))
            overlap = len(query_words.intersection(doc_words))
            if overlap > 0:
                scored.append((overlap, doc))

        scored.sort(key=lambda x: x[0], reverse=True)
        return [item[1] for item in scored[:top_k]]


# Global instance
rag_engine = KnowledgeBaseRAG()
