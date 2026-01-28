/**
 * Unsaved Changes Tracker
 * Tracks dirty state and warns before navigation
 */

class UnsavedChanges {
    constructor() {
        this.originalData = null;
        this.currentData = null;
        this.isDirty = false;
        this.indicator = document.getElementById('unsavedIndicator');

        // Warn before leaving page with unsaved changes
        window.addEventListener('beforeunload', (e) => {
            if (this.isDirty) {
                e.preventDefault();
                e.returnValue = '';
                return '';
            }
        });
    }

    /**
     * Set the original data snapshot
     * @param {object} data - The original data
     */
    setOriginal(data) {
        this.originalData = JSON.stringify(data);
        this.currentData = this.originalData;
        this.isDirty = false;
        this.updateIndicator();
    }

    /**
     * Update current data and check for changes
     * @param {object} data - The current data
     */
    update(data) {
        this.currentData = JSON.stringify(data);
        this.isDirty = this.currentData !== this.originalData;
        this.updateIndicator();
    }

    /**
     * Mark as saved (reset dirty state)
     * @param {object} data - The saved data
     */
    markSaved(data) {
        this.originalData = JSON.stringify(data);
        this.currentData = this.originalData;
        this.isDirty = false;
        this.updateIndicator();
    }

    /**
     * Discard changes and revert to original
     * @returns {object} - The original data
     */
    discard() {
        this.currentData = this.originalData;
        this.isDirty = false;
        this.updateIndicator();
        return JSON.parse(this.originalData);
    }

    /**
     * Update the unsaved indicator visibility
     */
    updateIndicator() {
        if (this.indicator) {
            this.indicator.style.display = this.isDirty ? 'block' : 'none';
        }
    }

    /**
     * Check if there are unsaved changes
     * @returns {boolean}
     */
    hasChanges() {
        return this.isDirty;
    }
}

// Make available globally
window.UnsavedChanges = UnsavedChanges;
