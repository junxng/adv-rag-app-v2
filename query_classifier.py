import os
import logging
from langchain.prompts import ChatPromptTemplate
from openai import OpenAI
import json

# the newest OpenAI model is "gpt-4o" which was released May 13, 2024.
# do not change this unless explicitly requested by the user

# Set up logging
logger = logging.getLogger(__name__)

# Initialize OpenAI client
OPENAI_API_KEY = os.environ.get("OPENAI_API_KEY")
openai = OpenAI(api_key=OPENAI_API_KEY)

def classify_query(query, chat_history=None):
    """
    Classifies a user query into one of three categories:
    - account: Related to user account, support tickets, personal data
    - troubleshooting: Technical issues requiring external information
    - knowledge: Company policies, procedures, internal information
    
    Args:
        query (str): The user's query text
        chat_history (list): List of previous messages in the conversation
    
    Returns:
        str: The query type (account, troubleshooting, knowledge)
    """
    try:
        # Include chat history for context
        context = ""
        if chat_history:
            # Get the last few messages for context (up to 5)
            recent_history = chat_history[-5:] if len(chat_history) > 5 else chat_history
            context = "Previous conversation:\n" + "\n".join([
                f"{msg['role']}: {msg['content']}" for msg in recent_history
            ])
        
        # Create the classification prompt
        classification_prompt = f"""
        Classify the following user query into ONE of these categories:
        - account: Related to user account, support tickets, personal data (e.g. "What's my ticket status?")
        - troubleshooting: Technical issues requiring external information (e.g. "How do I fix a slow laptop?")
        - knowledge: Company policies, procedures, internal information (e.g. "What is our remote work policy?")
        
        {context}
        
        User query: {query}
        
        Respond with a JSON object with a single key 'category' and the value as one of the three options: 'account', 'troubleshooting', or 'knowledge'.
        """
        
        # Call the OpenAI API for classification
        response = openai.chat.completions.create(
            model="gpt-4o",
            messages=[{"role": "user", "content": classification_prompt}],
            response_format={"type": "json_object"},
            temperature=0.3  # Lower temperature for more deterministic classification
        )
        
        # Extract and return the category
        result = json.loads(response.choices[0].message.content)
        category = result.get("category", "knowledge")  # Default to 'knowledge' if parsing fails
        
        logger.debug(f"Query classified as: {category}")
        return category
        
    except Exception as e:
        logger.error(f"Error in query classification: {str(e)}")
        # Default to knowledge base if classification fails
        return "knowledge"
