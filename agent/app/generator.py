from app.config import OPENAI_API_KEY
import openai
from typing import Generator, Union
import logging

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Initialize OpenAI client
client = openai.OpenAI(api_key=OPENAI_API_KEY)

def generate_answer(context: str, query: str, stream: bool = False) -> Union[str, Generator[str, None, None]]:
    try:
        logger.info(f"Generator received context length: {len(context) if context else 0}")
        logger.info(f"Generator received query: {query}")
        
        # Conversational queries
        conversational_patterns = [
            'hi', 'hello', 'hey', 'greetings', 'good morning', 'good afternoon', 'good evening',
            'how are you', 'thank you', 'thanks', 'bye', 'goodbye', 'see you',
            'nice to meet you', 'pleasure to meet you'
        ]
        query_lower = query.lower().strip()
        is_conversational = any(
            query_lower == pattern or 
            query_lower.startswith(pattern + ' ') or 
            query_lower.startswith(pattern + '?') or 
            query_lower.startswith(pattern + '!')
            for pattern in conversational_patterns
        )

        if is_conversational:
            logger.info("Conversational query detected")
            system_prompt = """You are a friendly and helpful assistant. Respond naturally to the user's message.
            For greetings, thank you messages, or general conversation, provide appropriate and engaging responses.
            Keep your responses concise, friendly, and conversational."""

            response = client.chat.completions.create(
                model="gpt-4",
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": query}
                ],
                stream=stream
            )

            if stream:
                logger.info("Streaming conversational response")
                for chunk in response:
                    if chunk.choices[0].delta.content is not None:
                        yield chunk.choices[0].delta.content
                return
            else:
                logger.info("Returning conversational response")
                return response.choices[0].message.content

        # If context is empty OR web search is OFF (we assume presence of "Web search results:" means it's ON)
        if not context or context.strip() == "" or "Web search results:" not in context:
            logger.info("Only DB results or empty context – using strict factual answer prompt")
            system_prompt = """You are a helpful assistant that answers questions based on the information in your database.
            IMPORTANT RULES:
            1. Use information that is present in the database content
            2. If the database content contains relevant information, provide a clear and informative answer
            3. If the database content doesn't contain the answer, respond with:
               "I don't have this information in my database. To get accurate answers, please upload relevant documents first."
            4. You can organize and structure the information in a clear way
            5. You can explain concepts that are mentioned in the database
            6. You can connect related pieces of information from the database
            7. DO NOT make up information not present in the database
            8. DO NOT add external knowledge that contradicts the database content"""

            prompt = f"""Context from database:
{context}

Question: {query}

Please provide a clear and informative answer based on the above context. If the context doesn't contain relevant information, say so."""

            response = client.chat.completions.create(
                model="gpt-4",
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": prompt}
                ],
                stream=stream
            )

            if stream:
                logger.info("Streaming strict DB-only response")
                for chunk in response:
                    if chunk.choices[0].delta.content is not None:
                        yield chunk.choices[0].delta.content
                return
            else:
                logger.info("Returning strict DB-only response")
                return response.choices[0].message.content

        # If both DB and web search results are present
        logger.info("Using AI model to generate response with DB + web context")

        if "Web search results:" in context:
            logger.info("Processing combined DB and web search results")
            system_prompt = """You are a helpful assistant. Use the information provided in the context to answer the question. 
            The context contains both database results and web search results. 
            Provide a clear, concise, and informative response based on the available information."""
        else:
            logger.info("Processing only database results")
            system_prompt = """You are a helpful assistant. Your task is to provide a clear and informative answer based on the database results provided.
            While you should primarily use the information from the database, you can:
            1. Organize and structure the information in a clear way
            2. Explain concepts that are mentioned in the database
            3. Connect related pieces of information
            4. Use your knowledge to help explain or clarify the database content
            5. Provide additional context if it helps explain the database content
            
            However, do not:
            1. Make up information not present in the database
            2. Add external knowledge that contradicts the database content
            3. Speculate beyond what's in the database
            
            If the database content is unclear or incomplete, you can:
            1. Explain what information is available
            2. Suggest what additional information might be helpful
            3. Ask for clarification if needed"""

        prompt = f"Context:\n{context}\n\nQuestion: {query}\n\nPlease provide a clear and informative answer based on the above context."

        response = client.chat.completions.create(
            model="gpt-4",
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": prompt}
            ],
            stream=stream
        )

        if stream:
            logger.info("Streaming AI response")
            for chunk in response:
                if chunk.choices[0].delta.content is not None:
                    yield chunk.choices[0].delta.content
        else:
            logger.info("Returning AI response")
            return response.choices[0].message.content

    except openai.RateLimitError:
        logger.error("OpenAI API rate limit exceeded")
        raise Exception("Rate limit exceeded. Please try again later.")
    except openai.APIError as e:
        logger.error(f"OpenAI API error: {str(e)}")
        raise Exception("Error communicating with OpenAI API")
    except Exception as e:
        logger.error(f"Unexpected error: {str(e)}")
        raise Exception("An unexpected error occurred")
