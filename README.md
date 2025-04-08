# Advanced RAG Application

This is an advanced RAG (Retrieval-Augmented Generation) application that uses FastAPI, Pinecone, and DynamoDB.

## Project Structure

```text
.
├── backend/
│   ├── app/
│   │   ├── __init__.py
│   │   ├── main.py
│   │   ├── models.py
│   │   ├── schemas.py
│   │   ├── database.py
│   │   ├── services.py
│   │   ├── vector_store.py
│   │   ├── pinecone_service.py
│   │   ├── aws_services.py
│   │   ├── document_service.py
│   │   ├── query_classifier.py
│   │   ├── data_sources.py
│   │   ├── monitoring.py
│   │   ├── templates/
│   │   └── static/
│   ├── main.py
│   ├── requirements.txt
│   └── .env
├── frontend/
│   ├── src/
│   │   ├── app/
│   │   │   ├── layout.tsx
│   │   │   ├── page.tsx
│   │   │   └── globals.css
│   │   └── components/
│   │       ├── ChatMessage.tsx
│   │       └── ChatInput.tsx
│   ├── package.json
│   ├── tsconfig.json
│   ├── next.config.js
│   ├── postcss.config.js
│   ├── tailwind.config.js
│   └── .env.local
├── .gitignore
└── README.md
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
- Monitoring and feedback collection
- Admin dashboard for analytics

## Using Pinecone

This application uses Pinecone as the primary vector database. Make sure you have:

1. Created a Pinecone account
2. Created an index with dimension 1536 (for OpenAI embeddings)
3. Added your Pinecone API key to the `.env` file

## Fallback to FAISS

If Pinecone is not available, the application will fall back to using FAISS as a local vector store. You can control this behavior with the `USE_FAISS_FALLBACK` environment variable.
