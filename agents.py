import os
import logging
from openai import OpenAI

# the newest OpenAI model is "gpt-4o" which was released May 13, 2024.
# do not change this unless explicitly requested by the user

# Set up logging
logger = logging.getLogger(__name__)

# Initialize OpenAI client
OPENAI_API_KEY = os.environ.get("OPENAI_API_KEY")
openai = OpenAI(api_key=OPENAI_API_KEY)

def format_chat_history(chat_history):
    """
    Format chat history for OpenAI API.
    
    Args:
        chat_history (list): List of message dictionaries with 'role' and 'content'
        
    Returns:
        list: Formatted messages for OpenAI API
    """
    formatted_messages = []
    
    # Add system message
    formatted_messages.append({
        "role": "system", 
        "content": "You are a helpful tech support assistant that provides accurate information and helpful solutions."
    })
    
    # Add chat history
    for message in chat_history:
        formatted_messages.append({
            "role": message["role"],
            "content": message["content"]
        })
    
    return formatted_messages

def generate_response(messages):
    """
    Generate a response using OpenAI GPT model.
    
    Args:
        messages (list): List of messages for the conversation
        
    Returns:
        str: The generated response
    """
    try:
        response = openai.chat.completions.create(
            model="gpt-4o",
            messages=messages,
            temperature=0.7,
            max_tokens=1000
        )
        
        return response.choices[0].message.content
        
    except Exception as e:
        logger.error(f"Error generating response: {str(e)}")
        return "I'm having trouble generating a response right now. Please try again later."
