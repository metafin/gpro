/**
 * Project Editor Controller
 * Manages the project editing interface
 */

// Operation type configuration - defines per-type properties
const OPERATION_CONFIG = {
    drill: {
        storageKey: 'drill_holes',
        label: 'Drill',
        badge: 'bg-primary',
        modalId: 'addDrillModal',
        editable: true,
        reorderable: false,
        hasCompensation: false,
        hasLeadIn: false,
        prefix: 'drill',
        hasGrid: true
    },
    circle: {
        storageKey: 'circular_cuts',
        label: 'Circle',
        badge: 'bg-info',
        modalId: 'addCircleModal',
        editable: true,
        reorderable: true,
        hasCompensation: true,
        hasLeadIn: true,
        prefix: 'circle',
        sizeField: { name: 'diameter', formName: 'circle_diameter' },
        coordFields: { single: ['center_x', 'center_y'], linear: ['start_center_x', 'start_center_y'] }
    },
    hex: {
        storageKey: 'hexagonal_cuts',
        label: 'Hex',
        badge: 'bg-warning',
        modalId: 'addHexModal',
        editable: true,
        reorderable: true,
        hasCompensation: true,
        hasLeadIn: true,
        prefix: 'hex',
        sizeField: { name: 'flat_to_flat', formName: 'hex_flat_to_flat' },
        coordFields: { single: ['center_x', 'center_y'], linear: ['start_center_x', 'start_center_y'] }
    },
    line: {
        storageKey: 'line_cuts',
        label: 'Line',
        badge: 'bg-success',
        modalId: 'addLineModal',
        editable: true,
        reorderable: true,
        hasCompensation: true,
        hasLeadIn: true,
        prefix: 'line',
        isCustomForm: true  // Line has special form handling (dynamic points)
    }
};

class ProjectEditor {
    constructor(projectId, projectData, materials, tools, machine) {
        this.projectId = projectId;
        this.data = projectData;
        this.materials = materials;
        this.tools = tools;
        this.machine = machine;

        this.unsaved = new UnsavedChanges();
        this.linePointCounter = 0;

        // Track which operation is being edited for each type (null = adding new)
        this.editingIndex = {
            drill: null,
            circle: null,
            hex: null,
            line: null
        };

        // Zoom state
        this.zoomLevel = 1.0;
        this.minZoom = 0.25;
        this.maxZoom = 4.0;
        this.zoomStep = 0.25;

        // Coordinate labels state: 'off', 'feature', or 'toolpath'
        this.coordsMode = 'off';

        this.init();
    }

    init() {
        // Set original data for change tracking
        this.unsaved.setOriginal(this.data);

        // Populate dropdowns
        this.populateMaterials();
        this.populateTools();
        this.updateOperationButtons();
        this.renderOperations();
        this.updateTubeOptionsVisibility();

        // Set initial values for tube options
        document.getElementById('tubeVoidSkip').checked = this.data.tube_void_skip || false;
        document.getElementById('workingLength').value = this.data.working_length || '';
        document.getElementById('tubeOrientation').value = this.data.tube_orientation || 'wide';
    }

    // --- Dropdown Population ---

    populateMaterials() {
        const select = document.getElementById('projectMaterial');
        select.innerHTML = '<option value="">-- Select Material --</option>';

        for (const [id, material] of Object.entries(this.materials)) {
            const option = document.createElement('option');
            option.value = id;
            option.textContent = material.display_name;
            if (id === this.data.material_id) {
                option.selected = true;
            }
            select.appendChild(option);
        }
    }

    populateTools() {
        const select = document.getElementById('projectTool');
        select.innerHTML = '<option value="">-- Select Tool --</option>';

        const toolType = this.data.project_type === 'drill' ? 'drill' : null;
        const currentToolId = this.data.project_type === 'drill'
            ? this.data.drill_tool_id
            : this.data.end_mill_tool_id;

        for (const tool of this.tools) {
            // Filter by type
            if (this.data.project_type === 'drill') {
                if (tool.tool_type !== 'drill') continue;
            } else {
                if (tool.tool_type === 'drill') continue;
            }

            const option = document.createElement('option');
            option.value = tool.id;
            option.textContent = `${tool.size}" ${tool.description || tool.tool_type.replace(/_/g, ' ')}`;
            if (tool.id === currentToolId) {
                option.selected = true;
            }
            select.appendChild(option);
        }
    }

    updateOperationButtons() {
        const container = document.getElementById('operationButtons');

        if (this.data.project_type === 'drill') {
            container.innerHTML = `
                <button type="button" class="btn btn-sm btn-primary" data-bs-toggle="modal" data-bs-target="#addDrillModal">
                    <i class="bi bi-plus"></i> Drill
                </button>
            `;
        } else {
            container.innerHTML = `
                <div class="btn-group btn-group-sm">
                    <button type="button" class="btn btn-info" data-bs-toggle="modal" data-bs-target="#addCircleModal">
                        <i class="bi bi-circle"></i> Circle
                    </button>
                    <button type="button" class="btn btn-warning" data-bs-toggle="modal" data-bs-target="#addHexModal">
                        <i class="bi bi-hexagon"></i> Hex
                    </button>
                    <button type="button" class="btn btn-success" data-bs-toggle="modal" data-bs-target="#addLineModal">
                        <i class="bi bi-bezier2"></i> Line
                    </button>
                </div>
            `;
        }
    }

    updateTubeOptionsVisibility() {
        const container = document.getElementById('tubeOptionsContainer');
        const material = this.materials[this.data.material_id];

        if (material && material.form === 'tube') {
            container.style.display = 'block';
        } else {
            container.style.display = 'none';
        }
    }

    // --- Field Updates ---

    updateField(field, value) {
        this.data[field] = value;
        this.unsaved.update(this.data);

        if (field === 'name') {
            document.getElementById('projectTitle').textContent = value;
        }

        if (field === 'material_id') {
            this.updateTubeOptionsVisibility();
        }
    }

