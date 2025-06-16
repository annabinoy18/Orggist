from fastapi import FastAPI, Request, HTTPException
from fastapi.responses import StreamingResponse, JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from app.search import search_similar, add_document
from app.generator import generate_answer
from app.web_search import fetch_web_search_context
from app.embedding import get_embedding
import logging
import sys

# Set up logging with more detailed configuration
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(sys.stdout)
    ]
)
logger = logging.getLogger(__name__)

app = FastAPI()

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Allow all origins for development
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

class Query(BaseModel):
    query: str
    web_search: bool = False
    similarity_threshold: float = 0.1

class EmbeddingRequest(BaseModel):
    text: str

class DocumentRequest(BaseModel):
    content: str

@app.post("/ask")
async def ask(query: Query):
    logger.info(f"Received web_search value: {query.web_search}, type: {type(query.web_search)}")
    try:
        # Log the incoming request details
        logger.info("=== New Query Request ===")
        logger.info(f"Query text: {query.query}")
        logger.info(f"Web search toggle: {query.web_search} (type: {type(query.web_search)})")
        logger.info(f"Similarity threshold: {query.similarity_threshold}")
        logger.info(f"Full query object: {query.dict()}")
        
        # Search for similar documents in vector DB
        context_docs = search_similar(
            query.query, 
            top_k=5,
            similarity_threshold=query.similarity_threshold
        )
        
        # Initialize context
        context = ""
        
        # Case 1: No documents found in vector DB
        if not context_docs:
            logger.info("No documents found in vector DB")
            if not query.web_search:
                logger.info("Web search is OFF - returning no results message")
                logger.info("Passing empty context to generator")
                return StreamingResponse(
                    (chunk.encode('utf-8') for chunk in generate_answer(
                        "",  # Empty context will trigger no results message
                        query.query,
                        stream=True
                    )),
                    media_type="text/html"
                )
            else:
                logger.info("Web search is ON - fetching web results")
                web_context = fetch_web_search_context(query.query)
                context = f"Web search results:\n{web_context}"
                logger.info(f"Web context length: {len(context)}")
        else:
            # Case 2: Documents found in vector DB
            db_context = "\n".join([doc["text"] for doc in context_docs])
            logger.info(f"Found {len(context_docs)} documents in vector DB")
            logger.info(f"DB context preview: {db_context[:200]}...")  # Log first 200 chars
            
            if not query.web_search:
                # Only use DB results
                logger.info("Web search is OFF - using only vector DB results")
                context = f"Vector DB results:\n{db_context}"
                logger.info(f"DB context length: {len(context)}")
                logger.info("Passing only DB results to generator")
            else:
                # Combine DB and web results
                logger.info("Web search is ON - combining with web results")
                web_context = fetch_web_search_context(query.query)
                context = f"Vector DB results:\n{db_context}\n\nWeb search results:\n{web_context}"
                logger.info(f"Combined context length: {len(context)}")
                logger.info("Passing combined results to generator")
        
        # Generate response
        logger.info("Generating final response")
        return StreamingResponse(
            (chunk.encode('utf-8') for chunk in generate_answer(
                context,
                query.query,
                stream=True
            )),
            media_type="text/html"
        )
        
    except Exception as e:
        logger.error(f"Error processing query: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/get-embedding")
async def get_text_embedding(request: EmbeddingRequest):
    try:
        logger.info(f"Received request for embedding text of length {len(request.text)}")
        embedding = get_embedding(request.text)
        if embedding is None:
            logger.error("Failed to generate embedding")
            raise HTTPException(status_code=500, detail="Failed to generate embedding")
        logger.info(f"Successfully generated embedding of length {len(embedding)}")
        return {"embedding": embedding}
    except Exception as e:
        logger.error(f"Error generating embedding: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/add-document")
async def add_document_endpoint(request: DocumentRequest):
    try:
        logger.info(f"Received request to add document of length {len(request.content)}")
        success = add_document(request.content)
        if not success:
            logger.error("Failed to add document")
            raise HTTPException(status_code=500, detail="Failed to add document")
        logger.info("Successfully added document")
        return {"status": "success", "message": "Document added successfully"}
    except Exception as e:
        logger.error(f"Error adding document: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))
