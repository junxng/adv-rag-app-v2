import os
import sys
import pytest
from dotenv import load_dotenv

# Add the parent directory to the path so we can import from app
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

# Load environment variables from .env file
load_dotenv()

# Import app modules after environment variables are loaded
from app.db.base import engine, Base, get_db
from app.core.config import settings

@pytest.fixture(scope="session")
def db_engine():
    """
    Create a clean database for testing
    """
    # Use in-memory SQLite database for testing
    test_engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(bind=test_engine)
    yield test_engine
    Base.metadata.drop_all(bind=test_engine)

@pytest.fixture(scope="function")
def db_session(db_engine):
    """
    Create a new database session for a test
    """
    connection = db_engine.connect()
    transaction = connection.begin()
    session = sessionmaker(autocommit=False, autoflush=False, bind=connection)()
    
    yield session
    
    session.close()
    transaction.rollback()
    connection.close()

@pytest.fixture(scope="function")
def client(db_session):
    """
    Create a test client for FastAPI
    """
    from app.main import app
    from fastapi.testclient import TestClient
    
    # Override the get_db dependency
    def override_get_db():
        try:
            yield db_session
        finally:
            pass
    
    app.dependency_overrides[get_db] = override_get_db
    
    with TestClient(app) as test_client:
        yield test_client
    
    # Remove the override after the test
    app.dependency_overrides = {}

@pytest.fixture(scope="session")
def mock_openai():
    """
    Mock OpenAI API responses
    """
    class MockOpenAI:
        def __init__(self, *args, **kwargs):
            pass
        
        class ChatCompletion:
            @staticmethod
            def create(*args, **kwargs):
                return {
                    "choices": [
                        {
                            "message": {
                                "content": "This is a mock response from OpenAI"
                            }
                        }
                    ]
                }
        
        class Embedding:
            @staticmethod
            def create(*args, **kwargs):
                return {
                    "data": [
                        {
                            "embedding": [0.1] * 1536  # Mock embedding vector
                        }
                    ]
                }
    
    return MockOpenAI

@pytest.fixture(scope="session")
def mock_dynamodb():
    """
    Mock DynamoDB for testing
    """
    import boto3
    from moto import mock_dynamodb
    
    with mock_dynamodb():
        # Create mock DynamoDB client
        dynamodb = boto3.resource('dynamodb', region_name='us-east-1')
        
        # Create test tables
        dynamodb.create_table(
            TableName='Users',
            KeySchema=[
                {
                    'AttributeName': 'UserId',
                    'KeyType': 'HASH'
                }
            ],
            AttributeDefinitions=[
                {
                    'AttributeName': 'UserId',
                    'AttributeType': 'S'
                }
            ],
            ProvisionedThroughput={
                'ReadCapacityUnits': 5,
                'WriteCapacityUnits': 5
            }
        )
        
        dynamodb.create_table(
            TableName='SupportTickets',
            KeySchema=[
                {
                    'AttributeName': 'TicketId',
                    'KeyType': 'HASH'
                }
            ],
            AttributeDefinitions=[
                {
                    'AttributeName': 'TicketId',
                    'AttributeType': 'S'
                },
                {
                    'AttributeName': 'UserId',
                    'AttributeType': 'S'
                }
            ],
            GlobalSecondaryIndexes=[
                {
                    'IndexName': 'UserIdIndex',
                    'KeySchema': [
                        {
                            'AttributeName': 'UserId',
                            'KeyType': 'HASH'
                        }
                    ],
                    'Projection': {
                        'ProjectionType': 'ALL'
                    },
                    'ProvisionedThroughput': {
                        'ReadCapacityUnits': 5,
                        'WriteCapacityUnits': 5
                    }
                }
            ],
            ProvisionedThroughput={
                'ReadCapacityUnits': 5,
                'WriteCapacityUnits': 5
            }
        )
        
        yield dynamodb

@pytest.fixture(scope="session")
def mock_s3():
    """
    Mock S3 for testing
    """
    import boto3
    from moto import mock_s3
    
    with mock_s3():
        # Create mock S3 client
        s3 = boto3.client('s3', region_name='us-east-1')
        
        # Create test bucket
        s3.create_bucket(Bucket='adv-rag-app')
        
        yield s3
