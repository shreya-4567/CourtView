from datetime import datetime
from app import db

class CaseQuery(db.Model):
    """Model to store case search queries and responses"""
    id = db.Column(db.Integer, primary_key=True)
    case_type = db.Column(db.String(100), nullable=False)
    case_number = db.Column(db.String(100), nullable=False)
    filing_year = db.Column(db.String(10), nullable=False)
    query_timestamp = db.Column(db.DateTime, default=datetime.utcnow)
    success = db.Column(db.Boolean, default=False)
    error_message = db.Column(db.Text)
    raw_response = db.Column(db.Text)
    
    # Parsed case data
    parties_names = db.Column(db.Text)
    filing_date = db.Column(db.String(50))
    next_hearing_date = db.Column(db.String(50))
    pdf_links = db.Column(db.Text)  # JSON string of PDF links
    case_status = db.Column(db.String(200))
    
    def __repr__(self):
        return f'<CaseQuery {self.case_type}/{self.case_number}/{self.filing_year}>'

class PDFDocument(db.Model):
    """Model to store PDF document metadata"""
    id = db.Column(db.Integer, primary_key=True)
    case_query_id = db.Column(db.Integer, db.ForeignKey('case_query.id'), nullable=False)
    filename = db.Column(db.String(255), nullable=False)
    url = db.Column(db.String(500), nullable=False)
    document_type = db.Column(db.String(100))  # order, judgment, etc.
    date_added = db.Column(db.DateTime, default=datetime.utcnow)
    
    case_query = db.relationship('CaseQuery', backref=db.backref('pdf_documents', lazy=True))
    
    def __repr__(self):
        return f'<PDFDocument {self.filename}>'
