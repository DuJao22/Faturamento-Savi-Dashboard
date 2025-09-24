// Main JavaScript functionality for SAVI Assistant

document.addEventListener('DOMContentLoaded', function() {
    // Initialize Feather icons
    feather.replace();
    
    // Initialize all components
    initializeTooltips();
    initializeFileUploads();
    initializeFormValidations();
    initializeDynamicContent();
    initializeAnimations();
});

/**
 * Initialize Bootstrap tooltips
 */
function initializeTooltips() {
    const tooltipTriggerList = [].slice.call(document.querySelectorAll('[data-bs-toggle="tooltip"]'));
    tooltipTriggerList.map(function(tooltipTriggerEl) {
        return new bootstrap.Tooltip(tooltipTriggerEl);
    });
}

/**
 * Initialize file upload functionality
 */
function initializeFileUploads() {
    const fileInputs = document.querySelectorAll('input[type="file"]');
    
    fileInputs.forEach(input => {
        // Create custom file upload area
        createFileUploadArea(input);
        
        // Add change event listener
        input.addEventListener('change', function(e) {
            handleFileSelect(e.target);
        });
    });
}

/**
 * Create enhanced file upload area
 * @param {HTMLInputElement} input - File input element
 */
function createFileUploadArea(input) {
    const wrapper = document.createElement('div');
    wrapper.className = 'file-upload-wrapper position-relative';
    
    const uploadArea = document.createElement('div');
    uploadArea.className = 'file-upload-area';
    uploadArea.innerHTML = `
        <i data-feather="upload-cloud" width="48" height="48" class="text-muted mb-3"></i>
        <p class="mb-2">Clique para selecionar ou arraste o arquivo aqui</p>
        <small class="text-muted">Formatos aceitos: ${input.accept || 'Todos os tipos'}</small>
    `;
    
    // Insert wrapper before input
    input.parentNode.insertBefore(wrapper, input);
    wrapper.appendChild(uploadArea);
    wrapper.appendChild(input);
    
    // Hide original input
    input.style.display = 'none';
    
    // Add click event to upload area
    uploadArea.addEventListener('click', () => input.click());
    
    // Add drag and drop functionality
    ['dragenter', 'dragover', 'dragleave', 'drop'].forEach(eventName => {
        uploadArea.addEventListener(eventName, preventDefaults, false);
    });
    
    ['dragenter', 'dragover'].forEach(eventName => {
        uploadArea.addEventListener(eventName, () => uploadArea.classList.add('dragover'), false);
    });
    
    ['dragleave', 'drop'].forEach(eventName => {
        uploadArea.addEventListener(eventName, () => uploadArea.classList.remove('dragover'), false);
    });
    
    uploadArea.addEventListener('drop', handleDrop, false);
    
    function preventDefaults(e) {
        e.preventDefault();
        e.stopPropagation();
    }
    
    function handleDrop(e) {
        const dt = e.dataTransfer;
        const files = dt.files;
        
        if (files.length > 0) {
            input.files = files;
            handleFileSelect(input);
        }
    }
}

/**
 * Handle file selection
 * @param {HTMLInputElement} input - File input element
 */
function handleFileSelect(input) {
    const file = input.files[0];
    const uploadArea = input.parentNode.querySelector('.file-upload-area');
    
    if (file) {
        // Update upload area to show selected file
        uploadArea.innerHTML = `
            <i data-feather="file" width="32" height="32" class="text-success mb-2"></i>
            <p class="mb-1 text-success"><strong>${file.name}</strong></p>
            <small class="text-muted">${formatFileSize(file.size)} - ${file.type || 'Tipo desconhecido'}</small>
            <button type="button" class="btn btn-sm btn-outline-secondary mt-2" onclick="clearFileInput(this)">
                <i data-feather="x" width="14" height="14" class="me-1"></i>
                Remover
            </button>
        `;
        feather.replace();
        
        // Validate file if validation function exists
        if (typeof validateFile === 'function') {
            validateFile(input, file);
        }
    } else {
        // Reset upload area
        resetFileUploadArea(uploadArea, input);
    }
}

