"""
RAG Example Store - Vector-Based Dynamic Example Retrieval
===========================================================
Enterprise-grade Retrieval Augmented Generation for DSPy examples.

Instead of using all 150+ hardcoded examples, this retrieves the
most semantically relevant examples for each user query.

Benefits:
- Better context: Only relevant examples in prompt
- Smaller prompts: ~5-10 examples vs 150+
- Dynamic learning: New approved feedback auto-added
- Faster inference: Less tokens = faster LLM response

Architecture:
    User Query → Embed → Vector Search → Top-K Examples → DSPy Prompt
                                ↓
                        [Vector Store]
                              ↑
                    Approved Feedback → Auto-Add
"""

import logging
import os
import json
import hashlib
from typing import List, Dict, Any, Optional, Tuple
from pathlib import Path
from datetime import datetime
import threading

logger = logging.getLogger(__name__)

# =============================================================================
# EMBEDDING MODEL - Using sentence-transformers (already installed)
# =============================================================================

try:
    from sentence_transformers import SentenceTransformer
    import numpy as np
    EMBEDDINGS_AVAILABLE = True
except ImportError:
    EMBEDDINGS_AVAILABLE = False
    logger.warning("sentence-transformers not installed. RAG disabled.")

# Configuration
EMBEDDING_MODEL = "all-MiniLM-L6-v2"  # Fast, 384 dimensions, great for similarity
EMBEDDING_DIM = 384
TOP_K_EXAMPLES = 8  # Number of examples to retrieve per query
SIMILARITY_THRESHOLD = 0.3  # Minimum similarity to include example
STORE_PATH = Path("/tmp/rag_example_store")
FEEDBACK_EXAMPLES_FILE = STORE_PATH / "feedback_examples.json"


# =============================================================================
# RAG EXAMPLE STORE CLASS
# =============================================================================

