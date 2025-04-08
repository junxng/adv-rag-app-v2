from pydantic import BaseModel
from typing import Optional, List, Dict, Any
from datetime import datetime

# Chat schemas
class ChatRequest(BaseModel):
    message: str

class ChatResponse(BaseModel):
    message: str
    source: str

# Feedback schemas
class FeedbackRequest(BaseModel):
    user_message: str
    bot_response: str
    rating: int
    correct_type: Optional[str] = None
    comments: Optional[str] = None

# User schemas
class UserBase(BaseModel):
    username: str
    email: str
    name: Optional[str] = None

class UserCreate(UserBase):
    pass

class User(UserBase):
    id: int
    created_at: datetime
    updated_at: datetime

    class Config:
        orm_mode = True

# Support ticket schemas
class SupportTicketBase(BaseModel):
    title: str
    description: Optional[str] = None
    status: str = "open"
    priority: str = "medium"

class SupportTicketCreate(SupportTicketBase):
    user_id: int

class SupportTicket(SupportTicketBase):
    id: int
    user_id: int
    created_at: datetime
    updated_at: datetime
    closed_at: Optional[datetime] = None

    class Config:
        orm_mode = True

# Knowledge article schemas
class KnowledgeArticleBase(BaseModel):
    title: str
    content: str
    category: Optional[str] = None

class KnowledgeArticleCreate(KnowledgeArticleBase):
    pass

class KnowledgeArticle(KnowledgeArticleBase):
    id: int
    created_at: datetime
    updated_at: datetime

    class Config:
        orm_mode = True

# Document schemas
class DocumentBase(BaseModel):
    original_filename: str
    mime_type: str
    is_public: bool = False

class DocumentCreate(DocumentBase):
    filename: str
    file_size: int
    s3_bucket: str
    s3_key: str
    user_id: Optional[int] = None
    ticket_id: Optional[int] = None

class Document(DocumentBase):
    id: int
    filename: str
    file_size: int
    s3_bucket: str
    s3_key: str
    created_at: datetime
    updated_at: datetime
    user_id: Optional[int] = None
    ticket_id: Optional[int] = None
    url: Optional[str] = None

    class Config:
        orm_mode = True
