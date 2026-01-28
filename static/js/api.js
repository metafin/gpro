/**
 * API utilities for GPRO
 * Provides consistent API call handling with error management
 */

const API = {
    /**
     * Make a POST request with JSON body
     * @param {string} url - The API endpoint
     * @param {object} data - The data to send
     * @returns {Promise<object>} - The response data
     */
    async post(url, data = {}) {
        try {
            const response = await fetch(url, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify(data),
            });

            const result = await response.json();

            if (!response.ok) {
                throw new Error(result.message || `HTTP error ${response.status}`);
            }

            return result;
        } catch (error) {
            console.error('API POST error:', error);
            throw error;
        }
    },

    /**
     * Make a GET request
     * @param {string} url - The API endpoint
     * @returns {Promise<object>} - The response data
     */
    async get(url) {
        try {
            const response = await fetch(url);
            const result = await response.json();

            if (!response.ok) {
                throw new Error(result.message || `HTTP error ${response.status}`);
            }

            return result;
        } catch (error) {
            console.error('API GET error:', error);
            throw error;
        }
    },

    /**
     * Show an error message to the user
     * @param {string} message - The error message
     * @param {HTMLElement} container - Optional container for the alert
     */
    showError(message, container = null) {
        const alertHtml = `
            <div class="alert alert-danger alert-dismissible fade show" role="alert">
                ${this.escapeHtml(message)}
                <button type="button" class="btn-close" data-bs-dismiss="alert"></button>
            </div>
        `;

        if (container) {
            container.insertAdjacentHTML('afterbegin', alertHtml);
        } else {
            // Find the main container or create one
            let mainContainer = document.querySelector('main.container');
            if (mainContainer) {
                mainContainer.insertAdjacentHTML('afterbegin', alertHtml);
            }
        }
    },

    /**
     * Show a success message to the user
     * @param {string} message - The success message
     * @param {HTMLElement} container - Optional container for the alert
     */
    showSuccess(message, container = null) {
        const targetContainer = container || document.querySelector('main.container');
        if (!targetContainer) return;

        // Remove any existing success alerts
        targetContainer.querySelectorAll('.alert-success').forEach(alert => alert.remove());

        const alertDiv = document.createElement('div');
        alertDiv.className = 'alert alert-success alert-dismissible fade show';
        alertDiv.setAttribute('role', 'alert');
        alertDiv.innerHTML = `
            ${this.escapeHtml(message)}
            <button type="button" class="btn-close" data-bs-dismiss="alert"></button>
        `;

        targetContainer.insertAdjacentElement('afterbegin', alertDiv);

        // Auto-dismiss after 3 seconds
        setTimeout(() => {
            alertDiv.classList.remove('show');
            setTimeout(() => alertDiv.remove(), 150);
        }, 3000);
    },

    /**
     * Escape HTML to prevent XSS
     * @param {string} text - The text to escape
     * @returns {string} - The escaped text
     */
    escapeHtml(text) {
        const div = document.createElement('div');
        div.textContent = text;
        return div.innerHTML;
    },

    /**
     * Download a file from a URL
     * @param {string} url - The download URL
     * @param {string} filename - Optional filename override
     */
    async download(url, filename = null) {
        try {
            const response = await fetch(url);

            if (!response.ok) {
                // Try to get error message from JSON response
                try {
                    const result = await response.json();
                    throw new Error(result.message || `Download failed: ${response.status}`);
                } catch (e) {
                    if (e.message.includes('Download failed')) throw e;
                    throw new Error(`Download failed: ${response.status}`);
                }
            }

            const blob = await response.blob();

            // Get filename from Content-Disposition header if not provided
            if (!filename) {
                const contentDisposition = response.headers.get('Content-Disposition');
                if (contentDisposition) {
                    const match = contentDisposition.match(/filename="?([^";\n]+)"?/);
                    if (match) {
                        filename = match[1];
                    }
                }
            }

            // Create download link
            const downloadUrl = window.URL.createObjectURL(blob);
            const a = document.createElement('a');
            a.href = downloadUrl;
            a.download = filename || 'download';
            document.body.appendChild(a);
            a.click();
            window.URL.revokeObjectURL(downloadUrl);
            document.body.removeChild(a);
        } catch (error) {
            console.error('Download error:', error);
            throw error;
        }
    }
};

// Make API available globally
window.API = API;
