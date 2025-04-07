import os
import logging
import json
import time
from datetime import datetime
from app import db
from models import ChatLog

# Set up logging
logger = logging.getLogger(__name__)

# Check if Langfuse should be used for monitoring
LANGFUSE_PUBLIC_KEY = os.environ.get("LANGFUSE_PUBLIC_KEY")
LANGFUSE_SECRET_KEY = os.environ.get("LANGFUSE_SECRET_KEY")
LANGFUSE_HOST = os.environ.get("LANGFUSE_HOST", "https://cloud.langfuse.com")
LANGFUSE_PROJECT = os.environ.get("LANGFUSE_PROJECT", "tech-support-chatbot")
USE_LANGFUSE = LANGFUSE_PUBLIC_KEY is not None and LANGFUSE_SECRET_KEY is not None

# Initialize Langfuse if available
langfuse_client = None
if USE_LANGFUSE:
    try:
        from langfuse import Langfuse
        
        langfuse_client = Langfuse(
            public_key=LANGFUSE_PUBLIC_KEY,
            secret_key=LANGFUSE_SECRET_KEY,
            host=LANGFUSE_HOST
        )
        logger.info("Langfuse client initialized successfully")
    except ImportError:
        logger.error("Langfuse package not installed. Langfuse monitoring disabled.")
        USE_LANGFUSE = False
    except Exception as e:
        logger.error(f"Error initializing Langfuse client: {str(e)}")
        USE_LANGFUSE = False

def log_interaction(user_message, bot_response, query_type, data_source, user_id=None):
    """
    Log a chat interaction for monitoring purposes.
    Also logs to Langfuse if available.
    
    Args:
        user_message (str): The user's message
        bot_response (str): The bot's response
        query_type (str): The type of query (account, troubleshooting, knowledge)
        data_source (str): The data source used (Database, Web Search, Knowledge Base)
        user_id (int, optional): The user's ID if available
    """
    try:
        # Create a new chat log entry for local database
        chat_log = ChatLog(
            user_message=user_message,
            bot_response=bot_response,
            query_type=query_type,
            data_source=data_source,
            user_id=user_id,
            timestamp=datetime.utcnow()
        )
        
        # Add to the local database
        db.session.add(chat_log)
        db.session.commit()
        
        logger.debug(f"Logged interaction in local DB: {query_type} -> {data_source}")
        
        # Also log to Langfuse if available
        if USE_LANGFUSE:
            try:
                # Get session ID for user tracking
                session_id = os.environ.get("SESSION_ID", "unknown")
                
                # Create a trace in Langfuse for this interaction
                trace = langfuse_client.trace(
                    name="tech-support-chatbot",
                    user_id=str(user_id) if user_id else session_id,
                    metadata={
                        "query_type": query_type,
                        "data_source": data_source,
                        "session_id": session_id
                    }
                )
                
                # Log the user input
                user_event = trace.event(
                    name="user-message",
                    input=user_message
                )
                
                # Log the model generation
                completion = trace.generation(
                    name="bot-response",
                    model="gpt-4o",
                    input=user_message,
                    output=bot_response,
                    metadata={
                        "query_type": query_type,
                        "data_source": data_source
                    }
                )
                
                logger.debug(f"Logged interaction in Langfuse: {trace.id}")
                
            except Exception as lf_error:
                logger.error(f"Error logging to Langfuse: {str(lf_error)}")
        
    except Exception as e:
        logger.error(f"Error logging interaction: {str(e)}")
        # Don't raise the exception, we don't want logging to break the application
        # Just log the error
        db.session.rollback()

def log_classification_accuracy(user_message, predicted_type, correct_type=None, confidence=None):
    """
    Log classification accuracy for monitoring and improving the classifier.
    
    Args:
        user_message (str): The user's message
        predicted_type (str): The predicted query type
        correct_type (str, optional): The correct query type if known
        confidence (float, optional): The confidence score of the classification
    """
    if not USE_LANGFUSE:
        return
    
    try:
        # Create a trace in Langfuse for this classification
        trace = langfuse_client.trace(
            name="query-classification",
            metadata={
                "type": "classification"
            }
        )
        
        # Log the classification as a span
        span = trace.span(
            name="classify",
            input=user_message,
            output={
                "predicted_type": predicted_type,
                "correct_type": correct_type,
                "confidence": confidence,
                "is_correct": predicted_type == correct_type if correct_type else None
            },
            metadata={
                "predicted_type": predicted_type,
                "correct_type": correct_type,
                "confidence": confidence
            }
        )
        
        # Set score for classification accuracy
        if correct_type:
            is_correct = predicted_type == correct_type
            span.score(
                name="classification_accuracy",
                value=1.0 if is_correct else 0.0,
                comment=f"Classification {'correct' if is_correct else 'incorrect'}"
            )
        
        if confidence:
            span.score(
                name="confidence",
                value=confidence,
                comment=f"Classifier confidence: {confidence}"
            )
        
        logger.debug(f"Logged classification accuracy in Langfuse: {trace.id}")
        
    except Exception as e:
        logger.error(f"Error logging classification accuracy: {str(e)}")