class RAGExampleStore:
    """
    Vector store for SQL examples with semantic retrieval.
    
    Features:
    - Embeds all training examples on initialization
    - Fast cosine similarity search
    - Auto-learns from approved feedback
    - Persists feedback examples to disk
    - Thread-safe operations
    """
    
    _instance = None
    _lock = threading.Lock()
    
    def __new__(cls):
        """Singleton pattern for shared store."""
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = super().__new__(cls)
                    cls._instance._initialized = False
        return cls._instance
    
    def __init__(self):
        """Initialize the RAG store."""
        if self._initialized:
            return
            
        self._initialized = True
        self.model: Optional[SentenceTransformer] = None
        self.examples: List[Dict[str, str]] = []  # {"question": ..., "sql": ...}
        self.embeddings: Optional[np.ndarray] = None
        self.feedback_examples: List[Dict[str, Any]] = []  # From approved feedback
        self._load_lock = threading.Lock()
        
        # Create store directory
        STORE_PATH.mkdir(parents=True, exist_ok=True)
        
        # Load on init
        self._load_model()
        self._load_base_examples()
        self._load_feedback_examples()
        
        logger.info(f"RAG Store initialized: {len(self.examples)} base + {len(self.feedback_examples)} feedback examples")
    
    def _load_model(self):
        """Load the embedding model."""
        if not EMBEDDINGS_AVAILABLE:
            logger.warning("Embeddings not available")
            return
            
        try:
            self.model = SentenceTransformer(EMBEDDING_MODEL)
            logger.info(f"Loaded embedding model: {EMBEDDING_MODEL}")
        except Exception as e:
            logger.error(f"Failed to load embedding model: {e}")
            self.model = None
    
    def _load_base_examples(self):
        """Load base training examples from DSPy optimizer."""
        try:
            from chatbot.dspy_optimizer import TRAINING_EXAMPLES
            self.examples = list(TRAINING_EXAMPLES)
            
            # Embed all examples
            if self.model and self.examples:
                questions = [ex["question"] for ex in self.examples]
                self.embeddings = self.model.encode(questions, convert_to_numpy=True)
                logger.info(f"Embedded {len(self.examples)} base examples")
        except ImportError as e:
            logger.error(f"Could not import training examples: {e}")
            self.examples = []
    
    def _load_feedback_examples(self):
        """Load approved feedback examples from disk."""
        try:
            if FEEDBACK_EXAMPLES_FILE.exists():
                with open(FEEDBACK_EXAMPLES_FILE, 'r') as f:
                    self.feedback_examples = json.load(f)
                logger.info(f"Loaded {len(self.feedback_examples)} feedback examples")
                
                # Re-embed all examples including feedback
                self._rebuild_embeddings()
        except Exception as e:
            logger.error(f"Failed to load feedback examples: {e}")
            self.feedback_examples = []
    
    def _save_feedback_examples(self):
        """Persist feedback examples to disk."""
        try:
            with open(FEEDBACK_EXAMPLES_FILE, 'w') as f:
                json.dump(self.feedback_examples, f, indent=2, default=str)
            logger.info(f"Saved {len(self.feedback_examples)} feedback examples")
        except Exception as e:
            logger.error(f"Failed to save feedback examples: {e}")
    
    def _rebuild_embeddings(self):
        """Rebuild embeddings including feedback examples."""
        if not self.model:
            return
            
        with self._load_lock:
            # Combine base + feedback examples
            all_examples = self.examples + [
                {"question": ex["question"], "sql": ex["sql"]}
                for ex in self.feedback_examples
            ]
            
            if all_examples:
                questions = [ex["question"] for ex in all_examples]
                self.embeddings = self.model.encode(questions, convert_to_numpy=True)
                logger.info(f"Rebuilt embeddings: {len(all_examples)} total examples")
    
    def retrieve(
        self, 
        query: str, 
        top_k: int = TOP_K_EXAMPLES,
        threshold: float = SIMILARITY_THRESHOLD
    ) -> List[Dict[str, str]]:
        """
        Retrieve most relevant examples for a query.
        
        Args:
            query: User's natural language question
            top_k: Maximum number of examples to return
            threshold: Minimum similarity score (0-1)
            
        Returns:
            List of {"question": ..., "sql": ...} examples
        """
        if not self.model or self.embeddings is None:
            # Fallback: return first N examples
            logger.warning("RAG not available, returning first examples")
            return self.examples[:top_k]
        
        try:
            # Embed the query
            query_embedding = self.model.encode([query], convert_to_numpy=True)[0]
            
            # Compute cosine similarities
            # Normalize for cosine similarity
            query_norm = query_embedding / (np.linalg.norm(query_embedding) + 1e-8)
            embeddings_norm = self.embeddings / (np.linalg.norm(self.embeddings, axis=1, keepdims=True) + 1e-8)
            
            similarities = np.dot(embeddings_norm, query_norm)
            
            # Get top-k indices above threshold
            all_examples = self.examples + [
                {"question": ex["question"], "sql": ex["sql"]}
                for ex in self.feedback_examples
            ]
            
            # Sort by similarity
            sorted_indices = np.argsort(similarities)[::-1]
            
            results = []
            for idx in sorted_indices:
                if len(results) >= top_k:
                    break
                if similarities[idx] >= threshold:
                    results.append({
                        "question": all_examples[idx]["question"],
                        "sql": all_examples[idx]["sql"],
                        "similarity": float(similarities[idx])
                    })
            
            logger.debug(f"Retrieved {len(results)} examples for: '{query[:50]}...'")
            return results
            
        except Exception as e:
            logger.error(f"RAG retrieval failed: {e}")
            return self.examples[:top_k]
    
    def add_feedback_example(
        self,
        question: str,
        sql: str,
        feedback_id: str,
        approved_by: str,
        source: str = "feedback"
    ) -> bool:
        """
        Add a new example from approved feedback.
        
        This is the auto-learning mechanism - when admins approve
        a query correction, it gets added to the example store.
        
        Args:
            question: Natural language question
            sql: Correct SQL query
            feedback_id: ID of the feedback record
            approved_by: Admin who approved
            source: Where this came from
            
        Returns:
            True if added successfully
        """
        try:
            # Check for duplicates
            example_hash = hashlib.md5(f"{question}:{sql}".encode()).hexdigest()
            for ex in self.feedback_examples:
                if ex.get("hash") == example_hash:
                    logger.info(f"Duplicate example, skipping: {question[:50]}")
                    return False
            
            # Add new example
            new_example = {
                "question": question,
                "sql": sql,
                "feedback_id": feedback_id,
                "approved_by": approved_by,
                "source": source,
                "added_at": datetime.utcnow().isoformat(),
                "hash": example_hash
            }
            
            self.feedback_examples.append(new_example)
            
            # Persist to disk
            self._save_feedback_examples()
            
            # Rebuild embeddings
            self._rebuild_embeddings()
            
            logger.info(f"Added feedback example: {question[:50]}...")
            return True
            
        except Exception as e:
            logger.error(f"Failed to add feedback example: {e}")
            return False
    
    def get_stats(self) -> Dict[str, Any]:
        """Get store statistics."""
        return {
            "base_examples": len(self.examples),
            "feedback_examples": len(self.feedback_examples),
            "total_examples": len(self.examples) + len(self.feedback_examples),
            "embeddings_loaded": self.embeddings is not None,
            "embedding_model": EMBEDDING_MODEL if self.model else None,
            "embedding_dim": EMBEDDING_DIM,
            "top_k": TOP_K_EXAMPLES,
            "similarity_threshold": SIMILARITY_THRESHOLD
        }
    
    def search_similar(self, query: str, top_k: int = 5) -> List[Dict[str, Any]]:
        """
        Search for similar questions (for debugging/admin).
        
        Returns examples with similarity scores.
        """
        results = self.retrieve(query, top_k=top_k, threshold=0.0)
        return results
    
    def export_feedback_examples(self) -> List[Dict[str, Any]]:
        """Export all feedback examples for training."""
        return self.feedback_examples.copy()
    
    def clear_feedback_examples(self) -> int:
        """Clear all feedback examples (admin only)."""
        count = len(self.feedback_examples)
        self.feedback_examples = []
        self._save_feedback_examples()
        self._rebuild_embeddings()
        return count


