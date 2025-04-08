import os
import io
import uuid
import logging
from werkzeug.utils import secure_filename
from aws_services import S3Service
from models import Document, db

# Set up logging
logger = logging.getLogger(__name__)

# Constants
# Use a safe bucket name that follows S3 naming conventions
S3_DOCUMENT_BUCKET = os.environ.get("S3_DOCUMENT_BUCKET")
if not S3_DOCUMENT_BUCKET:
    logger.warning("S3_DOCUMENT_BUCKET not set in environment variables")
    # Create a unique but deterministic bucket name based on AWS account ID
    # This avoids conflicts with globally unique bucket names
    import hashlib
    import boto3
    
    try:
        # Try to get AWS account ID to make a unique bucket name
        sts = boto3.client('sts',
            region_name=os.environ.get("AWS_REGION", "us-east-1"),
            aws_access_key_id=os.environ.get("AWS_ACCESS_KEY_ID"),
            aws_secret_access_key=os.environ.get("AWS_SECRET_ACCESS_KEY")
        )
        account_id = sts.get_caller_identity()["Account"]
        logger.info(f"Using AWS Account ID: {account_id} for bucket name generation")
        
        # Create a hash of the account ID to ensure uniqueness while being deterministic
        hash_obj = hashlib.md5(account_id.encode())
        hash_suffix = hash_obj.hexdigest()[:8]
        S3_DOCUMENT_BUCKET = f"tech-support-docs-{hash_suffix}"
    except Exception as e:
        logger.warning(f"Could not determine AWS account ID: {str(e)}")
        # Fall back to a generic name
        S3_DOCUMENT_BUCKET = "tech-support-documents"
        
logger.info(f"Using S3 bucket for document storage: {S3_DOCUMENT_BUCKET}")
    
ALLOWED_EXTENSIONS = {'txt', 'pdf', 'doc', 'docx', 'xls', 'xlsx', 'png', 'jpg', 'jpeg', 'gif'}
MAX_CONTENT_LENGTH = 16 * 1024 * 1024  # 16 MB

# Global flag to track S3 availability
s3_available = False

def init_s3_bucket():
    """
    Initialize the S3 bucket for document storage.
    This should be called when the application starts.
    """
    global s3_available
    
    try:
        logger.info(f"Initializing S3 bucket: {S3_DOCUMENT_BUCKET}")
        s3_service = S3Service()
        success = s3_service.create_bucket_if_not_exists(S3_DOCUMENT_BUCKET)
        if success:
            logger.info(f"S3 bucket initialized successfully: {S3_DOCUMENT_BUCKET}")
            s3_available = True
        else:
            logger.warning(f"S3 bucket not available: {S3_DOCUMENT_BUCKET}")
            logger.warning("Document storage will be disabled. Please check AWS credentials and permissions.")
            s3_available = False
    except Exception as e:
        logger.error(f"Error initializing S3 bucket: {str(e)}")
        logger.warning("Document storage will be disabled. Please check AWS credentials and permissions.")
        s3_available = False

def allowed_file(filename):
    """
    Check if a filename has an allowed extension.
    
    Args:
        filename (str): The filename to check
        
    Returns:
        bool: True if the file extension is allowed, False otherwise
    """
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

def create_s3_key(user_id, ticket_id, original_filename):
    """
    Create a unique S3 key for a document.
    
    Args:
        user_id (int): The user ID
        ticket_id (int): The ticket ID, can be None
        original_filename (str): Original filename
        
    Returns:
        str: The S3 key
    """
    # Secure the filename
    secure_name = secure_filename(original_filename)
    
    # Generate a unique identifier
    unique_id = str(uuid.uuid4())
    
    # Create path components
    if ticket_id:
        return f"user_{user_id}/ticket_{ticket_id}/{unique_id}_{secure_name}"
    else:
        return f"user_{user_id}/{unique_id}_{secure_name}"

