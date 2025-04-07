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
OPENAI_API_KEY = os.environ.get("OPENAI_API_KEY")
openai = OpenAI(api_key=OPENAI_API_KEY)

# Global variables for vector store
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
    Initialize the FAISS vector store with knowledge base articles.
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
        
        logger.info(f"Vector store initialized with {len(documents)} documents")
        
    except Exception as e:
        logger.error(f"Error initializing vector store: {str(e)}")

def query_vector_store(query, top_k=3):
    """
    Query the vector store for documents relevant to the query.
    
    Args:
        query (str): The query text
        top_k (int): Number of top results to return
        
    Returns:
        list: The relevant documents
    """
    global index, documents
    
    if index is None or not documents:
        logger.warning("Vector store not initialized")
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
        logger.error(f"Error querying vector store: {str(e)}")
        return []
