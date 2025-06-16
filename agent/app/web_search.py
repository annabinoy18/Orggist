from app.config import GEMINI_API_KEY
import google.generativeai as genai
import logging

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

genai.configure(api_key=GEMINI_API_KEY)
model = genai.GenerativeModel("gemini-2.0-flash")

def fetch_web_search_context(query: str) -> str:
    try:
        logger.info(f"Starting web search for query: {query}")
        chat = model.start_chat(history=[])
        response = chat.send_message(f"Search the web for this query and summarize key points:\n\n{query}")
        logger.info("Web search completed successfully")
        return response.text
    except Exception as e:
        logger.error(f"Error in web search: {str(e)}")
        return "Error performing web search. Please try again later."
