import os
import sys
import logging
import time
from dotenv import load_dotenv

# Set up logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# Load environment variables
load_dotenv()

# Langfuse credentials
LANGFUSE_PUBLIC_KEY = os.environ.get("LANGFUSE_PUBLIC_KEY")
LANGFUSE_SECRET_KEY = os.environ.get("LANGFUSE_SECRET_KEY")
LANGFUSE_HOST = os.environ.get("LANGFUSE_HOST", "https://cloud.langfuse.com")

def test_langfuse_credentials():
    """Test if Langfuse credentials are valid"""
    logger.info("Testing Langfuse credentials...")
    
    if not LANGFUSE_PUBLIC_KEY or not LANGFUSE_SECRET_KEY:
        logger.error("Langfuse credentials not found in environment variables")
        return False
    
    try:
        # Import Langfuse
        from langfuse import Langfuse
        
        # Initialize Langfuse client
        langfuse = Langfuse(
            public_key=LANGFUSE_PUBLIC_KEY,
            secret_key=LANGFUSE_SECRET_KEY,
            host=LANGFUSE_HOST
        )
        
        logger.info("Langfuse client initialized successfully")
        return True
    
    except ImportError:
        logger.error("Langfuse package not installed. Please install it with 'pip install langfuse'")
        return False
    except Exception as e:
        logger.error(f"Error initializing Langfuse client: {str(e)}")
        return False

class LangfuseTester:
    """Class for testing Langfuse operations"""
    
    def __init__(self):
        """Initialize Langfuse client with credentials"""
        try:
            from langfuse import Langfuse
            
            self.langfuse = Langfuse(
                public_key=LANGFUSE_PUBLIC_KEY,
                secret_key=LANGFUSE_SECRET_KEY,
                host=LANGFUSE_HOST
            )
            
            logger.info("Langfuse tester initialized successfully")
        except ImportError:
            logger.error("Langfuse package not installed")
            raise
        except Exception as e:
            logger.error(f"Error initializing Langfuse tester: {str(e)}")
            raise
    
    def create_test_trace(self):
        """Create a test trace in Langfuse"""
        try:
            # Create a trace
            trace = self.langfuse.trace(
                name="test-trace",
                user_id="test-user",
                metadata={
                    "test": True,
                    "environment": "development"
                }
            )
            
            logger.info(f"Test trace created successfully with ID: {trace.id}")
            return trace
        
        except Exception as e:
            logger.error(f"Error creating test trace: {str(e)}")
            return None
    
    def create_test_span(self, trace):
        """Create a test span in a trace"""
        try:
            # Create a span
            span = trace.span(
                name="test-span",
                input="This is a test input",
                output="This is a test output",
                metadata={
                    "test": True,
                    "type": "span"
                }
            )
            
            logger.info(f"Test span created successfully with ID: {span.id}")
            return span
        
        except Exception as e:
            logger.error(f"Error creating test span: {str(e)}")
            return None
    
    def create_test_generation(self, trace):
        """Create a test generation in a trace"""
        try:
            # Create a generation
            generation = trace.generation(
                name="test-generation",
                model="gpt-4o",
                input="What is the capital of France?",
                output="The capital of France is Paris.",
                metadata={
                    "test": True,
                    "type": "generation"
                }
            )
            
            logger.info(f"Test generation created successfully with ID: {generation.id}")
            return generation
        
        except Exception as e:
            logger.error(f"Error creating test generation: {str(e)}")
            return None
    
    def create_test_event(self, trace):
        """Create a test event in a trace"""
        try:
            # Create an event
            event = trace.event(
                name="test-event",
                input="This is a test event",
                metadata={
                    "test": True,
                    "type": "event"
                }
            )
            
            logger.info(f"Test event created successfully with ID: {event.id}")
            return event
        
        except Exception as e:
            logger.error(f"Error creating test event: {str(e)}")
            return None
    
    def add_test_score(self, trace):
        """Add a test score to a trace"""
        try:
            # Add a score
            score = trace.score(
                name="test-score",
                value=0.95,
                comment="This is a test score"
            )
            
            logger.info(f"Test score added successfully")
            return score
        
        except Exception as e:
            logger.error(f"Error adding test score: {str(e)}")
            return None
    
    def simulate_chat_interaction(self):
        """Simulate a complete chat interaction with Langfuse logging"""
        try:
            # Create a trace for the chat interaction
            trace = self.langfuse.trace(
                name="chat-interaction",
                user_id="test-user",
                metadata={
                    "session_id": "test-session",
                    "test": True
                }
            )
            
            # Log user message
            user_event = trace.event(
                name="user-message",
                input="How do I reset my password?"
            )
            
            # Log query classification
            classification = trace.span(
                name="classify-query",
                input="How do I reset my password?",
                output="account",
                metadata={
                    "confidence": 0.92,
                    "query_type": "account"
                }
            )
            
            # Add classification score
            classification.score(
                name="classification_accuracy",
                value=1.0,
                comment="Classification correct"
            )
            
            # Log document retrieval
            retrieval = trace.span(
                name="retrieve-documents",
                input="How do I reset my password?",
                output=["Document 1", "Document 2"],
                metadata={
                    "num_docs": 2,
                    "data_source": "knowledge_base"
                }
            )
            
            # Add retrieval score
            retrieval.score(
                name="relevance",
                value=0.85,
                comment="Retrieval relevance score"
            )
            
            # Log model generation
            generation = trace.generation(
                name="generate-response",
                model="gpt-4o",
                input="How do I reset my password?",
                output="To reset your password, go to the login page and click on 'Forgot Password'. Follow the instructions sent to your email.",
                metadata={
                    "query_type": "account",
                    "data_source": "knowledge_base"
                }
            )
            
            # Log bot response
            bot_event = trace.event(
                name="bot-response",
                input="To reset your password, go to the login page and click on 'Forgot Password'. Follow the instructions sent to your email."
            )
            
            # Add user satisfaction score
            trace.score(
                name="user_satisfaction",
                value=0.9,
                comment="User found the response helpful"
            )
            
            logger.info(f"Simulated chat interaction logged successfully with trace ID: {trace.id}")
            return trace
        
        except Exception as e:
            logger.error(f"Error simulating chat interaction: {str(e)}")
            return None

