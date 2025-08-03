# Court Case Data Fetcher

A Flask web application that fetches and displays case information from Indian court websites, specifically targeting Delhi High Court. The application provides a user-friendly interface to search for cases and download associated documents.

## Features

- **Case Search**: Search cases by type, number, and filing year
- **Data Extraction**: Automatically parse case details including parties, dates, and status
- **Document Access**: View and download PDF documents linked to cases
- **Search History**: Track previous searches with timestamps
- **Error Handling**: Comprehensive error handling with user-friendly messages
- **Responsive UI**: Bootstrap-based responsive design with dark theme

## Court Target

This application targets the **Delhi High Court** (https://delhihighcourt.nic.in/) for case data retrieval. The scraper is designed to handle the specific structure and requirements of this court's website.

## Technology Stack

- **Backend**: Flask (Python)
- **Database**: PostgreSQL with SQLAlchemy ORM
- **Frontend**: HTML5, Bootstrap 5, JavaScript
- **Web Scraping**: Beautiful Soup 4, Requests
- **Styling**: Bootstrap with Replit dark theme

## Setup Instructions

### Prerequisites

- Python 3.8+
- PostgreSQL database
- Internet connection for accessing court websites

### Environment Variables

Create a `.env` file in the root directory with the following variables:

```env
# Database Configuration
DATABASE_URL=postgresql://username:password@localhost:5432/court_scraper
PGHOST=localhost
PGPORT=5432
PGDATABASE=court_scraper
PGUSER=your_username
PGPASSWORD=your_password

# Flask Configuration
SESSION_SECRET=your-secret-key-here
FLASK_ENV=development
