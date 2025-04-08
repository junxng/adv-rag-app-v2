# Advanced RAG Application

This is an advanced RAG (Retrieval-Augmented Generation) application that uses FastAPI, Pinecone, and DynamoDB with comprehensive MLOps practices for monitoring, testing, and deployment.

## Project Structure

```text
adv-rag-app-v2/
├── backend/
│   ├── app/
│   │   ├── api/                      # API routes organized by domain
│   │   │   ├── __init__.py
│   │   │   ├── chat.py               # Chat endpoints
│   │   │   ├── documents.py          # Document management endpoints
│   │   │   ├── admin.py              # Admin dashboard endpoints
│   │   │   └── feedback.py           # Feedback endpoints
│   │   ├── core/                     # Core application components
│   │   │   ├── __init__.py
│   │   │   ├── config.py             # Configuration management
│   │   │   ├── security.py           # Authentication and authorization
│   │   │   └── logging.py            # Logging configuration
│   │   ├── db/                       # Database related code
│   │   │   ├── __init__.py
│   │   │   ├── base.py               # Base database setup
│   │   │   ├── models.py             # SQLAlchemy models
│   │   │   └── schemas.py            # Pydantic schemas
│   │   ├── services/                 # Business logic services
│   │   │   ├── __init__.py
│   │   │   ├── aws_service.py        # AWS integration (S3, DynamoDB)
│   │   │   ├── vector_service.py     # Vector store operations
│   │   │   ├── document_service.py   # Document processing
│   │   │   ├── chat_service.py       # Chat processing
│   │   │   └── monitoring_service.py # Monitoring and analytics
│   │   ├── ml/                       # Machine learning components
│   │   │   ├── __init__.py
│   │   │   ├── query_classifier.py   # Query classification
│   │   │   ├── embeddings.py         # Embedding generation
│   │   │   └── llm_service.py        # LLM integration
│   │   ├── static/                   # Static files
│   │   ├── templates/                # HTML templates
│   │   ├── __init__.py
│   │   └── main.py                   # FastAPI application
│   ├── tests/                        # Test directory
│   │   ├── __init__.py
│   │   ├── conftest.py               # Test configuration
│   │   ├── unit/                     # Unit tests
│   │   │   ├── __init__.py
│   │   │   ├── test_query_classifier.py
│   │   │   └── test_vector_store.py
│   │   └── integration/              # Integration tests
│   │       ├── __init__.py
│   │       ├── test_dynamodb.py
│   │       ├── test_langfuse.py
│   │       └── test_api.py
│   ├── scripts/                      # Utility scripts
│   │   ├── seed_data.py              # Seed database with sample data
│   │   └── setup_aws.py              # Set up AWS resources
│   ├── requirements/                 # Split requirements by environment
│   │   ├── base.txt                  # Base requirements
│   │   ├── dev.txt                   # Development requirements
│   │   └── prod.txt                  # Production requirements
│   ├── Dockerfile                    # Docker configuration for backend
│   ├── .env.example                  # Example environment variables
│   └── main.py                       # Entry point
├── frontend/
│   ├── src/
│   │   ├── app/                      # Next.js app directory
│   │   ├── components/               # React components
│   │   │   ├── chat/                 # Chat components
│   │   │   ├── documents/            # Document management components
│   │   │   └── admin/                # Admin dashboard components
│   │   ├── hooks/                    # Custom React hooks
│   │   ├── lib/                      # Utility functions
│   │   ├── services/                 # API service clients
│   │   └── types/                    # TypeScript type definitions
│   ├── public/                       # Static assets
│   ├── Dockerfile                    # Docker configuration for frontend
│   └── .env.example                  # Example environment variables
├── infra/                            # Infrastructure as code
│   ├── terraform/                    # Terraform configuration
│   │   ├── main.tf                   # Main Terraform configuration
│   │   ├── variables.tf              # Terraform variables
│   │   └── outputs.tf                # Terraform outputs
│   └── docker-compose.yml            # Docker Compose for local development
├── .github/                          # GitHub workflows
│   └── workflows/
│       ├── ci.yml                    # CI workflow
│       └── cd.yml                    # CD workflow
├── docs/                             # Documentation
│   ├── architecture.md               # Architecture documentation
│   ├── setup.md                      # Setup instructions
│   └── mlops.md                      # MLOps documentation
├── .gitignore                        # Git ignore file
├── README.md                         # Project README
└── LICENSE                           # License file
```