/**
 * Clear file input
 * @param {HTMLButtonElement} button - Clear button
 */
function clearFileInput(button) {
    const uploadArea = button.closest('.file-upload-area');
    const input = uploadArea.parentNode.querySelector('input[type="file"]');
    
    input.value = '';
    resetFileUploadArea(uploadArea, input);
}

/**
 * Reset file upload area to initial state
 * @param {HTMLElement} uploadArea - Upload area element
 * @param {HTMLInputElement} input - File input element
 */
function resetFileUploadArea(uploadArea, input) {
    uploadArea.innerHTML = `
        <i data-feather="upload-cloud" width="48" height="48" class="text-muted mb-3"></i>
        <p class="mb-2">Clique para selecionar ou arraste o arquivo aqui</p>
        <small class="text-muted">Formatos aceitos: ${input.accept || 'Todos os tipos'}</small>
    `;
    feather.replace();
}

/**
 * Format file size for display
 * @param {number} bytes - File size in bytes
 * @returns {string} Formatted file size
 */
function formatFileSize(bytes) {
    if (bytes === 0) return '0 Bytes';
    
    const k = 1024;
    const sizes = ['Bytes', 'KB', 'MB', 'GB'];
    const i = Math.floor(Math.log(bytes) / Math.log(k));
    
    return parseFloat((bytes / Math.pow(k, i)).toFixed(2)) + ' ' + sizes[i];
}

/**
 * Initialize form validations
 */
function initializeFormValidations() {
    const forms = document.querySelectorAll('form[data-validate="true"]');
    
    forms.forEach(form => {
        form.addEventListener('submit', function(e) {
            if (!validateForm(form)) {
                e.preventDefault();
                e.stopPropagation();
            }
            
            form.classList.add('was-validated');
        });
    });
}

/**
 * Validate form
 * @param {HTMLFormElement} form - Form element
 * @returns {boolean} Validation result
 */
function validateForm(form) {
    let isValid = true;
    const requiredFields = form.querySelectorAll('[required]');
    
    requiredFields.forEach(field => {
        if (!field.value.trim()) {
            isValid = false;
            showFieldError(field, 'Este campo é obrigatório');
        } else {
            clearFieldError(field);
        }
    });
    
    // Custom validations
    const emailFields = form.querySelectorAll('input[type="email"]');
    emailFields.forEach(field => {
        if (field.value && !isValidEmail(field.value)) {
            isValid = false;
            showFieldError(field, 'Email inválido');
        }
    });
    
    return isValid;
}

/**
 * Show field error
 * @param {HTMLElement} field - Form field
 * @param {string} message - Error message
 */
function showFieldError(field, message) {
    field.classList.add('is-invalid');
    
    let feedback = field.parentNode.querySelector('.invalid-feedback');
    if (!feedback) {
        feedback = document.createElement('div');
        feedback.className = 'invalid-feedback';
        field.parentNode.appendChild(feedback);
    }
    feedback.textContent = message;
}

/**
 * Clear field error
 * @param {HTMLElement} field - Form field
 */
function clearFieldError(field) {
    field.classList.remove('is-invalid');
    const feedback = field.parentNode.querySelector('.invalid-feedback');
    if (feedback) {
        feedback.remove();
    }
}

/**
 * Validate email format
 * @param {string} email - Email address
 * @returns {boolean} Validation result
 */
function isValidEmail(email) {
    const emailRegex = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;
    return emailRegex.test(email);
}

/**
 * Initialize dynamic content updates
 */
