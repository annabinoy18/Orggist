import pickle
from pathlib import Path
import logging
import sys
import os

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format='%(message)s',
    handlers=[logging.StreamHandler(sys.stdout)]
)
logger = logging.getLogger(__name__)

def check_vector_db():
    # Get the absolute path to the data directory
    current_dir = Path(os.path.dirname(os.path.abspath(__file__)))
    data_dir = current_dir.parent / "data"
    doc_store_path = data_dir / "doc_store.pkl"
    
    print(f"\nChecking database at: {doc_store_path}")
    
    try:
        if not doc_store_path.exists():
            print(f"Document store file not found at: {doc_store_path}")
            return
            
        with open(doc_store_path, 'rb') as f:
            doc_store = pickle.load(f)
        
        print("\n=== Vector Database Contents ===")
        print(f"Total documents stored: {len(doc_store)}")
        print("\nDocument contents:")
        
        for i, doc in enumerate(doc_store, 1):
            print(f"\n--- Document {i} ---")
            # Print first 500 characters of each document
            preview = doc[:500] + "..." if len(doc) > 500 else doc
            print(preview)
            
    except Exception as e:
        print(f"Error reading document store: {str(e)}")
        print(f"Current working directory: {os.getcwd()}")
        print(f"Data directory exists: {data_dir.exists()}")
        if data_dir.exists():
            print(f"Files in data directory: {list(data_dir.glob('*'))}")

if __name__ == "__main__":
    check_vector_db() 