import os
import logging
import json
import requests
from sqlalchemy import text
from openai import OpenAI
from .db.base import SessionLocal
from .db.models import User, SupportTicket
from .vector_store import query_vector_store

# the newest OpenAI model is "gpt-4o" which was released May 13, 2024.
# do not change this unless explicitly requested by the user

# Set up logging
logger = logging.getLogger(__name__)

# Initialize OpenAI client
OPENAI_API_KEY = os.environ.get("OPENAI_API_KEY", "")
# Only initialize the OpenAI client if we have an API key
if OPENAI_API_KEY:
    openai = OpenAI(api_key=OPENAI_API_KEY)
else:
    logger.warning("OPENAI_API_KEY not found in environment variables")
    # Create a placeholder for the openai client to avoid errors
    openai = None

# Initialize Tavily API
TAVILY_API_KEY = os.environ.get("TAVILY_API_KEY", "default_key")

def query_sql_database(question, user_id, chat_history=None):
    """
    Queries the database for user account or support ticket information.
    First tries AWS DynamoDB, falls back to SQL database if AWS credentials not available.

    Args:
        question (str): The user's question
        user_id (int): The user's ID
        chat_history (list): Previous messages in the conversation

    Returns:
        str: The formatted response to the user's query
    """
    try:
        # Try to use DynamoDB first if AWS credentials are available
        aws_access_key = os.environ.get("AWS_ACCESS_KEY_ID")
        aws_secret_key = os.environ.get("AWS_SECRET_ACCESS_KEY")

        if aws_access_key and aws_secret_key:
            # Import here to avoid circular imports
            from .aws_services import DynamoDBService

            # Use DynamoDB
            dynamodb = DynamoDBService()

            # Convert int user_id to string for DynamoDB
            dynamo_user_id = f"user{user_id}"

            # Get user data from DynamoDB
            user_data = dynamodb.get_user_data(dynamo_user_id)
            if not user_data:
                logger.warning(f"User with ID {dynamo_user_id} not found in DynamoDB, falling back to SQL")
                return query_sql_database_fallback(question, user_id, chat_history)

            # Get user tickets from DynamoDB
            ticket_data = dynamodb.get_user_tickets(dynamo_user_id)

            # Create a data context for the AI
            data_context = {
                "user": user_data,
                "tickets": ticket_data
            }

            # Create a prompt for the AI to analyze the data
            prompt = f"""
            You are a tech support assistant with access to the following user data:

            {json.dumps(data_context, indent=2)}

            A user with ID {user_id} has asked: "{question}"

            Based on the available data, provide a helpful and accurate response.
            Focus only on the information that's relevant to their query.
            For ticket status questions, mention the most recent ticket first.
            Be conversational but precise, and don't make up information.
            """

            # Check if OpenAI client is available
            if openai is None:
                logger.error("OpenAI client not initialized, cannot generate response")
                return "I'm having trouble accessing your account information right now. Please try again later."

            # Use OpenAI to generate a response based on the data
            response = openai.chat.completions.create(
                model="gpt-4o",
                messages=[{"role": "user", "content": prompt}],
                temperature=0.7
            )

            return response.choices[0].message.content

        else:
            # If AWS credentials are not available, use SQL database
            logger.info("AWS credentials not available, using SQL database instead")
            return query_sql_database_fallback(question, user_id, chat_history)

    except Exception as e:
        logger.error(f"Error querying database: {str(e)}")
        return "I'm having trouble accessing your account information right now. Please try again later."

