from datetime import datetime
from sqlalchemy import Column, Integer, String, Text, DateTime, Boolean, ForeignKey
from sqlalchemy.orm import relationship
from .db.base import Base

class User(Base):
    __tablename__ = 'user'
    id = Column(Integer, primary_key=True)
    username = Column(String(64), unique=True, nullable=False)
    email = Column(String(120), unique=True, nullable=False)
    name = Column(String(120))
    tickets = relationship('SupportTicket', back_populates='user')
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

class SupportTicket(Base):
    __tablename__ = 'support_ticket'
    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey('user.id'), nullable=False)
    title = Column(String(120), nullable=False)
    description = Column(Text)
    status = Column(String(20), default='open')  # open, closed, in progress
    priority = Column(String(20), default='medium')  # low, medium, high
    resolution = Column(Text)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    closed_at = Column(DateTime)

    # Relationships
    user = relationship('User', back_populates='tickets')

class KnowledgeArticle(Base):
    __tablename__ = 'knowledge_article'
    id = Column(Integer, primary_key=True)
    title = Column(String(120), nullable=False)
    content = Column(Text, nullable=False)
    category = Column(String(50))
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

class ChatLog(Base):
    __tablename__ = 'chat_log'
    id = Column(Integer, primary_key=True)
    user_message = Column(Text, nullable=False)
    bot_response = Column(Text, nullable=False)
    query_type = Column(String(50))  # account, troubleshooting, knowledge
    data_source = Column(String(50))  # Database, Web Search, Knowledge Base
    timestamp = Column(DateTime, default=datetime.utcnow)
    user_id = Column(Integer, ForeignKey('user.id'), nullable=True)

    # Relationships
    user = relationship('User')

class Document(Base):
    __tablename__ = 'document'
    id = Column(Integer, primary_key=True)
    filename = Column(String(255), nullable=False)
    original_filename = Column(String(255), nullable=False)
    file_size = Column(Integer, nullable=False)  # Size in bytes
    mime_type = Column(String(100), nullable=False)
    s3_bucket = Column(String(120), nullable=False)
    s3_key = Column(String(255), nullable=False, unique=True)
    is_public = Column(Boolean, default=False)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    user_id = Column(Integer, ForeignKey('user.id'), nullable=True)
    ticket_id = Column(Integer, ForeignKey('support_ticket.id'), nullable=True)

    # Relationships
    user = relationship('User')
    ticket = relationship('SupportTicket')

    def get_download_url(self, expiration=3600):
        """
        Generate a download URL for this document.

        Args:
            expiration (int): URL expiration time in seconds

        Returns:
            str: Presigned URL for the document or None if S3 is not available
        """
        # Import here to avoid circular import
        from document_service import s3_available

        if not s3_available:
            # S3 storage is not available
            return None

        from .aws_services import S3Service

        s3_service = S3Service()
        return s3_service.get_file_url(self.s3_bucket, self.s3_key, expiration)
