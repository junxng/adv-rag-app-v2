import pytest
import os
from unittest.mock import patch, MagicMock

# Import the module to test
from app.query_classifier import classify_query

class TestQueryClassifier:
    """
    Unit tests for the query classifier
    """
    
    @patch('app.query_classifier.openai')
    def test_classify_account_query(self, mock_openai):
        """
        Test classification of an account-related query
        """
        # Mock the OpenAI response
        mock_response = MagicMock()
        mock_response.choices[0].message.content = '{"category": "account", "confidence": 0.95, "explanation": "This is about user account"}'
        mock_openai.chat.completions.create.return_value = mock_response
        
        # Test query
        query = "What's the status of my support ticket?"
        chat_history = []
        
        # Call the function
        result = classify_query(query, chat_history)
        
        # Assert the result
        assert result == "account"
        
        # Verify the OpenAI API was called with the right parameters
        mock_openai.chat.completions.create.assert_called_once()
    
    @patch('app.query_classifier.openai')
    def test_classify_troubleshooting_query(self, mock_openai):
        """
        Test classification of a troubleshooting query
        """
        # Mock the OpenAI response
        mock_response = MagicMock()
        mock_response.choices[0].message.content = '{"category": "troubleshooting", "confidence": 0.9, "explanation": "This is about technical troubleshooting"}'
        mock_openai.chat.completions.create.return_value = mock_response
        
        # Test query
        query = "How do I fix my WiFi connection?"
        chat_history = []
        
        # Call the function
        result = classify_query(query, chat_history)
        
        # Assert the result
        assert result == "troubleshooting"
    
    @patch('app.query_classifier.openai')
    def test_classify_knowledge_query(self, mock_openai):
        """
        Test classification of a knowledge query
        """
        # Mock the OpenAI response
        mock_response = MagicMock()
        mock_response.choices[0].message.content = '{"category": "knowledge", "confidence": 0.85, "explanation": "This is about company knowledge"}'
        mock_openai.chat.completions.create.return_value = mock_response
        
        # Test query
        query = "What is the company's remote work policy?"
        chat_history = []
        
        # Call the function
        result = classify_query(query, chat_history)
        
        # Assert the result
        assert result == "knowledge"
    
    @patch('app.query_classifier.openai')
    def test_classify_with_chat_history(self, mock_openai):
        """
        Test classification with chat history context
        """
        # Mock the OpenAI response
        mock_response = MagicMock()
        mock_response.choices[0].message.content = '{"category": "account", "confidence": 0.8, "explanation": "Based on context, this is about user account"}'
        mock_openai.chat.completions.create.return_value = mock_response
        
        # Test query with chat history
        query = "Can you check it for me?"
        chat_history = [
            {"role": "user", "content": "I submitted a ticket yesterday"},
            {"role": "assistant", "content": "I can help you with that. Do you have the ticket number?"},
        ]
        
        # Call the function
        result = classify_query(query, chat_history)
        
        # Assert the result
        assert result == "account"
    
    @patch('app.query_classifier.openai', None)
    def test_classify_without_openai(self):
        """
        Test classification when OpenAI client is not available
        """
        # Test query
        query = "What's the status of my support ticket?"
        chat_history = []
        
        # Call the function
        result = classify_query(query, chat_history)
        
        # Should default to knowledge when OpenAI is not available
        assert result == "knowledge"
    
    @patch('app.query_classifier.openai')
    def test_classify_with_error(self, mock_openai):
        """
        Test classification when an error occurs
        """
        # Mock the OpenAI API to raise an exception
        mock_openai.chat.completions.create.side_effect = Exception("API error")
        
        # Test query
        query = "What's the status of my support ticket?"
        chat_history = []
        
        # Call the function
        result = classify_query(query, chat_history)
        
        # Should default to knowledge on error
        assert result == "knowledge"