def query_sql_database_fallback(question, user_id, chat_history=None):
    """
    Fallback method that queries the SQL database for user account or support ticket information.

    Args:
        question (str): The user's question
        user_id (int): The user's ID
        chat_history (list): Previous messages in the conversation

    Returns:
        str: The formatted response to the user's query
    """
    try:
        # Create a database session
        db = SessionLocal()
        data_context = None

        try:
            # Get user data
            user = db.query(User).filter(User.id == user_id).first()
            if not user:
                return "I couldn't find your user account. Please contact support."

            # Create a context of available data for the AI
            user_tickets = db.query(SupportTicket).filter(SupportTicket.user_id == user_id).all()
            ticket_data = []
            for ticket in user_tickets:
                ticket_data.append({
                    "id": ticket.id,
                    "title": ticket.title,
                    "status": ticket.status,
                    "priority": ticket.priority,
                    "created_at": ticket.created_at.isoformat(),
                    "updated_at": ticket.updated_at.isoformat(),
                    "closed_at": ticket.closed_at.isoformat() if ticket.closed_at else None
                })

            # Create a data context for the AI
            data_context = {
                "user": {
                    "id": user.id,
                    "username": user.username,
                    "email": user.email,
                    "name": user.name
                },
                "tickets": ticket_data
            }
        finally:
            # Always close the database session
            db.close()

        # If we couldn't get user data, return an error message
        if data_context is None:
            return "I'm having trouble accessing your account information right now. Please try again later."

        # Create a prompt for the AI to analyze the data
        prompt = f"""
        You are a tech support assistant with access to the following user data:

        {json.dumps(data_context, indent=2)}

        A user with ID {user_id} has asked: "{question}"

        Based on the available data, provide a helpful and accurate response.
        Focus only on the information that's relevant to their query.
        For ticket status questions, mention the most recent ticket first.
        Be conversational but precise, and don't make up information.
        """

        # Check if OpenAI client is available
        if openai is None:
            logger.error("OpenAI client not initialized, cannot generate response")
            return "I'm having trouble accessing your account information right now. Please try again later."

        # Use OpenAI to generate a response based on the data
        response = openai.chat.completions.create(
            model="gpt-4o",
            messages=[{"role": "user", "content": prompt}],
            temperature=0.7
        )

        return response.choices[0].message.content

except Exception as e:
    logger.error(f"Error in SQL database fallback: {str(e)}")
    return "I'm having trouble accessing your account information right now. Please try again later."

def search_tavily(question, chat_history=None):
    """
    Searches the web using Tavily API for troubleshooting information.

    Args:
        question (str): The user's technical question
        chat_history (list): Previous messages in the conversation

    Returns:
        str: The formatted response with troubleshooting information
    """
    try:
        # Get Tavily API key
        tavily_api_key = os.environ.get("TAVILY_API_KEY")

        # Decide whether to use real Tavily API or simulated response
        if tavily_api_key and tavily_api_key != "default_key":
            # Use the real Tavily API
            search_results = query_tavily_api(question)
            logger.info("Using real Tavily API for web search")
        else:
            # Fall back to simulated search
            search_results = simulate_tavily_search(question)
            logger.info("Using simulated Tavily search (TAVILY_API_KEY not configured)")

        # Create a prompt for the AI to synthesize the search results
        prompt = f"""
        You are a tech support assistant helping with technical troubleshooting.

        The user asked: "{question}"

        Based on web search results, here is the relevant information:

        {json.dumps(search_results, indent=2)}

        Please provide a helpful and accurate response that synthesizes this information.
        Include specific technical steps when available.
        Cite the source of information when appropriate.
        Be conversational but precise, and don't make up information.
        If the search results don't directly answer the question, acknowledge that and provide general guidance.
        """

        # Check if OpenAI client is available
        if openai is None:
            logger.error("OpenAI client not initialized, cannot generate response")
            return "I'm having trouble searching for troubleshooting information right now. Please try again later."

        # Use OpenAI to generate a response based on the search results
        response = openai.chat.completions.create(
            model="gpt-4o",
            messages=[{"role": "user", "content": prompt}],
            temperature=0.7
        )

        return response.choices[0].message.content

    except Exception as e:
        logger.error(f"Error searching Tavily: {str(e)}")
        return "I'm having trouble searching for troubleshooting information right now. Please try again later."

