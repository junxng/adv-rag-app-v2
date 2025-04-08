from sqlalchemy.orm import Session
from . import models, schemas
from typing import List, Optional

# User services
def get_user(db: Session, user_id: int):
    return db.query(models.User).filter(models.User.id == user_id).first()

def get_user_by_email(db: Session, email: str):
    return db.query(models.User).filter(models.User.email == email).first()

def get_users(db: Session, skip: int = 0, limit: int = 100):
    return db.query(models.User).offset(skip).limit(limit).all()

def create_user(db: Session, user: schemas.UserCreate):
    db_user = models.User(**user.dict())
    db.add(db_user)
    db.commit()
    db.refresh(db_user)
    return db_user

# Support ticket services
def get_ticket(db: Session, ticket_id: int):
    return db.query(models.SupportTicket).filter(models.SupportTicket.id == ticket_id).first()

def get_user_tickets(db: Session, user_id: int, skip: int = 0, limit: int = 100):
    return db.query(models.SupportTicket).filter(models.SupportTicket.user_id == user_id).offset(skip).limit(limit).all()

def create_ticket(db: Session, ticket: schemas.SupportTicketCreate):
    db_ticket = models.SupportTicket(**ticket.dict())
    db.add(db_ticket)
    db.commit()
    db.refresh(db_ticket)
    return db_ticket

# Knowledge article services
def get_article(db: Session, article_id: int):
    return db.query(models.KnowledgeArticle).filter(models.KnowledgeArticle.id == article_id).first()

def get_articles(db: Session, skip: int = 0, limit: int = 100):
    return db.query(models.KnowledgeArticle).offset(skip).limit(limit).all()

def get_articles_by_category(db: Session, category: str, skip: int = 0, limit: int = 100):
    return db.query(models.KnowledgeArticle).filter(models.KnowledgeArticle.category == category).offset(skip).limit(limit).all()

def create_article(db: Session, article: schemas.KnowledgeArticleCreate):
    db_article = models.KnowledgeArticle(**article.dict())
    db.add(db_article)
    db.commit()
    db.refresh(db_article)
    return db_article

# Document services
def get_document(db: Session, document_id: int):
    return db.query(models.Document).filter(models.Document.id == document_id).first()

def get_user_documents(db: Session, user_id: int, skip: int = 0, limit: int = 100):
    return db.query(models.Document).filter(models.Document.user_id == user_id).offset(skip).limit(limit).all()

def create_document(db: Session, document: schemas.DocumentCreate):
    db_document = models.Document(**document.dict())
    db.add(db_document)
    db.commit()
    db.refresh(db_document)
    return db_document

def delete_document(db: Session, document_id: int):
    db_document = db.query(models.Document).filter(models.Document.id == document_id).first()
    if db_document:
        db.delete(db_document)
        db.commit()
        return True
    return False