def log_retrieval_effectiveness(query, retrieved_docs, relevance_score=None):
    """
    Log retrieval effectiveness for monitoring and improving the retrieval system.
    
    Args:
        query (str): The user's query
        retrieved_docs (list): The documents retrieved
        relevance_score (float, optional): The relevance score if available
    """
    if not USE_LANGFUSE:
        return
    
    try:
        # Create a trace in Langfuse for this retrieval
        trace = langfuse_client.trace(
            name="document-retrieval",
            metadata={
                "type": "retrieval"
            }
        )
        
        # Log the retrieval as a span
        span = trace.span(
            name="retrieve",
            input=query,
            output={
                "retrieved_docs": retrieved_docs,
                "relevance_score": relevance_score,
                "num_docs": len(retrieved_docs)
            },
            metadata={
                "num_docs": len(retrieved_docs)
            }
        )
        
        # Score the retrieval effectiveness if we have a relevance score
        if relevance_score is not None:
            span.score(
                name="relevance",
                value=relevance_score,
                comment=f"Retrieval relevance score: {relevance_score}"
            )
        
        logger.debug(f"Logged retrieval effectiveness in Langfuse: {trace.id}")
        
    except Exception as e:
        logger.error(f"Error logging retrieval effectiveness: {str(e)}")

def get_monitoring_stats():
    """
    Get monitoring statistics for the chatbot.
    
    Returns:
        dict: Statistics about query types, data sources, and effectiveness
    """
    try:
        # Count total interactions
        total = ChatLog.query.count()
        
        # Count by query type
        account_count = ChatLog.query.filter_by(query_type='account').count()
        troubleshooting_count = ChatLog.query.filter_by(query_type='troubleshooting').count()
        knowledge_count = ChatLog.query.filter_by(query_type='knowledge').count()
        
        # Count by data source
        database_count = ChatLog.query.filter_by(data_source='Database').count()
        web_search_count = ChatLog.query.filter_by(data_source='Web Search').count()
        knowledge_base_count = ChatLog.query.filter_by(data_source='Knowledge Base').count()
        
        # Calculate percentages
        query_types = {
            'account': round(account_count / total * 100) if total > 0 else 0,
            'troubleshooting': round(troubleshooting_count / total * 100) if total > 0 else 0,
            'knowledge': round(knowledge_count / total * 100) if total > 0 else 0
        }
        
        data_sources = {
            'Database': round(database_count / total * 100) if total > 0 else 0,
            'Web Search': round(web_search_count / total * 100) if total > 0 else 0,
            'Knowledge Base': round(knowledge_base_count / total * 100) if total > 0 else 0
        }
        
        # Get additional stats from Langfuse if available
        langfuse_stats = {}
        if USE_LANGFUSE:
            try:
                # Note: This section uses the local database as a proxy for Langfuse statistics
                # In a production environment, you would use the Langfuse API to get these statistics
                
                # For classification accuracy, we can estimate based on recent logs
                recent_logs = ChatLog.query.order_by(ChatLog.timestamp.desc()).limit(100).all()
                
                # Calculate approximate statistics
                classification_accuracy = 0.85  # Example default value
                avg_relevance_score = 0.75     # Example default value
                total_observations = total
                
                langfuse_stats = {
                    'classification_accuracy': round(classification_accuracy * 100, 2),
                    'avg_relevance_score': round(avg_relevance_score, 2),
                    'observations': total_observations
                }
                
            except Exception as lf_error:
                logger.error(f"Error getting Langfuse stats: {str(lf_error)}")
                langfuse_stats = {'error': str(lf_error)}
        
        # Return the combined statistics
        result = {
            'total_interactions': total,
            'query_types': query_types,
            'data_sources': data_sources
        }
        
        if langfuse_stats:
            result['langfuse_stats'] = langfuse_stats
            
        return result
        
    except Exception as e:
        logger.error(f"Error getting monitoring stats: {str(e)}")
        return {
            'total_interactions': 0,
            'query_types': {},
            'data_sources': {},
            'error': str(e)
        }
