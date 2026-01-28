/**
 * Validation utilities for GPRO
 * Provides coordinate and parameter validation
 */

const Validation = {
    /**
     * Check if a value is a valid coordinate within machine bounds
     * @param {number} value - The coordinate value
     * @param {number} max - The maximum allowed value
     * @returns {boolean} - True if valid
     */
    isValidCoordinate(value, max) {
        const num = parseFloat(value);
        return !isNaN(num) && num >= 0 && num <= max;
    },

    /**
     * Check if a value is a positive number
     * @param {number} value - The value to check
     * @returns {boolean} - True if positive number
     */
    isPositiveNumber(value) {
        const num = parseFloat(value);
        return !isNaN(num) && num > 0;
    },

    /**
     * Check if a value is a non-negative number
     * @param {number} value - The value to check
     * @returns {boolean} - True if non-negative number
     */
    isNonNegativeNumber(value) {
        const num = parseFloat(value);
        return !isNaN(num) && num >= 0;
    },

    /**
     * Check if a value is a positive integer
     * @param {number} value - The value to check
     * @returns {boolean} - True if positive integer
     */
    isPositiveInteger(value) {
        const num = parseInt(value, 10);
        return !isNaN(num) && num > 0 && num === parseFloat(value);
    },

    /**
     * Validate a drill operation
     * @param {object} operation - The drill operation
     * @param {object} machine - Machine settings with max_x and max_y
     * @returns {string[]} - Array of error messages
     */
    validateDrillOperation(operation, machine) {
        const errors = [];

        if (operation.type === 'single') {
            if (!this.isValidCoordinate(operation.x, machine.max_x)) {
                errors.push(`X coordinate must be between 0 and ${machine.max_x}`);
            }
            if (!this.isValidCoordinate(operation.y, machine.max_y)) {
                errors.push(`Y coordinate must be between 0 and ${machine.max_y}`);
            }
        } else if (operation.type === 'pattern_linear') {
            if (!this.isValidCoordinate(operation.start_x, machine.max_x)) {
                errors.push(`Start X must be between 0 and ${machine.max_x}`);
            }
            if (!this.isValidCoordinate(operation.start_y, machine.max_y)) {
                errors.push(`Start Y must be between 0 and ${machine.max_y}`);
            }
            if (!this.isPositiveNumber(operation.spacing)) {
                errors.push('Spacing must be a positive number');
            }
            if (!this.isPositiveInteger(operation.count)) {
                errors.push('Count must be a positive integer');
            }
        } else if (operation.type === 'pattern_grid') {
            if (!this.isValidCoordinate(operation.start_x, machine.max_x)) {
                errors.push(`Start X must be between 0 and ${machine.max_x}`);
            }
            if (!this.isValidCoordinate(operation.start_y, machine.max_y)) {
                errors.push(`Start Y must be between 0 and ${machine.max_y}`);
            }
            if (!this.isPositiveNumber(operation.x_spacing)) {
                errors.push('X spacing must be a positive number');
            }
            if (!this.isPositiveNumber(operation.y_spacing)) {
                errors.push('Y spacing must be a positive number');
            }
            if (!this.isPositiveInteger(operation.x_count)) {
                errors.push('X count must be a positive integer');
            }
            if (!this.isPositiveInteger(operation.y_count)) {
                errors.push('Y count must be a positive integer');
            }
        }

        return errors;
    },

    /**
     * Validate a circular cut operation
     * @param {object} operation - The circle operation
     * @param {object} machine - Machine settings
     * @returns {string[]} - Array of error messages
     */
    validateCircleOperation(operation, machine) {
        const errors = [];

        if (operation.type === 'single') {
            if (!this.isValidCoordinate(operation.center_x, machine.max_x)) {
                errors.push(`Center X must be between 0 and ${machine.max_x}`);
            }
            if (!this.isValidCoordinate(operation.center_y, machine.max_y)) {
                errors.push(`Center Y must be between 0 and ${machine.max_y}`);
            }
            if (!this.isPositiveNumber(operation.diameter)) {
                errors.push('Diameter must be a positive number');
            }
        } else if (operation.type === 'pattern_linear') {
            if (!this.isValidCoordinate(operation.start_center_x, machine.max_x)) {
                errors.push(`Start center X must be between 0 and ${machine.max_x}`);
            }
            if (!this.isValidCoordinate(operation.start_center_y, machine.max_y)) {
                errors.push(`Start center Y must be between 0 and ${machine.max_y}`);
            }
            if (!this.isPositiveNumber(operation.diameter)) {
                errors.push('Diameter must be a positive number');
            }
            if (!this.isPositiveNumber(operation.spacing)) {
                errors.push('Spacing must be a positive number');
            }
            if (!this.isPositiveInteger(operation.count)) {
                errors.push('Count must be a positive integer');
            }
        }

        return errors;
    },

    /**
     * Validate a hexagonal cut operation
     * @param {object} operation - The hex operation
     * @param {object} machine - Machine settings
     * @returns {string[]} - Array of error messages
     */
    validateHexOperation(operation, machine) {
        const errors = [];

        if (operation.type === 'single') {
            if (!this.isValidCoordinate(operation.center_x, machine.max_x)) {
                errors.push(`Center X must be between 0 and ${machine.max_x}`);
            }
            if (!this.isValidCoordinate(operation.center_y, machine.max_y)) {
                errors.push(`Center Y must be between 0 and ${machine.max_y}`);
            }
            if (!this.isPositiveNumber(operation.flat_to_flat)) {
                errors.push('Flat-to-flat must be a positive number');
            }
        } else if (operation.type === 'pattern_linear') {
            if (!this.isValidCoordinate(operation.start_center_x, machine.max_x)) {
                errors.push(`Start center X must be between 0 and ${machine.max_x}`);
            }
            if (!this.isValidCoordinate(operation.start_center_y, machine.max_y)) {
                errors.push(`Start center Y must be between 0 and ${machine.max_y}`);
            }
            if (!this.isPositiveNumber(operation.flat_to_flat)) {
                errors.push('Flat-to-flat must be a positive number');
            }
            if (!this.isPositiveNumber(operation.spacing)) {
                errors.push('Spacing must be a positive number');
            }
            if (!this.isPositiveInteger(operation.count)) {
                errors.push('Count must be a positive integer');
            }
        }

        return errors;
    },

    /**
     * Validate a line cut operation
     * @param {object} operation - The line operation
     * @param {object} machine - Machine settings
     * @returns {string[]} - Array of error messages
     */
    validateLineOperation(operation, machine) {
        const errors = [];
        const points = operation.points || [];

        if (points.length < 2) {
            errors.push('Line cut must have at least 2 points');
        }

        points.forEach((point, index) => {
            if (!this.isValidCoordinate(point.x, machine.max_x)) {
                errors.push(`Point ${index + 1}: X must be between 0 and ${machine.max_x}`);
            }
            if (!this.isValidCoordinate(point.y, machine.max_y)) {
                errors.push(`Point ${index + 1}: Y must be between 0 and ${machine.max_y}`);
            }
            if (point.line_type === 'arc') {
                if (!this.isValidCoordinate(point.arc_center_x, machine.max_x)) {
                    errors.push(`Point ${index + 1}: Arc center X must be between 0 and ${machine.max_x}`);
                }
                if (!this.isValidCoordinate(point.arc_center_y, machine.max_y)) {
                    errors.push(`Point ${index + 1}: Arc center Y must be between 0 and ${machine.max_y}`);
                }
            }
        });

        return errors;
    },

    /**
     * Validate an entire project
     * @param {object} project - The project data
     * @param {object} machine - Machine settings
     * @returns {string[]} - Array of error messages
     */
    validateProject(project, machine) {
        const errors = [];

        // Required fields
        if (!project.name || project.name.trim() === '') {
            errors.push('Project name is required');
        }

        if (!project.material_id) {
            errors.push('Material must be selected');
        }

        if (project.project_type === 'drill' && !project.drill_tool_id) {
            errors.push('Drill tool must be selected');
        }

        if (project.project_type === 'cut' && !project.end_mill_tool_id) {
            errors.push('End mill tool must be selected');
        }

        // Check for operations
        const ops = project.operations || {};
        let hasOperations = false;

        if (project.project_type === 'drill') {
            if (ops.drill_holes && ops.drill_holes.length > 0) {
                hasOperations = true;
                ops.drill_holes.forEach((op, i) => {
                    const opErrors = this.validateDrillOperation(op, machine);
                    opErrors.forEach(e => errors.push(`Drill ${i + 1}: ${e}`));
                });
            }
        } else {
            if (ops.circular_cuts && ops.circular_cuts.length > 0) {
                hasOperations = true;
                ops.circular_cuts.forEach((op, i) => {
                    const opErrors = this.validateCircleOperation(op, machine);
                    opErrors.forEach(e => errors.push(`Circle ${i + 1}: ${e}`));
                });
            }
            if (ops.hexagonal_cuts && ops.hexagonal_cuts.length > 0) {
                hasOperations = true;
                ops.hexagonal_cuts.forEach((op, i) => {
                    const opErrors = this.validateHexOperation(op, machine);
                    opErrors.forEach(e => errors.push(`Hex ${i + 1}: ${e}`));
                });
            }
            if (ops.line_cuts && ops.line_cuts.length > 0) {
                hasOperations = true;
                ops.line_cuts.forEach((op, i) => {
                    const opErrors = this.validateLineOperation(op, machine);
                    opErrors.forEach(e => errors.push(`Line ${i + 1}: ${e}`));
                });
            }
        }

        if (!hasOperations) {
            errors.push('Project must have at least one operation');
        }

        return errors;
    },

    /**
     * Display validation errors in a container
     * @param {string[]} errors - Array of error messages
     * @param {HTMLElement} container - Container element to display errors
     */
    displayErrors(errors, container) {
        container.innerHTML = '';

        if (errors.length === 0) {
            container.innerHTML = '<div class="text-success"><i class="bi bi-check-circle"></i> All validations passed</div>';
            return;
        }

        const list = document.createElement('ul');
        list.className = 'list-unstyled text-danger mb-0';

        errors.forEach(error => {
            const li = document.createElement('li');
            li.innerHTML = `<i class="bi bi-exclamation-triangle"></i> ${API.escapeHtml(error)}`;
            list.appendChild(li);
        });

        container.appendChild(list);
    }
};

// Make Validation available globally
window.Validation = Validation;
