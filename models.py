from datetime import datetime, timedelta
from app import db
from flask_login import UserMixin
from werkzeug.security import generate_password_hash, check_password_hash
from sqlalchemy import UniqueConstraint
import json

# User Management Models
class User(UserMixin, db.Model):
    """Enhanced User model with authentication and profile management"""
    __tablename__ = 'users'
    
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False, index=True)
    email = db.Column(db.String(120), unique=True, nullable=False, index=True)
    password_hash = db.Column(db.String(256), nullable=False)
    
    # Profile information
    full_name = db.Column(db.String(100))
    organization = db.Column(db.String(200))
    phone = db.Column(db.String(20))
    
    # Account status
    is_active = db.Column(db.Boolean, default=True)
    is_verified = db.Column(db.Boolean, default=False)
    verification_token = db.Column(db.String(100))
    
    # Timestamps
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    last_login = db.Column(db.DateTime)
    
    # User preferences
    preferences = db.Column(db.Text)  # JSON string for user preferences
    
    # Relationships
    case_queries = db.relationship('CaseQuery', backref='user', lazy=True, cascade='all, delete-orphan')
    search_history = db.relationship('SearchHistory', backref='user', lazy=True, cascade='all, delete-orphan')
    
    def set_password(self, password):
        """Set password hash"""
        self.password_hash = generate_password_hash(password)
    
    def check_password(self, password):
        """Check password against hash"""
        return check_password_hash(self.password_hash, password)
    
    def get_preferences(self):
        """Get user preferences as dict"""
        if self.preferences:
            try:
                return json.loads(self.preferences)
            except json.JSONDecodeError:
                return {}
        return {}
    
    def set_preferences(self, prefs_dict):
        """Set user preferences from dict"""
        self.preferences = json.dumps(prefs_dict)
    
    def update_last_login(self):
        """Update last login timestamp"""
        self.last_login = datetime.utcnow()
        db.session.commit()
    
    def __repr__(self):
        return f'<User {self.username}>'

# Enhanced Case Query Model
class CaseQuery(db.Model):
    """Enhanced model to store case search queries and responses"""
    __tablename__ = 'case_queries'
    
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False, index=True)
    
    # Search parameters
    case_type = db.Column(db.String(100), nullable=False, index=True)
    case_number = db.Column(db.String(100), nullable=False, index=True)
    filing_year = db.Column(db.String(10), nullable=False, index=True)
    
    # Query metadata
    query_timestamp = db.Column(db.DateTime, default=datetime.utcnow, nullable=False, index=True)
    success = db.Column(db.Boolean, default=False, index=True)
    error_message = db.Column(db.Text)
    raw_response = db.Column(db.Text)
    response_time = db.Column(db.Float)  # Response time in seconds
    
    # Parsed case data
    parties_names = db.Column(db.Text)
    filing_date = db.Column(db.String(50))
    next_hearing_date = db.Column(db.String(50))
    case_status = db.Column(db.String(200), index=True)
    judge_name = db.Column(db.String(200))
    court_hall = db.Column(db.String(100))
    
    # Case financial details
    case_value = db.Column(db.String(100))
    fees_paid = db.Column(db.String(100))
    
    # Additional metadata
    pdf_links = db.Column(db.Text)  # JSON string of PDF links
    is_favorite = db.Column(db.Boolean, default=False, index=True)
    notes = db.Column(db.Text)  # User notes
    tags = db.Column(db.String(500))  # Comma-separated tags
    
    # Relationships
    pdf_documents = db.relationship('PDFDocument', backref='case_query', lazy=True, cascade='all, delete-orphan')
    
    # Unique constraint to prevent duplicate queries
    __table_args__ = (
        UniqueConstraint('user_id', 'case_type', 'case_number', 'filing_year', 
                        name='uq_user_case_query'),
    )
    
    def get_case_reference(self):
        """Get formatted case reference"""
        return f"{self.case_type}/{self.case_number}/{self.filing_year}"
    
    def get_pdf_links_list(self):
        """Get PDF links as list"""
        if self.pdf_links:
            try:
                return json.loads(self.pdf_links)
            except json.JSONDecodeError:
                return []
        return []
    
    def set_pdf_links_list(self, links_list):
        """Set PDF links from list"""
        self.pdf_links = json.dumps(links_list)
    
    def get_tags_list(self):
        """Get tags as list"""
        if self.tags:
            return [tag.strip() for tag in self.tags.split(',') if tag.strip()]
        return []
    
    def set_tags_list(self, tags_list):
        """Set tags from list"""
        self.tags = ', '.join(tags_list)
    
    def __repr__(self):
        return f'<CaseQuery {self.get_case_reference()}>'

