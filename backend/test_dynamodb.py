import os
import sys
import logging
import boto3
from dotenv import load_dotenv
from botocore.exceptions import ClientError

# Set up logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# Load environment variables
load_dotenv()

# AWS credentials
AWS_ACCESS_KEY = os.environ.get("AWS_ACCESS_KEY_ID")
AWS_SECRET_KEY = os.environ.get("AWS_SECRET_ACCESS_KEY")
AWS_REGION = os.environ.get("AWS_REGION", "us-east-1")

def test_aws_credentials():
    """Test if AWS credentials are valid"""
    logger.info("Testing AWS credentials...")
    
    if not AWS_ACCESS_KEY or not AWS_SECRET_KEY:
        logger.error("AWS credentials not found in environment variables")
        return False
    
    try:
        # Create a simple STS client to validate credentials
        sts = boto3.client(
            'sts',
            region_name=AWS_REGION,
            aws_access_key_id=AWS_ACCESS_KEY,
            aws_secret_access_key=AWS_SECRET_KEY
        )
        
        # Get caller identity
        response = sts.get_caller_identity()
        logger.info(f"AWS credentials are valid. Account ID: {response['Account']}")
        return True
    
    except ClientError as e:
        logger.error(f"AWS credentials are invalid: {str(e)}")
        return False
    except Exception as e:
        logger.error(f"Unexpected error testing AWS credentials: {str(e)}")
        return False

class DynamoDBTester:
    """Class for testing DynamoDB operations"""
    
    def __init__(self):
        """Initialize DynamoDB client with credentials"""
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
    
    def list_tables(self):
        """List all DynamoDB tables"""
        try:
            response = self.client.list_tables()
            tables = response.get('TableNames', [])
            logger.info(f"Found {len(tables)} DynamoDB tables: {', '.join(tables)}")
            return tables
        except ClientError as e:
            logger.error(f"Error listing DynamoDB tables: {str(e)}")
            return []
    
    def create_test_table(self, table_name="TestTable"):
        """Create a test table"""
        try:
            # Check if table already exists
            existing_tables = self.client.list_tables()['TableNames']
            if table_name in existing_tables:
                logger.info(f"Table {table_name} already exists")
                return True
            
            # Create the table
            table = self.client.create_table(
                TableName=table_name,
                KeySchema=[
                    {
                        'AttributeName': 'id',
                        'KeyType': 'HASH'  # Partition key
                    }
                ],
                AttributeDefinitions=[
                    {
                        'AttributeName': 'id',
                        'AttributeType': 'S'
                    }
                ],
                ProvisionedThroughput={
                    'ReadCapacityUnits': 5,
                    'WriteCapacityUnits': 5
                }
            )
            
            logger.info(f"Table {table_name} created successfully")
            return True
        
        except ClientError as e:
            logger.error(f"Error creating test table: {str(e)}")
            return False
    
    def insert_test_item(self, table_name="TestTable", item_id="test1"):
        """Insert a test item into the table"""
        try:
            table = self.dynamodb.Table(table_name)
            
            # Insert item
            response = table.put_item(
                Item={
                    'id': item_id,
                    'test_value': 'This is a test item',
                    'number_value': 42
                }
            )
            
            logger.info(f"Test item inserted successfully into {table_name}")
            return True
        
        except ClientError as e:
            logger.error(f"Error inserting test item: {str(e)}")
            return False
    
    def get_test_item(self, table_name="TestTable", item_id="test1"):
        """Retrieve a test item from the table"""
        try:
            table = self.dynamodb.Table(table_name)
            
            # Get item
            response = table.get_item(
                Key={
                    'id': item_id
                }
            )
            
            if 'Item' in response:
                item = response['Item']
                logger.info(f"Retrieved test item: {item}")
                return item
            else:
                logger.warning(f"Item with ID {item_id} not found")
                return None
        
        except ClientError as e:
            logger.error(f"Error retrieving test item: {str(e)}")
            return None
    
    def delete_test_item(self, table_name="TestTable", item_id="test1"):
        """Delete a test item from the table"""
        try:
            table = self.dynamodb.Table(table_name)
            
            # Delete item
            response = table.delete_item(
                Key={
                    'id': item_id
                }
            )
            
            logger.info(f"Test item deleted successfully from {table_name}")
            return True
        
        except ClientError as e:
            logger.error(f"Error deleting test item: {str(e)}")
            return False
    
    def delete_test_table(self, table_name="TestTable"):
        """Delete the test table"""
        try:
            # Check if table exists
            existing_tables = self.client.list_tables()['TableNames']
            if table_name not in existing_tables:
                logger.info(f"Table {table_name} does not exist")
                return True
            
            # Delete the table
            self.client.delete_table(TableName=table_name)
            logger.info(f"Table {table_name} deleted successfully")
            return True
        
        except ClientError as e:
            logger.error(f"Error deleting test table: {str(e)}")
            return False

def run_dynamodb_tests():
    """Run all DynamoDB tests"""
    # First test AWS credentials
    if not test_aws_credentials():
        logger.error("AWS credentials test failed. Exiting.")
        return False
    
    # Initialize DynamoDB tester
    tester = DynamoDBTester()
    
    # List existing tables
    tables = tester.list_tables()
    
    # Create test table
    if not tester.create_test_table():
        logger.error("Failed to create test table. Exiting.")
        return False
    
    # Insert test item
    if not tester.insert_test_item():
        logger.error("Failed to insert test item. Exiting.")
        return False
    
    # Get test item
    item = tester.get_test_item()
    if not item:
        logger.error("Failed to retrieve test item. Exiting.")
        return False
    
    # Delete test item
    if not tester.delete_test_item():
        logger.error("Failed to delete test item. Exiting.")
        return False
    
    # Delete test table
    if not tester.delete_test_table():
        logger.error("Failed to delete test table. Exiting.")
        return False
    
    logger.info("All DynamoDB tests completed successfully!")
    return True

if __name__ == "__main__":
    success = run_dynamodb_tests()
    sys.exit(0 if success else 1)
