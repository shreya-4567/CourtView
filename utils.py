import re
from datetime import datetime
import logging

logger = logging.getLogger(__name__)

def validate_case_number(case_number):
    """
    Validate case number format
    
    Args:
        case_number (str): Case number to validate
        
    Returns:
        bool: True if valid, False otherwise
    """
    if not case_number:
        return False
    
    # Remove whitespace
    case_number = case_number.strip()
    
    # Check if it's only digits
    if not re.match(r'^\d+$', case_number):
        return False
    
    # Check reasonable length (1-10 digits)
    if len(case_number) < 1 or len(case_number) > 10:
        return False
    
    return True

def validate_filing_year(year_str):
    """
    Validate filing year
    
    Args:
        year_str (str): Year string to validate
        
    Returns:
        tuple: (is_valid, year_int)
    """
    try:
        year = int(year_str)
        current_year = datetime.now().year
        
        if 1950 <= year <= current_year:
            return True, year
        else:
            return False, None
    except (ValueError, TypeError):
        return False, None

def clean_text(text):
    """
    Clean and normalize text extracted from web pages
    
    Args:
        text (str): Raw text to clean
        
    Returns:
        str: Cleaned text
    """
    if not text:
        return ""
    
    # Remove excessive whitespace
    text = re.sub(r'\s+', ' ', text)
    
    # Remove common HTML artifacts
    text = text.replace('&nbsp;', ' ')
    text = text.replace('&amp;', '&')
    text = text.replace('&lt;', '<')
    text = text.replace('&gt;', '>')
    text = text.replace('&quot;', '"')
    
    return text.strip()

def extract_date_patterns(text):
    """
    Extract date patterns from text
    
    Args:
        text (str): Text to search for dates
        
    Returns:
        list: List of found date strings
    """
    if not text:
        return []
    
    # Common date patterns in Indian court documents
    patterns = [
        r'\b\d{1,2}[-/.]\d{1,2}[-/.]\d{2,4}\b',  # DD/MM/YYYY or DD-MM-YYYY
        r'\b\d{1,2}\s+(Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)[a-z]*,?\s+\d{2,4}\b',  # DD Mon YYYY
        r'\b(Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)[a-z]*\s+\d{1,2},?\s+\d{2,4}\b',  # Mon DD YYYY
    ]
    
    dates = []
    for pattern in patterns:
        matches = re.finditer(pattern, text, re.IGNORECASE)
        for match in matches:
            dates.append(match.group())
    
    return list(set(dates))  # Remove duplicates

def format_case_reference(case_type, case_number, filing_year):
    """
    Format case reference in standard format
    
    Args:
        case_type (str): Case type code
        case_number (str): Case number
        filing_year (str): Filing year
        
    Returns:
        str: Formatted case reference
    """
    return f"{case_type.upper()}/{case_number}/{filing_year}"

def sanitize_filename(filename):
    """
    Sanitize filename for safe download
    
    Args:
        filename (str): Original filename
        
    Returns:
        str: Sanitized filename
    """
    if not filename:
        return "document"
    
    # Remove invalid characters
    filename = re.sub(r'[<>:"/\\|?*]', '_', filename)
    
    # Remove excessive dots and spaces
    filename = re.sub(r'\.+', '.', filename)
    filename = re.sub(r'\s+', '_', filename)
    
    # Ensure reasonable length
    if len(filename) > 100:
        name, ext = filename.rsplit('.', 1) if '.' in filename else (filename, '')
        filename = name[:95] + ('.' + ext if ext else '')
    
    return filename

def is_pdf_url(url):
    """
    Check if URL likely points to a PDF
    
    Args:
        url (str): URL to check
        
    Returns:
        bool: True if likely a PDF URL
    """
    if not url:
        return False
    
    url_lower = url.lower()
    return (
        url_lower.endswith('.pdf') or
        'pdf' in url_lower or
        'download' in url_lower or
        'document' in url_lower
    )

def log_search_attempt(case_type, case_number, filing_year, success, error=None):
    """
    Log search attempt for monitoring
    
    Args:
        case_type (str): Case type
        case_number (str): Case number
        filing_year (str): Filing year
        success (bool): Whether search was successful
        error (str, optional): Error message if failed
    """
    case_ref = format_case_reference(case_type, case_number, filing_year)
    
    if success:
        logger.info(f"Successful search: {case_ref}")
    else:
        logger.warning(f"Failed search: {case_ref} - {error}")

def get_document_type_icon(doc_type):
    """
    Get Font Awesome icon class for document type
    
    Args:
        doc_type (str): Document type
        
    Returns:
        str: Font Awesome icon class
    """
    doc_type = doc_type.lower() if doc_type else ''
    
    icon_map = {
        'order': 'fas fa-gavel',
        'judgment': 'fas fa-balance-scale',
        'notice': 'fas fa-bell',
        'petition': 'fas fa-file-alt',
        'document': 'fas fa-file-pdf',
    }
    
    return icon_map.get(doc_type, 'fas fa-file-pdf')

# Constants for validation
MAX_CASE_NUMBER_LENGTH = 10
MIN_FILING_YEAR = 1950
MAX_FILENAME_LENGTH = 100

# Common case status mappings
CASE_STATUS_MAPPING = {
    'pending': 'Pending',
    'disposed': 'Disposed',
    'dismissed': 'Dismissed',
    'allowed': 'Allowed',
    'withdrawn': 'Withdrawn',
    'transferred': 'Transferred',
}

def normalize_case_status(status):
    """
    Normalize case status text
    
    Args:
        status (str): Raw status text
        
    Returns:
        str: Normalized status
    """
    if not status:
        return "Unknown"
    
    status_lower = status.lower().strip()
    
    for key, normalized in CASE_STATUS_MAPPING.items():
        if key in status_lower:
            return normalized
    
    # Return original if no mapping found
    return status.strip()