    updateTool(toolId) {
        const id = toolId ? parseInt(toolId) : null;
        if (this.data.project_type === 'drill') {
            this.data.drill_tool_id = id;
        } else {
            this.data.end_mill_tool_id = id;
        }
        this.unsaved.update(this.data);
    }

    changeType(newType) {
        if (newType === this.data.project_type) return;

        // Check if there are operations
        const ops = this.data.operations || {};
        const hasOps = (ops.drill_holes?.length || 0) +
                       (ops.circular_cuts?.length || 0) +
                       (ops.hexagonal_cuts?.length || 0) +
                       (ops.line_cuts?.length || 0) > 0;

        if (hasOps) {
            if (!confirm('Changing project type will clear all operations. Continue?')) {
                document.getElementById('projectType').value = this.data.project_type;
                return;
            }
        }

        this.data.project_type = newType;
        this.data.operations = {
            drill_holes: [],
            circular_cuts: [],
            hexagonal_cuts: [],
            line_cuts: []
        };

        this.populateTools();
        this.updateOperationButtons();
        this.renderOperations();
        this.unsaved.update(this.data);
    }

    // --- Operations Rendering ---

    renderOperations() {
        const list = document.getElementById('operationsList');
        const noOps = document.getElementById('noOperations');
        const ops = this.data.operations || {};

        let html = '';
        let count = 0;
        let sequenceNum = 1;

        // Drill holes (sequence numbers, but no reordering)
        const drillHoles = ops.drill_holes || [];
        drillHoles.forEach((op, i) => {
            html += this.renderOperationItem('drill', op, i, sequenceNum++, true, true);
            count++;
        });

        // Circular cuts
        const circularCuts = ops.circular_cuts || [];
        circularCuts.forEach((op, i) => {
            const isFirst = i === 0;
            const isLast = i === circularCuts.length - 1;
            html += this.renderOperationItem('circle', op, i, sequenceNum++, isFirst, isLast);
            count++;
        });

        // Hexagonal cuts
        const hexCuts = ops.hexagonal_cuts || [];
        hexCuts.forEach((op, i) => {
            const isFirst = i === 0;
            const isLast = i === hexCuts.length - 1;
            html += this.renderOperationItem('hex', op, i, sequenceNum++, isFirst, isLast);
            count++;
        });

        // Line cuts
        const lineCuts = ops.line_cuts || [];
        lineCuts.forEach((op, i) => {
            const isFirst = i === 0;
            const isLast = i === lineCuts.length - 1;
            html += this.renderOperationItem('line', op, i, sequenceNum++, isFirst, isLast);
            count++;
        });

        list.innerHTML = html;
        noOps.style.display = count === 0 ? 'block' : 'none';
    }

    renderOperationItem(type, operation, index, sequenceNum, isFirst, isLast) {
        const config = OPERATION_CONFIG[type];
        const summary = this.getOperationSummary(type, operation);

        // Edit button - shown if type is editable
        const editButton = config.editable
            ? `<button type="button" class="btn btn-sm btn-outline-secondary me-1" onclick="editor.editOperation('${type}', ${index})" title="Edit">
                    <i class="bi bi-pencil"></i>
                </button>`
            : '';

        // Duplicate button
        const duplicateButton = `<button type="button" class="btn btn-sm btn-outline-secondary me-1" onclick="editor.duplicateOperation('${type}', ${index})" title="Duplicate">
                <i class="bi bi-copy"></i>
            </button>`;

        // Reorder buttons - shown if type is reorderable
        const reorderButtons = config.reorderable ? `
            <button type="button" class="btn btn-sm btn-outline-secondary me-1 ${isFirst ? 'disabled' : ''}"
                    onclick="editor.moveOperation('${type}', ${index}, -1)" ${isFirst ? 'disabled' : ''} title="Move up">
                <i class="bi bi-arrow-up"></i>
            </button>
            <button type="button" class="btn btn-sm btn-outline-secondary me-1 ${isLast ? 'disabled' : ''}"
                    onclick="editor.moveOperation('${type}', ${index}, 1)" ${isLast ? 'disabled' : ''} title="Move down">
                <i class="bi bi-arrow-down"></i>
            </button>
        ` : '';

        return `
            <div class="operation-item">
                <span class="badge bg-secondary me-1">#${sequenceNum}</span>
                <span class="badge ${config.badge}">${config.label}</span>
                <span class="operation-summary">${API.escapeHtml(summary)}</span>
                <div class="operation-actions">
                    ${reorderButtons}
                    ${editButton}
                    ${duplicateButton}
                    <button type="button" class="btn btn-sm btn-outline-danger" onclick="editor.removeOperation('${type}', ${index})" title="Delete">
                        <i class="bi bi-trash"></i>
                    </button>
                </div>
            </div>
        `;
    }

    getOperationSummary(type, op) {
        const comp = op.compensation || 'none';
        const compText = comp === 'none' ? '' : ` [${comp}]`;

        // Lead-in override indicator
        const leadInOverride = op.lead_in_mode === 'manual' ? ' *' : '';

        if (type === 'drill') {
            if (op.type === 'single') {
                return `(${op.x}, ${op.y}): point`;
            } else if (op.type === 'pattern_linear') {
                return `(${op.start_x}, ${op.start_y}): linear, ${op.count} on ${op.axis.toUpperCase()}, ${op.spacing}" spacing`;
            } else if (op.type === 'pattern_grid') {
                return `(${op.start_x}, ${op.start_y}): grid, ${op.x_count}x${op.y_count}, ${op.x_spacing}" x ${op.y_spacing}" spacing`;
            }
        } else if (type === 'circle') {
            if (op.type === 'single') {
                return `${op.diameter}" circle at (${op.center_x}, ${op.center_y})${compText}${leadInOverride}`;
            } else if (op.type === 'pattern_linear') {
                return `${op.count} x ${op.diameter}" circles along ${op.axis.toUpperCase()}${compText}${leadInOverride}`;
            }
        } else if (type === 'hex') {
            if (op.type === 'single') {
                return `${op.flat_to_flat}" hex at (${op.center_x}, ${op.center_y})${compText}${leadInOverride}`;
            } else if (op.type === 'pattern_linear') {
                return `${op.count} x ${op.flat_to_flat}" hexes along ${op.axis.toUpperCase()}${compText}${leadInOverride}`;
            }
        } else if (type === 'line') {
            const pointCount = op.points?.length || 0;
            return `${pointCount} point${pointCount !== 1 ? 's' : ''}${compText}${leadInOverride}`;
        }
        return 'Unknown operation';
    }

