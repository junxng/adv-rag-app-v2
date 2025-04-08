import os
import sys
import logging
import argparse
from dotenv import load_dotenv

# Set up logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# Load environment variables
load_dotenv()

def test_environment_variables():
    """Test if all required environment variables are set"""
    logger.info("Testing environment variables...")
    
    # Required AWS variables
    aws_vars = {
        "AWS_ACCESS_KEY_ID": os.environ.get("AWS_ACCESS_KEY_ID"),
        "AWS_SECRET_ACCESS_KEY": os.environ.get("AWS_SECRET_ACCESS_KEY"),
        "AWS_REGION": os.environ.get("AWS_REGION", "us-east-1")
    }
    
    # Required Langfuse variables
    langfuse_vars = {
        "LANGFUSE_PUBLIC_KEY": os.environ.get("LANGFUSE_PUBLIC_KEY"),
        "LANGFUSE_SECRET_KEY": os.environ.get("LANGFUSE_SECRET_KEY")
    }
    
    # Check AWS variables
    aws_missing = [var for var, value in aws_vars.items() if not value]
    if aws_missing:
        logger.warning(f"Missing AWS environment variables: {', '.join(aws_missing)}")
    else:
        logger.info("All required AWS environment variables are set")
    
    # Check Langfuse variables
    langfuse_missing = [var for var, value in langfuse_vars.items() if not value]
    if langfuse_missing:
        logger.warning(f"Missing Langfuse environment variables: {', '.join(langfuse_missing)}")
    else:
        logger.info("All required Langfuse environment variables are set")
    
    return not aws_missing, not langfuse_missing

def test_dynamodb():
    """Run DynamoDB tests"""
    logger.info("Running DynamoDB tests...")
    
    try:
        # Import the DynamoDB test module
        from test_dynamodb import run_dynamodb_tests
        
        # Run the tests
        success = run_dynamodb_tests()
        
        if success:
            logger.info("DynamoDB tests passed successfully")
        else:
            logger.error("DynamoDB tests failed")
        
        return success
    
    except ImportError:
        logger.error("Failed to import test_dynamodb module")
        return False
    except Exception as e:
        logger.error(f"Unexpected error in DynamoDB tests: {str(e)}")
        return False

def test_langfuse():
    """Run Langfuse tests"""
    logger.info("Running Langfuse tests...")
    
    try:
        # Import the Langfuse test module
        from test_langfuse import run_langfuse_tests
        
        # Run the tests
        success = run_langfuse_tests()
        
        if success:
            logger.info("Langfuse tests passed successfully")
        else:
            logger.error("Langfuse tests failed")
        
        return success
    
    except ImportError:
        logger.error("Failed to import test_langfuse module")
        return False
    except Exception as e:
        logger.error(f"Unexpected error in Langfuse tests: {str(e)}")
        return False