def upload_document(file_storage, user_id, ticket_id=None, is_public=False):
    """
    Upload a document to S3 and store its metadata in the database.
    
    Args:
        file_storage (FileStorage): Flask file object
        user_id (int): The user ID
        ticket_id (int, optional): The ticket ID
        is_public (bool, optional): Whether the document is public
        
    Returns:
        Document: The created Document object or None if upload fails
    """
    # Check if S3 is available
    global s3_available
    if not s3_available:
        logger.error("S3 storage is not available. Document upload is disabled.")
        return None
    
    s3_service = None
    s3_key = None
    document = None
    
    try:
        # Initialize S3 service
        s3_service = S3Service()
        
        # Check if the file is valid
        if file_storage is None or file_storage.filename == '':
            logger.error("No file provided")
            return None
            
        if not allowed_file(file_storage.filename):
            logger.error(f"File type not allowed: {file_storage.filename}")
            return None
            
        # Check file size
        file_storage.seek(0, os.SEEK_END)
        file_size = file_storage.tell()
        file_storage.seek(0)
        
        if file_size > MAX_CONTENT_LENGTH:
            logger.error(f"File too large: {file_size} bytes")
            return None
            
        # Create S3 key
        original_filename = file_storage.filename
        s3_key = create_s3_key(user_id, ticket_id, original_filename)
        
        # Upload file to S3
        content_type = file_storage.content_type or 'application/octet-stream'
        success = s3_service.upload_fileobj(
            file_storage, 
            S3_DOCUMENT_BUCKET, 
            s3_key,
            content_type=content_type
        )
        
        if not success:
            logger.error("Failed to upload file to S3")
            return None
            
        # Create document record in database
        document = Document(
            filename=secure_filename(original_filename),
            original_filename=original_filename,
            file_size=file_size,
            mime_type=content_type,
            s3_bucket=S3_DOCUMENT_BUCKET,
            s3_key=s3_key,
            is_public=is_public,
            user_id=user_id,
            ticket_id=ticket_id
        )
        
        db.session.add(document)
        db.session.commit()
        
        logger.info(f"Document uploaded successfully: {s3_key}")
        return document
        
    except Exception as e:
        logger.error(f"Error uploading document: {str(e)}")
        if document and hasattr(document, 'id') and document.id:
            db.session.rollback()
            # Try to delete from S3 if it was uploaded
            if s3_service and s3_key:
                s3_service.delete_object(S3_DOCUMENT_BUCKET, s3_key)
        return None

def upload_document_from_string(content, filename, user_id, ticket_id=None, is_public=False, content_type=None):
    """
    Upload a document from a string to S3 and store its metadata in the database.
    
    Args:
        content (str): The string content of the file
        filename (str): The name of the file
        user_id (int): The user ID
        ticket_id (int, optional): The ticket ID
        is_public (bool, optional): Whether the document is public
        content_type (str, optional): The content type of the file
        
    Returns:
        Document: The created Document object or None if upload fails
    """
    # Check if S3 is available
    global s3_available
    if not s3_available:
        logger.error("S3 storage is not available. Document upload is disabled.")
        return None
    
    s3_service = None
    s3_key = None
    document = None
    
    try:
        # Initialize S3 service
        s3_service = S3Service()
        
        # Check if the filename is valid
        if not allowed_file(filename):
            logger.error(f"File type not allowed: {filename}")
            return None
            
        # Convert content to bytes
        file_obj = io.BytesIO(content.encode('utf-8') if isinstance(content, str) else content)
        file_size = len(content.encode('utf-8') if isinstance(content, str) else content)
        
        # Check file size
        if file_size > MAX_CONTENT_LENGTH:
            logger.error(f"File too large: {file_size} bytes")
            return None
            
        # Create S3 key
        s3_key = create_s3_key(user_id, ticket_id, filename)
        
        # Upload file to S3
        if content_type is None:
            content_type = 'text/plain'
            if filename.endswith('.pdf'):
                content_type = 'application/pdf'
            elif filename.endswith('.doc'):
                content_type = 'application/msword'
            elif filename.endswith('.docx'):
                content_type = 'application/vnd.openxmlformats-officedocument.wordprocessingml.document'
            
        success = s3_service.upload_fileobj(
            file_obj, 
            S3_DOCUMENT_BUCKET, 
            s3_key,
            content_type=content_type
        )
        
        if not success:
            logger.error("Failed to upload file to S3")
            return None
            
        # Create document record in database
        document = Document(
            filename=secure_filename(filename),
            original_filename=filename,
            file_size=file_size,
            mime_type=content_type,
            s3_bucket=S3_DOCUMENT_BUCKET,
            s3_key=s3_key,
            is_public=is_public,
            user_id=user_id,
            ticket_id=ticket_id
        )
        
        db.session.add(document)
        db.session.commit()
        
        logger.info(f"Document uploaded successfully: {s3_key}")
        return document
        
    except Exception as e:
        logger.error(f"Error uploading document: {str(e)}")
        if document and hasattr(document, 'id') and document.id:
            db.session.rollback()
            # Try to delete from S3 if it was uploaded
            if s3_service and s3_key:
                s3_service.delete_object(S3_DOCUMENT_BUCKET, s3_key)
        return None