    getStorageKey(type) {
        return OPERATION_CONFIG[type].storageKey;
    }

    editOperation(type, index) {
        const config = OPERATION_CONFIG[type];
        const key = this.getStorageKey(type);
        const operation = this.data.operations[key][index];
        if (!operation) return;

        this.editingIndex[type] = index;

        // Line operations have custom form handling
        if (config.isCustomForm) {
            this.editLineOperation(index);
            return;
        }

        // Populate the pattern form with operation data
        this.populatePatternForm(type, operation);

        // Update modal title and button text
        const modal = document.getElementById(config.modalId);
        const title = modal.querySelector('.modal-title');
        const submitBtn = modal.querySelector('button[type="submit"]');
        title.textContent = title.dataset.editTitle || `Edit ${config.label}`;
        submitBtn.textContent = submitBtn.dataset.editText || 'Save Changes';

        // Open the modal
        new bootstrap.Modal(modal).show();
    }

    populatePatternForm(type, operation) {
        const config = OPERATION_CONFIG[type];
        const prefix = config.prefix;

        // Determine pattern type from operation
        let patternType = 'single';
        if (operation.type === 'pattern_linear') {
            patternType = 'linear';
        } else if (operation.type === 'pattern_grid') {
            patternType = 'grid';
        }

        // Get the starting X/Y coordinates regardless of pattern type
        let startX, startY;
        if (config.coordFields) {
            // Circle/hex use center_x/start_center_x
            startX = operation[config.coordFields.single[0]] || operation[config.coordFields.linear[0]] || 0;
            startY = operation[config.coordFields.single[1]] || operation[config.coordFields.linear[1]] || 0;
        } else {
            // Drill uses x/start_x
            startX = operation.x || operation.start_x || 0;
            startY = operation.y || operation.start_y || 0;
        }

        // Populate ALL coordinate fields so switching patterns preserves values
        // Single point fields
        document.querySelector(`[name="${prefix}_x"]`).value = startX;
        document.querySelector(`[name="${prefix}_y"]`).value = startY;
        // Linear pattern fields
        document.querySelector(`[name="${prefix}_start_x"]`).value = startX;
        document.querySelector(`[name="${prefix}_start_y"]`).value = startY;
        // Grid pattern fields (if present)
        const gridStartX = document.querySelector(`[name="${prefix}_grid_start_x"]`);
        const gridStartY = document.querySelector(`[name="${prefix}_grid_start_y"]`);
        if (gridStartX) gridStartX.value = startX;
        if (gridStartY) gridStartY.value = startY;

        // Set pattern type dropdown and show correct fields
        const patternSelect = document.querySelector(`[name="${prefix}_pattern_type"]`);
        patternSelect.value = patternType;
        patternSelect.dataset.prevPattern = patternType;  // Initialize for togglePatternFields
        togglePatternFields(prefix);

        // Populate pattern-specific fields (non-coordinate)
        if (patternType === 'linear') {
            document.querySelector(`[name="${prefix}_axis"]`).value = operation.axis || 'x';
            document.querySelector(`[name="${prefix}_spacing"]`).value = operation.spacing || 0.5;
            document.querySelector(`[name="${prefix}_count"]`).value = operation.count || 1;
        } else if (patternType === 'grid' && config.hasGrid) {
            document.querySelector(`[name="${prefix}_x_spacing"]`).value = operation.x_spacing || 0.5;
            document.querySelector(`[name="${prefix}_y_spacing"]`).value = operation.y_spacing || 0.5;
            document.querySelector(`[name="${prefix}_x_count"]`).value = operation.x_count || 1;
            document.querySelector(`[name="${prefix}_y_count"]`).value = operation.y_count || 1;
        }

        // Populate size field if applicable
        if (config.sizeField) {
            const sizeInput = document.querySelector(`[name="${config.sizeField.formName}"]`);
            if (sizeInput) {
                sizeInput.value = operation[config.sizeField.name] || 0.5;
            }
        }

        // Populate compensation field if applicable
        if (config.hasCompensation) {
            const compSelect = document.getElementById(`${prefix}Compensation`);
            if (compSelect) {
                compSelect.value = operation.compensation || 'none';
            }
        }

        // Populate hold_time field if applicable
        const holdTimeInput = document.getElementById(`${prefix}HoldTime`);
        if (holdTimeInput) {
            holdTimeInput.value = operation.hold_time || 0;
        }

        // Populate lead-in fields if applicable
        if (config.hasLeadIn) {
            const modeSelect = document.getElementById(`${prefix}LeadInMode`);
            const typeSelect = document.getElementById(`${prefix}LeadInType`);
            const angleInput = document.getElementById(`${prefix}LeadInApproachAngle`);

            if (modeSelect) {
                modeSelect.value = operation.lead_in_mode || 'auto';
                toggleLeadInFields(prefix);
            }
            if (typeSelect) {
                typeSelect.value = operation.lead_in_type || (prefix === 'line' ? 'ramp' : 'helical');
            }
            if (angleInput) {
                angleInput.value = operation.lead_in_approach_angle || 90;
            }
        }
    }

