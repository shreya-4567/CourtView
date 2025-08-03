import requests
import logging
from bs4 import BeautifulSoup
from urllib.parse import urljoin, urlparse
import json
import time
import re

logger = logging.getLogger(__name__)

class DelhiHighCourtScraper:
    """Scraper for Delhi High Court website"""
    
    def __init__(self):
        self.base_url = "https://delhihighcourt.nic.in"
        self.search_url = f"{self.base_url}/case_status.asp"
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
        })
    
    def search_case(self, case_type, case_number, filing_year):
        """
        Search for a case on Delhi High Court website
        
        Args:
            case_type (str): Type of case (e.g., "CRL.A", "W.P.(C)", etc.)
            case_number (str): Case number
            filing_year (str): Filing year
            
        Returns:
            dict: Parsed case information or error details
        """
        try:
            logger.info(f"Searching case: {case_type}/{case_number}/{filing_year}")
            
            # First, get the search page to obtain any necessary tokens
            search_page = self.session.get(self.search_url)
            search_page.raise_for_status()
            
            soup = BeautifulSoup(search_page.content, 'html.parser')
            
            # Look for any hidden form fields (CSRF tokens, viewstate, etc.)
            form = soup.find('form')
            form_data = {}
            
            if form:
                # Extract hidden fields
                hidden_inputs = form.find_all('input', type='hidden')
                for hidden in hidden_inputs:
                    name = hidden.get('name')
                    value = hidden.get('value', '')
                    if name:
                        form_data[name] = value
            
            # Add our search parameters
            form_data.update({
                'case_type': case_type,
                'case_no': case_number,
                'case_year': filing_year,
                'submit': 'Search'
            })
            
            # Submit the search form
            logger.debug(f"Submitting form data: {form_data}")
            response = self.session.post(self.search_url, data=form_data)
            response.raise_for_status()
            
            # Parse the response
            return self._parse_case_response(response.content, case_type, case_number, filing_year)
            
        except requests.RequestException as e:
            logger.error(f"Network error while searching case: {e}")
            return {
                'success': False,
                'error': f'Network error: {str(e)}',
                'raw_response': None
            }
        except Exception as e:
            logger.error(f"Unexpected error while searching case: {e}")
            return {
                'success': False,
                'error': f'Unexpected error: {str(e)}',
                'raw_response': None
            }
    
    def _parse_case_response(self, html_content, case_type, case_number, filing_year):
        """
        Parse the HTML response from the court website
        
        Args:
            html_content: Raw HTML content from the response
            case_type, case_number, filing_year: Original search parameters
            
        Returns:
            dict: Parsed case information
        """
        try:
            soup = BeautifulSoup(html_content, 'html.parser')
            raw_html = str(soup)
            
            # Check for common error indicators
            error_indicators = [
                'no record found',
                'invalid case number',
                'case not found',
                'error occurred',
                'invalid input'
            ]
            
            text_content = soup.get_text().lower()
            for indicator in error_indicators:
                if indicator in text_content:
                    return {
                        'success': False,
                        'error': f'Case not found: {case_type}/{case_number}/{filing_year}',
                        'raw_response': raw_html
                    }
            
            # Initialize result structure
            result = {
                'success': True,
                'error': None,
                'raw_response': raw_html,
                'parties_names': None,
                'filing_date': None,
                'next_hearing_date': None,
                'case_status': None,
                'pdf_links': []
            }
            
            # Extract case information using various selectors
            # This is a generic approach since court website structures vary
            
            # Look for tables containing case information
            tables = soup.find_all('table')
            for table in tables:
                rows = table.find_all('tr')
                for row in rows:
                    cells = row.find_all(['td', 'th'])
                    if len(cells) >= 2:
                        label = cells[0].get_text(strip=True).lower()
                        value = cells[1].get_text(strip=True)
                        
                        if 'parties' in label or 'petitioner' in label or 'respondent' in label:
                            if not result['parties_names']:
                                result['parties_names'] = value
                            else:
                                result['parties_names'] += f" vs {value}"
                        
                        elif 'filing' in label and 'date' in label:
                            result['filing_date'] = value
                        
                        elif 'next' in label and ('hearing' in label or 'date' in label):
                            result['next_hearing_date'] = value
                        
                        elif 'status' in label:
                            result['case_status'] = value
            
            # Look for PDF links
            pdf_links = soup.find_all('a', href=True)
            for link in pdf_links:
                href = link.get('href')
                if href and ('.pdf' in href.lower() or 'download' in href.lower()):
                    # Convert relative URLs to absolute
                    full_url = urljoin(self.base_url, href)
                    link_text = link.get_text(strip=True)
                    
                    result['pdf_links'].append({
                        'url': full_url,
                        'title': link_text if link_text else 'Document',
                        'type': self._classify_document_type(link_text)
                    })
            
            # If we couldn't find structured data, try to extract from general text
            if not any([result['parties_names'], result['filing_date'], result['case_status']]):
                # Fallback: extract any meaningful information from the page
                main_content = soup.find('div', {'id': 'main'}) or soup.find('body')
                if main_content:
                    text = main_content.get_text()
                    
                    # Use regex to find date patterns
                    date_pattern = r'\b\d{1,2}[-/.]\d{1,2}[-/.]\d{2,4}\b'
                    dates = re.findall(date_pattern, text)
                    if dates:
                        result['filing_date'] = dates[0] if not result['filing_date'] else result['filing_date']
                        if len(dates) > 1:
                            result['next_hearing_date'] = dates[1] if not result['next_hearing_date'] else result['next_hearing_date']
                    
                    # Look for "vs" pattern to identify parties
                    vs_pattern = r'([A-Za-z\s]+)\s+vs?\s+([A-Za-z\s]+)'
                    parties_match = re.search(vs_pattern, text, re.IGNORECASE)
                    if parties_match and not result['parties_names']:
                        result['parties_names'] = f"{parties_match.group(1).strip()} vs {parties_match.group(2).strip()}"
            
            # If we still don't have essential information, mark as found but incomplete
            if not result['parties_names'] and not result['filing_date']:
                result['case_status'] = 'Case found but information extraction incomplete'
            
            logger.info(f"Successfully parsed case data for {case_type}/{case_number}/{filing_year}")
            return result
            
        except Exception as e:
            logger.error(f"Error parsing case response: {e}")
            return {
                'success': False,
                'error': f'Error parsing response: {str(e)}',
                'raw_response': str(html_content) if html_content else None
            }
    
    def _classify_document_type(self, link_text):
        """Classify document type based on link text"""
        link_text = link_text.lower()
        if 'order' in link_text:
            return 'order'
        elif 'judgment' in link_text or 'judgement' in link_text:
            return 'judgment'
        elif 'notice' in link_text:
            return 'notice'
        else:
            return 'document'
    
    def download_pdf(self, pdf_url):
        """
        Download PDF from the given URL
        
        Args:
            pdf_url (str): URL of the PDF to download
            
        Returns:
            bytes: PDF content if successful, None otherwise
        """
        try:
            logger.info(f"Downloading PDF from: {pdf_url}")
            response = self.session.get(pdf_url, timeout=30)
            response.raise_for_status()
            
            # Verify it's actually a PDF
            content_type = response.headers.get('content-type', '').lower()
            if 'pdf' not in content_type and not pdf_url.lower().endswith('.pdf'):
                logger.warning(f"URL may not be a PDF: {pdf_url}")
            
            return response.content
            
        except Exception as e:
            logger.error(f"Error downloading PDF from {pdf_url}: {e}")
            return None

# Case type mappings for Delhi High Court
DELHI_HC_CASE_TYPES = {
    'CRL.A': 'Criminal Appeal',
    'CRL.M.C': 'Criminal Miscellaneous',
    'CRL.REV.P': 'Criminal Revision Petition',
    'W.P.(C)': 'Writ Petition (Civil)',
    'W.P.(CRL)': 'Writ Petition (Criminal)',
    'FAO': 'First Appeal from Order',
    'RFA': 'Regular First Appeal',
    'CM': 'Civil Miscellaneous',
    'CS(OS)': 'Civil Suit (Original Side)',
    'CS(COMM)': 'Commercial Suit',
    'ARB.P': 'Arbitration Petition',
    'CONT.CAS': 'Contempt Case',
    'MAT.APP': 'Matrimonial Appeal'
}
