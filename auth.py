"""
Authentication module for Court Case Data Fetcher
Handles user registration, login, logout, and session management
"""

import secrets
import string
from datetime import datetime, timedelta
from flask import Blueprint, render_template, request, redirect, url_for, flash, session, jsonify
from flask_login import login_user, logout_user, login_required, current_user
from werkzeug.security import generate_password_hash
from app import app, db
from models import User, UserSession, SearchHistory, SystemAnalytics
import logging

logger = logging.getLogger(__name__)

# Create authentication blueprint
auth_bp = Blueprint('auth', __name__, url_prefix='/auth')

def generate_verification_token():
    """Generate a secure verification token"""
    alphabet = string.ascii_letters + string.digits
    return ''.join(secrets.choice(alphabet) for _ in range(32))

def record_analytics(metric_name, metric_value, additional_data=None):
    """Record system analytics"""
    try:
        analytics = SystemAnalytics(
            metric_name=metric_name,
            metric_value=metric_value,
            additional_data=additional_data
        )
        db.session.add(analytics)
        db.session.commit()
    except Exception as e:
        logger.error(f"Failed to record analytics: {e}")

@auth_bp.route('/register', methods=['GET', 'POST'])
def register():
    """User registration"""
    if current_user.is_authenticated:
        return redirect(url_for('dashboard'))
    
    if request.method == 'POST':
        try:
            # Get form data
            username = request.form.get('username', '').strip()
            email = request.form.get('email', '').strip().lower()
            password = request.form.get('password', '')
            confirm_password = request.form.get('confirm_password', '')
            full_name = request.form.get('full_name', '').strip()
            organization = request.form.get('organization', '').strip()
            
            # Validation
            if not all([username, email, password, confirm_password]):
                flash('All fields are required', 'error')
                return render_template('auth/register.html')
            
            if password != confirm_password:
                flash('Passwords do not match', 'error')
                return render_template('auth/register.html')
            
            if len(password) < 8:
                flash('Password must be at least 8 characters long', 'error')
                return render_template('auth/register.html')
            
            if len(username) < 3:
                flash('Username must be at least 3 characters long', 'error')
                return render_template('auth/register.html')
            
            # Check if user already exists
            if User.query.filter_by(username=username).first():
                flash('Username already exists', 'error')
                return render_template('auth/register.html')
            
            if User.query.filter_by(email=email).first():
                flash('Email already registered', 'error')
                return render_template('auth/register.html')
            
            # Create new user
            user = User(
                username=username,
                email=email,
                full_name=full_name,
                organization=organization,
                verification_token=generate_verification_token(),
                is_verified=True  # For demo purposes, auto-verify
            )
            user.set_password(password)
            
            db.session.add(user)
            db.session.commit()
            
            # Record analytics
            record_analytics('user_registration', 1)
            
            flash('Registration successful! Please log in.', 'success')
            return redirect(url_for('auth.login'))
            
        except Exception as e:
            logger.error(f"Registration error: {e}")
            flash('Registration failed. Please try again.', 'error')
            return render_template('auth/register.html')
    
    return render_template('auth/register.html')

@auth_bp.route('/login', methods=['GET', 'POST'])
def login():
    """User login"""
    if current_user.is_authenticated:
        return redirect(url_for('dashboard'))
    
    if request.method == 'POST':
        try:
            identifier = request.form.get('identifier', '').strip()  # username or email
            password = request.form.get('password', '')
            remember_me = request.form.get('remember_me', False)
            
            if not all([identifier, password]):
                flash('Please enter both username/email and password', 'error')
                return render_template('auth/login.html')
            
            # Find user by username or email
            user = User.query.filter(
                (User.username == identifier) | (User.email == identifier.lower())
            ).first()
            
            if not user or not user.check_password(password):
                flash('Invalid username/email or password', 'error')
                record_analytics('failed_login', 1)
                return render_template('auth/login.html')
            
            if not user.is_active:
                flash('Account is deactivated. Please contact support.', 'error')
                return render_template('auth/login.html')
            
            # Login user
            login_user(user, remember=remember_me)
            user.update_last_login()
            
            # Create user session record
            session_token = generate_verification_token()
            user_session = UserSession(
                user_id=user.id,
                session_token=session_token,
                ip_address=request.remote_addr,
                user_agent=request.headers.get('User-Agent', ''),
                expires_at=datetime.utcnow() + timedelta(hours=24 if not remember_me else 720)  # 30 days if remember me
            )
            db.session.add(user_session)
            db.session.commit()
            
            # Store session token
            session['session_token'] = session_token
            
            # Record analytics
            record_analytics('successful_login', 1)
            
            flash(f'Welcome back, {user.full_name or user.username}!', 'success')
            
            # Redirect to next page or dashboard
            next_page = request.args.get('next')
            if next_page:
                return redirect(next_page)
            return redirect(url_for('dashboard'))
            
        except Exception as e:
            logger.error(f"Login error: {e}")
            flash('Login failed. Please try again.', 'error')
            return render_template('auth/login.html')
    
    return render_template('auth/login.html')