function initializeDynamicContent() {
    // Auto-refresh elements with data-refresh attribute
    const refreshElements = document.querySelectorAll('[data-refresh]');
    
    refreshElements.forEach(element => {
        const interval = parseInt(element.dataset.refresh) * 1000;
        const url = element.dataset.refreshUrl;
        
        if (url && interval > 0) {
            setInterval(() => {
                fetchAndUpdateElement(element, url);
            }, interval);
        }
    });
    
    // Initialize real-time status updates
    initializeStatusUpdates();
}

/**
 * Fetch and update element content
 * @param {HTMLElement} element - Element to update
 * @param {string} url - URL to fetch data from
 */
async function fetchAndUpdateElement(element, url) {
    try {
        const response = await fetch(url);
        if (response.ok) {
            const data = await response.json();
            updateElementContent(element, data);
        }
    } catch (error) {
        console.error('Error updating element:', error);
    }
}

/**
 * Update element content based on data
 * @param {HTMLElement} element - Element to update
 * @param {Object} data - Data to use for update
 */
function updateElementContent(element, data) {
    if (element.dataset.updateType === 'status') {
        updateStatusBadge(element, data.status);
    } else if (element.dataset.updateType === 'progress') {
        updateProgressBar(element, data.progress);
    }
    // Add more update types as needed
}

/**
 * Update status badge
 * @param {HTMLElement} badge - Badge element
 * @param {string} status - New status
 */
function updateStatusBadge(badge, status) {
    // Remove existing status classes
    badge.classList.remove('bg-primary', 'bg-success', 'bg-warning', 'bg-danger', 'bg-info');
    
    // Add new status class and update text
    switch (status) {
        case 'completed':
            badge.classList.add('bg-success');
            badge.innerHTML = '<i data-feather="check" width="12" height="12" class="me-1"></i>Concluída';
            break;
        case 'processing':
            badge.classList.add('bg-warning');
            badge.innerHTML = '<i data-feather="clock" width="12" height="12" class="me-1"></i>Processando';
            break;
        case 'error':
            badge.classList.add('bg-danger');
            badge.innerHTML = '<i data-feather="x" width="12" height="12" class="me-1"></i>Erro';
            break;
        default:
            badge.classList.add('bg-secondary');
            badge.innerHTML = '<i data-feather="help-circle" width="12" height="12" class="me-1"></i>Desconhecido';
    }
    
    feather.replace();
}

/**
 * Initialize status updates for analysis sessions
 */
function initializeStatusUpdates() {
    const statusElements = document.querySelectorAll('[data-session-id]');
    
    statusElements.forEach(element => {
        const sessionId = element.dataset.sessionId;
        if (sessionId) {
            checkSessionStatus(sessionId, element);
        }
    });
}

/**
 * Check session status
 * @param {string} sessionId - Session ID
 * @param {HTMLElement} element - Element to update
 */
async function checkSessionStatus(sessionId, element) {
    try {
        const response = await fetch(`/api/session-status/${sessionId}`);
        if (response.ok) {
            const data = await response.json();
            
            if (data.status === 'completed' || data.status === 'error') {
                // Status changed, reload page to show updated content
                window.location.reload();
            }
        }
    } catch (error) {
        console.error('Error checking session status:', error);
    }
}

/**
 * Initialize animations
 */
function initializeAnimations() {
    // Intersection Observer for scroll animations
    const observerOptions = {
        threshold: 0.1,
        rootMargin: '0px 0px -50px 0px'
    };
    
    const observer = new IntersectionObserver((entries) => {
        entries.forEach(entry => {
            if (entry.isIntersecting) {
                entry.target.classList.add('fade-in');
            }
        });
    }, observerOptions);
    
    // Observe elements with animation classes
    document.querySelectorAll('.animate-on-scroll').forEach(el => {
        observer.observe(el);
    });
    
    // Add slide-up animation to cards
    document.querySelectorAll('.card').forEach((card, index) => {
        card.style.animationDelay = `${index * 0.1}s`;
        card.classList.add('slide-up');
    });
}

