import requests
import PyPDF2
import io
from typing import List
import json
import os
from datetime import datetime
from app.search import add_document
from app.embedding import get_embedding
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import logging

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Create FastAPI app
app = FastAPI()

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Allow all origins for development
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Define request model
class PDFProcessRequest(BaseModel):
    presigned_urls: List[str]
    file_names: List[str]

class PDFProcessor:
    def __init__(self):
        self.processed_files = set()  # Keep track of processed files to avoid duplicates
        logger.info("PDFProcessor initialized")

    def download_pdf(self, presigned_url: str) -> bytes:
        """Download PDF from presigned URL"""
        try:
            logger.info(f"Attempting to download PDF from URL: {presigned_url[:100]}...")
            response = requests.get(presigned_url)
            response.raise_for_status()
            logger.info(f"Successfully downloaded PDF, size: {len(response.content)} bytes")
            return response.content
        except Exception as e:
            logger.error(f"Error downloading PDF: {str(e)}")
            return None

    def extract_text_from_pdf(self, pdf_content: bytes) -> str:
        """Extract text from PDF content"""
        try:
            logger.info("Starting PDF text extraction")
            pdf_file = io.BytesIO(pdf_content)
            pdf_reader = PyPDF2.PdfReader(pdf_file)
            text = ""
            total_pages = len(pdf_reader.pages)
            logger.info(f"PDF has {total_pages} pages")
            
            for i, page in enumerate(pdf_reader.pages):
                page_text = page.extract_text()
                text += page_text + "\n"
                logger.info(f"Extracted text from page {i+1}/{total_pages}, length: {len(page_text)} chars")
            
            logger.info(f"Total extracted text length: {len(text)} chars")
            return text
        except Exception as e:
            logger.error(f"Error extracting text from PDF: {str(e)}")
            return None

    def chunk_text(self, text: str, chunk_size: int = 1000) -> List[str]:
        """Split text into smaller chunks for better processing"""
        logger.info(f"Starting text chunking, total text length: {len(text)} chars")
        words = text.split()
        chunks = []
        current_chunk = []
        current_size = 0

        for word in words:
            current_chunk.append(word)
            current_size += len(word) + 1  # +1 for space
            if current_size >= chunk_size:
                chunks.append(" ".join(current_chunk))
                current_chunk = []
                current_size = 0

        if current_chunk:
            chunks.append(" ".join(current_chunk))

        logger.info(f"Created {len(chunks)} chunks from text")
        return chunks

    def process_pdf_urls(self, presigned_urls: List[str], file_names: List[str]):
        """Process multiple PDF URLs and store their contents in vector DB"""
        logger.info("\n=== Starting PDF Processing ===")
        logger.info(f"Received {len(presigned_urls)} files to process")
        
        for url, file_name in zip(presigned_urls, file_names):
            logger.info(f"\nProcessing file: {file_name}")
            if file_name in self.processed_files:
                logger.info(f"File {file_name} already processed, skipping...")
                continue

            # Download PDF
            logger.info(f"Downloading PDF from URL...")
            pdf_content = self.download_pdf(url)
            if not pdf_content:
                logger.error(f"Failed to download {file_name}")
                continue
            logger.info(f"Successfully downloaded {file_name}")

            # Extract text
            logger.info(f"Extracting text from {file_name}...")
            text = self.extract_text_from_pdf(pdf_content)
            if not text:
                logger.error(f"Failed to extract text from {file_name}")
                continue
            logger.info(f"Successfully extracted text from {file_name}")

            # Create metadata
            metadata = {
                "file_name": file_name,
                "processed_date": datetime.now().isoformat(),
                "source_url": url
            }
            logger.info(f"Created metadata for {file_name}")

            # Split text into chunks and add to vector DB
            logger.info(f"Splitting text into chunks and adding to vector DB...")
            chunks = self.chunk_text(text)
            logger.info(f"Created {len(chunks)} chunks from {file_name}")
            
            successful_chunks = 0
            for i, chunk in enumerate(chunks):
                # Add metadata to each chunk
                chunk_with_metadata = f"[{file_name} - Page {i+1}] {chunk}"
                
                try:
                    # Get embedding for the chunk
                    logger.info(f"Getting embedding for chunk {i+1}/{len(chunks)}")
                    embedding = get_embedding(chunk_with_metadata)
                    
                    if embedding is None:
                        logger.error(f"Failed to get embedding for chunk {i+1}")
                        continue
                        
                    # Add to vector DB with embedding
                    add_document(chunk_with_metadata, embedding)
                    successful_chunks += 1
                    logger.info(f"Added chunk {i+1}/{len(chunks)} from {file_name} to vector DB")
                except Exception as e:
                    logger.error(f"Error processing chunk {i+1} from {file_name}: {str(e)}")

            logger.info(f"Successfully added {successful_chunks}/{len(chunks)} chunks to vector DB")
            
            # Mark as processed
            self.processed_files.add(file_name)
            logger.info(f"Successfully processed {file_name}")
        
        logger.info("\n=== PDF Processing Complete ===\n")

# Initialize PDF processor
pdf_processor = PDFProcessor()

@app.post("/process-pdfs")
async def process_pdfs(request: PDFProcessRequest):
    try:
        logger.info(f"Received request to process {len(request.presigned_urls)} PDFs")
        if len(request.presigned_urls) != len(request.file_names):
            logger.error("Number of URLs and file names don't match")
            raise HTTPException(status_code=400, detail="Number of URLs and file names must match")
        
        pdf_processor.process_pdf_urls(request.presigned_urls, request.file_names)
        logger.info("PDF processing completed successfully")
        return {"message": "PDFs processed successfully"}
    except Exception as e:
        logger.error(f"Error processing PDFs: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

if __name__ == "__main__":
    import uvicorn
    logger.info("Starting PDF processor server on port 8001")
    uvicorn.run(app, host="0.0.0.0", port=8001) 