    resetOperationModal(type) {
        const config = OPERATION_CONFIG[type];
        const modal = document.getElementById(config.modalId);
        const prefix = config.prefix;

        // Reset editing state
        this.editingIndex[type] = null;

        // Reset modal title and button text
        const title = modal.querySelector('.modal-title');
        const submitBtn = modal.querySelector('button[type="submit"]');
        title.textContent = title.dataset.addTitle || `Add ${config.label}`;
        submitBtn.textContent = submitBtn.dataset.addText || `Add ${config.label}`;

        // Reset pattern type to single and show appropriate fields
        const patternSelect = document.querySelector(`[name="${prefix}_pattern_type"]`);
        if (patternSelect) {
            patternSelect.value = 'single';
            togglePatternFields(prefix);
        }

        // Clear all form inputs
        const form = modal.querySelector('form');
        if (form) {
            const inputs = form.querySelectorAll('input[type="number"]');
            inputs.forEach(input => input.value = '');

            const selects = form.querySelectorAll('select:not([name$="_pattern_type"])');
            selects.forEach(select => {
                if (select.id && select.id.endsWith('Compensation')) {
                    select.value = 'none';
                } else if (select.id && select.id.endsWith('LeadInMode')) {
                    select.value = 'auto';
                } else if (select.id && select.id.endsWith('LeadInType')) {
                    // Default: helical for circles/hexes, ramp for lines
                    select.value = prefix === 'line' ? 'ramp' : 'helical';
                } else {
                    select.selectedIndex = 0;
                }
            });
        }

        // Reset lead-in fields visibility
        if (config.hasLeadIn) {
            toggleLeadInFields(prefix);
            const angleInput = document.getElementById(`${prefix}LeadInApproachAngle`);
            if (angleInput) {
                angleInput.value = 90;
            }
        }

        // Reset hold_time field
        const holdTimeInput = document.getElementById(`${prefix}HoldTime`);
        if (holdTimeInput) {
            holdTimeInput.value = 0;
        }
    }

    removeOperation(type, index) {
        if (!confirm('Remove this operation?')) return;

        const key = this.getStorageKey(type);
        this.data.operations[key].splice(index, 1);
        this.renderOperations();
        this.unsaved.update(this.data);
    }

    moveOperation(type, index, direction) {
        const key = this.getStorageKey(type);

        const array = this.data.operations[key];
        const newIndex = index + direction;

        // Check bounds
        if (newIndex < 0 || newIndex >= array.length) return;

        // Swap elements
        const temp = array[index];
        array[index] = array[newIndex];
        array[newIndex] = temp;

        this.renderOperations();
        this.refreshPreview();
        this.unsaved.update(this.data);
    }

    duplicateOperation(type, index) {
        const key = this.getStorageKey(type);
        const original = this.data.operations[key][index];
        if (!original) return;

        // Deep copy the operation and assign a new ID
        const duplicate = JSON.parse(JSON.stringify(original));
        duplicate.id = this.generateId();

        // Insert after the original
        this.data.operations[key].splice(index + 1, 0, duplicate);

        this.renderOperations();
        this.refreshPreview();
        this.unsaved.update(this.data);
    }

    // --- Add Operations ---

    generateId() {
        return 'op_' + Date.now() + '_' + Math.random().toString(36).substr(2, 9);
    }

    addDrillOperation() {
        const patternType = document.querySelector('[name="drill_pattern_type"]').value;

        let operation;
        if (this.editingIndex.drill !== null) {
            // Editing - preserve existing ID
            operation = this.data.operations.drill_holes[this.editingIndex.drill];
        } else {
            // Adding new
            operation = { id: this.generateId() };
        }

        // Clear old pattern-specific fields before setting new ones
        delete operation.x;
        delete operation.y;
        delete operation.start_x;
        delete operation.start_y;
        delete operation.axis;
        delete operation.spacing;
        delete operation.count;
        delete operation.x_spacing;
        delete operation.y_spacing;
        delete operation.x_count;
        delete operation.y_count;

        if (patternType === 'single') {
            operation.type = 'single';
            operation.x = parseFloat(document.querySelector('[name="drill_x"]').value) || 0;
            operation.y = parseFloat(document.querySelector('[name="drill_y"]').value) || 0;
        } else if (patternType === 'linear') {
            operation.type = 'pattern_linear';
            operation.start_x = parseFloat(document.querySelector('[name="drill_start_x"]').value) || 0;
            operation.start_y = parseFloat(document.querySelector('[name="drill_start_y"]').value) || 0;
            operation.axis = document.querySelector('[name="drill_axis"]').value;
            operation.spacing = parseFloat(document.querySelector('[name="drill_spacing"]').value) || 0.5;
            operation.count = parseInt(document.querySelector('[name="drill_count"]').value) || 1;
        } else if (patternType === 'grid') {
            operation.type = 'pattern_grid';
            operation.start_x = parseFloat(document.querySelector('[name="drill_grid_start_x"]').value) || 0;
            operation.start_y = parseFloat(document.querySelector('[name="drill_grid_start_y"]').value) || 0;
            operation.x_spacing = parseFloat(document.querySelector('[name="drill_x_spacing"]').value) || 0.5;
            operation.y_spacing = parseFloat(document.querySelector('[name="drill_y_spacing"]').value) || 0.5;
            operation.x_count = parseInt(document.querySelector('[name="drill_x_count"]').value) || 1;
            operation.y_count = parseInt(document.querySelector('[name="drill_y_count"]').value) || 1;
        }

        if (this.editingIndex.drill === null) {
            // Adding new operation
            if (!this.data.operations.drill_holes) {
                this.data.operations.drill_holes = [];
            }
            this.data.operations.drill_holes.push(operation);
        }

        this.editingIndex.drill = null;
        this.renderOperations();
        this.unsaved.update(this.data);
        bootstrap.Modal.getInstance(document.getElementById('addDrillModal')).hide();
        this.resetOperationModal('drill');
    }

