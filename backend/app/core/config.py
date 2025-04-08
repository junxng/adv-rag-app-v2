import os
from typing import Optional, Dict, Any, List
from pydantic import BaseModel, Field, validator
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

class Settings(BaseModel):
    """
    Application settings loaded from environment variables
    """
    # API settings
    API_V1_STR: str = "/api"
    PROJECT_NAME: str = "Tech Support Chatbot API"
    PROJECT_DESCRIPTION: str = "API for the tech support chatbot with RAG capabilities"
    VERSION: str = "1.0.0"
    
    # Database settings
    DATABASE_URL: str = Field(
        default="sqlite:///tech_support.db",
        description="Database connection string"
    )
    
    # Security settings
    SESSION_SECRET: str = Field(
        default="tech_support_chatbot_secret",
        description="Secret key for session middleware"
    )
    
    # AWS settings
    AWS_ACCESS_KEY_ID: Optional[str] = Field(
        default=None,
        description="AWS access key ID"
    )
    AWS_SECRET_ACCESS_KEY: Optional[str] = Field(
        default=None,
        description="AWS secret access key"
    )
    AWS_REGION: str = Field(
        default="us-east-1",
        description="AWS region"
    )
    S3_DOCUMENT_BUCKET: str = Field(
        default="adv-rag-app",
        description="S3 bucket for document storage"
    )
    
    # Pinecone settings
    PINECONE_API_KEY: Optional[str] = Field(
        default=None,
        description="Pinecone API key"
    )
    PINECONE_ENVIRONMENT: str = Field(
        default="gcp-starter",
        description="Pinecone environment"
    )
    PINECONE_INDEX_NAME: str = Field(
        default="tech-support-kb",
        description="Pinecone index name"
    )
    
    # OpenAI settings
    OPENAI_API_KEY: Optional[str] = Field(
        default=None,
        description="OpenAI API key"
    )
    OPENAI_EMBEDDING_MODEL: str = Field(
        default="text-embedding-ada-002",
        description="OpenAI embedding model"
    )
    OPENAI_COMPLETION_MODEL: str = Field(
        default="gpt-4o",
        description="OpenAI completion model"
    )
    
    # Tavily settings
    TAVILY_API_KEY: Optional[str] = Field(
        default=None,
        description="Tavily API key"
    )
    
    # Langfuse settings
    LANGFUSE_PUBLIC_KEY: Optional[str] = Field(
        default=None,
        description="Langfuse public key"
    )
    LANGFUSE_SECRET_KEY: Optional[str] = Field(
        default=None,
        description="Langfuse secret key"
    )
    LANGFUSE_HOST: str = Field(
        default="https://cloud.langfuse.com",
        description="Langfuse host"
    )
    LANGFUSE_PROJECT: str = Field(
        default="tech-support-chatbot",
        description="Langfuse project name"
    )
    
    # Feature flags
    USE_FAISS_FALLBACK: bool = Field(
        default=True,
        description="Whether to use FAISS as a fallback for vector search"
    )
    
    # CORS settings
    CORS_ORIGINS: List[str] = Field(
        default=["*"],
        description="List of allowed origins for CORS"
    )
    
    # Logging settings
    LOG_LEVEL: str = Field(
        default="INFO",
        description="Logging level"
    )
    
    @validator("DATABASE_URL", pre=True)
    def validate_database_url(cls, v: Optional[str]) -> str:
        """Validate and return the database URL."""
        if not v:
            return "sqlite:///tech_support.db"
        return v
    
    @validator("USE_FAISS_FALLBACK", pre=True)
    def validate_use_faiss_fallback(cls, v: Any) -> bool:
        """Convert string to boolean for USE_FAISS_FALLBACK."""
        if isinstance(v, str):
            return v.lower() == "true"
        return bool(v)
    
    @validator("CORS_ORIGINS", pre=True)
    def validate_cors_origins(cls, v: Any) -> List[str]:
        """Convert comma-separated string to list for CORS_ORIGINS."""
        if isinstance(v, str):
            return [origin.strip() for origin in v.split(",")]
        return v or ["*"]
    
    class Config:
        env_file = ".env"
        case_sensitive = True

# Create global settings object
settings = Settings(
    # Load all settings from environment variables
    **{k: v for k, v in os.environ.items() if k in Settings.__annotations__}
)
