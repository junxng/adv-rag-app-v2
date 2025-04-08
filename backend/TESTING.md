# Testing DynamoDB and Langfuse Integrations

This document provides instructions on how to test the DynamoDB and Langfuse integrations in the Tech Support Chatbot application.

## Prerequisites

Before running the tests, make sure you have:

1. AWS credentials with permissions to create, read, update, and delete DynamoDB tables
2. Langfuse account with API keys
3. All required environment variables set in the `backend/.env` file

## Required Environment Variables

For DynamoDB testing:
```
AWS_ACCESS_KEY_ID=your_aws_access_key
AWS_SECRET_ACCESS_KEY=your_aws_secret_key
AWS_REGION=us-east-1
```

For Langfuse testing:
```
LANGFUSE_PUBLIC_KEY=your_langfuse_public_key
LANGFUSE_SECRET_KEY=your_langfuse_secret_key
LANGFUSE_HOST=https://cloud.langfuse.com  # Optional, defaults to this value
```

## Installing Dependencies

Make sure you have all the required dependencies installed:

```bash
cd backend
pip install -r requirements.txt
```

## Running the Tests

### Test All Integrations

To run all tests (DynamoDB, Langfuse, and combined):

```bash
cd backend
python test_integrations.py --all
```

### Test DynamoDB Only

To test only the DynamoDB integration:

```bash
cd backend
python test_integrations.py --dynamodb
```

### Test Langfuse Only

To test only the Langfuse integration:

```bash
cd backend
python test_integrations.py --langfuse
```

### Test Combined Integration

To test the combined integration of DynamoDB and Langfuse:

```bash
cd backend
python test_integrations.py --combined
```

## Test Descriptions

### DynamoDB Tests

The DynamoDB tests perform the following operations:

1. Verify AWS credentials
2. List existing DynamoDB tables
3. Create a test table
4. Insert a test item
5. Retrieve the test item
6. Delete the test item
7. Delete the test table

### Langfuse Tests

The Langfuse tests perform the following operations:

1. Verify Langfuse credentials
2. Create a test trace
3. Create a test span
4. Create a test generation
5. Create a test event
6. Add a test score
7. Simulate a complete chat interaction with Langfuse logging

### Combined Integration Test

The combined integration test demonstrates how DynamoDB and Langfuse can work together:

1. Create a DynamoDB table
2. Create a Langfuse trace to monitor the operations
3. Insert an item into DynamoDB and log the operation in Langfuse
4. Retrieve the item from DynamoDB and log the result in Langfuse
5. Add a score in Langfuse based on the operation success
6. Clean up by deleting the item and table

## Viewing Results

### DynamoDB Results

You can view the created tables and items in the AWS DynamoDB console. However, the test script cleans up after itself, so the test table and items will be deleted after the test completes.

### Langfuse Results

You can view the traces, spans, generations, events, and scores in the Langfuse dashboard:

1. Go to [https://cloud.langfuse.com](https://cloud.langfuse.com)
2. Log in with your Langfuse account
3. Navigate to the "Traces" section to see the test traces

## Troubleshooting

### DynamoDB Issues

- Make sure your AWS credentials have the necessary permissions
- Check if you have reached the DynamoDB table limit in your AWS account
- Verify that the AWS region is correct

### Langfuse Issues

- Make sure your Langfuse API keys are correct
- Check if you have reached the Langfuse rate limit
- Verify that the Langfuse host URL is correct

If you encounter any issues, check the logs for detailed error messages.
