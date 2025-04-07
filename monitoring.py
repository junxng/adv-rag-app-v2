import logging
from datetime import datetime
from app import db
from models import ChatLog

# Set up logging
logger = logging.getLogger(__name__)

def log_interaction(user_message, bot_response, query_type, data_source, user_id=None):
    """
    Log a chat interaction for monitoring purposes.
    
    Args:
        user_message (str): The user's message
        bot_response (str): The bot's response
        query_type (str): The type of query (account, troubleshooting, knowledge)
        data_source (str): The data source used (Database, Web Search, Knowledge Base)
        user_id (int, optional): The user's ID if available
    """
    try:
        # Create a new chat log entry
        chat_log = ChatLog(
            user_message=user_message,
            bot_response=bot_response,
            query_type=query_type,
            data_source=data_source,
            user_id=user_id,
            timestamp=datetime.utcnow()
        )
        
        # Add to database
        db.session.add(chat_log)
        db.session.commit()
        
        logger.debug(f"Logged interaction: {query_type} -> {data_source}")
        
    except Exception as e:
        logger.error(f"Error logging interaction: {str(e)}")
        # Don't let monitoring errors affect the user experience
        db.session.rollback()

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
        
        return {
            'total_interactions': total,
            'query_types': query_types,
            'data_sources': data_sources
        }
        
    except Exception as e:
        logger.error(f"Error getting monitoring stats: {str(e)}")
        return {
            'total_interactions': 0,
            'query_types': {},
            'data_sources': {}
        }