    addCircleOperation() {
        const patternType = document.querySelector('[name="circle_pattern_type"]').value;
        const diameter = parseFloat(document.querySelector('[name="circle_diameter"]').value) || 0.5;
        const compensation = document.getElementById('circleCompensation')?.value || 'none';
        const holdTime = parseFloat(document.getElementById('circleHoldTime')?.value) || 0;

        // Read lead-in fields
        const leadInMode = document.getElementById('circleLeadInMode')?.value || 'auto';
        const leadInType = document.getElementById('circleLeadInType')?.value || 'helical';
        const leadInApproachAngle = parseFloat(document.getElementById('circleLeadInApproachAngle')?.value) || 90;

        let operation;
        if (this.editingIndex.circle !== null) {
            // Editing - preserve existing ID
            operation = this.data.operations.circular_cuts[this.editingIndex.circle];
            operation.diameter = diameter;
            operation.compensation = compensation;
        } else {
            // Adding new
            operation = { id: this.generateId(), diameter, compensation };
        }

        // Set hold_time
        operation.hold_time = holdTime;

        // Set lead-in fields
        operation.lead_in_mode = leadInMode;
        if (leadInMode === 'manual') {
            operation.lead_in_type = leadInType;
            operation.lead_in_approach_angle = leadInApproachAngle;
        } else {
            // Clean up manual lead-in fields when in auto mode
            delete operation.lead_in_type;
            delete operation.lead_in_approach_angle;
        }

        if (patternType === 'single') {
            operation.type = 'single';
            operation.center_x = parseFloat(document.querySelector('[name="circle_x"]').value) || 0;
            operation.center_y = parseFloat(document.querySelector('[name="circle_y"]').value) || 0;
            // Clean up linear fields if switching pattern type
            delete operation.start_center_x;
            delete operation.start_center_y;
            delete operation.axis;
            delete operation.spacing;
            delete operation.count;
        } else if (patternType === 'linear') {
            operation.type = 'pattern_linear';
            operation.start_center_x = parseFloat(document.querySelector('[name="circle_start_x"]').value) || 0;
            operation.start_center_y = parseFloat(document.querySelector('[name="circle_start_y"]').value) || 0;
            operation.axis = document.querySelector('[name="circle_axis"]').value;
            operation.spacing = parseFloat(document.querySelector('[name="circle_spacing"]').value) || 1;
            operation.count = parseInt(document.querySelector('[name="circle_count"]').value) || 1;
            // Clean up single fields if switching pattern type
            delete operation.center_x;
            delete operation.center_y;
        }

        if (this.editingIndex.circle === null) {
            // Adding new operation
            if (!this.data.operations.circular_cuts) {
                this.data.operations.circular_cuts = [];
            }
            this.data.operations.circular_cuts.push(operation);
        }

        this.editingIndex.circle = null;
        this.renderOperations();
        this.unsaved.update(this.data);
        bootstrap.Modal.getInstance(document.getElementById('addCircleModal')).hide();
        this.resetOperationModal('circle');
    }

    addHexOperation() {
        const patternType = document.querySelector('[name="hex_pattern_type"]').value;
        const flat_to_flat = parseFloat(document.querySelector('[name="hex_flat_to_flat"]').value) || 0.5;
        const compensation = document.getElementById('hexCompensation')?.value || 'none';
        const holdTime = parseFloat(document.getElementById('hexHoldTime')?.value) || 0;

        // Read lead-in fields
        const leadInMode = document.getElementById('hexLeadInMode')?.value || 'auto';
        const leadInType = document.getElementById('hexLeadInType')?.value || 'helical';
        const leadInApproachAngle = parseFloat(document.getElementById('hexLeadInApproachAngle')?.value) || 90;

        let operation;
        if (this.editingIndex.hex !== null) {
            // Editing - preserve existing ID
            operation = this.data.operations.hexagonal_cuts[this.editingIndex.hex];
            operation.flat_to_flat = flat_to_flat;
            operation.compensation = compensation;
        } else {
            // Adding new
            operation = { id: this.generateId(), flat_to_flat, compensation };
        }

        // Set hold_time
        operation.hold_time = holdTime;

        // Set lead-in fields
        operation.lead_in_mode = leadInMode;
        if (leadInMode === 'manual') {
            operation.lead_in_type = leadInType;
            operation.lead_in_approach_angle = leadInApproachAngle;
        } else {
            // Clean up manual lead-in fields when in auto mode
            delete operation.lead_in_type;
            delete operation.lead_in_approach_angle;
        }

        if (patternType === 'single') {
            operation.type = 'single';
            operation.center_x = parseFloat(document.querySelector('[name="hex_x"]').value) || 0;
            operation.center_y = parseFloat(document.querySelector('[name="hex_y"]').value) || 0;
            // Clean up linear fields if switching pattern type
            delete operation.start_center_x;
            delete operation.start_center_y;
            delete operation.axis;
            delete operation.spacing;
            delete operation.count;
        } else if (patternType === 'linear') {
            operation.type = 'pattern_linear';
            operation.start_center_x = parseFloat(document.querySelector('[name="hex_start_x"]').value) || 0;
            operation.start_center_y = parseFloat(document.querySelector('[name="hex_start_y"]').value) || 0;
            operation.axis = document.querySelector('[name="hex_axis"]').value;
            operation.spacing = parseFloat(document.querySelector('[name="hex_spacing"]').value) || 1;
            operation.count = parseInt(document.querySelector('[name="hex_count"]').value) || 1;
            // Clean up single fields if switching pattern type
            delete operation.center_x;
            delete operation.center_y;
        }

        if (this.editingIndex.hex === null) {
            // Adding new operation
            if (!this.data.operations.hexagonal_cuts) {
                this.data.operations.hexagonal_cuts = [];
            }
            this.data.operations.hexagonal_cuts.push(operation);
        }

        this.editingIndex.hex = null;
        this.renderOperations();
        this.unsaved.update(this.data);
        bootstrap.Modal.getInstance(document.getElementById('addHexModal')).hide();
        this.resetOperationModal('hex');
    }

