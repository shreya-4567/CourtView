# Court Case Data Fetcher

## Overview

This is a Flask web application that fetches and displays case information from Indian court websites, specifically targeting the Delhi High Court. The application provides a user-friendly interface to search for cases by type, number, and filing year, automatically parsing case details including parties, dates, status, and associated PDF documents. The system includes comprehensive search history tracking and error handling with a responsive Bootstrap-based dark theme UI.

## User Preferences

Preferred communication style: Simple, everyday language.

## System Architecture

### Frontend Architecture
- **Technology**: HTML5 templates with Bootstrap 5 framework using Replit's dark theme
- **Styling**: Custom CSS with Font Awesome icons for enhanced UX
- **Template Engine**: Jinja2 templating system with a base template structure
- **Responsive Design**: Mobile-first responsive layout with Bootstrap grid system
- **JavaScript**: Client-side form validation and interactive elements

### Backend Architecture
- **Framework**: Flask with SQLAlchemy ORM for database operations
- **Application Structure**: Modular design with separate files for routes, models, and scraping logic
- **Session Management**: Flask sessions with configurable secret keys
- **Middleware**: ProxyFix middleware for proper request handling behind proxies
- **Error Handling**: Comprehensive error handling with user-friendly flash messages
- **Logging**: Built-in Python logging for debugging and monitoring

### Web Scraping Engine
- **Library**: Beautiful Soup 4 with Requests for HTTP operations
- **Target**: Delhi High Court website (delhihighcourt.nic.in)
- **Strategy**: Session-based scraping with proper headers and form handling
- **Data Extraction**: Automated parsing of case details, parties, dates, and PDF links
- **Error Recovery**: Robust error handling for site downtime and invalid responses

### Database Design
- **Primary Database**: PostgreSQL with SQLAlchemy ORM
- **Models**: 
  - CaseQuery: Stores search queries, responses, and parsed case data
  - PDFDocument: Stores PDF metadata with foreign key relationships
- **Features**: Connection pooling, automatic table creation, and relationship management
- **Configuration**: Environment-based database URL configuration

### Data Storage Strategy
- **Query Logging**: Every search request is logged with timestamp and success status
- **Case Data**: Parsed information stored including parties, dates, status, and PDF links
- **Document Management**: PDF metadata stored with links to original court documents
- **Search History**: Complete audit trail of user searches and results

## External Dependencies

### Core Dependencies
- **Flask**: Web framework for Python applications
- **SQLAlchemy**: ORM for database operations and migrations
- **PostgreSQL**: Primary database for data persistence
- **Beautiful Soup 4**: HTML/XML parsing for web scraping
- **Requests**: HTTP library for court website interactions

### Frontend Dependencies
- **Bootstrap 5**: CSS framework with Replit dark theme customization
- **Font Awesome**: Icon library for enhanced user interface
- **CDN Services**: External hosting for CSS and JavaScript libraries

### Court Website Integration
- **Delhi High Court**: Primary target at delhihighcourt.nic.in
- **Form Handling**: Automated form submission with hidden field extraction
- **Session Management**: Persistent sessions for court website interactions
- **Document Access**: Direct linking to court-hosted PDF documents

### Environment Configuration
- **Environment Variables**: Database credentials, session secrets, and Flask configuration
- **Development Tools**: Debug mode, logging configuration, and development server setup
- **Production Ready**: ProxyFix middleware and proper error handling for deployment