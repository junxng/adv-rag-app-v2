import os
import logging
import json
import time
from datetime import datetime
from app import db
from models import ChatLog

# Set up logging
logger = logging.getLogger(__name__)

# Check if LangSmith should be used for monitoring
LANGSMITH_API_KEY = os.environ.get("LANGSMITH_API_KEY")
LANGSMITH_PROJECT = os.environ.get("LANGSMITH_PROJECT", "tech-support-chatbot")
USE_LANGSMITH = LANGSMITH_API_KEY is not None

# Initialize LangSmith if available
if USE_LANGSMITH:
    try:
        from langsmith import Client
        langsmith_client = Client(api_key=LANGSMITH_API_KEY)
        logger.info("LangSmith client initialized successfully")
    except Exception as e:
        logger.error(f"Error initializing LangSmith client: {str(e)}")
        USE_LANGSMITH = False

def log_interaction(user_message, bot_response, query_type, data_source, user_id=None):
    """
    Log a chat interaction for monitoring purposes.
    Also logs to LangSmith if available.
    
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
        
        # Also log to LangSmith if available
        if USE_LANGSMITH:
            try:
                # Create a run in LangSmith
                session_id = os.environ.get("SESSION_ID", "unknown")
                
                run_id = langsmith_client.create_run(
                    name="tech-support-chatbot",
                    run_type="llm",
                    inputs={
                        "user_message": user_message,
                        "query_type": query_type,
                        "data_source": data_source,
                        "user_id": str(user_id) if user_id else None
                    },
                    outputs={
                        "bot_response": bot_response
                    },
                    start_time=datetime.utcnow(),
                    end_time=datetime.utcnow(),
                    project_name=LANGSMITH_PROJECT,
                    extra={
                        "session_id": session_id
                    }
                )
                
                logger.debug(f"Logged interaction in LangSmith: {run_id}")
                
            except Exception as ls_error:
                logger.error(f"Error logging to LangSmith: {str(ls_error)}")
        
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
    if not USE_LANGSMITH:
        return
    
    try:
        # Log classification accuracy to LangSmith
        run_id = langsmith_client.create_run(
            name="query-classification",
            run_type="chain",
            inputs={
                "user_message": user_message
            },
            outputs={
                "predicted_type": predicted_type,
                "correct_type": correct_type,
                "confidence": confidence,
                "is_correct": predicted_type == correct_type if correct_type else None
            },
            start_time=datetime.utcnow(),
            end_time=datetime.utcnow(),
            project_name=LANGSMITH_PROJECT,
            extra={
                "type": "classification"
            }
        )
        
        logger.debug(f"Logged classification accuracy in LangSmith: {run_id}")
        
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
    if not USE_LANGSMITH:
        return
    
    try:
        # Log retrieval effectiveness to LangSmith
        run_id = langsmith_client.create_run(
            name="document-retrieval",
            run_type="retriever",
            inputs={
                "query": query
            },
            outputs={
                "retrieved_docs": retrieved_docs,
                "relevance_score": relevance_score,
                "num_docs": len(retrieved_docs)
            },
            start_time=datetime.utcnow(),
            end_time=datetime.utcnow(),
            project_name=LANGSMITH_PROJECT,
            extra={
                "type": "retrieval"
            }
        )
        
        logger.debug(f"Logged retrieval effectiveness in LangSmith: {run_id}")
        
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
        
        # Get additional stats from LangSmith if available
        langsmith_stats = {}
        if USE_LANGSMITH:
            try:
                # Get classification accuracy from LangSmith
                classification_runs = langsmith_client.list_runs(
                    project_name=LANGSMITH_PROJECT,
                    filter={"extra.type": "classification"},
                    limit=1000
                )
                
                total_classifications = len(classification_runs)
                correct_classifications = sum(
                    1 for run in classification_runs 
                    if run.outputs and run.outputs.get("is_correct")
                )
                
                if total_classifications > 0:
                    classification_accuracy = correct_classifications / total_classifications * 100
                else:
                    classification_accuracy = 0
                
                # Get retrieval effectiveness from LangSmith
                retrieval_runs = langsmith_client.list_runs(
                    project_name=LANGSMITH_PROJECT,
                    filter={"extra.type": "retrieval"},
                    limit=1000
                )
                
                avg_relevance_score = 0
                if retrieval_runs:
                    total_relevance = 0
                    count = 0
                    for run in retrieval_runs:
                        if run.outputs and "relevance_score" in run.outputs:
                            total_relevance += run.outputs["relevance_score"]
                            count += 1
                    if count > 0:
                        avg_relevance_score = total_relevance / count
                
                langsmith_stats = {
                    'classification_accuracy': round(classification_accuracy, 2),
                    'avg_relevance_score': round(avg_relevance_score, 2),
                    'langsmith_runs': total_classifications + len(retrieval_runs)
                }
                
            except Exception as ls_error:
                logger.error(f"Error getting LangSmith stats: {str(ls_error)}")
                langsmith_stats = {'error': str(ls_error)}
        
        # Return the combined statistics
        result = {
            'total_interactions': total,
            'query_types': query_types,
            'data_sources': data_sources
        }
        
        if langsmith_stats:
            result['langsmith_stats'] = langsmith_stats
            
        return result
        
    except Exception as e:
        logger.error(f"Error getting monitoring stats: {str(e)}")
        return {
            'total_interactions': 0,
            'query_types': {},
            'data_sources': {},
            'error': str(e)
        }