def get_document(document_id):
    """
    Get a document by ID.
    
    Args:
        document_id (int): The document ID
        
    Returns:
        Document: The document object or None if not found
    """
    return Document.query.get(document_id)

def get_user_documents(user_id):
    """
    Get all documents for a user.
    
    Args:
        user_id (int): The user ID
        
    Returns:
        list: The list of Document objects
    """
    return Document.query.filter_by(user_id=user_id).all()

def get_ticket_documents(ticket_id):
    """
    Get all documents for a ticket.
    
    Args:
        ticket_id (int): The ticket ID
        
    Returns:
        list: The list of Document objects
    """
    return Document.query.filter_by(ticket_id=ticket_id).all()

def delete_document(document_id, user_id=None):
    """
    Delete a document.
    
    Args:
        document_id (int): The document ID
        user_id (int, optional): The user ID for permission check
        
    Returns:
        bool: True if successful, False otherwise
    """
    # Check if S3 is available
    global s3_available
    if not s3_available:
        logger.error("S3 storage is not available. Document deletion is disabled.")
        return False
    
    try:
        document = Document.query.get(document_id)
        
        if document is None:
            logger.error(f"Document not found: {document_id}")
            return False
            
        # Check if the user has permission to delete this document
        if user_id is not None and document.user_id != user_id:
            logger.error(f"User {user_id} does not have permission to delete document {document_id}")
            return False
            
        # Delete from S3
        s3_service = S3Service()
        s3_success = s3_service.delete_object(document.s3_bucket, document.s3_key)
        
        if not s3_success:
            logger.error(f"Failed to delete document from S3: {document.s3_key}")
            return False
            
        # Delete from database
        db.session.delete(document)
        db.session.commit()
        
        logger.info(f"Document deleted successfully: {document_id}")
        return True
        
    except Exception as e:
        logger.error(f"Error deleting document: {str(e)}")
        db.session.rollback()
        return False

def download_document_content(document_id):
    """
    Download a document's content.
    
    Args:
        document_id (int): The document ID
        
    Returns:
        tuple: (BytesIO object, document) or (None, None) if download fails
    """
    # Check if S3 is available
    global s3_available
    if not s3_available:
        logger.error("S3 storage is not available. Document download is disabled.")
        return None, None
    
    try:
        document = Document.query.get(document_id)
        
        if document is None:
            logger.error(f"Document not found: {document_id}")
            return None, None
            
        # Download from S3
        s3_service = S3Service()
        file_obj = io.BytesIO()
        
        s3_client = s3_service.s3
        s3_client.download_fileobj(document.s3_bucket, document.s3_key, file_obj)
        
        # Reset file position
        file_obj.seek(0)
        
        return file_obj, document
        
    except Exception as e:
        logger.error(f"Error downloading document: {str(e)}")
        return None, None

def get_document_url(document_id, expiration=3600):
    """
    Get a presigned URL for a document.
    
    Args:
        document_id (int): The document ID
        expiration (int, optional): URL expiration time in seconds
        
    Returns:
        str: The presigned URL or None if error
    """
    # Check if S3 is available
    global s3_available
    if not s3_available:
        logger.error("S3 storage is not available. Document URL generation is disabled.")
        return None
    
    try:
        document = Document.query.get(document_id)
        
        if document is None:
            logger.error(f"Document not found: {document_id}")
            return None
            
        return document.get_download_url(expiration)
        
    except Exception as e:
        logger.error(f"Error getting document URL: {str(e)}")
        return None