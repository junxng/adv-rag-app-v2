from datetime import datetime
from app import db

class User(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(64), unique=True, nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False)
    name = db.Column(db.String(120))
    tickets = db.relationship('SupportTicket', backref='user', lazy='dynamic')
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

class SupportTicket(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    title = db.Column(db.String(120), nullable=False)
    description = db.Column(db.Text)
    status = db.Column(db.String(20), default='open')  # open, closed, in progress
    priority = db.Column(db.String(20), default='medium')  # low, medium, high
    resolution = db.Column(db.Text)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    closed_at = db.Column(db.DateTime)

class KnowledgeArticle(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(120), nullable=False)
    content = db.Column(db.Text, nullable=False)
    category = db.Column(db.String(50))
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

class ChatLog(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_message = db.Column(db.Text, nullable=False)
    bot_response = db.Column(db.Text, nullable=False)
    query_type = db.Column(db.String(50))  # account, troubleshooting, knowledge
    data_source = db.Column(db.String(50))  # Database, Web Search, Knowledge Base
    timestamp = db.Column(db.DateTime, default=datetime.utcnow)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=True)

class Document(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    filename = db.Column(db.String(255), nullable=False)
    original_filename = db.Column(db.String(255), nullable=False)
    file_size = db.Column(db.Integer, nullable=False)  # Size in bytes
    mime_type = db.Column(db.String(100), nullable=False)
    s3_bucket = db.Column(db.String(120), nullable=False)
    s3_key = db.Column(db.String(255), nullable=False, unique=True)
    is_public = db.Column(db.Boolean, default=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=True)
    ticket_id = db.Column(db.Integer, db.ForeignKey('support_ticket.id'), nullable=True)
    
    # Add relationships
    user = db.relationship('User', backref=db.backref('documents', lazy='dynamic'))
    ticket = db.relationship('SupportTicket', backref=db.backref('documents', lazy='dynamic'))
    
    def get_download_url(self, expiration=3600):
        """
        Generate a download URL for this document.
        
        Args:
            expiration (int): URL expiration time in seconds
            
        Returns:
            str: Presigned URL for the document
        """
        from aws_services import S3Service
        
        s3_service = S3Service()
        return s3_service.get_file_url(self.s3_bucket, self.s3_key, expiration)
