import os
import logging
from langchain.memory import ConversationBufferMemory, ChatMessageHistory
from langchain.schema import HumanMessage, AIMessage

# Set up logging
logger = logging.getLogger(__name__)

class MemoryManager:
    """
    Manager for handling conversation memory using LangChain's memory components.
    This provides more sophisticated conversation history management than basic session storage.
    """
    
    def __init__(self):
        """Initialize the memory manager."""
        self.memories = {}  # Dictionary to store memories by session ID
    
    def get_memory(self, session_id):
        """
        Get or create a memory for a specific session.
        
        Args:
            session_id (str): The session identifier
            
        Returns:
            ConversationBufferMemory: The memory for this session
        """
        if session_id not in self.memories:
            # Create a new memory for this session
            self.memories[session_id] = ConversationBufferMemory(
                memory_key="chat_history",
                return_messages=True
            )
            logger.debug(f"Created new memory for session {session_id}")
        
        return self.memories[session_id]
    
    def add_user_message(self, session_id, message):
        """
        Add a user message to the memory.
        
        Args:
            session_id (str): The session identifier
            message (str): The user's message
        """
        memory = self.get_memory(session_id)
        memory.chat_memory.add_user_message(message)
        logger.debug(f"Added user message to session {session_id}")
    
    def add_ai_message(self, session_id, message):
        """
        Add an AI message to the memory.
        
        Args:
            session_id (str): The session identifier
            message (str): The AI's message
        """
        memory = self.get_memory(session_id)
        memory.chat_memory.add_ai_message(message)
        logger.debug(f"Added AI message to session {session_id}")
    
    def get_chat_history(self, session_id, k=None):
        """
        Get the chat history for a session.
        
        Args:
            session_id (str): The session identifier
            k (int, optional): The number of recent messages to return. If None, returns all messages.
            
        Returns:
            list: The chat history as a list of messages
        """
        memory = self.get_memory(session_id)
        messages = memory.chat_memory.messages
        
        if k is not None and len(messages) > k:
            # Return only the k most recent messages
            messages = messages[-k:]
        
        # Convert to the format expected by our application
        formatted_messages = []
        for msg in messages:
            if isinstance(msg, HumanMessage):
                formatted_messages.append({"role": "user", "content": msg.content})
            elif isinstance(msg, AIMessage):
                formatted_messages.append({"role": "assistant", "content": msg.content})
        
        return formatted_messages
    
    def clear_memory(self, session_id):
        """
        Clear the memory for a session.
        
        Args:
            session_id (str): The session identifier
        """
        if session_id in self.memories:
            self.memories[session_id].clear()
            logger.debug(f"Cleared memory for session {session_id}")
    
    def import_from_session(self, session_id, chat_history):
        """
        Import chat history from a session into the LangChain memory.
        
        Args:
            session_id (str): The session identifier
            chat_history (list): List of message dictionaries with 'role' and 'content'
        """
        # Create a new memory with the chat history
        memory = ConversationBufferMemory(
            memory_key="chat_history",
            return_messages=True
        )
        
        # Create a message history
        message_history = ChatMessageHistory()
        
        # Add messages to the history
        for message in chat_history:
            if message["role"] == "user":
                message_history.add_user_message(message["content"])
            elif message["role"] == "assistant":
                message_history.add_ai_message(message["content"])
        
        # Set the chat memory
        memory.chat_memory = message_history
        
        # Store in our memories dictionary
        self.memories[session_id] = memory
        logger.debug(f"Imported chat history for session {session_id}")
    
    def get_memory_variables(self, session_id):
        """
        Get the memory variables for LangChain chains.
        
        Args:
            session_id (str): The session identifier
            
        Returns:
            dict: Dictionary with memory variables
        """
        memory = self.get_memory(session_id)
        return memory.load_memory_variables({})

# Create a singleton instance
memory_manager = MemoryManager()