@auth_bp.route('/logout')
@login_required
def logout():
    """User logout"""
    try:
        # Deactivate user session
        session_token = session.get('session_token')
        if session_token:
            user_session = UserSession.query.filter_by(
                session_token=session_token,
                user_id=current_user.id
            ).first()
            if user_session:
                user_session.is_active = False
                db.session.commit()
        
        # Record analytics
        record_analytics('user_logout', 1)
        
        # Clear session
        session.clear()
        
        # Logout user
        logout_user()
        
        flash('You have been logged out successfully', 'info')
        return redirect(url_for('index'))
        
    except Exception as e:
        logger.error(f"Logout error: {e}")
        flash('Logout error occurred', 'error')
        return redirect(url_for('index'))

@auth_bp.route('/profile')
@login_required
def profile():
    """User profile page"""
    try:
        # Get user statistics
        total_searches = current_user.case_queries.count()
        successful_searches = current_user.case_queries.filter_by(success=True).count()
        recent_searches = current_user.case_queries.order_by(
            current_user.case_queries.query_timestamp.desc()
        ).limit(10).all()
        
        # Get favorite cases
        favorite_cases = current_user.case_queries.filter_by(is_favorite=True).all()
        
        stats = {
            'total_searches': total_searches,
            'successful_searches': successful_searches,
            'success_rate': (successful_searches / total_searches * 100) if total_searches > 0 else 0,
            'recent_searches': recent_searches,
            'favorite_cases': favorite_cases
        }
        
        return render_template('auth/profile.html', stats=stats)
        
    except Exception as e:
        logger.error(f"Profile error: {e}")
        flash('Error loading profile', 'error')
        return redirect(url_for('dashboard'))

@auth_bp.route('/profile/edit', methods=['GET', 'POST'])
@login_required
def edit_profile():
    """Edit user profile"""
    if request.method == 'POST':
        try:
            # Update profile fields
            current_user.full_name = request.form.get('full_name', '').strip()
            current_user.organization = request.form.get('organization', '').strip()
            current_user.phone = request.form.get('phone', '').strip()
            
            # Update preferences
            preferences = {
                'email_notifications': request.form.get('email_notifications') == 'on',
                'dark_theme': request.form.get('dark_theme') == 'on',
                'auto_save_searches': request.form.get('auto_save_searches') == 'on'
            }
            current_user.set_preferences(preferences)
            
            current_user.updated_at = datetime.utcnow()
            db.session.commit()
            
            flash('Profile updated successfully', 'success')
            return redirect(url_for('auth.profile'))
            
        except Exception as e:
            logger.error(f"Profile update error: {e}")
            flash('Error updating profile', 'error')
    
    return render_template('auth/edit_profile.html')

@auth_bp.route('/change-password', methods=['GET', 'POST'])
@login_required
def change_password():
    """Change user password"""
    if request.method == 'POST':
        try:
            current_password = request.form.get('current_password', '')
            new_password = request.form.get('new_password', '')
            confirm_password = request.form.get('confirm_password', '')
            
            # Validation
            if not all([current_password, new_password, confirm_password]):
                flash('All fields are required', 'error')
                return render_template('auth/change_password.html')
            
            if not current_user.check_password(current_password):
                flash('Current password is incorrect', 'error')
                return render_template('auth/change_password.html')
            
            if new_password != confirm_password:
                flash('New passwords do not match', 'error')
                return render_template('auth/change_password.html')
            
            if len(new_password) < 8:
                flash('New password must be at least 8 characters long', 'error')
                return render_template('auth/change_password.html')
            
            # Update password
            current_user.set_password(new_password)
            current_user.updated_at = datetime.utcnow()
            db.session.commit()
            
            # Deactivate all other sessions
            UserSession.query.filter(
                UserSession.user_id == current_user.id,
                UserSession.session_token != session.get('session_token')
            ).update({'is_active': False})
            db.session.commit()
            
            flash('Password changed successfully', 'success')
            return redirect(url_for('auth.profile'))
            
        except Exception as e:
            logger.error(f"Password change error: {e}")
            flash('Error changing password', 'error')
    
    return render_template('auth/change_password.html')

@auth_bp.route('/api/check-username')
def check_username():
    """API endpoint to check username availability"""
    username = request.args.get('username', '').strip()
    if len(username) < 3:
        return jsonify({'available': False, 'message': 'Username too short'})
    
    user_exists = User.query.filter_by(username=username).first() is not None
    return jsonify({
        'available': not user_exists,
        'message': 'Username taken' if user_exists else 'Username available'
    })

@auth_bp.route('/api/check-email')
def check_email():
    """API endpoint to check email availability"""
    email = request.args.get('email', '').strip().lower()
    if '@' not in email:
        return jsonify({'available': False, 'message': 'Invalid email format'})
    
    user_exists = User.query.filter_by(email=email).first() is not None
    return jsonify({
        'available': not user_exists,
        'message': 'Email already registered' if user_exists else 'Email available'
    })

# Register blueprint with app
app.register_blueprint(auth_bp)