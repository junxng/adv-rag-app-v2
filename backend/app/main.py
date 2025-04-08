import os
import logging
from fastapi import FastAPI, Request, Response, Depends, HTTPException, File, UploadFile, Form
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.orm import Session
from typing import List, Dict, Any, Optional
from pydantic import BaseModel
from starlette.middleware.sessions import SessionMiddleware
from dotenv import load_dotenv

# Load environment variables from .env file in the backend directory
load_dotenv(dotenv_path="../backend/.env")

from .db.base import engine, Base, get_db
from .db import models
from . import schemas
from .services import monitoring_service

# Set up logging
logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)

# Create FastAPI app
app = FastAPI(title="Tech Support Chatbot API",
              description="API for the tech support chatbot with RAG capabilities",
              version="1.0.0")

# Add session middleware
app.add_middleware(
    SessionMiddleware,
    secret_key=os.environ.get("SESSION_SECRET", "tech_support_chatbot_secret")
)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Templates setup
templates = Jinja2Templates(directory="app/templates")

# Create database tables
Base.metadata.create_all(bind=engine)

# Initialize services
@app.on_event("startup")
async def startup_event():
    # Initialize the S3 bucket for document storage
    from .document_service import init_s3_bucket
    init_s3_bucket()

    # Try to initialize DynamoDB tables if AWS credentials are available
    try:
        aws_access_key = os.environ.get("AWS_ACCESS_KEY_ID")
        aws_secret_key = os.environ.get("AWS_SECRET_ACCESS_KEY")

        if aws_access_key and aws_secret_key:
            logger.info("AWS credentials found, initializing DynamoDB tables")
            from .aws_services import DynamoDBService
            dynamodb_service = DynamoDBService()
            dynamodb_service.create_tables_if_not_exist()

            # Check if there's data in the DynamoDB tables
            try:
                # Check if Users table has data
                result = dynamodb_service.client.scan(
                    TableName='Users',
                    Limit=1
                )

                if 'Items' not in result or len(result['Items']) == 0:
                    logger.info("No users found in DynamoDB, seeding sample data")
                    dynamodb_service.seed_sample_data()
                else:
                    logger.info("DynamoDB already contains user data, skipping seed")
            except Exception as e:
                logger.warning(f"Error checking DynamoDB data: {str(e)}")
        else:
            logger.info("AWS credentials not found, DynamoDB initialization skipped")
    except Exception as e:
        logger.warning(f"Error initializing DynamoDB: {str(e)}")

    # Initialize the database with some sample data if needed
    db = next(get_db())
    try:
        # Check if data already exists
        if db.query(models.User).count() == 0:
            # Create sample users
            user1 = models.User(
                username="johndoe",
                email="john.doe@example.com",
                name="John Doe"
            )
            db.add(user1)

            user2 = models.User(
                username="janedoe",
                email="jane.doe@example.com",
                name="Jane Doe"
            )
            db.add(user2)
            db.commit()

            # Create sample support tickets
            ticket1 = models.SupportTicket(
                user_id=1,
                title="Can't connect to WiFi",
                description="My laptop won't connect to the office WiFi",
                status="open",
                priority="medium"
            )
            db.add(ticket1)

            ticket2 = models.SupportTicket(
                user_id=1,
                title="Email not syncing",
                description="My outlook is not syncing with the server",
                status="closed",
                priority="high"
            )
            db.add(ticket2)

            # Create sample knowledge articles
            article1 = models.KnowledgeArticle(
                title="WiFi Troubleshooting Guide",
                content="1. Restart your router\n2. Check if WiFi is enabled on your device\n3. Forget the network and reconnect\n4. Update your network drivers\n5. Contact IT if the issue persists",
                category="troubleshooting"
            )
            db.add(article1)

            article2 = models.KnowledgeArticle(
                title="Remote Work Policy",
                content="Employees are allowed to work remotely up to 3 days per week. All remote work must be approved by your manager. Ensure you have a stable internet connection and proper home office setup.",
                category="policy"
            )
            db.add(article2)

            article3 = models.KnowledgeArticle(
                title="Password Reset Procedure",
                content="To reset your password, visit the company portal at portal.company.com and click on 'Forgot Password'. Follow the instructions sent to your recovery email.",
                category="account"
            )
            db.add(article3)
            db.commit()

            logger.info("Sample data initialized")
    except Exception as e:
        logger.error(f"Error initializing sample data: {str(e)}")
    finally:
        db.close()

    # Import components after database is initialized
    from .vector_store import initialize_vector_store

    # Initialize vector store
    initialize_vector_store()

# Routes
@app.get("/", response_class=HTMLResponse)
async def index(request: Request):
    return templates.TemplateResponse("index.html", {"request": request})

@app.post("/api/chat", response_model=schemas.ChatResponse)
async def chat(chat_request: schemas.ChatRequest, request: Request):
    try:
        user_message = chat_request.message

        # Get session ID
        session = request.session
        session_id = session.get("session_id")
        if not session_id:
            # Generate a new session ID if one doesn't exist
            session_id = os.urandom(16).hex()
            session["session_id"] = session_id

            # Store session ID in environment for LangSmith tracking
            os.environ["SESSION_ID"] = session_id

            # Initialize chat history
            session["chat_history"] = []

        # Get chat history
        chat_history = session.get("chat_history", [])

        # Add user message to history
        chat_history.append({"role": "user", "content": user_message})

        # Import components
        from .query_classifier import classify_query
        from .data_sources import query_sql_database, search_tavily, retrieve_from_vectordb
        # Use the monitoring service for logging interactions

        # Classify query
        query_type = classify_query(user_message, chat_history)
        logger.debug(f"Query classified as: {query_type}")

        # Route to appropriate data source
        if query_type == "account":
            # Mock user ID for demo (in real app, this would come from authentication)
            user_id = 1
            response = query_sql_database(user_message, user_id, chat_history)
            source = "Database"
        elif query_type == "troubleshooting":
            response = search_tavily(user_message, chat_history)
            source = "Web Search"
        else:  # knowledge base
            response = retrieve_from_vectordb(user_message, chat_history)
            source = "Knowledge Base"

        # Add bot response to history
        chat_history.append({"role": "assistant", "content": response})

        # Update session
        session["chat_history"] = chat_history

        # Log interaction for monitoring
        monitoring_service.log_chat_interaction(
            user_message=user_message,
            bot_response=response,
            query_type=query_type,
            data_source=source,
            session_id=session.get("session_id")
        )

        return schemas.ChatResponse(message=response, source=source)

    except Exception as e:
        logger.error(f"Error processing query: {str(e)}")
        raise HTTPException(status_code=500, detail="Error processing your request")

