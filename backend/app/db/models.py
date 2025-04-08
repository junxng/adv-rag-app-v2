"""
SQLAlchemy models for the application.
"""
from datetime import datetime
from sqlalchemy import Column, Integer, String, Text, DateTime, ForeignKey, Float, Boolean
from sqlalchemy.orm import relationship

from .base import Base

class User(Base):
    """
    User model.
    """
    __tablename__ = "users"
    
    id = Column(Integer, primary_key=True, index=True)
    username = Column(String(50), unique=True, index=True)
    email = Column(String(100), unique=True, index=True)
    hashed_password = Column(String(100))
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    
    # Relationships
    tickets = relationship("SupportTicket", back_populates="user")
    chat_logs = relationship("ChatLog", back_populates="user")

class SupportTicket(Base):
    """
    Support ticket model.
    """
    __tablename__ = "support_tickets"
    
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"))
    title = Column(String(200))
    description = Column(Text)
    status = Column(String(20), default="open")  # open, in_progress, closed
    priority = Column(String(20), default="medium")  # low, medium, high
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    closed_at = Column(DateTime, nullable=True)
    
    # Relationships
    user = relationship("User", back_populates="tickets")

class KnowledgeArticle(Base):
    """
    Knowledge article model.
    """
    __tablename__ = "knowledge_articles"
    
    id = Column(Integer, primary_key=True, index=True)
    title = Column(String(200))
    content = Column(Text)
    category = Column(String(50))
    tags = Column(String(200))  # Comma-separated tags
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Vector embedding for search
    embedding_id = Column(String(100), nullable=True)

class ChatLog(Base):
    """
    Chat log model for monitoring and analytics.
    """
    __tablename__ = "chat_logs"
    
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=True)
    session_id = Column(String(100), index=True)
    user_message = Column(Text)
    bot_response = Column(Text)
    query_type = Column(String(50))  # account, troubleshooting, knowledge
    data_source = Column(String(50))  # Database, Web Search, Knowledge Base
    timestamp = Column(DateTime, default=datetime.utcnow)
    
    # Relationships
    user = relationship("User", back_populates="chat_logs")
    feedback = relationship("Feedback", back_populates="chat_log", uselist=False)

class Feedback(Base):
    """
    User feedback on chatbot responses.
    """
    __tablename__ = "feedback"
    
    id = Column(Integer, primary_key=True, index=True)
    chat_log_id = Column(Integer, ForeignKey("chat_logs.id"))
    rating = Column(Integer)  # 1-5 star rating
    correct_type = Column(String(50), nullable=True)  # Correct query type if misclassified
    comments = Column(Text, nullable=True)
    timestamp = Column(DateTime, default=datetime.utcnow)
    
    # Relationships
    chat_log = relationship("ChatLog", back_populates="feedback")

class Document(Base):
    """
    Document model for document management.
    """
    __tablename__ = "documents"
    
    id = Column(Integer, primary_key=True, index=True)
    title = Column(String(200))
    description = Column(Text, nullable=True)
    file_path = Column(String(500))  # S3 path
    file_type = Column(String(50))
    file_size = Column(Integer)  # Size in bytes
    uploaded_at = Column(DateTime, default=datetime.utcnow)
    
    # Vector embedding for search
    embedding_id = Column(String(100), nullable=True)