    addLinePoint() {
        const container = document.getElementById('linePointsList');
        const index = this.linePointCounter++;
        const isFirst = container.children.length === 0;

        const html = `
            <div class="line-point-container mb-2" id="linePoint_${index}">
                <div class="row g-2 align-items-end">
                    <div class="col-3">
                        <label class="form-label small">X</label>
                        <input type="number" class="form-control form-control-sm" name="line_point_x_${index}" step="0.001" placeholder="0.000">
                    </div>
                    <div class="col-3">
                        <label class="form-label small">Y</label>
                        <input type="number" class="form-control form-control-sm" name="line_point_y_${index}" step="0.001" placeholder="0.000">
                    </div>
                    <div class="col-3">
                        <label class="form-label small">Type</label>
                        <select class="form-select form-select-sm" name="line_point_type_${index}" onchange="editor.toggleArcFields(${index})">
                            ${isFirst ? '<option value="start">Start</option>' : '<option value="straight">Straight</option>'}
                            ${!isFirst ? '<option value="arc">Arc</option>' : ''}
                        </select>
                    </div>
                    <div class="col-auto d-flex align-items-end gap-1">
                        <button type="button" class="btn btn-sm btn-outline-secondary" onclick="editor.moveLinePoint(${index}, -1)" title="Move up">
                            <i class="bi bi-arrow-up"></i>
                        </button>
                        <button type="button" class="btn btn-sm btn-outline-secondary" onclick="editor.moveLinePoint(${index}, 1)" title="Move down">
                            <i class="bi bi-arrow-down"></i>
                        </button>
                        <button type="button" class="btn btn-sm btn-outline-danger" onclick="editor.removeLinePoint(${index})">
                            <i class="bi bi-x"></i>
                        </button>
                    </div>
                </div>
                <div class="row g-2 mt-1 px-2 pb-2 pt-1 rounded arc-fields-${index}" style="display: none; background-color: #f0f0f0;">
                    <div class="col-3">
                        <label class="form-label small text-muted mb-0">Arc Center X</label>
                        <input type="number" class="form-control form-control-sm" name="line_point_arc_x_${index}" step="0.001">
                    </div>
                    <div class="col-3">
                        <label class="form-label small text-muted mb-0">Arc Center Y</label>
                        <input type="number" class="form-control form-control-sm" name="line_point_arc_y_${index}" step="0.001">
                    </div>
                    <div class="col-3">
                        <label class="form-label small text-muted mb-0">Direction</label>
                        <select class="form-select form-select-sm" name="line_point_arc_dir_${index}">
                            <option value="">Auto</option>
                            <option value="cw">CW (G02)</option>
                            <option value="ccw">CCW (G03)</option>
                        </select>
                    </div>
                </div>
            </div>
        `;

        container.insertAdjacentHTML('beforeend', html);
        this.updateLinePointButtons();
    }

    toggleArcFields(index) {
        const type = document.querySelector(`[name="line_point_type_${index}"]`).value;
        const arcRow = document.querySelector(`.arc-fields-${index}`);
        if (arcRow) {
            arcRow.style.display = type === 'arc' ? 'flex' : 'none';
        }
    }

    removeLinePoint(index) {
        const element = document.getElementById(`linePoint_${index}`);
        if (element) {
            element.remove();
            this.updateLinePointButtons();
        }
    }

    moveLinePoint(index, direction) {
        const container = document.getElementById('linePointsList');
        const pointDivs = Array.from(container.querySelectorAll('[id^="linePoint_"]'));
        const currentElement = document.getElementById(`linePoint_${index}`);

        if (!currentElement) return;

        const currentIndex = pointDivs.indexOf(currentElement);
        const targetIndex = currentIndex + direction;

        // Check bounds
        if (targetIndex < 0 || targetIndex >= pointDivs.length) return;

        const targetElement = pointDivs[targetIndex];

        // Swap DOM positions
        if (direction === -1) {
            // Moving up: insert current before target
            container.insertBefore(currentElement, targetElement);
        } else {
            // Moving down: insert current after target
            if (targetElement.nextSibling) {
                container.insertBefore(currentElement, targetElement.nextSibling);
            } else {
                container.appendChild(currentElement);
            }
        }

        // Update the first point's type selector to "Start" and others to "Straight/Arc"
        this.updateLinePointTypes();
        this.updateLinePointButtons();
    }

    updateLinePointTypes() {
        const container = document.getElementById('linePointsList');
        const pointDivs = Array.from(container.querySelectorAll('[id^="linePoint_"]'));

        pointDivs.forEach((div, i) => {
            const pointIndex = div.id.split('_')[1];
            const typeSelect = document.querySelector(`[name="line_point_type_${pointIndex}"]`);
            if (!typeSelect) return;

            const currentValue = typeSelect.value;

            if (i === 0) {
                // First point must be "Start"
                typeSelect.innerHTML = '<option value="start">Start</option>';
                typeSelect.value = 'start';
                // Hide arc fields for first point
                const arcRow = document.querySelector(`.arc-fields-${pointIndex}`);
                if (arcRow) arcRow.style.display = 'none';
            } else {
                // Other points can be Straight or Arc
                if (typeSelect.querySelector('option[value="start"]')) {
                    // This was a start point, convert to straight/arc options
                    typeSelect.innerHTML = `
                        <option value="straight">Straight</option>
                        <option value="arc">Arc</option>
                    `;
                    // Preserve arc selection if it was arc, otherwise default to straight
                    typeSelect.value = currentValue === 'arc' ? 'arc' : 'straight';
                }
                this.toggleArcFields(parseInt(pointIndex));
            }
        });
    }

    updateLinePointButtons() {
        const container = document.getElementById('linePointsList');
        const pointDivs = Array.from(container.querySelectorAll('[id^="linePoint_"]'));
        const count = pointDivs.length;

        pointDivs.forEach((div, i) => {
            const upBtn = div.querySelector('button[title="Move up"]');
            const downBtn = div.querySelector('button[title="Move down"]');

            if (upBtn) {
                upBtn.disabled = i === 0;
                upBtn.classList.toggle('disabled', i === 0);
            }
            if (downBtn) {
                downBtn.disabled = i === count - 1;
                downBtn.classList.toggle('disabled', i === count - 1);
            }
        });
    }