## Prerequisites

- Python 3.11+
- Node.js 18+
- uv (Python package manager)
- Pinecone account
- AWS account (for DynamoDB)
- OpenAI API key

## Environment Variables

### Backend Environment Variables

Create a `.env` file in the `backend` directory with the following variables:

```env
# Database Configuration
DATABASE_URL=sqlite:///tech_support.db

# OpenAI API Key
OPENAI_API_KEY=your_openai_api_key

# Session Secret
SESSION_SECRET=tech_support_chatbot_secret

# AWS Configuration for DynamoDB
AWS_ACCESS_KEY_ID=your_aws_access_key
AWS_SECRET_ACCESS_KEY=your_aws_secret_key
AWS_REGION=us-east-1
S3_DOCUMENT_BUCKET=adv-rag-app

# Pinecone Configuration
PINECONE_API_KEY=your_pinecone_api_key
PINECONE_ENVIRONMENT=gcp-starter
PINECONE_INDEX_NAME=tech-support-kb

# Tavily API Key (optional)
# TAVILY_API_KEY=your_tavily_api_key
```

### Frontend Environment Variables

Create a `.env.local` file in the `frontend` directory with the following variables:

```env
# API endpoint for backend
NEXT_PUBLIC_API_URL=http://localhost:5000

# Optional: Analytics or other frontend-specific variables
# NEXT_PUBLIC_ANALYTICS_ID=your-analytics-id
```

## Installation

### Backend

```bash
cd backend
uv venv
source .venv/bin/activate  # On Windows: .venv\\Scripts\\activate
uv pip install -r requirements.txt
```

### Frontend

```bash
cd frontend
npm install  # or use: uv npm install
```

## Running the Application

### Backend

```bash
cd backend
uvicorn app.main:app --reload
```

The API will be available at [http://localhost:8000](http://localhost:8000)

### Frontend

```bash
cd frontend
npm run dev  # Start Next.js development server
```

The frontend will be available at [http://localhost:3000](http://localhost:3000)

## API Documentation

FastAPI automatically generates API documentation. You can access it at:

- Swagger UI: [http://localhost:8000/docs](http://localhost:8000/docs)
- ReDoc: [http://localhost:8000/redoc](http://localhost:8000/redoc)

## Features

- Query classification (account, troubleshooting, knowledge)
- Vector search using Pinecone
- DynamoDB integration for user data
- Document management with S3
- Monitoring and feedback collection with Langfuse
- Admin dashboard for analytics
- Comprehensive testing framework
- Docker and Docker Compose support
- CI/CD with GitHub Actions
- MLOps best practices implementation

## Using Pinecone

This application uses Pinecone as the primary vector database. Make sure you have:

1. Created a Pinecone account
2. Created an index with dimension 1536 (for OpenAI embeddings)
3. Added your Pinecone API key to the `.env` file

## Fallback to FAISS

If Pinecone is not available, the application will fall back to using FAISS as a local vector store. You can control this behavior with the `USE_FAISS_FALLBACK` environment variable.

## MLOps Implementation

This project implements MLOps best practices for reliable and scalable AI applications:

1. **Monitoring and Observability**:
   - Langfuse integration for LLM observability
   - Structured logging for better debugging
   - Performance metrics tracking

2. **Testing Framework**:
   - Unit tests for individual components
   - Integration tests for service interactions
   - Mocked AWS services for testing

3. **CI/CD Pipeline**:
   - GitHub Actions for automated testing
   - Docker builds for consistent environments
   - Deployment automation

4. **Infrastructure as Code**:
   - Docker Compose for local development
   - Containerized services for portability

For more details, see the [MLOps documentation](docs/mlops.md).