@app.post("/api/reset")
async def reset_chat(request: Request):
    # Get session ID
    session = request.session
    session_id = session.get("session_id")

    # Clear session chat history
    session["chat_history"] = []

    # Clear LangChain memory if available
    if session_id:
        try:
            from .memory_manager import memory_manager
            memory_manager.clear_memory(session_id)
            logger.debug(f"Cleared LangChain memory for session {session_id}")
        except Exception as e:
            logger.warning(f"Failed to clear LangChain memory: {str(e)}")

    return {"status": "success"}

@app.get("/api/stats")
async def get_stats():
    """
    Get monitoring statistics for the chatbot.
    This endpoint requires admin authentication in a production environment.
    """
    try:
        stats = monitoring_service.get_monitoring_stats()
        return stats
    except Exception as e:
        logger.error(f"Error getting stats: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/admin/dashboard", response_class=HTMLResponse)
async def admin_dashboard(request: Request):
    """
    Admin dashboard for monitoring chatbot performance.
    This route should be protected by authentication in a production environment.
    """
    # In a real application, add authentication check here
    return templates.TemplateResponse("admin_dashboard.html", {"request": request})

@app.post("/api/feedback")
async def submit_feedback(feedback: schemas.FeedbackRequest, request: Request):
    """
    Submit user feedback on chatbot responses.
    This feedback is used to improve classification accuracy and retrieval effectiveness.
    """
    try:
        # Get session
        session = request.session
        user_message = feedback.user_message
        bot_response = feedback.bot_response
        feedback_rating = feedback.rating
        correct_type = feedback.correct_type
        comments = feedback.comments

        if not all([user_message, bot_response, feedback_rating]):
            raise HTTPException(status_code=400, detail="Missing required fields")

        # Log feedback in database
        db = next(get_db())
        try:
            # Create feedback entry
            # Use monitoring service for feedback
            monitoring_service.log_feedback(
                trace_id=session.get('trace_id', 'unknown'),
                score=float(feedback_rating) / 5.0,  # Convert to 0-1 scale
                comment=comments,
                name="user_feedback"
            )

            # If user indicated the correct classification type, use it to improve the classifier
            if correct_type:
                monitoring_service.log_classification(
                    user_message=user_message,
                    predicted_type="unknown",  # We don't know the predicted type here
                    correct_type=correct_type
                )

            return {"status": "success"}
        finally:
            db.close()

    except Exception as e:
        logger.error(f"Error submitting feedback: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

# Document management routes
@app.get("/documents", response_class=HTMLResponse)
async def document_list(request: Request):
    """
    Display a list of documents for the current user.
    In a real application, this would require authentication.
    """
    # Mock user ID for demo (in real app, this would come from authentication)
    user_id = 1

    # Check if S3 is available
    from .document_service import s3_available, get_user_documents
    documents = get_user_documents(user_id)

    return templates.TemplateResponse("documents.html", {
        "request": request,
        "documents": documents,
        "s3_available": s3_available
    })

@app.get("/api/documents")
async def api_document_list():
    """
    API endpoint to get a list of documents for the current user.
    """
    # Mock user ID for demo (in real app, this would come from authentication)
    user_id = 1

    from .document_service import get_user_documents, s3_available
    documents = get_user_documents(user_id)

    # Convert documents to JSON-serializable format
    result = []
    for doc in documents:
        result.append({
            'id': doc.id,
            'filename': doc.original_filename,
            'size': doc.file_size,
            'mime_type': doc.mime_type,
            'created_at': doc.created_at.isoformat(),
            'url': doc.get_download_url(),
            's3_available': s3_available
        })

    return {
        'documents': result,
        's3_available': s3_available
    }

@app.post("/api/documents/upload")
async def api_upload_document(file: UploadFile = File(...)):
    """
    API endpoint to upload a document.
    """
    # Check if S3 is available
    from .document_service import s3_available, upload_document
    if not s3_available:
        raise HTTPException(
            status_code=503,
            detail="Document storage is currently unavailable. Please check AWS credentials and permissions."
        )

    # Mock user ID for demo (in real app, this would come from authentication)
    user_id = 1

    # If user does not select a file, browser also
    # submits an empty part without filename
    if file.filename == '':
        raise HTTPException(status_code=400, detail="No selected file")

    try:
        # Read file content
        content = await file.read()

        # Upload document
        document = upload_document(content, file.filename, user_id)

        if document:
            return {
                'id': document.id,
                'filename': document.original_filename,
                'size': document.file_size,
                'mime_type': document.mime_type,
                'created_at': document.created_at.isoformat(),
                'url': document.get_download_url()
            }
        else:
            raise HTTPException(status_code=500, detail="Failed to upload document")

    except Exception as e:
        logger.error(f"Error uploading document: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

# Serve static files
app.mount("/static", StaticFiles(directory="app/static"), name="static")