def query_tavily_api(question):
    """
    Queries the Tavily API for web search results.

    Args:
        question (str): The user's technical question

    Returns:
        list: List of search result objects
    """
    try:
        # Get Tavily API key
        tavily_api_key = os.environ.get("TAVILY_API_KEY")

        if not tavily_api_key:
            logger.error("No Tavily API key found")
            return simulate_tavily_search(question)

        # Tavily API endpoint
        endpoint = "https://api.tavily.com/search"

        # Prepare the request
        headers = {
            "Content-Type": "application/json",
            "X-API-Key": tavily_api_key
        }

        data = {
            "query": question,
            "search_depth": "basic",  # or "advanced" for more comprehensive results
            "include_domains": [],  # Optional: specify domains to include
            "exclude_domains": [],  # Optional: specify domains to exclude
            "max_results": 5  # Number of results to return
        }

        # Send the request
        response = requests.post(endpoint, headers=headers, json=data, timeout=10)

        # Check if the request was successful
        if response.status_code == 200:
            result = response.json()

            # Process and format the results
            formatted_results = []
            for item in result.get("results", []):
                formatted_results.append({
                    "title": item.get("title", "No title"),
                    "content": item.get("content", "No content"),
                    "url": item.get("url", "#")
                })

            return formatted_results

        else:
            logger.error(f"Tavily API error: {response.status_code}: {response.text}")
            # Fall back to simulated search on API error
            return simulate_tavily_search(question)

    except Exception as e:
        logger.error(f"Error querying Tavily API: {str(e)}")
        # Fall back to simulated search on exception
        return simulate_tavily_search(question)

def simulate_tavily_search(query):
    """
    Simulates a Tavily search response for demonstration purposes.
    Used as a fallback when Tavily API is not available.
    """
    # Create a simulated search response based on the query
    if "wifi" in query.lower() or "network" in query.lower():
        return [
            {
                "title": "Troubleshooting WiFi Connection Issues",
                "content": "Common solutions for WiFi problems include: 1) Restart your router, 2) Check for network adapter issues, 3) Reset network settings, 4) Update router firmware, 5) Check for interference from other devices.",
                "url": "https://support.microsoft.com/en-us/windows/fix-wi-fi-connection-issues-in-windows-9424a1f7-6a3b-65a6-4d78-7f07eee84f2c"
            },
            {
                "title": "Reset Network Adapter in Windows",
                "content": "To reset your network adapter, open Command Prompt as administrator and run the following commands: 'netsh winsock reset' and 'netsh int ip reset'. Then restart your computer.",
                "url": "https://www.digitaltrends.com/computing/how-to-reset-a-router/"
            }
        ]
    elif "slow" in query.lower() and ("computer" in query.lower() or "laptop" in query.lower() or "pc" in query.lower()):
        return [
            {
                "title": "How to Speed Up a Slow Computer",
                "content": "To speed up a slow computer: 1) Close unnecessary background programs, 2) Remove unused applications, 3) Run disk cleanup, 4) Defragment your drive, 5) Add more RAM, 6) Check for malware, 7) Update drivers and OS.",
                "url": "https://www.pcmag.com/how-to/how-to-speed-up-your-laptop"
            },
            {
                "title": "10 Quick Fixes for a Slow PC",
                "content": "Quick fixes include: checking for Windows updates, disabling startup programs, cleaning up temporary files, and using the Windows Performance Troubleshooter.",
                "url": "https://support.microsoft.com/en-us/windows/tips-to-improve-pc-performance-in-windows-b3b3ef5b-5953-fb6a-2528-4bbed82fba96"
            }
        ]
    elif "printer" in query.lower():
        return [
            {
                "title": "How to Fix Common Printer Problems",
                "content": "Common printer solutions: 1) Check connection cables, 2) Restart the printer, 3) Clear the print queue, 4) Reinstall or update printer drivers, 5) Check for paper jams, 6) Verify ink/toner levels.",
                "url": "https://www.hp.com/us-en/shop/tech-takes/how-to-fix-common-printer-problems"
            },
            {
                "title": "Printer Troubleshooting Guide",
                "content": "For network printers, ensure the printer is on the same network as your computer. Try adding the printer again using its IP address. For Windows, use the built-in printer troubleshooter in Settings > Devices > Printers & scanners.",
                "url": "https://support.microsoft.com/en-us/windows/fix-printer-problems-in-windows-bf5d38dc-ec37-570a-91cf-ee2bbb86fcee"
            }
        ]
    elif "email" in query.lower() or "outlook" in query.lower():
        return [
            {
                "title": "Fix Outlook Sync Issues",
                "content": "To fix Outlook syncing problems: 1) Check your internet connection, 2) Update Outlook to the latest version, 3) Repair your Outlook data files, 4) Create a new Outlook profile, 5) Clear the Outlook cache.",
                "url": "https://support.microsoft.com/en-us/office/fix-outlook-connection-problems-in-office-365-and-exchange-online-a15af714-928c-4e99-a65d-69a4295c0735"
            },
            {
                "title": "Troubleshooting Email Connection Problems",
                "content": "Common email issues can be fixed by checking server settings, verifying your password hasn't expired, and ensuring your account hasn't been locked for security reasons.",
                "url": "https://support.microsoft.com/en-us/office/resolve-connection-problems-in-outlook-for-windows-86280aa7-1f02-49bf-9b21-6e16ae86fba6"
            }
        ]
    else:
        return [
            {
                "title": "IT Troubleshooting: The Essential Guide",
                "content": "The basic troubleshooting methodology includes these steps: 1) Identify the problem, 2) Establish a theory of probable cause, 3) Test the theory, 4) Establish a plan of action, 5) Implement the solution, 6) Verify functionality, 7) Document the solution.",
                "url": "https://www.comptia.org/blog/a-guide-to-basic-computer-troubleshooting"
            },
            {
                "title": "Common Computer Problems and Solutions",
                "content": "Most technical issues fall into categories: hardware failures, software conflicts, network connectivity, driver issues, malware infections, and user errors. Start by determining which category your problem belongs to.",
                "url": "https://www.pcmag.com/how-to/pc-troubleshooting-101-a-guide-for-beginners"
            }
        ]

