from flask import render_template, request, redirect, url_for, flash, jsonify, send_file
from flask_login import login_required, current_user
from app import app, db
from models import CaseQuery, PDFDocument, SearchHistory, SystemAnalytics, User
from scraper import DelhiHighCourtScraper, DELHI_HC_CASE_TYPES
import json
import logging
import time
from io import BytesIO
from datetime import datetime
from sqlalchemy import desc, func
from sqlalchemy.exc import IntegrityError

logger = logging.getLogger(__name__)

@app.route('/')
def index():
    """Landing page - redirect to dashboard if logged in, otherwise show login/register options"""
    if current_user.is_authenticated:
        return redirect(url_for('dashboard'))
    return render_template('landing.html')

@app.route('/dashboard')
@login_required
def dashboard():
    """Main dashboard for authenticated users"""
    try:
        # Get user statistics
        total_searches = current_user.case_queries.count()
        successful_searches = current_user.case_queries.filter_by(success=True).count()
        recent_searches = current_user.case_queries.order_by(desc(CaseQuery.query_timestamp)).limit(5).all()
        favorite_cases = current_user.case_queries.filter_by(is_favorite=True).limit(5).all()
        
        # Get system statistics for admin view
        system_stats = None
        if current_user.username == 'admin':  # Simple admin check
            system_stats = {
                'total_users': User.query.count(),
                'total_searches': CaseQuery.query.count(),
                'successful_searches': CaseQuery.query.filter_by(success=True).count(),
                'recent_registrations': User.query.filter(
                    User.created_at >= datetime.utcnow().replace(hour=0, minute=0, second=0, microsecond=0)
                ).count()
            }
        
        stats = {
            'total_searches': total_searches,
            'successful_searches': successful_searches,
            'success_rate': (successful_searches / total_searches * 100) if total_searches > 0 else 0,
            'recent_searches': recent_searches,
            'favorite_cases': favorite_cases,
            'system_stats': system_stats
        }
        
        return render_template('dashboard.html', stats=stats, case_types=DELHI_HC_CASE_TYPES)
        
    except Exception as e:
        logger.error(f"Dashboard error: {e}")
        flash('Error loading dashboard', 'error')
        return render_template('dashboard.html', stats={}, case_types=DELHI_HC_CASE_TYPES)

@app.route('/search', methods=['POST'])
@login_required
def search_case():
    """Handle case search form submission"""
    try:
        case_type = request.form.get('case_type', '').strip()
        case_number = request.form.get('case_number', '').strip()
        filing_year = request.form.get('filing_year', '').strip()
        
        # Validate input
        if not all([case_type, case_number, filing_year]):
            flash('All fields are required', 'error')
            return redirect(url_for('dashboard'))
        
        # Validate year format
        try:
            year = int(filing_year)
            current_year = datetime.now().year
            if year < 1950 or year > current_year:
                flash(f'Filing year must be between 1950 and {current_year}', 'error')
                return redirect(url_for('dashboard'))
        except ValueError:
            flash('Filing year must be a valid number', 'error')
            return redirect(url_for('dashboard'))
        
        # Check for duplicate search
        existing_query = CaseQuery.query.filter_by(
            user_id=current_user.id,
            case_type=case_type,
            case_number=case_number,
            filing_year=filing_year
        ).first()
        
        if existing_query:
            flash('You have already searched for this case. Showing previous results.', 'info')
            return render_template('results.html', 
                                 case=existing_query, 
                                 pdf_links=existing_query.get_pdf_links_list())
        
        # Record search in history
        search_query = f"{case_type}/{case_number}/{filing_year}"
        search_history = SearchHistory(
            user_id=current_user.id,
            search_query=search_query,
            search_type='case_search'
        )
        db.session.add(search_history)
        
        # Create database record for this query
        start_time = time.time()
        query_record = CaseQuery(
            user_id=current_user.id,
            case_type=case_type,
            case_number=case_number,
            filing_year=filing_year,
            query_timestamp=datetime.utcnow()
        )
        
        # Perform the search
        scraper = DelhiHighCourtScraper()
        result = scraper.search_case(case_type, case_number, filing_year)
        
        # Calculate response time
        response_time = time.time() - start_time
        
        # Update query record with results
        query_record.success = result['success']
        query_record.error_message = result.get('error')
        query_record.raw_response = result.get('raw_response')
        query_record.response_time = response_time
        
        if result['success']:
            query_record.parties_names = result.get('parties_names')
            query_record.filing_date = result.get('filing_date')
            query_record.next_hearing_date = result.get('next_hearing_date')
            query_record.case_status = result.get('case_status')
            query_record.judge_name = result.get('judge_name')
            query_record.court_hall = result.get('court_hall')
            query_record.set_pdf_links_list(result.get('pdf_links', []))
        
        # Update search history with result count
        search_history.result_count = 1 if result['success'] else 0
        
        # Save to database
        try:
            db.session.add(query_record)
            db.session.commit()
            
            # Save PDF documents to separate table
            if result['success'] and result.get('pdf_links'):
                for pdf_info in result['pdf_links']:
                    pdf_doc = PDFDocument(
                        case_query_id=query_record.id,
                        title=pdf_info.get('title', 'Document'),
                        filename=pdf_info.get('title', 'Document'),
                        original_url=pdf_info['url'],
                        document_type=pdf_info.get('type', 'document')
                    )
                    db.session.add(pdf_doc)
                db.session.commit()
                
        except IntegrityError:
            db.session.rollback()
            flash('This case has already been searched by you.', 'warning')
            existing_query = CaseQuery.query.filter_by(
                user_id=current_user.id,
                case_type=case_type,
                case_number=case_number,
                filing_year=filing_year
            ).first()
            return render_template('results.html', 
                                 case=existing_query, 
                                 pdf_links=existing_query.get_pdf_links_list())
        
        # Record analytics
        analytics = SystemAnalytics(
            metric_name='case_search',
            metric_value=1 if result['success'] else 0,
            additional_data=json.dumps({
                'case_type': case_type,
                'response_time': response_time,
                'user_id': current_user.id
            })
        )
        db.session.add(analytics)
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
        return redirect(url_for('dashboard'))

