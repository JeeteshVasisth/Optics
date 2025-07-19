# Optics Calculator

## Overview

This is a Flask-based web application for calculating optical parameters and visualizing ray diagrams for mirrors and lenses. The application provides an interactive interface where users can input optical system parameters and receive calculated results along with visual ray diagrams.

## User Preferences

Preferred communication style: Simple, everyday language.

## System Architecture

### Frontend Architecture
- **Framework**: Bootstrap 5 with dark theme for responsive UI
- **JavaScript**: Vanilla JavaScript for form validation and dynamic interactions
- **Styling**: Custom CSS with Bootstrap overrides for optical calculator specific styling
- **Icons**: Font Awesome for visual elements
- **Template Engine**: Jinja2 templates with Flask

### Backend Architecture
- **Framework**: Flask (Python web framework)
- **Structure**: Single-file application (app.py) with modular class design
- **Session Management**: Flask sessions with configurable secret key
- **Logging**: Python logging module configured for debugging

### Visualization System
- **Plotting Library**: Matplotlib with 'Agg' backend for server-side image generation
- **Image Handling**: Base64 encoding for embedding plots directly in HTML responses
- **Mathematical Calculations**: NumPy for numerical computations

## Key Components

### OpticsCalculator Class
- **Purpose**: Core calculation engine for optical parameters
- **Functionality**: Handles lens/mirror calculations, input validation, and error management
- **Methods**: 
  - `reset_values()`: Initializes calculation variables
  - `validate_inputs()`: Comprehensive input validation with error reporting

### Flask Application Structure
- **Main Application**: `app.py` contains the Flask app and OpticsCalculator class
- **Entry Point**: `main.py` serves as the application launcher
- **Templates**: 
  - `base.html`: Base template with navigation and footer
  - `index.html`: Main calculator interface
- **Static Assets**:
  - `custom.css`: Application-specific styling
  - `optics.js`: Client-side form validation and interaction logic

### Input Validation System
- **Client-side**: Real-time validation using JavaScript
- **Server-side**: Comprehensive validation in OpticsCalculator class
- **Error Handling**: Detailed error messages for different optical scenarios
- **Visual Feedback**: Bootstrap validation classes for immediate user feedback

## Data Flow

1. **User Input**: Forms collect optical parameters (focal length, distances, heights)
2. **Client Validation**: JavaScript validates inputs in real-time
3. **Form Submission**: AJAX or form submission sends data to Flask backend
4. **Server Processing**: OpticsCalculator validates inputs and performs calculations
5. **Visualization**: Matplotlib generates ray diagrams as base64 encoded images
6. **Response**: JSON response with calculated values, errors, and diagram images
7. **UI Update**: Frontend updates results section and displays diagrams

## External Dependencies

### Python Libraries
- **Flask**: Web framework for HTTP handling and templating
- **Matplotlib**: Scientific plotting library for ray diagrams
- **NumPy**: Numerical computing for mathematical operations
- **Base64**: Built-in library for image encoding

### Frontend Libraries
- **Bootstrap 5**: CSS framework for responsive design
- **Font Awesome 6.4.0**: Icon library for UI elements
- **CDN-hosted**: External libraries loaded from CDNs for performance

### Configuration Dependencies
- **Environment Variables**: `SESSION_SECRET` for Flask session security
- **Python Environment**: Requires Python with scientific computing stack

## Deployment Strategy

### Development Setup
- **Local Development**: Flask development server with debug mode enabled
- **Host Configuration**: Binds to all interfaces (0.0.0.0) on port 5000
- **Debug Mode**: Enabled for development with auto-reload functionality

### Production Considerations
- **WSGI Server**: Application structure supports WSGI deployment (Gunicorn, uWSGI)
- **Environment Variables**: Uses environment-based configuration for secrets
- **Static Files**: Separate static file serving recommended for production
- **Logging**: Configurable logging level for production monitoring

### File Structure
```
/
├── app.py              # Main Flask application
├── main.py             # Application entry point
├── templates/          # Jinja2 templates
│   ├── base.html       # Base template
│   └── index.html      # Main calculator interface
├── static/             # Static assets
│   ├── css/
│   │   └── custom.css  # Custom styling
│   └── js/
│       └── optics.js   # Client-side logic
└── attached_assets/    # Legacy/backup files
```

### Security Features
- **Session Management**: Configurable session secrets
- **Input Validation**: Multi-layered validation (client and server)
- **Error Handling**: Graceful error handling without exposing system details
- **Content Security**: Bootstrap and Font Awesome loaded from trusted CDNs