    addLineOperation() {
        const container = document.getElementById('linePointsList');
        const pointDivs = container.querySelectorAll('[id^="linePoint_"]');
        const points = [];

        pointDivs.forEach(div => {
            const index = div.id.split('_')[1];
            const x = parseFloat(document.querySelector(`[name="line_point_x_${index}"]`).value) || 0;
            const y = parseFloat(document.querySelector(`[name="line_point_y_${index}"]`).value) || 0;
            const lineType = document.querySelector(`[name="line_point_type_${index}"]`).value;

            const point = { x, y, line_type: lineType };

            if (lineType === 'arc') {
                point.arc_center_x = parseFloat(document.querySelector(`[name="line_point_arc_x_${index}"]`).value) || 0;
                point.arc_center_y = parseFloat(document.querySelector(`[name="line_point_arc_y_${index}"]`).value) || 0;
                const arcDir = document.querySelector(`[name="line_point_arc_dir_${index}"]`).value;
                if (arcDir) {
                    point.arc_direction = arcDir;
                }
            }

            points.push(point);
        });

        if (points.length < 2) {
            alert('Line cut needs at least 2 points');
            return;
        }

        // Read lead-in fields
        const leadInMode = document.getElementById('lineLeadInMode')?.value || 'auto';
        const leadInType = document.getElementById('lineLeadInType')?.value || 'ramp';
        const leadInApproachAngle = parseFloat(document.getElementById('lineLeadInApproachAngle')?.value) || 90;
        const holdTime = parseFloat(document.getElementById('lineHoldTime')?.value) || 0;

        if (this.editingIndex.line !== null) {
            // Update existing operation
            const existing = this.data.operations.line_cuts[this.editingIndex.line];
            existing.points = points;
            existing.compensation = document.getElementById('lineCompensation').value;
            existing.hold_time = holdTime;
            existing.lead_in_mode = leadInMode;
            if (leadInMode === 'manual') {
                existing.lead_in_type = leadInType;
                existing.lead_in_approach_angle = leadInApproachAngle;
            } else {
                delete existing.lead_in_type;
                delete existing.lead_in_approach_angle;
            }
        } else {
            // Add new operation
            const operation = {
                id: this.generateId(),
                points: points,
                compensation: document.getElementById('lineCompensation').value,
                hold_time: holdTime,
                lead_in_mode: leadInMode
            };
            if (leadInMode === 'manual') {
                operation.lead_in_type = leadInType;
                operation.lead_in_approach_angle = leadInApproachAngle;
            }

            if (!this.data.operations.line_cuts) {
                this.data.operations.line_cuts = [];
            }
            this.data.operations.line_cuts.push(operation);
        }

        this.renderOperations();
        this.unsaved.update(this.data);

        // Clear line points and reset form
        container.innerHTML = '';
        this.linePointCounter = 0;
        this.editingIndex.line = null;
        document.getElementById('lineCompensation').value = 'none';

        bootstrap.Modal.getInstance(document.getElementById('addLineModal')).hide();
        this.resetLineModalTitle();
    }

    editLineOperation(index) {
        const operation = this.data.operations.line_cuts[index];
        if (!operation) return;

        this.editingIndex.line = index;

        // Clear existing points in modal
        const container = document.getElementById('linePointsList');
        container.innerHTML = '';
        this.linePointCounter = 0;

        // Add points using existing function, then populate values
        operation.points.forEach((point, i) => {
            this.addLinePoint();
            const pointIndex = this.linePointCounter - 1;

            // Fill in the values
            document.querySelector(`[name="line_point_x_${pointIndex}"]`).value = point.x;
            document.querySelector(`[name="line_point_y_${pointIndex}"]`).value = point.y;

            // Set type (if not first point)
            const typeSelect = document.querySelector(`[name="line_point_type_${pointIndex}"]`);
            if (i > 0 && point.line_type) {
                typeSelect.value = point.line_type;
                this.toggleArcFields(pointIndex);
            }

            // Fill arc center and direction if it's an arc
            if (point.line_type === 'arc') {
                document.querySelector(`[name="line_point_arc_x_${pointIndex}"]`).value = point.arc_center_x || '';
                document.querySelector(`[name="line_point_arc_y_${pointIndex}"]`).value = point.arc_center_y || '';
                document.querySelector(`[name="line_point_arc_dir_${pointIndex}"]`).value = point.arc_direction || '';
            }
        });

        // Set compensation value
        document.getElementById('lineCompensation').value = operation.compensation || 'none';

        // Set hold_time value
        document.getElementById('lineHoldTime').value = operation.hold_time || 0;

        // Set lead-in values
        const modeSelect = document.getElementById('lineLeadInMode');
        const typeSelect = document.getElementById('lineLeadInType');
        const angleInput = document.getElementById('lineLeadInApproachAngle');

        if (modeSelect) {
            modeSelect.value = operation.lead_in_mode || 'auto';
            toggleLeadInFields('line');
        }
        if (typeSelect) {
            typeSelect.value = operation.lead_in_type || 'ramp';
        }
        if (angleInput) {
            angleInput.value = operation.lead_in_approach_angle || 90;
        }

        // Update modal title and button
        document.querySelector('#addLineModal .modal-title').textContent = 'Edit Line Cut';
        document.querySelector('#addLineModal button[type="submit"]').textContent = 'Save Changes';

        // Open modal
        new bootstrap.Modal(document.getElementById('addLineModal')).show();
    }

    resetLineModalTitle() {
        this.editingIndex.line = null;
        document.querySelector('#addLineModal .modal-title').textContent = 'Add Line Cut';
        document.querySelector('#addLineModal button[type="submit"]').textContent = 'Add Line Cut';

        // Clear line points
        const container = document.getElementById('linePointsList');
        container.innerHTML = '';
        this.linePointCounter = 0;
        document.getElementById('lineCompensation').value = 'none';
        document.getElementById('lineHoldTime').value = 0;

        // Reset lead-in fields
        const modeSelect = document.getElementById('lineLeadInMode');
        const typeSelect = document.getElementById('lineLeadInType');
        const angleInput = document.getElementById('lineLeadInApproachAngle');

        if (modeSelect) {
            modeSelect.value = 'auto';
            toggleLeadInFields('line');
        }
        if (typeSelect) {
            typeSelect.value = 'ramp';
        }
        if (angleInput) {
            angleInput.value = 90;
        }
    }

    // --- Save / Discard ---

