import faiss
import numpy as np
import os
import pickle
from pathlib import Path
import logging
from typing import List, Dict, Any
from .embedding import get_embedding

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Get the absolute path to the data directory
current_dir = Path(os.path.dirname(os.path.abspath(__file__)))
data_dir = current_dir.parent / "data"
data_dir.mkdir(exist_ok=True, parents=True)

# Define file paths
index_path = data_dir / "faiss_index.bin"
doc_store_path = data_dir / "doc_store.pkl"

# Initialize or load FAISS index and document store
def load_or_create_index():
    """Load existing index and document store or create new ones"""
    try:
        # Check if both files exist and have content
        if index_path.exists() and doc_store_path.exists():
            try:
                logger.info(f"Loading existing index and document store from {data_dir}")
                index = faiss.read_index(str(index_path))
                with open(doc_store_path, 'rb') as f:
                    doc_store = pickle.load(f)
                
                # Verify that both index and doc_store have content
                if index.ntotal > 0 and len(doc_store) > 0:
                    logger.info(f"Successfully loaded index with {index.ntotal} vectors and {len(doc_store)} documents")
                    return index, doc_store
                else:
                    logger.warning("Existing index or document store is empty, creating new ones")
            except Exception as e:
                logger.error(f"Error loading existing index or document store: {str(e)}")
                logger.info("Creating new index and document store")
        else:
            logger.info("Index or document store files not found, creating new ones")
        
        # Create new index and document store
        index = faiss.IndexFlatL2(768)
        doc_store = []
        logger.info("Created new empty index and document store")
        return index, doc_store
        
    except Exception as e:
        logger.error(f"Unexpected error in load_or_create_index: {str(e)}")
        # If there's an error, create a new index
        index = faiss.IndexFlatL2(768)
        doc_store = []
        return index, doc_store

# Load or create index and document store
index, doc_store = load_or_create_index()

def save_index_and_docs():
    """Save the current index and document store to disk"""
    try:
        logger.info("Saving index and document store to disk")
        # Ensure directory exists
        data_dir.mkdir(exist_ok=True, parents=True)
        
        # Save index
        faiss.write_index(index, str(index_path))
        
        # Save document store
        with open(doc_store_path, 'wb') as f:
            pickle.dump(doc_store, f)
            
        logger.info(f"Saved index with {index.ntotal} vectors and {len(doc_store)} documents")
    except Exception as e:
        logger.error(f"Error saving index and docs: {str(e)}")
        raise

def add_document(text: str, embedding: List[float] = None):
    """Add a document to the vector store"""
    try:
        logger.info(f"Adding document to vector store, text length: {len(text)}")
        logger.info(f"Current index size before adding: {index.ntotal} vectors")
        logger.info(f"Current document store size before adding: {len(doc_store)} documents")
        
        # If embedding is not provided, get it
        if embedding is None:
            embedding = get_embedding(text)
            if embedding is None:
                logger.error("Failed to get embedding for document")
                return False
            logger.info(f"Generated embedding of length: {len(embedding)}")

        # Add to FAISS index
        index.add(np.array([embedding]))
        
        # Add to document store
        doc_store.append(text)
        
        # Save to disk
        save_index_and_docs()
        
        logger.info(f"Successfully added document to vector store")
        logger.info(f"New index size: {index.ntotal} vectors")
        logger.info(f"New document store size: {len(doc_store)} documents")
        logger.info(f"Document preview: {text[:200]}...")
        return True
    except Exception as e:
        logger.error(f"Error adding document to vector store: {str(e)}")
        return False

def search_similar(query: str, top_k: int = 5, similarity_threshold: float = 0.05) -> List[Dict[str, Any]]:
    """Search for similar documents"""
    try:
        logger.info(f"Searching for similar documents to query: {query[:100]}...")
        logger.info(f"Using similarity threshold: {similarity_threshold}")
        logger.info(f"Current index size: {index.ntotal} vectors")
        logger.info(f"Current document store size: {len(doc_store)} documents")
        
        if index.ntotal == 0:
            logger.warning("No documents in the index")
            return []

        # Get embedding for the query
        query_embedding = get_embedding(query)
        if query_embedding is None:
            logger.error("Failed to get embedding for query")
            return []

        # Search in FAISS index
        distances, indices = index.search(np.array([query_embedding]), top_k)
        
        # Get the corresponding documents
        results = []
        logger.info("=== Detailed Search Results ===")
        for i, (distance, idx) in enumerate(zip(distances[0], indices[0])):
            if idx < len(doc_store):  # Ensure index is valid
                similarity_score = float(1 / (1 + distance))  # Convert distance to similarity score
                logger.info(f"\nResult {i+1}:")
                logger.info(f"  Distance: {distance:.6f}")
                logger.info(f"  Similarity Score: {similarity_score:.6f}")
                logger.info(f"  Threshold: {similarity_threshold:.6f}")
                logger.info(f"  Document Index: {idx}")
                logger.info(f"  Document Preview: {doc_store[idx][:200]}...")
                
                if similarity_score >= similarity_threshold:
                    results.append({
                        "text": doc_store[idx],
                        "score": similarity_score,
                        "rank": i + 1
                    })
                    logger.info(f"  ✓ Match accepted (score >= threshold)")
                else:
                    logger.info(f"  ✗ Match rejected (score < threshold)")
            else:
                logger.warning(f"Invalid index {idx} found in search results")

        logger.info(f"\nSearch Summary:")
        logger.info(f"Total results found: {len(results)}")
        logger.info(f"Results above threshold: {len(results)}")
        logger.info(f"Results below threshold: {top_k - len(results)}")
        return results
    except Exception as e:
        logger.error(f"Error searching for similar documents: {str(e)}")
        return []
