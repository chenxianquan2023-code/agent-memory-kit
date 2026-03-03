"""
Vector memory storage using embeddings for semantic search.
"""

import json
import hashlib
from pathlib import Path
from typing import List, Dict, Any, Optional, Tuple
from dataclasses import dataclass
import numpy as np


@dataclass
class VectorEntry:
    """A single vector memory entry."""
    id: str
    text: str
    vector: List[float]
    metadata: Dict[str, Any]
    timestamp: str


class VectorMemory:
    """
    Semantic vector storage for memories.
    
    Features:
    - Text embedding storage
    - Cosine similarity search
    - Automatic clustering
    - Semantic deduplication
    """
    
    def __init__(self, workspace: str, embedding_dim: int = 384):
        self.workspace = Path(workspace) / "vector_store"
        self.workspace.mkdir(parents=True, exist_ok=True)
        
        self.embedding_dim = embedding_dim
        self.index_file = self.workspace / "vector_index.json"
        
        # In-memory cache
        self._vectors: Dict[str, VectorEntry] = {}
        self._index: Optional[np.ndarray] = None
        self._ids: List[str] = []
        
        self._load_index()
    
    def _load_index(self):
        """Load existing vector index."""
        if self.index_file.exists():
            with open(self.index_file, 'r') as f:
                data = json.load(f)
                for entry_data in data.get("entries", []):
                    entry = VectorEntry(**entry_data)
                    self._vectors[entry.id] = entry
            self._rebuild_index()
    
    def _rebuild_index(self):
        """Rebuild numpy index for fast search."""
        if not self._vectors:
            self._index = None
            self._ids = []
            return
        
        self._ids = list(self._vectors.keys())
        vectors = [self._vectors[id].vector for id in self._ids]
        self._index = np.array(vectors)
    
    def add(self, text: str, 
            vector: Optional[List[float]] = None,
            metadata: Optional[Dict] = None,
            entry_id: Optional[str] = None) -> str:
        """
        Add a memory with its vector embedding.
        
        Args:
            text: The text content
            vector: Pre-computed embedding (if None, will use simple hash)
            metadata: Additional metadata
            entry_id: Optional custom ID
            
        Returns:
            Entry ID
        """
        if entry_id is None:
            entry_id = hashlib.md5(text.encode()).hexdigest()[:12]
        
        # If no vector provided, create a simple one (in production, use real embeddings)
        if vector is None:
            vector = self._simple_embed(text)
        
        entry = VectorEntry(
            id=entry_id,
            text=text,
            vector=vector,
            metadata=metadata or {},
            timestamp=self._now()
        )
        
        self._vectors[entry_id] = entry
        self._rebuild_index()
        self._persist()
        
        return entry_id
    
    def search(self, query: str, 
               query_vector: Optional[List[float]] = None,
               top_k: int = 5,
               threshold: float = 0.7) -> List[Dict]:
        """
        Semantic search for similar memories.
        
        Args:
            query: Query text
            query_vector: Pre-computed query embedding
            top_k: Number of results
            threshold: Minimum similarity score
            
        Returns:
            List of matching entries with scores
        """
        if not self._vectors or self._index is None:
            return []
        
        # Get query vector
        if query_vector is None:
            query_vector = self._simple_embed(query)
        query_vector = np.array(query_vector)
        
        # Compute cosine similarities
        similarities = self._cosine_similarity(query_vector, self._index)
        
        # Get top-k matches
        top_indices = np.argsort(similarities)[::-1][:top_k]
        
        results = []
        for idx in top_indices:
            score = similarities[idx]
            if score < threshold:
                continue
            
            entry_id = self._ids[idx]
            entry = self._vectors[entry_id]
            
            results.append({
                "id": entry.id,
                "text": entry.text,
                "score": float(score),
                "metadata": entry.metadata,
                "timestamp": entry.timestamp
            })
        
        return results
    
    def find_similar(self, entry_id: str, 
                     top_k: int = 5) -> List[Dict]:
        """Find memories similar to a given entry."""
        if entry_id not in self._vectors:
            return []
        
        entry = self._vectors[entry_id]
        return self.search(entry.text, entry.vector, top_k)
    
    def cluster(self, n_clusters: int = 5) -> Dict[str, List[str]]:
        """
        Cluster memories into semantic groups.
        
        Returns:
            Dict mapping cluster ID to list of entry IDs
        """
        if len(self._vectors) < n_clusters:
            return {"all": list(self._vectors.keys())}
        
        from sklearn.cluster import KMeans
        
        # Run K-means clustering
        kmeans = KMeans(n_clusters=n_clusters, random_state=42)
        labels = kmeans.fit_predict(self._index)
        
        # Group by cluster
        clusters = {}
        for idx, label in enumerate(labels):
            entry_id = self._ids[idx]
            cluster_key = f"cluster_{label}"
            if cluster_key not in clusters:
                clusters[cluster_key] = []
            clusters[cluster_key].append(entry_id)
        
        return clusters
    
    def deduplicate(self, threshold: float = 0.95) -> List[str]:
        """
        Find and remove duplicate memories.
        
        Returns:
            List of removed entry IDs
        """
        duplicates = []
        
        for entry_id in list(self._vectors.keys()):
            if entry_id in duplicates:
                continue
            
            # Find similar entries
            similar = self.find_similar(entry_id, top_k=10)
            
            for match in similar:
                if match["id"] != entry_id and match["score"] >= threshold:
                    duplicates.append(match["id"])
                    if match["id"] in self._vectors:
                        del self._vectors[match["id"]]
        
        if duplicates:
            self._rebuild_index()
            self._persist()
        
        return duplicates
    
    def get_stats(self) -> Dict[str, Any]:
        """Get vector store statistics."""
        return {
            "total_entries": len(self._vectors),
            "embedding_dim": self.embedding_dim,
            "index_size_mb": self._get_file_size(),
            "clusters_available": len(self._vectors) >= 5
        }
    
    def _simple_embed(self, text: str) -> List[float]:
        """
        Simple embedding for demo (in production, use real model like sentence-transformers).
        
        This is a naive implementation that creates a hash-based vector.
        For real use, replace with: sentence_transformers.SentenceTransformer
        """
        # Simple bag-of-words embedding
        words = text.lower().split()
        vector = [0.0] * self.embedding_dim
        
        for word in words:
            # Hash word to position
            pos = hash(word) % self.embedding_dim
            vector[pos] += 1.0
        
        # Normalize
        norm = sum(x**2 for x in vector) ** 0.5
        if norm > 0:
            vector = [x / norm for x in vector]
        
        return vector
    
    def _cosine_similarity(self, a: np.ndarray, b: np.ndarray) -> np.ndarray:
        """Compute cosine similarity between vector and matrix."""
        a_norm = a / (np.linalg.norm(a) + 1e-8)
        b_norm = b / (np.linalg.norm(b, axis=1, keepdims=True) + 1e-8)
        return np.dot(b_norm, a_norm)
    
    def _persist(self):
        """Save vector index to disk."""
        data = {
            "entries": [
                {
                    "id": e.id,
                    "text": e.text,
                    "vector": e.vector,
                    "metadata": e.metadata,
                    "timestamp": e.timestamp
                }
                for e in self._vectors.values()
            ]
        }
        with open(self.index_file, 'w') as f:
            json.dump(data, f)
    
    def _now(self) -> str:
        """Get current timestamp."""
        from datetime import datetime
        return datetime.now().isoformat()
    
    def _get_file_size(self) -> float:
        """Get index file size in MB."""
        if self.index_file.exists():
            return round(self.index_file.stat().st_size / (1024 * 1024), 2)
        return 0.0
