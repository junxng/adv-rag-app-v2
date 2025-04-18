import os
import logging
import json
from langchain.prompts import ChatPromptTemplate
from langchain_openai import ChatOpenAI
from langchain.output_parsers import StructuredOutputParser
from langchain.output_parsers import ResponseSchema
from openai import OpenAI

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
    # The actual client will be initialized when needed
    openai = None

# Define the LangChain classifier
def get_langchain_classifier():
    """
    Creates and returns a LangChain classifier for query categorization.

    Returns:
        tuple: LangChain model and output parser
    """
    # Define the schema for the expected output
    category_schema = ResponseSchema(
        name="category",
        description="The category the query belongs to (account, troubleshooting, or knowledge)",
        type="string",
        enum=["account", "troubleshooting", "knowledge"]
    )

    confidence_schema = ResponseSchema(
        name="confidence",
        description="Confidence score between 0 and 1",
        type="number"
    )

    explanation_schema = ResponseSchema(
        name="explanation",
        description="Brief explanation of why this category was chosen",
        type="string"
    )

    # Create the output parser
    output_parser = StructuredOutputParser.from_response_schemas([
        category_schema, confidence_schema, explanation_schema
    ])

    # Get the format instructions
    format_instructions = output_parser.get_format_instructions()

    # Create the prompt template
    prompt_template = ChatPromptTemplate.from_template("""
    You are a query classifier for a technical support system.

    Classify the following user query into ONE of these categories:
    - account: Related to user account, support tickets, personal data (e.g. "What's my ticket status?")
    - troubleshooting: Technical issues requiring external information (e.g. "How do I fix a slow laptop?")
    - knowledge: Company policies, procedures, internal information (e.g. "What is our remote work policy?")

    Previous conversation context (if any):
    {context}

    User query: {query}

    {format_instructions}
    """)

    # Create the LLM
    llm = ChatOpenAI(
        model="gpt-4o",
        temperature=0.3,
        api_key=OPENAI_API_KEY
    )

    return prompt_template, llm, output_parser

def classify_query(query, chat_history=None):
    """
    Classifies a user query into one of three categories using LangChain:
    - account: Related to user account, support tickets, personal data
    - troubleshooting: Technical issues requiring external information
    - knowledge: Company policies, procedures, internal information

    Args:
        query (str): The user's query text
        chat_history (list): List of previous messages in the conversation

    Returns:
        str: The query type (account, troubleshooting, knowledge)
    """
    try:
        # Include chat history for context
        context = ""
        if chat_history:
            # Get the last few messages for context (up to 5)
            recent_history = chat_history[-5:] if len(chat_history) > 5 else chat_history
            context = "\n".join([
                f"{msg['role']}: {msg['content']}" for msg in recent_history
            ])

        # Get the LangChain classifier components
        prompt_template, llm, output_parser = get_langchain_classifier()

        # Format the prompt with our data
        prompt = prompt_template.format(query=query, context=context)

        try:
            # Try the LangChain classification first
            response = llm.invoke(prompt)
            parsed_output = output_parser.parse(response.content)

            category = parsed_output.get("category", "knowledge")
            confidence = parsed_output.get("confidence", 0)
            explanation = parsed_output.get("explanation", "")

            logger.debug(f"LangChain classification: {category} (confidence: {confidence})")
            logger.debug(f"Explanation: {explanation}")

            # Log classification data for monitoring (if monitoring module is available)
            try:
                from .services.monitoring_service import monitoring_service
                monitoring_service.log_classification(
                    user_message=query,
                    predicted_type=category,
                    confidence=confidence
                )
            except Exception as monitoring_error:
                logger.warning(f"Failed to log classification accuracy: {str(monitoring_error)}")

            return category

        except Exception as lc_error:
            # Fall back to direct OpenAI API call if LangChain fails
            logger.warning(f"LangChain classification failed: {str(lc_error)}. Falling back to direct API.")

            # Create the classification prompt for direct API
            classification_prompt = f"""
            Classify the following user query into ONE of these categories:
            - account: Related to user account, support tickets, personal data (e.g. "What's my ticket status?")
            - troubleshooting: Technical issues requiring external information (e.g. "How do I fix a slow laptop?")
            - knowledge: Company policies, procedures, internal information (e.g. "What is our remote work policy?")

            {context}

            User query: {query}

            Respond with a JSON object with a single key 'category' and the value as one of the three options: 'account', 'troubleshooting', or 'knowledge'.
            """

            # Check if OpenAI client is available
            if openai is None:
                logger.error("OpenAI client not initialized, cannot use fallback")
                return "knowledge"  # Default to knowledge if OpenAI not available

            try:
                # Call the OpenAI API directly
                response = openai.chat.completions.create(
                    model="gpt-4o",
                    messages=[{"role": "user", "content": classification_prompt}],
                    response_format={"type": "json_object"},
                    temperature=0.3
                )

                # Extract and return the category
                result = json.loads(response.choices[0].message.content)
                category = result.get("category", "knowledge")
            except Exception as openai_error:
                logger.error(f"Error calling OpenAI API: {str(openai_error)}")
                return "knowledge"  # Default to knowledge if API call fails

            logger.debug(f"Fallback classification: {category}")

            # Log classification data for monitoring (if monitoring module is available)
            try:
                from .services.monitoring_service import monitoring_service
                monitoring_service.log_classification(
                    user_message=query,
                    predicted_type=category,
                    confidence=None  # No confidence score from direct API call
                )
            except Exception as monitoring_error:
                logger.warning(f"Failed to log classification accuracy: {str(monitoring_error)}")

            return category

    except Exception as e:
        logger.error(f"Error in query classification: {str(e)}")
        # Default to knowledge base if classification fails
        return "knowledge"