# =============================================================================
# SINGLETON ACCESS
# =============================================================================

_store_instance: Optional[RAGExampleStore] = None


def get_rag_store() -> RAGExampleStore:
    """Get the singleton RAG store instance."""
    global _store_instance
    if _store_instance is None:
        _store_instance = RAGExampleStore()
    return _store_instance


def retrieve_examples(query: str, top_k: int = TOP_K_EXAMPLES) -> List[Dict[str, str]]:
    """
    Convenience function to retrieve examples.
    
    Usage:
        examples = retrieve_examples("how many users are there")
        for ex in examples:
            print(f"Q: {ex['question']}")
            print(f"SQL: {ex['sql']}")
    """
    store = get_rag_store()
    return store.retrieve(query, top_k=top_k)


def add_approved_feedback(
    question: str,
    sql: str,
    feedback_id: str,
    approved_by: str
) -> bool:
    """
    Add approved feedback as a new training example.
    
    Call this when an admin approves a SQL correction.
    """
    store = get_rag_store()
    return store.add_feedback_example(
        question=question,
        sql=sql,
        feedback_id=feedback_id,
        approved_by=approved_by
    )


# =============================================================================
# TESTING
# =============================================================================

if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    
    print("Testing RAG Example Store...")
    store = get_rag_store()
    
    # Test retrieval
    test_queries = [
        "how many users are there",
        "show me all files uploaded today",
        "who approved user20",
        "storage used by each organization",
        "pending users waiting for approval"
    ]
    
    print(f"\n📊 Store Stats: {store.get_stats()}")
    
    for query in test_queries:
        print(f"\n🔍 Query: {query}")
        examples = store.retrieve(query, top_k=3)
        for i, ex in enumerate(examples, 1):
            sim = ex.get('similarity', 'N/A')
            print(f"  {i}. [{sim:.3f}] {ex['question'][:60]}")
    
    # Test adding feedback
    print("\n➕ Testing feedback addition...")
    success = store.add_feedback_example(
        question="test query from feedback",
        sql="SELECT 1",
        feedback_id="test-123",
        approved_by="admin"
    )
    print(f"Added: {success}")
    print(f"New stats: {store.get_stats()}")
