import google.generativeai as genai
import logging
from typing import List, Optional
from app.config import GEMINI_API_KEY

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Configure Gemini API
genai.configure(api_key=GEMINI_API_KEY)

# Initialize the model
model = genai.get_model("embedding-001")

def get_embedding(text: str) -> Optional[List[float]]:
    """Get embedding for text using Gemini API"""
    try:
        logger.info(f"Getting embedding for text of length {len(text)}")
        
        # Get embedding
        result = genai.embed_content(
            model="embedding-001",
            content=text,
            task_type="retrieval_document"
        )
        
        if result and "embedding" in result:
            logger.info(f"Successfully generated embedding of length {len(result['embedding'])}")
            return result["embedding"]
        else:
            logger.error("Failed to get embedding from model response")
            return None
            
    except Exception as e:
        logger.error(f"Error getting embedding: {str(e)}")
        return None
