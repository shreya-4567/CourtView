from flask import render_template, request, redirect, url_for, flash, jsonify, send_file
from app import app, db
from models import CaseQuery, PDFDocument
from scraper import DelhiHighCourtScraper, DELHI_HC_CASE_TYPES
import json
import logging
from io import BytesIO
from datetime import datetime

logger = logging.getLogger(__name__)

@app.route('/')
def index():
    """Main page with search form"""
    return render_template('index.html', case_types=DELHI_HC_CASE_TYPES)

@app.route('/search', methods=['POST'])
def search_case():
    """Handle case search form submission"""
    try:
        case_type = request.form.get('case_type', '').strip()
        case_number = request.form.get('case_number', '').strip()
        filing_year = request.form.get('filing_year', '').strip()
        
        # Validate input
        if not all([case_type, case_number, filing_year]):
            flash('All fields are required', 'error')
            return redirect(url_for('index'))
        
        # Validate year format
        try:
            year = int(filing_year)
            current_year = datetime.now().year
            if year < 1950 or year > current_year:
                flash(f'Filing year must be between 1950 and {current_year}', 'error')
                return redirect(url_for('index'))
        except ValueError:
            flash('Filing year must be a valid number', 'error')
            return redirect(url_for('index'))
        
        # Create database record for this query
        query_record = CaseQuery(
            case_type=case_type,
            case_number=case_number,
            filing_year=filing_year,
            query_timestamp=datetime.utcnow()
        )
        
        # Perform the search
        scraper = DelhiHighCourtScraper()
        result = scraper.search_case(case_type, case_number, filing_year)
        
        # Update query record with results
        query_record.success = result['success']
        query_record.error_message = result.get('error')
        query_record.raw_response = result.get('raw_response')
        
        if result['success']:
            query_record.parties_names = result.get('parties_names')
            query_record.filing_date = result.get('filing_date')
            query_record.next_hearing_date = result.get('next_hearing_date')
            query_record.case_status = result.get('case_status')
            query_record.pdf_links = json.dumps(result.get('pdf_links', []))
        
        # Save to database
        db.session.add(query_record)
        db.session.commit()
        
        # Save PDF documents to separate table
        if result['success'] and result.get('pdf_links'):
            for pdf_info in result['pdf_links']:
                pdf_doc = PDFDocument(
                    case_query_id=query_record.id,
                    filename=pdf_info.get('title', 'Document'),
                    url=pdf_info['url'],
                    document_type=pdf_info.get('type', 'document')
                )
                db.session.add(pdf_doc)
            db.session.commit()
        
        if result['success']:
            flash('Case information retrieved successfully', 'success')
            return render_template('results.html', 
                                 case=query_record, 
                                 pdf_links=result.get('pdf_links', []))
        else:
            flash(f"Search failed: {result['error']}", 'error')
            return render_template('results.html', 
                                 case=query_record, 
                                 pdf_links=[])
    
    except Exception as e:
        logger.error(f"Error in case search: {e}")
        flash('An unexpected error occurred. Please try again.', 'error')
        return redirect(url_for('index'))

@app.route('/download_pdf/<int:pdf_id>')
def download_pdf(pdf_id):
    """Download a PDF document"""
    try:
        pdf_doc = PDFDocument.query.get_or_404(pdf_id)
        
        scraper = DelhiHighCourtScraper()
        pdf_content = scraper.download_pdf(pdf_doc.url)
        
        if pdf_content:
            # Create a filename
            filename = f"{pdf_doc.filename}.pdf"
            if not filename.lower().endswith('.pdf'):
                filename += '.pdf'
            
            # Clean filename
            filename = "".join(c for c in filename if c.isalnum() or c in (' ', '-', '_', '.')).rstrip()
            
            return send_file(
                BytesIO(pdf_content),
                as_attachment=True,
                download_name=filename,
                mimetype='application/pdf'
            )
        else:
            flash('Failed to download PDF. The file may no longer be available.', 'error')
            return redirect(url_for('index'))
    
    except Exception as e:
        logger.error(f"Error downloading PDF {pdf_id}: {e}")
        flash('Error downloading PDF', 'error')
        return redirect(url_for('index'))

@app.route('/history')
def search_history():
    """Display search history"""
    try:
        queries = CaseQuery.query.order_by(CaseQuery.query_timestamp.desc()).limit(50).all()
        return render_template('history.html', queries=queries)
    except Exception as e:
        logger.error(f"Error fetching search history: {e}")
        flash('Error loading search history', 'error')
        return redirect(url_for('index'))

@app.route('/api/case_types')
def get_case_types():
    """API endpoint to get available case types"""
    return jsonify(DELHI_HC_CASE_TYPES)

@app.errorhandler(404)
def not_found_error(error):
    return render_template('404.html'), 404

@app.errorhandler(500)
def internal_error(error):
    db.session.rollback()
    logger.error(f"Internal server error: {error}")
    return render_template('500.html'), 500
