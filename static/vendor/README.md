# Vendor Directory

This directory contains third-party CSS and JavaScript libraries.

## Current Dependencies (via CDN)

The base template uses CDN links for the following libraries:
- Bootstrap 5.3.0 (CSS & JS)

## Local Vendor Files

If you need to include vendor files locally instead of using CDN:

### CSS Libraries
Place CSS files in subdirectories like:
- `css/bootstrap/`
- `css/fontawesome/`
- `css/datatables/`

### JavaScript Libraries
Place JS files in subdirectories like:
- `js/jquery/`
- `js/bootstrap/`
- `js/datatables/`
- `js/chartjs/`

### Fonts
Place font files in:
- `fonts/`

## Usage

To include vendor files in templates:
```html
{% load static %}
<link rel="stylesheet" href="{% static 'vendor/css/library/library.css' %}">
<script src="{% static 'vendor/js/library/library.js' %}"></script>
```

## Version Management

Keep track of library versions in this README when adding new vendor files.