/**
 * Show loading spinner on buttons
 * @param {HTMLButtonElement} button - Button element
 * @param {string} text - Loading text
 */
function showButtonLoading(button, text = 'Carregando...') {
    const originalText = button.innerHTML;
    button.dataset.originalText = originalText;
    button.disabled = true;
    button.innerHTML = `<span class="spinner-border spinner-border-sm me-2"></span>${text}`;
}

/**
 * Hide loading spinner on buttons
 * @param {HTMLButtonElement} button - Button element
 */
function hideButtonLoading(button) {
    const originalText = button.dataset.originalText;
    if (originalText) {
        button.innerHTML = originalText;
        button.disabled = false;
    }
}

/**
 * Show toast notification
 * @param {string} message - Message to show
 * @param {string} type - Toast type (success, error, info, warning)
 */
function showToast(message, type = 'info') {
    // Create toast container if it doesn't exist
    let toastContainer = document.querySelector('.toast-container');
    if (!toastContainer) {
        toastContainer = document.createElement('div');
        toastContainer.className = 'toast-container position-fixed top-0 end-0 p-3';
        toastContainer.style.zIndex = '9999';
        document.body.appendChild(toastContainer);
    }
    
    // Create toast element
    const toastId = 'toast-' + Date.now();
    const toastHTML = `
        <div id="${toastId}" class="toast" role="alert">
            <div class="toast-header">
                <i data-feather="${getToastIcon(type)}" width="16" height="16" class="me-2 text-${type}"></i>
                <strong class="me-auto">${getToastTitle(type)}</strong>
                <button type="button" class="btn-close" data-bs-dismiss="toast"></button>
            </div>
            <div class="toast-body">
                ${message}
            </div>
        </div>
    `;
    
    toastContainer.insertAdjacentHTML('beforeend', toastHTML);
    
    const toastElement = document.getElementById(toastId);
    const toast = new bootstrap.Toast(toastElement, {
        autohide: true,
        delay: 5000
    });
    
    // Replace feather icons
    feather.replace();
    
    // Show toast
    toast.show();
    
    // Remove from DOM after hiding
    toastElement.addEventListener('hidden.bs.toast', () => {
        toastElement.remove();
    });
}

/**
 * Get toast icon based on type
 * @param {string} type - Toast type
 * @returns {string} Feather icon name
 */
function getToastIcon(type) {
    const icons = {
        success: 'check-circle',
        error: 'alert-circle',
        warning: 'alert-triangle',
        info: 'info'
    };
    return icons[type] || icons.info;
}

/**
 * Get toast title based on type
 * @param {string} type - Toast type
 * @returns {string} Toast title
 */
function getToastTitle(type) {
    const titles = {
        success: 'Sucesso',
        error: 'Erro',
        warning: 'Atenção',
        info: 'Informação'
    };
    return titles[type] || titles.info;
}

/**
 * Utility function to copy text to clipboard
 * @param {string} text - Text to copy
 */
async function copyToClipboard(text) {
    try {
        await navigator.clipboard.writeText(text);
        showToast('Texto copiado para a área de transferência!', 'success');
    } catch (error) {
        console.error('Error copying to clipboard:', error);
        showToast('Erro ao copiar texto', 'error');
    }
}

/**
 * Debounce function to limit function calls
 * @param {Function} func - Function to debounce
 * @param {number} wait - Wait time in milliseconds
 * @returns {Function} Debounced function
 */
function debounce(func, wait) {
    let timeout;
    return function executedFunction(...args) {
        const later = () => {
            clearTimeout(timeout);
            func(...args);
        };
        clearTimeout(timeout);
        timeout = setTimeout(later, wait);
    };
}

// Export functions for global use
window.saviUtils = {
    showButtonLoading,
    hideButtonLoading,
    showToast,
    copyToClipboard,
    debounce,
    formatFileSize,
    clearFileInput
};
