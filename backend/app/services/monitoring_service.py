import os
import json
import time
import uuid
from datetime import datetime
from typing import Dict, List, Any, Optional, Union

from ..core.config import settings
from ..core.logging import get_logger

# Set up logger
logger = get_logger(__name__)

# Initialize Langfuse if available
langfuse_client = None
if settings.LANGFUSE_PUBLIC_KEY and settings.LANGFUSE_SECRET_KEY:
    try:
        from langfuse import Langfuse

        langfuse_client = Langfuse(
            public_key=settings.LANGFUSE_PUBLIC_KEY,
            secret_key=settings.LANGFUSE_SECRET_KEY,
            host=settings.LANGFUSE_HOST
        )
        logger.info("Langfuse client initialized successfully")
    except ImportError:
        logger.error("Langfuse package not installed. Langfuse monitoring disabled.")
    except Exception as e:
        logger.error(f"Error initializing Langfuse client: {str(e)}")

class MonitoringService:
    """
    Service for monitoring and tracking application metrics and events.
    Integrates with Langfuse for LLM observability.
    """

    def __init__(self, db_session=None):
        """
        Initialize the monitoring service.

        Args:
            db_session: SQLAlchemy database session
        """
        self.db_session = db_session
        self.langfuse = langfuse_client

    def create_trace(
        self,
        name: str,
        user_id: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None
    ) -> Any:
        """
        Create a new trace in Langfuse.

        Args:
            name: Name of the trace
            user_id: User ID for the trace
            metadata: Additional metadata

        Returns:
            Langfuse trace object or None if Langfuse is not available
        """
        if not self.langfuse:
            logger.debug(f"Langfuse not available, skipping trace creation for {name}")
            return None

        try:
            # Get session ID for user tracking
            session_id = os.environ.get("SESSION_ID", str(uuid.uuid4()))

            # Create trace
            trace = self.langfuse.trace(
                name=name,
                user_id=user_id or session_id,
                metadata=metadata or {}
            )

            logger.debug(f"Created Langfuse trace: {trace.id}")
            return trace

        except Exception as e:
            logger.error(f"Error creating Langfuse trace: {str(e)}")
            return None

    def log_chat_interaction(
        self,
        user_message: str,
        bot_response: str,
        query_type: str,
        data_source: str,
        user_id: Optional[str] = None,
        session_id: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Log a chat interaction for monitoring purposes.

        Args:
            user_message: The user's message
            bot_response: The bot's response
            query_type: The type of query (account, troubleshooting, knowledge)
            data_source: The data source used (Database, Web Search, Knowledge Base)
            user_id: The user's ID if available
            session_id: The session ID
            metadata: Additional metadata

        Returns:
            Dictionary with logging results
        """
        try:
            # Create a timestamp
            timestamp = datetime.utcnow().isoformat()

            # Log to database if session is available
            db_log_id = None
            if self.db_session:
                from ..db.models import ChatLog

                chat_log = ChatLog(
                    user_message=user_message,
                    bot_response=bot_response,
                    query_type=query_type,
                    data_source=data_source,
                    user_id=user_id,
                    timestamp=datetime.utcnow()
                )

                self.db_session.add(chat_log)
                self.db_session.commit()
                db_log_id = chat_log.id

                logger.debug(f"Logged interaction in database: ID={db_log_id}")

            # Log to Langfuse if available
            trace_id = None
            if self.langfuse:
                try:
                    # Get session ID for user tracking
                    session_id = session_id or os.environ.get("SESSION_ID", "unknown")

                    # Create a trace in Langfuse for this interaction
                    trace = self.langfuse.trace(
                        name="chat-interaction",
                        user_id=str(user_id) if user_id else session_id,
                        metadata={
                            "query_type": query_type,
                            "data_source": data_source,
                            "session_id": session_id,
                            **(metadata or {})
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
                        model=settings.OPENAI_COMPLETION_MODEL,
                        input=user_message,
                        output=bot_response,
                        metadata={
                            "query_type": query_type,
                            "data_source": data_source
                        }
                    )

                    trace_id = trace.id
                    logger.debug(f"Logged interaction in Langfuse: {trace_id}")

                except Exception as lf_error:
                    logger.error(f"Error logging to Langfuse: {str(lf_error)}")

            return {
                "success": True,
                "timestamp": timestamp,
                "db_log_id": db_log_id,
                "trace_id": trace_id
            }

        except Exception as e:
            logger.error(f"Error logging interaction: {str(e)}")
            return {
                "success": False,
                "error": str(e)
            }

    def log_classification(
        self,
        user_message: str,
        predicted_type: str,
        correct_type: Optional[str] = None,
        confidence: Optional[float] = None,
        trace: Any = None,
        metadata: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Log classification accuracy for monitoring and improving the classifier.

        Args:
            user_message: The user's message
            predicted_type: The predicted query type
            correct_type: The correct query type if known
            confidence: The confidence score of the classification
            trace: Existing Langfuse trace to add to
            metadata: Additional metadata

        Returns:
            Dictionary with logging results
        """
        if not self.langfuse:
            return {"success": False, "reason": "Langfuse not available"}

        try:
            # Create a trace in Langfuse for this classification if not provided
            if not trace:
                trace = self.langfuse.trace(
                    name="query-classification",
                    metadata={
                        "type": "classification",
                        **(metadata or {})
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
                    "confidence": confidence,
                    **(metadata or {})
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

            logger.debug(f"Logged classification in Langfuse: {trace.id}")

            return {
                "success": True,
                "trace_id": trace.id,
                "span_id": span.id
            }

        except Exception as e:
            logger.error(f"Error logging classification: {str(e)}")
            return {
                "success": False,
                "error": str(e)
            }

    def log_retrieval(
        self,
        query: str,
        retrieved_docs: List[Dict[str, Any]],
        relevance_score: Optional[float] = None,
        trace: Any = None,
        metadata: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Log retrieval effectiveness for monitoring and improving the retrieval system.

        Args:
            query: The user's query
            retrieved_docs: The documents retrieved
            relevance_score: The relevance score if available
            trace: Existing Langfuse trace to add to
            metadata: Additional metadata

        Returns:
            Dictionary with logging results
        """
        if not self.langfuse:
            return {"success": False, "reason": "Langfuse not available"}

        try:
            # Create a trace in Langfuse for this retrieval if not provided
            if not trace:
                trace = self.langfuse.trace(
                    name="document-retrieval",
                    metadata={
                        "type": "retrieval",
                        **(metadata or {})
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
                    "num_docs": len(retrieved_docs),
                    **(metadata or {})
                }
            )

            # Score the retrieval effectiveness if we have a relevance score
            if relevance_score is not None:
                span.score(
                    name="relevance",
                    value=relevance_score,
                    comment=f"Retrieval relevance score: {relevance_score}"
                )

            logger.debug(f"Logged retrieval in Langfuse: {trace.id}")

            return {
                "success": True,
                "trace_id": trace.id,
                "span_id": span.id
            }

        except Exception as e:
            logger.error(f"Error logging retrieval: {str(e)}")
            return {
                "success": False,
                "error": str(e)
            }

    def log_llm_generation(
        self,
        prompt: str,
        completion: str,
        model: str,
        tokens_prompt: Optional[int] = None,
        tokens_completion: Optional[int] = None,
        latency_ms: Optional[int] = None,
        trace: Any = None,
        metadata: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Log an LLM generation for monitoring.

        Args:
            prompt: The prompt sent to the LLM
            completion: The completion returned by the LLM
            model: The model used
            tokens_prompt: Number of tokens in the prompt
            tokens_completion: Number of tokens in the completion
            latency_ms: Latency in milliseconds
            trace: Existing Langfuse trace to add to
            metadata: Additional metadata

        Returns:
            Dictionary with logging results
        """
        if not self.langfuse:
            return {"success": False, "reason": "Langfuse not available"}

        try:
            # Create a trace in Langfuse for this generation if not provided
            if not trace:
                trace = self.langfuse.trace(
                    name="llm-generation",
                    metadata={
                        "type": "generation",
                        "model": model,
                        **(metadata or {})
                    }
                )

            # Log the generation
            generation = trace.generation(
                name="generate",
                model=model,
                input=prompt,
                output=completion,
                metadata={
                    "tokens_prompt": tokens_prompt,
                    "tokens_completion": tokens_completion,
                    "latency_ms": latency_ms,
                    **(metadata or {})
                }
            )

            logger.debug(f"Logged LLM generation in Langfuse: {trace.id}")

            return {
                "success": True,
                "trace_id": trace.id,
                "generation_id": generation.id
            }

        except Exception as e:
            logger.error(f"Error logging LLM generation: {str(e)}")
            return {
                "success": False,
                "error": str(e)
            }

    def log_feedback(
        self,
        trace_id: str,
        score: float,
        comment: Optional[str] = None,
        name: str = "user_feedback"
    ) -> Dict[str, Any]:
        """
        Log user feedback for a trace.

        Args:
            trace_id: The ID of the trace to add feedback to
            score: The feedback score (0-1)
            comment: Optional comment
            name: Name of the feedback

        Returns:
            Dictionary with logging results
        """
        if not self.langfuse:
            return {"success": False, "reason": "Langfuse not available"}

        try:
            # Add feedback to the trace
            self.langfuse.score(
                trace_id=trace_id,
                name=name,
                value=score,
                comment=comment
            )

            logger.debug(f"Logged feedback for trace {trace_id}")

            return {
                "success": True,
                "trace_id": trace_id
            }

        except Exception as e:
            logger.error(f"Error logging feedback: {str(e)}")
            return {
                "success": False,
                "error": str(e)
            }

    def get_monitoring_stats(self) -> Dict[str, Any]:
        """
        Get monitoring statistics for the chatbot.

        Returns:
            Dictionary with statistics
        """
        try:
            # Get stats from database if available
            db_stats = {}
            if self.db_session:
                from ..db.models import ChatLog

                # Count total interactions
                total = self.db_session.query(ChatLog).count()

                # Count by query type
                account_count = self.db_session.query(ChatLog).filter_by(query_type='account').count()
                troubleshooting_count = self.db_session.query(ChatLog).filter_by(query_type='troubleshooting').count()
                knowledge_count = self.db_session.query(ChatLog).filter_by(query_type='knowledge').count()

                # Count by data source
                database_count = self.db_session.query(ChatLog).filter_by(data_source='Database').count()
                web_search_count = self.db_session.query(ChatLog).filter_by(data_source='Web Search').count()
                knowledge_base_count = self.db_session.query(ChatLog).filter_by(data_source='Knowledge Base').count()

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

                db_stats = {
                    'total_interactions': total,
                    'query_types': query_types,
                    'data_sources': data_sources
                }

            # Get stats from Langfuse if available
            langfuse_stats = {}
            if self.langfuse:
                # Note: In a real implementation, you would use the Langfuse API to get statistics
                # For now, we'll use placeholder values
                langfuse_stats = {
                    'classification_accuracy': 85.5,  # Example value
                    'avg_relevance_score': 0.78,      # Example value
                    'avg_latency_ms': 1250,           # Example value
                    'total_tokens': 125000            # Example value
                }

            # Combine stats
            result = {
                **db_stats,
                'langfuse_stats': langfuse_stats if langfuse_stats else None
            }

            return result

        except Exception as e:
            logger.error(f"Error getting monitoring stats: {str(e)}")
            return {
                'error': str(e)
            }

# Create a singleton instance
monitoring_service = MonitoringService()
