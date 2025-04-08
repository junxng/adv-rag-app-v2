import os
import logging
import json
from openai import OpenAI
from pinecone import Pinecone, ServerlessSpec
from langchain.embeddings import OpenAIEmbeddings
from langchain_pinecone import PineconeVectorStore
from .db.models import KnowledgeArticle

# Set up logging
logger = logging.getLogger(__name__)

# Initialize OpenAI client
OPENAI_API_KEY = os.environ.get("OPENAI_API_KEY")
openai = OpenAI(api_key=OPENAI_API_KEY)

# Pinecone configuration
PINECONE_API_KEY = os.environ.get("PINECONE_API_KEY")
PINECONE_ENVIRONMENT = os.environ.get("PINECONE_ENVIRONMENT", "gcp-starter")
PINECONE_INDEX_NAME = os.environ.get("PINECONE_INDEX_NAME", "tech-support-kb")

class PineconeService:
    """Service class for Pinecone vector database operations"""

    def __init__(self):
        """Initialize Pinecone client with appropriate credentials."""
        if not PINECONE_API_KEY:
            logger.warning("PINECONE_API_KEY is not set. Vector store will not be available.")
            self.is_available = False
            return

        try:
            # Initialize Pinecone
            self.pc = Pinecone(api_key=PINECONE_API_KEY)

            # Check if index exists
            indexes = [index.name for index in self.pc.list_indexes()]

            if PINECONE_INDEX_NAME not in indexes:
                # Create index if it doesn't exist
                self.pc.create_index(
                    name=PINECONE_INDEX_NAME,
                    dimension=1536,  # OpenAI embedding dimension
                    metric="cosine",
                    spec=ServerlessSpec(
                        cloud="aws",
                        region="us-west-2"
                    )
                )
                logger.info(f"Created Pinecone index: {PINECONE_INDEX_NAME}")

            # Get the index
            self.index = self.pc.Index(PINECONE_INDEX_NAME)
            self.is_available = True

            # Set up LangChain integration
            self.embeddings = OpenAIEmbeddings(openai_api_key=OPENAI_API_KEY)
            self.vector_store = PineconeVectorStore(
                index=self.index,
                embedding=self.embeddings,
                text_key="text"
            )

            logger.info("Pinecone service initialized successfully")

        except Exception as e:
            logger.error(f"Error initializing Pinecone: {str(e)}")
            self.is_available = False

    def populate_from_knowledge_articles(self):
        """
        Populate the vector store with knowledge articles from the database.

        Returns:
            bool: True if successful, False otherwise
        """
        if not self.is_available:
            logger.warning("Pinecone is not available. Cannot populate vector store.")
            return False

        try:
            # Get knowledge articles from database
            articles = KnowledgeArticle.query.all()

            if not articles:
                logger.warning("No knowledge articles found in database")
                return False

            # Prepare documents for ingestion
            documents = []
            for article in articles:
                # Create a document with metadata
                text = f"{article.title}\n{article.content}"
                metadata = {
                    "id": article.id,
                    "title": article.title,
                    "category": article.category
                }
                documents.append((str(article.id), text, metadata))

            # Insert into Pinecone
            for doc_id, text, metadata in documents:
                embedding = self.embeddings.embed_query(text)
                self.index.upsert(vectors=[{
                    "id": doc_id,
                    "values": embedding,
                    "metadata": {
                        "text": text,
                        **metadata
                    }
                }])

            logger.info(f"Populated Pinecone with {len(documents)} documents")
            return True

        except Exception as e:
            logger.error(f"Error populating Pinecone: {str(e)}")
            return False

    def query(self, query_text, top_k=3):
        """
        Query the vector store for relevant documents.

        Args:
            query_text (str): The query text
            top_k (int): Number of results to return

        Returns:
            list: List of relevant documents
        """
        if not self.is_available:
            logger.warning("Pinecone is not available. Cannot query vector store.")
            return []

        try:
            # Get embedding for query
            query_embedding = self.embeddings.embed_query(query_text)

            # Query Pinecone
            results = self.index.query(
                vector=query_embedding,
                top_k=top_k,
                include_metadata=True
            )

            # Format results
            documents = []
            for match in results.matches:
                metadata = match.metadata
                documents.append({
                    "id": match.id,
                    "title": metadata.get("title", ""),
                    "content": metadata.get("text", ""),
                    "category": metadata.get("category", ""),
                    "score": match.score
                })

            return documents

        except Exception as e:
            logger.error(f"Error querying Pinecone: {str(e)}")
            return []

    def delete_all(self):
        """
        Delete all vectors from the index.

        Returns:
            bool: True if successful, False otherwise
        """
        if not self.is_available:
            logger.warning("Pinecone is not available. Cannot delete vectors.")
            return False

        try:
            self.index.delete(delete_all=True)
            logger.info(f"Deleted all vectors from index {PINECONE_INDEX_NAME}")
            return True

        except Exception as e:
            logger.error(f"Error deleting vectors from Pinecone: {str(e)}")
            return False