def test_combined_integration():
    """Test DynamoDB and Langfuse integration together"""
    logger.info("Running combined integration test...")
    
    try:
        # Import required modules
        import boto3
        from langfuse import Langfuse
        from botocore.exceptions import ClientError
        
        # AWS credentials
        AWS_ACCESS_KEY = os.environ.get("AWS_ACCESS_KEY_ID")
        AWS_SECRET_KEY = os.environ.get("AWS_SECRET_ACCESS_KEY")
        AWS_REGION = os.environ.get("AWS_REGION", "us-east-1")
        
        # Langfuse credentials
        LANGFUSE_PUBLIC_KEY = os.environ.get("LANGFUSE_PUBLIC_KEY")
        LANGFUSE_SECRET_KEY = os.environ.get("LANGFUSE_SECRET_KEY")
        LANGFUSE_HOST = os.environ.get("LANGFUSE_HOST", "https://cloud.langfuse.com")
        
        # Initialize DynamoDB client
        dynamodb = boto3.resource(
            'dynamodb',
            region_name=AWS_REGION,
            aws_access_key_id=AWS_ACCESS_KEY,
            aws_secret_access_key=AWS_SECRET_KEY
        )
        
        # Initialize Langfuse client
        langfuse = Langfuse(
            public_key=LANGFUSE_PUBLIC_KEY,
            secret_key=LANGFUSE_SECRET_KEY,
            host=LANGFUSE_HOST
        )
        
        # Create a test table
        table_name = "TestIntegrationTable"
        
        # Check if table already exists
        client = boto3.client(
            'dynamodb',
            region_name=AWS_REGION,
            aws_access_key_id=AWS_ACCESS_KEY,
            aws_secret_access_key=AWS_SECRET_KEY
        )
        
        existing_tables = client.list_tables()['TableNames']
        
        if table_name not in existing_tables:
            # Create the table
            client.create_table(
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
        
        # Create a trace in Langfuse
        trace = langfuse.trace(
            name="dynamodb-integration-test",
            metadata={
                "test": True,
                "integration": "dynamodb"
            }
        )
        
        # Log the start of the operation
        span = trace.span(
            name="dynamodb-operation",
            input=f"Testing DynamoDB operations on table {table_name}"
        )
        
        # Insert an item into DynamoDB
        table = dynamodb.Table(table_name)
        item_id = "integration-test-1"
        
        table.put_item(
            Item={
                'id': item_id,
                'test_value': 'Integration test item',
                'timestamp': '2023-01-01T00:00:00Z'
            }
        )
        
        logger.info(f"Test item inserted into {table_name}")
        
        # Get the item from DynamoDB
        response = table.get_item(
            Key={
                'id': item_id
            }
        )
        
        if 'Item' in response:
            item = response['Item']
            logger.info(f"Retrieved test item: {item}")
            
            # Log the successful operation in Langfuse
            span.end(
                output=f"Successfully retrieved item: {item}",
                metadata={
                    "success": True,
                    "item_id": item_id
                }
            )
            
            # Add a score for the operation
            span.score(
                name="operation_success",
                value=1.0,
                comment="DynamoDB operation completed successfully"
            )
        else:
            logger.error(f"Item with ID {item_id} not found")
            
            # Log the failed operation in Langfuse
            span.end(
                output=f"Failed to retrieve item with ID {item_id}",
                metadata={
                    "success": False,
                    "item_id": item_id
                }
            )
            
            # Add a score for the operation
            span.score(
                name="operation_success",
                value=0.0,
                comment="DynamoDB operation failed"
            )
            
            # Clean up and return
            client.delete_table(TableName=table_name)
            return False
        
        # Delete the item
        table.delete_item(
            Key={
                'id': item_id
            }
        )
        
        logger.info(f"Test item deleted from {table_name}")
        
        # Delete the table
        client.delete_table(TableName=table_name)
        logger.info(f"Table {table_name} deleted successfully")
        
        # Log the completion of the test
        trace.event(
            name="test-completed",
            input="Combined integration test completed successfully"
        )
        
        logger.info("Combined integration test completed successfully")
        return True
    
    except ClientError as e:
        logger.error(f"DynamoDB error in combined test: {str(e)}")
        return False
    except Exception as e:
        logger.error(f"Unexpected error in combined test: {str(e)}")
        return False

def main():
    """Main function to run the tests"""
    parser = argparse.ArgumentParser(description="Test DynamoDB and Langfuse integrations")
    parser.add_argument("--dynamodb", action="store_true", help="Run DynamoDB tests")
    parser.add_argument("--langfuse", action="store_true", help="Run Langfuse tests")
    parser.add_argument("--combined", action="store_true", help="Run combined integration test")
    parser.add_argument("--all", action="store_true", help="Run all tests")
    
    args = parser.parse_args()
    
    # If no arguments provided, run all tests
    if not (args.dynamodb or args.langfuse or args.combined or args.all):
        args.all = True
    
    # Test environment variables
    aws_vars_ok, langfuse_vars_ok = test_environment_variables()
    
    # Track test results
    results = {}
    
    # Run DynamoDB tests
    if args.dynamodb or args.all:
        if aws_vars_ok:
            results["dynamodb"] = test_dynamodb()
        else:
            logger.error("Skipping DynamoDB tests due to missing environment variables")
            results["dynamodb"] = False
    
    # Run Langfuse tests
    if args.langfuse or args.all:
        if langfuse_vars_ok:
            results["langfuse"] = test_langfuse()
        else:
            logger.error("Skipping Langfuse tests due to missing environment variables")
            results["langfuse"] = False
    
    # Run combined integration test
    if args.combined or args.all:
        if aws_vars_ok and langfuse_vars_ok:
            results["combined"] = test_combined_integration()
        else:
            logger.error("Skipping combined integration test due to missing environment variables")
            results["combined"] = False
    
    # Print summary
    logger.info("\n=== Test Results Summary ===")
    for test, result in results.items():
        logger.info(f"{test.capitalize()} tests: {'PASSED' if result else 'FAILED'}")
    
    # Return success if all tests passed
    return all(results.values())

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
