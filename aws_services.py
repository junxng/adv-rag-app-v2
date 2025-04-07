import os
import boto3
import logging
import json
from botocore.exceptions import ClientError

# Set up logging
logger = logging.getLogger(__name__)

# Initialize AWS clients based on environment variables
AWS_ACCESS_KEY = os.environ.get("AWS_ACCESS_KEY_ID")
AWS_SECRET_KEY = os.environ.get("AWS_SECRET_ACCESS_KEY")
AWS_REGION = os.environ.get("AWS_REGION", "us-east-1")

class DynamoDBService:
    """Service class for DynamoDB operations"""
    
    def __init__(self):
        """Initialize DynamoDB client with appropriate credentials."""
        self.dynamodb = boto3.resource(
            'dynamodb',
            region_name=AWS_REGION,
            aws_access_key_id=AWS_ACCESS_KEY,
            aws_secret_access_key=AWS_SECRET_KEY
        )
        self.client = boto3.client(
            'dynamodb',
            region_name=AWS_REGION,
            aws_access_key_id=AWS_ACCESS_KEY,
            aws_secret_access_key=AWS_SECRET_KEY
        )
        
    def get_user_data(self, user_id):
        """
        Retrieve user data from DynamoDB.
        
        Args:
            user_id (str): The ID of the user
            
        Returns:
            dict: User data or None if not found
        """
        try:
            table = self.dynamodb.Table('Users')
            response = table.get_item(
                Key={
                    'UserId': user_id
                }
            )
            
            if 'Item' in response:
                return response['Item']
            else:
                logger.warning(f"User with ID {user_id} not found in DynamoDB")
                return None
                
        except ClientError as e:
            logger.error(f"DynamoDB error retrieving user: {str(e)}")
            return None
    
    def get_user_tickets(self, user_id):
        """
        Retrieve support tickets for a specific user from DynamoDB.
        
        Args:
            user_id (str): The ID of the user
            
        Returns:
            list: List of ticket data or empty list if none found
        """
        try:
            table = self.dynamodb.Table('SupportTickets')
            response = table.query(
                IndexName='UserIdIndex',
                KeyConditionExpression=boto3.dynamodb.conditions.Key('UserId').eq(user_id)
            )
            
            if 'Items' in response:
                return response['Items']
            else:
                logger.warning(f"No tickets found for user with ID {user_id}")
                return []
                
        except ClientError as e:
            logger.error(f"DynamoDB error retrieving tickets: {str(e)}")
            return []
    
    def create_tables_if_not_exist(self):
        """Create the necessary DynamoDB tables if they don't already exist."""
        try:
            # Check if tables already exist
            existing_tables = self.client.list_tables()['TableNames']
            
            # Create Users table if it doesn't exist
            if 'Users' not in existing_tables:
                self.client.create_table(
                    TableName='Users',
                    KeySchema=[
                        {
                            'AttributeName': 'UserId',
                            'KeyType': 'HASH'  # Partition key
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
                logger.info("Users table created successfully")
            
            # Create SupportTickets table if it doesn't exist
            if 'SupportTickets' not in existing_tables:
                self.client.create_table(
                    TableName='SupportTickets',
                    KeySchema=[
                        {
                            'AttributeName': 'TicketId',
                            'KeyType': 'HASH'  # Partition key
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
                logger.info("SupportTickets table created successfully")
                
        except ClientError as e:
            logger.error(f"Error creating DynamoDB tables: {str(e)}")
    
    def seed_sample_data(self):
        """Seed the DynamoDB tables with sample data for demonstration purposes."""
        try:
            # Seed Users table
            users_table = self.dynamodb.Table('Users')
            
            # Sample users
            sample_users = [
                {
                    'UserId': 'user1',
                    'Username': 'johndoe',
                    'Email': 'john.doe@example.com',
                    'Name': 'John Doe',
                    'CreatedAt': '2025-01-01T00:00:00Z'
                },
                {
                    'UserId': 'user2',
                    'Username': 'janedoe',
                    'Email': 'jane.doe@example.com',
                    'Name': 'Jane Doe',
                    'CreatedAt': '2025-01-02T00:00:00Z'
                }
            ]
            
            # Add users
            for user in sample_users:
                users_table.put_item(Item=user)
            
            # Seed SupportTickets table
            tickets_table = self.dynamodb.Table('SupportTickets')
            
            # Sample tickets
            sample_tickets = [
                {
                    'TicketId': 'ticket1',
                    'UserId': 'user1',
                    'Title': "Can't connect to WiFi",
                    'Description': "My laptop won't connect to the office WiFi",
                    'Status': 'open',
                    'Priority': 'medium',
                    'CreatedAt': '2025-03-01T00:00:00Z'
                },
                {
                    'TicketId': 'ticket2',
                    'UserId': 'user1',
                    'Title': 'Email not syncing',
                    'Description': 'My outlook is not syncing with the server',
                    'Status': 'closed',
                    'Priority': 'high',
                    'CreatedAt': '2025-03-15T00:00:00Z',
                    'ClosedAt': '2025-03-16T00:00:00Z'
                },
                {
                    'TicketId': 'ticket3',
                    'UserId': 'user2',
                    'Title': 'Printer not working',
                    'Description': "Can't print to the network printer",
                    'Status': 'in progress',
                    'Priority': 'low',
                    'CreatedAt': '2025-03-20T00:00:00Z'
                }
            ]
            
            # Add tickets
            for ticket in sample_tickets:
                tickets_table.put_item(Item=ticket)
                
            logger.info("Sample data seeded successfully")
            
        except ClientError as e:
            logger.error(f"Error seeding sample data: {str(e)}")

class S3Service:
    """Service class for S3 operations"""
    
    def __init__(self):
        """Initialize S3 client with appropriate credentials."""
        self.s3 = boto3.client(
            's3',
            region_name=AWS_REGION,
            aws_access_key_id=AWS_ACCESS_KEY,
            aws_secret_access_key=AWS_SECRET_KEY
        )
        self.resource = boto3.resource(
            's3',
            region_name=AWS_REGION,
            aws_access_key_id=AWS_ACCESS_KEY,
            aws_secret_access_key=AWS_SECRET_KEY
        )
        
    def create_bucket_if_not_exists(self, bucket_name):
        """
        Create an S3 bucket if it doesn't already exist.
        
        Args:
            bucket_name (str): The name of the bucket to create
            
        Returns:
            bool: True if successful, False otherwise
        """
        try:
            # Check if bucket already exists
            response = self.s3.list_buckets()
            existing_buckets = [bucket['Name'] for bucket in response['Buckets']]
            
            if bucket_name not in existing_buckets:
                # Create the bucket
                if AWS_REGION == 'us-east-1':
                    self.s3.create_bucket(
                        Bucket=bucket_name
                    )
                else:
                    self.s3.create_bucket(
                        Bucket=bucket_name,
                        CreateBucketConfiguration={
                            'LocationConstraint': AWS_REGION
                        }
                    )
                logger.info(f"Bucket {bucket_name} created successfully")
            
            return True
            
        except ClientError as e:
            logger.error(f"Error creating S3 bucket: {str(e)}")
            return False
    
    def upload_file(self, file_path, bucket_name, object_key):
        """
        Upload a file to S3.
        
        Args:
            file_path (str): The local path to the file
            bucket_name (str): The name of the bucket
            object_key (str): The key to use for the object in S3
            
        Returns:
            bool: True if successful, False otherwise
        """
        try:
            self.s3.upload_file(file_path, bucket_name, object_key)
            logger.info(f"File {file_path} uploaded to {bucket_name}/{object_key}")
            return True
            
        except ClientError as e:
            logger.error(f"Error uploading file to S3: {str(e)}")
            return False
    
    def download_file(self, bucket_name, object_key, file_path):
        """
        Download a file from S3.
        
        Args:
            bucket_name (str): The name of the bucket
            object_key (str): The key of the object in S3
            file_path (str): The local path to save the file
            
        Returns:
            bool: True if successful, False otherwise
        """
        try:
            self.s3.download_file(bucket_name, object_key, file_path)
            logger.info(f"File {bucket_name}/{object_key} downloaded to {file_path}")
            return True
            
        except ClientError as e:
            logger.error(f"Error downloading file from S3: {str(e)}")
            return False
    
    def get_file_url(self, bucket_name, object_key, expiration=3600):
        """
        Generate a presigned URL for a file in S3.
        
        Args:
            bucket_name (str): The name of the bucket
            object_key (str): The key of the object in S3
            expiration (int): URL expiration time in seconds
            
        Returns:
            str: The presigned URL or None if error
        """
        try:
            url = self.s3.generate_presigned_url(
                'get_object',
                Params={
                    'Bucket': bucket_name,
                    'Key': object_key
                },
                ExpiresIn=expiration
            )
            return url
            
        except ClientError as e:
            logger.error(f"Error generating presigned URL: {str(e)}")
            return None