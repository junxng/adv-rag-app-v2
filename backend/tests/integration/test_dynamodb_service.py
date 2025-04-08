import pytest
import os
import boto3
from moto import mock_dynamodb

from app.aws_services import DynamoDBService

@mock_dynamodb
class TestDynamoDBService:
    """
    Integration tests for DynamoDB service
    """
    
    def setup_method(self):
        """
        Set up test environment before each test
        """
        # Set environment variables for testing
        os.environ["AWS_ACCESS_KEY_ID"] = "test"
        os.environ["AWS_SECRET_ACCESS_KEY"] = "test"
        os.environ["AWS_REGION"] = "us-east-1"
        
        # Create mock DynamoDB tables
        self.dynamodb = boto3.resource('dynamodb', region_name='us-east-1')
        
        # Create Users table
        self.dynamodb.create_table(
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
        
        # Create SupportTickets table
        self.dynamodb.create_table(
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
        
        # Initialize the service
        self.service = DynamoDBService()
        
        # Add test data
        self._add_test_data()
    
    def _add_test_data(self):
        """
        Add test data to the tables
        """
        # Add test user
        users_table = self.dynamodb.Table('Users')
        users_table.put_item(
            Item={
                'UserId': 'user1',
                'Username': 'testuser',
                'Email': 'test@example.com',
                'Name': 'Test User',
                'CreatedAt': '2025-01-01T00:00:00Z'
            }
        )
        
        # Add test tickets
        tickets_table = self.dynamodb.Table('SupportTickets')
        tickets_table.put_item(
            Item={
                'TicketId': 'ticket1',
                'UserId': 'user1',
                'Title': 'Test Ticket 1',
                'Description': 'This is a test ticket',
                'Status': 'open',
                'Priority': 'medium',
                'CreatedAt': '2025-03-01T00:00:00Z'
            }
        )
        tickets_table.put_item(
            Item={
                'TicketId': 'ticket2',
                'UserId': 'user1',
                'Title': 'Test Ticket 2',
                'Description': 'This is another test ticket',
                'Status': 'closed',
                'Priority': 'high',
                'CreatedAt': '2025-03-15T00:00:00Z',
                'ClosedAt': '2025-03-16T00:00:00Z'
            }
        )
    
    def test_get_user_data(self):
        """
        Test retrieving user data
        """
        # Get user data
        user_data = self.service.get_user_data('user1')
        
        # Assert the result
        assert user_data is not None
        assert user_data['UserId'] == 'user1'
        assert user_data['Username'] == 'testuser'
        assert user_data['Email'] == 'test@example.com'
    
    def test_get_nonexistent_user(self):
        """
        Test retrieving a user that doesn't exist
        """
        # Get nonexistent user
        user_data = self.service.get_user_data('nonexistent')
        
        # Assert the result
        assert user_data is None
    
    def test_get_user_tickets(self):
        """
        Test retrieving user tickets
        """
        # Get user tickets
        tickets = self.service.get_user_tickets('user1')
        
        # Assert the result
        assert len(tickets) == 2
        assert any(ticket['TicketId'] == 'ticket1' for ticket in tickets)
        assert any(ticket['TicketId'] == 'ticket2' for ticket in tickets)
    
    def test_get_tickets_for_nonexistent_user(self):
        """
        Test retrieving tickets for a user that doesn't exist
        """
        # Get tickets for nonexistent user
        tickets = self.service.get_user_tickets('nonexistent')
        
        # Assert the result
        assert len(tickets) == 0
    
    def test_create_tables_if_not_exist(self):
        """
        Test creating tables if they don't exist
        """
        # Delete the tables first
        self.dynamodb.Table('Users').delete()
        self.dynamodb.Table('SupportTickets').delete()
        
        # Wait for tables to be deleted
        waiter = self.dynamodb.meta.client.get_waiter('table_not_exists')
        waiter.wait(TableName='Users')
        waiter.wait(TableName='SupportTickets')
        
        # Create tables
        self.service.create_tables_if_not_exist()
        
        # Check if tables exist
        existing_tables = self.dynamodb.meta.client.list_tables()['TableNames']
        
        # Assert the result
        assert 'Users' in existing_tables
        assert 'SupportTickets' in existing_tables
    
    def test_seed_sample_data(self):
        """
        Test seeding sample data
        """
        # Delete existing data
        users_table = self.dynamodb.Table('Users')
        tickets_table = self.dynamodb.Table('SupportTickets')
        
        # Scan and delete all items in Users table
        response = users_table.scan()
        for item in response.get('Items', []):
            users_table.delete_item(Key={'UserId': item['UserId']})
        
        # Scan and delete all items in SupportTickets table
        response = tickets_table.scan()
        for item in response.get('Items', []):
            tickets_table.delete_item(Key={'TicketId': item['TicketId']})
        
        # Seed sample data
        self.service.seed_sample_data()
        
        # Check if data was seeded
        users_response = users_table.scan()
        tickets_response = tickets_table.scan()
        
        # Assert the result
        assert len(users_response.get('Items', [])) > 0
        assert len(tickets_response.get('Items', [])) > 0
