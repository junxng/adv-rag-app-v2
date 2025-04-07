import os
import logging
import json
from flask import Flask, request, render_template, jsonify, session
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy.orm import DeclarativeBase
from werkzeug.middleware.proxy_fix import ProxyFix

# Set up logging
logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)

# Database setup
class Base(DeclarativeBase):
    pass

db = SQLAlchemy(model_class=Base)
app = Flask(__name__)
app.secret_key = os.environ.get("SESSION_SECRET", "tech_support_chatbot_secret")
app.wsgi_app = ProxyFix(app.wsgi_app, x_proto=1, x_host=1)

# Configure database
app.config["SQLALCHEMY_DATABASE_URI"] = os.environ.get("DATABASE_URL")
app.config["SQLALCHEMY_ENGINE_OPTIONS"] = {
    "pool_recycle": 300,
    "pool_pre_ping": True,
}
db.init_app(app)

with app.app_context():
    # Import models here for table creation
    import models
    
    # Create tables
    db.create_all()
    
    # Initialize the database with some sample data if needed
    from models import User, SupportTicket, KnowledgeArticle
    
    # Check if data already exists
    if User.query.count() == 0:
        # Create sample users
        user1 = User(
            username="johndoe",
            email="john.doe@example.com",
            name="John Doe"
        )
        db.session.add(user1)
        
        user2 = User(
            username="janedoe",
            email="jane.doe@example.com",
            name="Jane Doe"
        )
        db.session.add(user2)
        db.session.commit()
        
        # Create sample support tickets
        ticket1 = SupportTicket(
            user_id=1,
            title="Can't connect to WiFi",
            description="My laptop won't connect to the office WiFi",
            status="open",
            priority="medium"
        )
        db.session.add(ticket1)
        
        ticket2 = SupportTicket(
            user_id=1,
            title="Email not syncing",
            description="My outlook is not syncing with the server",
            status="closed",
            priority="high"
        )
        db.session.add(ticket2)
        
        ticket3 = SupportTicket(
            user_id=2,
            title="Printer not working",
            description="Can't print to the network printer",
            status="in progress",
            priority="low"
        )
        db.session.add(ticket3)
        db.session.commit()
        
        # Create sample knowledge articles
        article1 = KnowledgeArticle(
            title="VPN Setup Guide",
            content="To set up VPN, download the company VPN client and log in using your SSO credentials. If you have issues connecting, ensure your internet connection is stable and try restarting the client.",
            category="remote_work"
        )
        db.session.add(article1)
        
        article2 = KnowledgeArticle(
            title="Remote Work Policy",
            content="Employees are allowed to work remotely up to 3 days per week. All remote work must be approved by your manager. Ensure you have a stable internet connection and proper home office setup.",
            category="policy"
        )
        db.session.add(article2)
        
        article3 = KnowledgeArticle(
            title="Password Reset Procedure",
            content="To reset your password, visit the company portal at portal.company.com and click on 'Forgot Password'. Follow the instructions sent to your recovery email.",
            category="account"
        )
        db.session.add(article3)
        db.session.commit()
        
        logger.info("Sample data initialized")

# Import components after database is initialized
from query_classifier import classify_query
from data_sources import query_sql_database, search_tavily, retrieve_from_vectordb
from monitoring import log_interaction
from vector_store import initialize_vector_store

# Initialize vector store
with app.app_context():
    initialize_vector_store()

# Routes
@app.route('/')
def index():
    return render_template('index.html')

@app.route('/api/chat', methods=['POST'])
def chat():
    data = request.json
    user_message = data.get('message', '')
    
    # Get or initialize chat history
    chat_history = session.get('chat_history', [])
    
    # Add user message to history
    chat_history.append({"role": "user", "content": user_message})
    
    try:
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
        
        # Log the interaction for monitoring
        log_interaction(user_message, response, query_type, source)
        
        # Add bot response to history
        chat_history.append({"role": "assistant", "content": response})
        
        # Limit history size to prevent session from growing too large
        if len(chat_history) > 20:
            chat_history = chat_history[-20:]
        
        # Save updated history to session
        session['chat_history'] = chat_history
        
        return jsonify({
            "message": response,
            "source": source
        })
    
    except Exception as e:
        logger.error(f"Error processing query: {str(e)}")
        return jsonify({
            "message": "I'm sorry, I encountered an error while processing your request. Please try again.",
            "source": "Error"
        }), 500

@app.route('/api/reset', methods=['POST'])
def reset_chat():
    session['chat_history'] = []
    return jsonify({"status": "success"})