def retrieve_from_vectordb(question, chat_history=None):
    """
    Retrieves information from the vector database for company knowledge queries.

    Args:
        question (str): The user's question about company policies/knowledge
        chat_history (list): Previous messages in the conversation

    Returns:
        str: The formatted response with company knowledge information
    """
    try:
        # Query the vector store for relevant documents
        relevant_docs = query_vector_store(question)

        # Calculate a simple relevance score (0-1) based on the number of docs returned
        # and their content length in relation to the query
        relevance_score = 0
        if relevant_docs:
            # Simple heuristic: average length of content vs query length
            avg_content_length = sum(len(doc.get('content', '')) for doc in relevant_docs) / len(relevant_docs)
            query_length = len(question)
            relevance_ratio = min(avg_content_length / max(query_length, 1), 10) / 10  # Cap at 1.0
            relevance_score = min(1.0, 0.5 + (0.5 * relevance_ratio))  # Base 0.5 + up to 0.5 for content ratio

        # Log retrieval effectiveness for monitoring
        try:
            from .services.monitoring_service import monitoring_service
            monitoring_service.log_retrieval(
                query=question,
                retrieved_docs=relevant_docs,
                relevance_score=relevance_score
            )
        except Exception as monitoring_error:
            logger.warning(f"Failed to log retrieval effectiveness: {str(monitoring_error)}")

        # Create a prompt for the AI to synthesize the retrieved documents
        prompt = f"""
        You are a tech support assistant providing information about company policies and knowledge.

        The user asked: "{question}"

        Based on our knowledge base, here is the relevant information:

        {json.dumps(relevant_docs, indent=2)}

        Please provide a helpful and accurate response that synthesizes this information.
        Be conversational but precise, and don't make up information.
        If the information doesn't fully answer their question, acknowledge that and stick to what we know.
        """

        # Check if OpenAI client is available
        if openai is None:
            logger.error("OpenAI client not initialized, cannot generate response")
            return "I'm having trouble accessing our knowledge base right now. Please try again later."

        # Use OpenAI to generate a response based on the retrieved documents
        response = openai.chat.completions.create(
            model="gpt-4o",
            messages=[{"role": "user", "content": prompt}],
            temperature=0.7
        )

        return response.choices[0].message.content

    except Exception as e:
        logger.error(f"Error retrieving from vector database: {str(e)}")
        return "I'm having trouble accessing our knowledge base right now. Please try again later."