@app.route('/download_pdf/<int:pdf_id>')
@login_required
def download_pdf(pdf_id):
    """Download a PDF document"""
    try:
        pdf_doc = PDFDocument.query.get_or_404(pdf_id)
        
        # Check if user has access to this document
        if pdf_doc.case_query.user_id != current_user.id:
            flash('Access denied', 'error')
            return redirect(url_for('dashboard'))
        
        scraper = DelhiHighCourtScraper()
        pdf_content = scraper.download_pdf(pdf_doc.original_url)
        
        if pdf_content:
            # Update download statistics
            pdf_doc.increment_download_count()
            
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
            return redirect(url_for('dashboard'))
    
    except Exception as e:
        logger.error(f"Error downloading PDF {pdf_id}: {e}")
        flash('Error downloading PDF', 'error')
        return redirect(url_for('dashboard'))

@app.route('/history')
@login_required
def search_history():
    """Display user's search history"""
    try:
        page = request.args.get('page', 1, type=int)
        per_page = 20
        
        queries = current_user.case_queries.order_by(desc(CaseQuery.query_timestamp)).paginate(
            page=page, per_page=per_page, error_out=False
        )
        
        return render_template('history.html', queries=queries)
    except Exception as e:
        logger.error(f"Error fetching search history: {e}")
        flash('Error loading search history', 'error')
        return redirect(url_for('dashboard'))

@app.route('/favorites')
@login_required
def favorites():
    """Display user's favorite cases"""
    try:
        page = request.args.get('page', 1, type=int)
        per_page = 20
        
        favorites = current_user.case_queries.filter_by(is_favorite=True).order_by(
            desc(CaseQuery.query_timestamp)
        ).paginate(page=page, per_page=per_page, error_out=False)
        
        return render_template('favorites.html', favorites=favorites)
    except Exception as e:
        logger.error(f"Error loading favorites: {e}")
        flash('Error loading favorites', 'error')
        return redirect(url_for('dashboard'))

@app.route('/toggle_favorite/<int:case_id>')
@login_required
def toggle_favorite(case_id):
    """Toggle favorite status of a case"""
    try:
        case = CaseQuery.query.get_or_404(case_id)
        
        # Check ownership
        if case.user_id != current_user.id:
            flash('Access denied', 'error')
            return redirect(url_for('dashboard'))
        
        case.is_favorite = not case.is_favorite
        db.session.commit()
        
        status = 'added to' if case.is_favorite else 'removed from'
        flash(f'Case {status} favorites', 'success')
        
        return redirect(request.referrer or url_for('dashboard'))
        
    except Exception as e:
        logger.error(f"Error toggling favorite: {e}")
        flash('Error updating favorite status', 'error')
        return redirect(url_for('dashboard'))

@app.route('/add_note/<int:case_id>', methods=['POST'])
@login_required
def add_note(case_id):
    """Add or update note for a case"""
    try:
        case = CaseQuery.query.get_or_404(case_id)
        
        # Check ownership
        if case.user_id != current_user.id:
            flash('Access denied', 'error')
            return redirect(url_for('dashboard'))
        
        note = request.form.get('note', '').strip()
        case.notes = note if note else None
        db.session.commit()
        
        flash('Note updated successfully', 'success')
        return redirect(request.referrer or url_for('dashboard'))
        
    except Exception as e:
        logger.error(f"Error adding note: {e}")
        flash('Error updating note', 'error')
        return redirect(url_for('dashboard'))

@app.route('/advanced_search')
@login_required
def advanced_search():
    """Advanced search page with filters"""
    return render_template('advanced_search.html', case_types=DELHI_HC_CASE_TYPES)

@app.route('/analytics')
@login_required
def analytics():
    """User analytics dashboard"""
    try:
        # Only allow admin users to view system analytics
        if current_user.username != 'admin':
            flash('Access denied', 'error')
            return redirect(url_for('dashboard'))
        
        # Get system metrics
        total_users = User.query.count()
        active_users = User.query.filter_by(is_active=True).count()
        total_searches = CaseQuery.query.count()
        successful_searches = CaseQuery.query.filter_by(success=True).count()
        
        # Get recent activity
        recent_searches = CaseQuery.query.order_by(desc(CaseQuery.query_timestamp)).limit(10).all()
        recent_users = User.query.order_by(desc(User.created_at)).limit(10).all()
        
        # Get search statistics by case type
        search_stats = db.session.query(
            CaseQuery.case_type,
            func.count(CaseQuery.id).label('count'),
            func.avg(CaseQuery.response_time).label('avg_response_time')
        ).group_by(CaseQuery.case_type).all()
        
        analytics_data = {
            'total_users': total_users,
            'active_users': active_users,
            'total_searches': total_searches,
            'successful_searches': successful_searches,
            'success_rate': (successful_searches / total_searches * 100) if total_searches > 0 else 0,
            'recent_searches': recent_searches,
            'recent_users': recent_users,
            'search_stats': search_stats
        }
        
        return render_template('analytics.html', data=analytics_data)
        
    except Exception as e:
        logger.error(f"Error loading analytics: {e}")
        flash('Error loading analytics', 'error')
        return redirect(url_for('dashboard'))

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