# Enhanced PDF Document Model
class PDFDocument(db.Model):
    """Enhanced model to store PDF document metadata"""
    __tablename__ = 'pdf_documents'
    
    id = db.Column(db.Integer, primary_key=True)
    case_query_id = db.Column(db.Integer, db.ForeignKey('case_queries.id'), nullable=False, index=True)
    
    # Document details
    filename = db.Column(db.String(255), nullable=False)
    original_url = db.Column(db.String(500), nullable=False)
    document_type = db.Column(db.String(100), index=True)  # order, judgment, etc.
    file_size = db.Column(db.Integer)  # Size in bytes
    content_type = db.Column(db.String(100))
    
    # Document metadata
    title = db.Column(db.String(500))
    description = db.Column(db.Text)
    date_issued = db.Column(db.String(50))
    issuing_authority = db.Column(db.String(200))
    
    # Download tracking
    download_count = db.Column(db.Integer, default=0)
    last_downloaded = db.Column(db.DateTime)
    
    # Timestamps
    date_added = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
    last_verified = db.Column(db.DateTime)  # When URL was last verified as working
    
    # Status
    is_available = db.Column(db.Boolean, default=True)
    verification_status = db.Column(db.String(50), default='pending')  # pending, verified, broken
    
    def increment_download_count(self):
        """Increment download counter"""
        self.download_count = (self.download_count or 0) + 1
        self.last_downloaded = datetime.utcnow()
        db.session.commit()
    
    def __repr__(self):
        return f'<PDFDocument {self.filename}>'

# Search History Model
class SearchHistory(db.Model):
    """Track user search patterns and frequently accessed cases"""
    __tablename__ = 'search_history'
    
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False, index=True)
    
    # Search details
    search_query = db.Column(db.String(500), nullable=False)
    search_type = db.Column(db.String(50), default='case_search')  # case_search, document_search, etc.
    result_count = db.Column(db.Integer, default=0)
    
    # Timestamps
    searched_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False, index=True)
    
    def __repr__(self):
        return f'<SearchHistory {self.search_query}>'

# System Analytics Model
class SystemAnalytics(db.Model):
    """Track system usage and performance metrics"""
    __tablename__ = 'system_analytics'
    
    id = db.Column(db.Integer, primary_key=True)
    
    # Metrics
    metric_name = db.Column(db.String(100), nullable=False, index=True)
    metric_value = db.Column(db.Float, nullable=False)
    metric_unit = db.Column(db.String(50))
    
    # Metadata
    recorded_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False, index=True)
    additional_data = db.Column(db.Text)  # JSON string for additional data
    
    def __repr__(self):
        return f'<SystemAnalytics {self.metric_name}={self.metric_value}>'

# User Session Model for enhanced security
class UserSession(db.Model):
    """Track user sessions for security and analytics"""
    __tablename__ = 'user_sessions'
    
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False, index=True)
    session_token = db.Column(db.String(100), unique=True, nullable=False, index=True)
    
    # Session details
    ip_address = db.Column(db.String(45))  # IPv6 compatible
    user_agent = db.Column(db.Text)
    is_active = db.Column(db.Boolean, default=True, index=True)
    
    # Timestamps
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
    last_activity = db.Column(db.DateTime, default=datetime.utcnow, index=True)
    expires_at = db.Column(db.DateTime, nullable=False, index=True)
    
    # Relationships
    user = db.relationship('User', backref='sessions')
    
    def is_expired(self):
        """Check if session is expired"""
        return datetime.utcnow() > self.expires_at
    
    def extend_session(self, hours=24):
        """Extend session expiry"""
        self.expires_at = datetime.utcnow() + timedelta(hours=hours)
        self.last_activity = datetime.utcnow()
    
    def __repr__(self):
        return f'<UserSession {self.session_token}>'
