// Main JavaScript file for SOMA project

document.addEventListener('DOMContentLoaded', function() {
    // Initialize tooltips
    var tooltipTriggerList = [].slice.call(document.querySelectorAll('[data-bs-toggle="tooltip"]'));
    var tooltipList = tooltipTriggerList.map(function (tooltipTriggerEl) {
        return new bootstrap.Tooltip(tooltipTriggerEl);
    });

    // Initialize popovers
    var popoverTriggerList = [].slice.call(document.querySelectorAll('[data-bs-toggle="popover"]'));
    var popoverList = popoverTriggerList.map(function (popoverTriggerEl) {
        return new bootstrap.Popover(popoverTriggerEl);
    });

    // Auto-hide alerts after 5 seconds
    const alerts = document.querySelectorAll('.alert:not(.alert-permanent)');
    alerts.forEach(function(alert) {
        setTimeout(function() {
            const bsAlert = new bootstrap.Alert(alert);
            bsAlert.close();
        }, 5000);
    });

    // Confirm delete actions
    const deleteButtons = document.querySelectorAll('[data-confirm-delete]');
    deleteButtons.forEach(function(button) {
        button.addEventListener('click', function(e) {
            e.preventDefault();
            const message = this.getAttribute('data-confirm-delete') || '¿Estás seguro de que quieres eliminar este elemento?';
            if (confirm(message)) {
                // If it's a form button, submit the form
                if (this.closest('form')) {
                    this.closest('form').submit();
                }
                // If it's a link, follow the link
                else if (this.getAttribute('href')) {
                    window.location.href = this.getAttribute('href');
                }
            }
        });
    });

    // Table row selection
    const selectableRows = document.querySelectorAll('.table-selectable tbody tr');
    selectableRows.forEach(function(row) {
        row.addEventListener('click', function() {
            row.classList.toggle('table-active');
            const checkbox = row.querySelector('input[type="checkbox"]');
            if (checkbox) {
                checkbox.checked = !checkbox.checked;
            }
        });
    });

    // Search functionality
    const searchInput = document.getElementById('searchInput');
    if (searchInput) {
        searchInput.addEventListener('input', function() {
            const searchTerm = this.value.toLowerCase();
            const rows = document.querySelectorAll('.searchable-table tbody tr');
            
            rows.forEach(function(row) {
                const text = row.textContent.toLowerCase();
                if (text.includes(searchTerm)) {
                    row.style.display = '';
                } else {
                    row.style.display = 'none';
                }
            });
        });
    }
});

// Utility functions
const SOMA = {
    // Show success message
    showSuccess: function(message) {
        this.showAlert(message, 'success');
    },

    // Show error message
    showError: function(message) {
        this.showAlert(message, 'danger');
    },

    // Show warning message
    showWarning: function(message) {
        this.showAlert(message, 'warning');
    },

    // Show info message
    showInfo: function(message) {
        this.showAlert(message, 'info');
    },

    // Generic alert function
    showAlert: function(message, type) {
        const alertDiv = document.createElement('div');
        alertDiv.className = `alert alert-${type} alert-dismissible fade show`;
        alertDiv.innerHTML = `
            ${message}
            <button type="button" class="btn-close" data-bs-dismiss="alert" aria-label="Close"></button>
        `;
        
        const container = document.querySelector('.container-fluid') || document.body;
        container.insertBefore(alertDiv, container.firstChild);
        
        // Auto-hide after 5 seconds
        setTimeout(function() {
            const bsAlert = new bootstrap.Alert(alertDiv);
            bsAlert.close();
        }, 5000);
    },

    // Format currency
    formatCurrency: function(amount, currency = 'MXN') {
        return new Intl.NumberFormat('es-MX', {
            style: 'currency',
            currency: currency
        }).format(amount);
    },

    // Format date
    formatDate: function(date, options = {}) {
        const defaultOptions = {
            year: 'numeric',
            month: 'long',
            day: 'numeric'
        };
        return new Intl.DateTimeFormat('es-MX', { ...defaultOptions, ...options }).format(new Date(date));
    }
};

// Make SOMA utilities globally available
window.SOMA = SOMA;