    async save() {
        try {
            const result = await API.post(`/api/projects/${this.projectId}/save`, this.data);
            if (result.status === 'ok') {
                this.data.modified_at = result.data.modified_at;
                this.unsaved.markSaved(this.data);
                API.showSuccess('Project saved');
            }
        } catch (error) {
            API.showError('Failed to save: ' + error.message);
        }
    }

    discard() {
        if (!confirm('Discard all unsaved changes?')) return;

        this.data = this.unsaved.discard();
        document.getElementById('projectName').value = this.data.name;
        document.getElementById('projectType').value = this.data.project_type;
        document.getElementById('tubeVoidSkip').checked = this.data.tube_void_skip || false;
        document.getElementById('workingLength').value = this.data.working_length || '';
        document.getElementById('tubeOrientation').value = this.data.tube_orientation || 'wide';

        this.populateMaterials();
        this.populateTools();
        this.updateOperationButtons();
        this.renderOperations();
        this.updateTubeOptionsVisibility();
    }

    // --- Preview ---

    async refreshPreview() {
        const container = document.getElementById('previewContainer');
        container.innerHTML = '<div class="text-center py-4"><div class="spinner-border text-primary"></div><p class="mt-2">Generating preview...</p></div>';

        try {
            const result = await API.post(`/api/projects/${this.projectId}/preview`, {
                operations: this.data.operations,
                coords_mode: this.coordsMode
            });

            if (result.status === 'ok' && result.data?.svg) {
                container.innerHTML = result.data.svg;
            } else if (result.svg) {
                container.innerHTML = result.svg;
            } else {
                container.innerHTML = '<span class="text-muted">No preview available</span>';
            }

            // Apply current zoom level after loading new SVG
            this.applyZoom();
        } catch (error) {
            container.innerHTML = `<span class="text-danger"><i class="bi bi-exclamation-triangle"></i> ${API.escapeHtml(error.message)}</span>`;
        }

        // Also validate
        this.validate();
    }

    // --- Zoom Controls ---

    zoomIn() {
        this.setZoom(this.zoomLevel + this.zoomStep);
    }

    zoomOut() {
        this.setZoom(this.zoomLevel - this.zoomStep);
    }

    resetZoom() {
        this.setZoom(1.0);
    }

    setZoom(level) {
        // Clamp to min/max
        this.zoomLevel = Math.max(this.minZoom, Math.min(this.maxZoom, level));
        this.applyZoom();
        this.updateZoomDisplay();
    }

    applyZoom() {
        const container = document.getElementById('previewContainer');
        const svg = container.querySelector('svg');
        if (!svg) return;

        // Get original dimensions from SVG attributes
        const originalWidth = parseFloat(svg.getAttribute('width'));
        const originalHeight = parseFloat(svg.getAttribute('height'));
        if (!originalWidth || !originalHeight) return;

        // Ensure SVG is wrapped in a zoom wrapper div
        let wrapper = container.querySelector('.svg-zoom-wrapper');
        if (!wrapper) {
            wrapper = document.createElement('div');
            wrapper.className = 'svg-zoom-wrapper';
            svg.parentNode.insertBefore(wrapper, svg);
            wrapper.appendChild(svg);
        }

        // Set wrapper size to accommodate zoomed SVG (this enables scrolling)
        wrapper.style.width = `${originalWidth * this.zoomLevel}px`;
        wrapper.style.height = `${originalHeight * this.zoomLevel}px`;

        // Apply CSS transform to SVG for visual scaling
        svg.style.transform = `scale(${this.zoomLevel})`;
        svg.style.transformOrigin = 'top left';
    }

    updateZoomDisplay() {
        const btn = document.getElementById('zoomLevelBtn');
        if (btn) {
            btn.textContent = `${Math.round(this.zoomLevel * 100)}%`;
        }
    }

    handleZoomWheel(event) {
        // Only zoom on Ctrl+wheel or Cmd+wheel (Mac)
        if (event.ctrlKey || event.metaKey) {
            event.preventDefault();
            if (event.deltaY < 0) {
                this.zoomIn();
            } else {
                this.zoomOut();
            }
        }
    }

    // --- Coordinate Labels Mode ---

    setCoordsMode(mode) {
        this.coordsMode = mode;
        this.refreshPreview();
    }

    async validate() {
        const container = document.getElementById('validationResults');

        try {
            const result = await API.post(`/api/projects/${this.projectId}/validate`);
            Validation.displayErrors(result.errors || [], container);
        } catch (error) {
            container.innerHTML = `<span class="text-danger">${API.escapeHtml(error.message)}</span>`;
        }
    }

    // --- Download ---

    async download() {
        // Check for unsaved changes
        if (this.unsaved.hasChanges()) {
            if (!confirm('Save changes before downloading?')) return;
            await this.save();
        }

        // Validate first
        try {
            const result = await API.post(`/api/projects/${this.projectId}/validate`);
            if (!result.valid) {
                alert('Please fix validation errors before downloading:\n\n' + result.errors.join('\n'));
                return;
            }
        } catch (error) {
            API.showError('Validation failed: ' + error.message);
            return;
        }

        // Download
        try {
            await API.download(`/api/projects/${this.projectId}/download`);
        } catch (error) {
            API.showError('Download failed: ' + error.message);
        }
    }
}

// Initialize editor when page loads
let editor;
document.addEventListener('DOMContentLoaded', () => {
    editor = new ProjectEditor(PROJECT_ID, PROJECT_DATA, MATERIALS, TOOLS, MACHINE);

    // Add modal reset handlers for when modals are closed without saving
    ['drill', 'circle', 'hex'].forEach(type => {
        const config = OPERATION_CONFIG[type];
        const modal = document.getElementById(config.modalId);
        if (modal) {
            modal.addEventListener('hidden.bs.modal', () => {
                editor.resetOperationModal(type);
            });
        }
    });

    // Line modal has special reset handling
    const lineModal = document.getElementById('addLineModal');
    if (lineModal) {
        lineModal.addEventListener('hidden.bs.modal', () => {
            editor.resetLineModalTitle();
        });
    }
});
