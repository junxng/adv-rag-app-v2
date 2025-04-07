import os
import json
import logging
import numpy as np
import faiss
from openai import OpenAI
from models import KnowledgeArticle

# the newest OpenAI model is "gpt-4o" which was released May 13, 2024.
# do not change this unless explicitly requested by the user

# Set up logging
logger = logging.getLogger(__name__)

# Initialize OpenAI client
OPENAI_API_KEY = os.environ.get("OPENAI_API_KEY", "")
# Only initialize the OpenAI client if we have an API key
if OPENAI_API_KEY:
    openai = OpenAI(api_key=OPENAI_API_KEY)
else:
    logger.warning("OPENAI_API_KEY not found in environment variables")
    # Create a placeholder for the openai client to avoid errors
    openai = None

# Check if Pinecone should be used
USE_PINECONE = os.environ.get("USE_PINECONE", "false").lower() == "true"
PINECONE_API_KEY = os.environ.get("PINECONE_API_KEY")

# Global variables for local FAISS vector store (fallback)
index = None
documents = []
document_ids = []

def get_embedding(text):
    """
    Get embedding for a text using OpenAI's embedding model.
    
    Args:
        text (str): The text to embed
        
    Returns:
        list: The embedding vector
    """
    # If OpenAI client is not available, return a zero vector
    if openai is None:
        logger.warning("OpenAI client not initialized, returning zero vector")
        return [0] * 1536  # Ada embeddings are 1536 dimensions
        
    try:
        response = openai.embeddings.create(
            model="text-embedding-ada-002",
            input=text
        )
        return response.data[0].embedding
    except Exception as e:
        logger.error(f"Error generating embedding: {str(e)}")
        # Return a zero vector if embedding fails
        return [0] * 1536  # Ada embeddings are 1536 dimensions

def initialize_vector_store():
    """
    Initialize the vector store with knowledge base articles.
    Uses Pinecone if available, otherwise falls back to local FAISS.
    """
    # Try to use Pinecone if configured
    if USE_PINECONE and PINECONE_API_KEY:
        try:
            # Import Pinecone service (import here to avoid circular imports)
            from pinecone_service import PineconeService
            
            # Initialize Pinecone
            pinecone = PineconeService()
            
            # Populate Pinecone from knowledge articles
            if pinecone.is_available:
                success = pinecone.populate_from_knowledge_articles()
                if success:
                    logger.info("Pinecone vector store initialized successfully")
                    return
                else:
                    logger.warning("Failed to populate Pinecone, falling back to FAISS")
            else:
                logger.warning("Pinecone is not available, falling back to FAISS")
                
        except Exception as e:
            logger.error(f"Error initializing Pinecone: {str(e)}")
            logger.warning("Falling back to local FAISS vector store")
    
    # Initialize local FAISS vector store as fallback
    initialize_faiss_vector_store()

def initialize_faiss_vector_store():
    """
    Initialize the local FAISS vector store with knowledge base articles.
    """
    global index, documents, document_ids
    
    try:
        # Get knowledge articles from database
        articles = KnowledgeArticle.query.all()
        
        if not articles:
            logger.warning("No knowledge articles found in database")
            return
        
        # Create document representations
        documents = []
        document_ids = []
        embeddings = []
        
        for article in articles:
            # Create a document with the article content
            doc = {
                "id": article.id,
                "title": article.title,
                "content": article.content,
                "category": article.category
            }
            documents.append(doc)
            document_ids.append(article.id)
            
            # Get embedding for the article
            text_to_embed = f"{article.title}\n{article.content}"
            embedding = get_embedding(text_to_embed)
            embeddings.append(embedding)
        
        # Create FAISS index
        dimension = len(embeddings[0])
        index = faiss.IndexFlatL2(dimension)
        
        # Add embeddings to index
        embeddings_array = np.array(embeddings).astype('float32')
        index.add(embeddings_array)
        
        logger.info(f"FAISS vector store initialized with {len(documents)} documents")
        
    except Exception as e:
        logger.error(f"Error initializing FAISS vector store: {str(e)}")

def query_vector_store(query, top_k=3):
    """
    Query the vector store for documents relevant to the query.
    Uses Pinecone if available, otherwise falls back to local FAISS.
    
    Args:
        query (str): The query text
        top_k (int): Number of top results to return
        
    Returns:
        list: The relevant documents
    """
    # Try to use Pinecone if configured
    if USE_PINECONE and PINECONE_API_KEY:
        try:
            # Import Pinecone service
            from pinecone_service import PineconeService
            
            # Initialize Pinecone
            pinecone = PineconeService()
            
            # Query Pinecone
            if pinecone.is_available:
                results = pinecone.query(query, top_k)
                if results:
                    return results
                else:
                    logger.warning("No results from Pinecone, falling back to FAISS")
            else:
                logger.warning("Pinecone is not available, falling back to FAISS")
                
        except Exception as e:
            logger.error(f"Error querying Pinecone: {str(e)}")
            logger.warning("Falling back to local FAISS vector store")
    
    # Query local FAISS vector store as fallback
    return query_faiss_vector_store(query, top_k)

def query_faiss_vector_store(query, top_k=3):
    """
    Query the local FAISS vector store for documents relevant to the query.
    
    Args:
        query (str): The query text
        top_k (int): Number of top results to return
        
    Returns:
        list: The relevant documents
    """
    global index, documents
    
    if index is None or not documents:
        logger.warning("FAISS vector store not initialized")
        return []
    
    try:
        # Get embedding for the query
        query_embedding = get_embedding(query)
        query_embedding_array = np.array([query_embedding]).astype('float32')
        
        # Search the index
        D, I = index.search(query_embedding_array, top_k)
        
        # Collect results
        results = []
        for i in I[0]:
            if i < len(documents):
                results.append(documents[i])
        
        return results
        
    except Exception as e:
        logger.error(f"Error querying FAISS vector store: {str(e)}")
        return []