def run_langfuse_tests():
    """Run all Langfuse tests"""
    # First test Langfuse credentials
    if not test_langfuse_credentials():
        logger.error("Langfuse credentials test failed. Exiting.")
        return False
    
    try:
        # Initialize Langfuse tester
        tester = LangfuseTester()
        
        # Create test trace
        trace = tester.create_test_trace()
        if not trace:
            logger.error("Failed to create test trace. Exiting.")
            return False
        
        # Create test span
        span = tester.create_test_span(trace)
        if not span:
            logger.error("Failed to create test span. Exiting.")
            return False
        
        # Create test generation
        generation = tester.create_test_generation(trace)
        if not generation:
            logger.error("Failed to create test generation. Exiting.")
            return False
        
        # Create test event
        event = tester.create_test_event(trace)
        if not event:
            logger.error("Failed to create test event. Exiting.")
            return False
        
        # Add test score
        score = tester.add_test_score(trace)
        if not score:
            logger.error("Failed to add test score. Exiting.")
            return False
        
        # Simulate chat interaction
        chat_trace = tester.simulate_chat_interaction()
        if not chat_trace:
            logger.error("Failed to simulate chat interaction. Exiting.")
            return False
        
        logger.info("All Langfuse tests completed successfully!")
        return True
    
    except Exception as e:
        logger.error(f"Unexpected error in Langfuse tests: {str(e)}")
        return False

if __name__ == "__main__":
    success = run_langfuse_tests()
    sys.exit(0 if success else 1)
