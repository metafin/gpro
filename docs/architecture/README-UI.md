# UI Architecture

This document describes the frontend architecture of GPRO, covering templates, JavaScript modules, and styling.

## Overview

GPRO uses a server-rendered frontend with Jinja2 templates and vanilla JavaScript for interactivity. The stack:

- **Templates**: Jinja2 with template inheritance
- **Styling**: Bootstrap 5 with custom CSS overrides
- **JavaScript**: Vanilla JS, no framework
- **AJAX**: Fetch API for API communication

## File Structure

```
├── templates/
│   ├── base.html               # Master template
│   ├── login.html              # Authentication
│   ├── index.html              # Projects dashboard
│   ├── partials/               # Reusable components
│   │   ├── coord_input.html    # X/Y coordinate input
│   │   ├── pattern_fields.html # Pattern type fields
│   │   ├── modal_footer.html   # Modal buttons
│   │   └── lead_in_fields.html # Lead-in settings fields
│   ├── project/
│   │   ├── new.html            # New project form
│   │   └── edit.html           # Project editor (main workspace)
│   └── settings/
│       ├── index.html          # Settings dashboard (links to all settings pages)
│       ├── tools.html          # Tool management
│       ├── materials.html      # Material list
│       ├── material_edit.html  # Material editor
│       ├── machine.html        # Machine settings
│       └── general.html        # General settings (safety/travel heights, warmup)
│
└── static/
    ├── css/
    │   └── styles.css          # Custom styles
    ├── fonts/
    │   └── gpro-brand.ttf      # Logo font
    └── js/
        ├── api.js              # API utilities
        ├── validation.js       # Input validation
        ├── project-editor.js   # Editor controller
        └── unsaved-changes.js  # Dirty state tracking
```

## Template Inheritance

### Base Template (`templates/base.html`)

Master template with:
- Navbar with "GPRO" brand logo
- Flash message display
- Content block for pages
- Footer: "GPRO is an FPRO Production"
- Bootstrap 5 and custom CSS

```html
<!DOCTYPE html>
<html>
<head>
    <title>{% block title %}GPRO{% endblock %}</title>
    <link href="bootstrap.min.css" rel="stylesheet">
    <link href="{{ url_for('static', filename='css/styles.css') }}" rel="stylesheet">
</head>
<body>
    <nav class="navbar navbar-expand-lg navbar-dark bg-primary">
        <a class="navbar-brand" href="/">
            <span class="brand-text">GPRO</span>
        </a>
        <!-- Navigation links -->
    </nav>

    <main class="container py-4">
        <!-- Flash messages -->
        {% with messages = get_flashed_messages(with_categories=true) %}
        {% for category, message in messages %}
        <div class="alert alert-{{ category }}">{{ message }}</div>
        {% endfor %}
        {% endwith %}

        {% block content %}{% endblock %}
    </main>

    <footer>GPRO is an FPRO Production</footer>

    {% block scripts %}{% endblock %}
</body>
</html>
```

### Page Templates

Pages extend base and override blocks:

```html
{% extends "base.html" %}

{% block title %}Projects - GPRO{% endblock %}

{% block content %}
<h1>My Projects</h1>
<!-- Page content -->
{% endblock %}

{% block scripts %}
<script src="{{ url_for('static', filename='js/api.js') }}"></script>
{% endblock %}
```

## Reusable Partials

### Coordinate Input (`partials/coord_input.html`)

X/Y coordinate pair input with labels:

```html
{% macro coord_input(prefix, x_value='', y_value='', x_label='X', y_label='Y') %}
<div class="row g-2">
    <div class="col">
        <label class="form-label">{{ x_label }}</label>
        <input type="number" step="0.0001" name="{{ prefix }}_x"
               value="{{ x_value }}" class="form-control" required>
    </div>
    <div class="col">
        <label class="form-label">{{ y_label }}</label>
        <input type="number" step="0.0001" name="{{ prefix }}_y"
               value="{{ y_value }}" class="form-control" required>
    </div>
</div>
{% endmacro %}
```

### Pattern Fields (`partials/pattern_fields.html`)

Dynamic fields for linear/grid patterns:

```html
{% macro pattern_fields(prefix) %}
<div class="pattern-type-select mb-3">
    <select name="{{ prefix }}_type" class="form-select pattern-type-trigger">
        <option value="single">Single Point</option>
        <option value="pattern_linear">Linear Pattern</option>
        <option value="pattern_grid">Grid Pattern</option>
    </select>
</div>

<div class="pattern-linear-fields" style="display: none;">
    <div class="row g-2">
        <div class="col">
            <label>Axis</label>
            <select name="{{ prefix }}_axis" class="form-select">
                <option value="x">X (Horizontal)</option>
                <option value="y">Y (Vertical)</option>
            </select>
        </div>
        <div class="col">
            <label>Spacing</label>
            <input type="number" step="0.0001" name="{{ prefix }}_spacing">
        </div>
        <div class="col">
            <label>Count</label>
            <input type="number" min="2" name="{{ prefix }}_count">
        </div>
    </div>
</div>

<div class="pattern-grid-fields" style="display: none;">
    <!-- Grid-specific fields -->
</div>
{% endmacro %}
```

### Modal Footer (`partials/modal_footer.html`)

Standard modal buttons:

```html
{% macro modal_footer(confirm_text='Save', confirm_class='btn-primary') %}
<div class="modal-footer">
    <button type="button" class="btn btn-secondary" data-bs-dismiss="modal">
        Cancel
    </button>
    <button type="submit" class="btn {{ confirm_class }}">
        {{ confirm_text }}
    </button>
</div>
{% endmacro %}
```

## Key Pages

### Projects Dashboard (`index.html`)

Grid of project cards with actions:

```html
{% extends "base.html" %}
{% block content %}
<div class="d-flex justify-content-between align-items-center mb-4">
    <h1>Projects</h1>
    <a href="{{ url_for('projects.new') }}" class="btn btn-primary">
        New Project
    </a>
</div>

<div class="row row-cols-1 row-cols-md-3 g-4">
{% for project in projects %}
<div class="col">
    <div class="card h-100">
        <div class="card-body">
            <h5 class="card-title">{{ project.name }}</h5>
            <span class="badge bg-{{ 'primary' if project.project_type == 'drill' else 'info' }}">
                {{ project.project_type }}
            </span>
            <p class="card-text text-muted">
                {{ project.material.display_name if project.material else 'No material' }}
            </p>
        </div>
        <div class="card-footer">
            <small class="text-muted">
                Modified {{ project.modified_at.strftime('%b %d, %Y') }}
            </small>
            <div class="btn-group float-end">
                <a href="{{ url_for('projects.edit', project_id=project.id) }}"
                   class="btn btn-sm btn-outline-primary">Edit</a>
                <form action="{{ url_for('projects.delete', project_id=project.id) }}"
                      method="post" class="d-inline">
                    <button class="btn btn-sm btn-outline-danger">Delete</button>
                </form>
            </div>
        </div>
    </div>
</div>
{% endfor %}
</div>
{% endblock %}
```

### Project Editor (`project/edit.html`)

Main workspace with two-column layout:

```html
{% extends "base.html" %}
{% block content %}
<div class="row">
    <!-- Left column: Operations -->
    <div class="col-md-6">
        <div class="card mb-3">
            <div class="card-header">Project Info</div>
            <div class="card-body">
                <h5>{{ project.name }}</h5>
                <span class="badge">{{ project.project_type }}</span>
            </div>
        </div>

        <div class="card mb-3">
            <div class="card-header d-flex justify-content-between">
                <span>Operations</span>
                <div class="btn-group btn-group-sm">
                    <button class="btn btn-outline-primary" data-bs-toggle="modal"
                            data-bs-target="#drillModal">+ Drill</button>
                    <button class="btn btn-outline-info" data-bs-toggle="modal"
                            data-bs-target="#circleModal">+ Circle</button>
                    <!-- More buttons -->
                </div>
            </div>
            <div class="card-body">
                <div id="operations-list">
                    <!-- Populated by JavaScript -->
                </div>
            </div>
        </div>
    </div>

    <!-- Right column: Preview + Download -->
    <div class="col-md-6">
        <div class="card mb-3">
            <div class="card-header">Preview</div>
            <div class="card-body">
                <div id="preview-container">
                    <!-- SVG inserted here -->
                </div>
            </div>
        </div>

        <div id="validation-errors" class="alert alert-danger d-none"></div>

        <button id="download-btn" class="btn btn-success btn-lg w-100">
            Download G-Code
        </button>
    </div>
</div>

<!-- Modals for adding operations (embedded in edit.html) -->
<!-- Drill Modal: Pattern type, coordinates, spacing, count -->
<!-- Circle Modal: Center coords, diameter, pattern support, compensation -->
<!-- Hexagon Modal: Center coords, flat-to-flat, pattern support, compensation -->
<!-- Line Modal: Points list, arc support, tool compensation -->

{% endblock %}

{% block scripts %}
<script>
    // Data embedded from server
    const PROJECT_ID = "{{ project.id }}";
    const PROJECT_DATA = {{ project | tojson | safe }};
    const MATERIALS = {{ materials | tojson | safe }};
    const TOOLS = {{ tools | tojson | safe }};
    const MACHINE = {{ machine | tojson | safe }};
</script>
<script src="{{ url_for('static', filename='js/api.js') }}"></script>
<script src="{{ url_for('static', filename='js/validation.js') }}"></script>
<script src="{{ url_for('static', filename='js/project-editor.js') }}"></script>
<script src="{{ url_for('static', filename='js/unsaved-changes.js') }}"></script>
{% endblock %}
```

## Tool Compensation in Modals

All cut operation modals (Circle, Hexagon, Line) include a tool compensation dropdown:

| Value | Use Case | Effect |
|-------|----------|--------|
| `none` | Tool path matches design exactly | No offset applied |
| `interior` | Cutting a hole/pocket/window | Tool offsets inward by tool radius |
| `exterior` | Cutting out a shape from stock | Tool offsets outward by tool radius |

The default is typically `interior` for circles/hexagons (cutting holes) and `none` for lines.

## Line Cut Modal

The Line Cut modal (`#addLineModal`) provides fields for:

### Points List
Dynamic list of path points:
- **X, Y**: Coordinates for each point
- **Type**: Start (first point), Straight, or Arc
- **Arc Center X, Y**: Only shown for Arc type segments

### Path Options
- **Closed Path**: Checkbox to connect last point back to first
- **Tool Compensation**: Dropdown to select compensation type

### Tool Compensation Dropdown

See "Tool Compensation in Modals" section above for details. The compensation is stored in the operation's JSON and applied during G-code generation.

## JavaScript Modules

### API Utilities (`static/js/api.js`)

Shared API communication:

```javascript
async function apiPost(url, data) {
    const response = await fetch(url, {
        method: 'POST',
        headers: {'Content-Type': 'application/json'},
        body: JSON.stringify(data)
    });
    const result = await response.json();
    if (result.status === 'error') {
        throw new Error(result.message || 'API error');
    }
    return result.data;
}

async function apiGet(url) {
    const response = await fetch(url);
    const result = await response.json();
    if (result.status === 'error') {
        throw new Error(result.message || 'API error');
    }
    return result.data;
}
```

### Validation (`static/js/validation.js`)

Input validation functions:

```javascript
function isValidCoordinate(value, maxX, maxY) {
    const num = parseFloat(value);
    return !isNaN(num) && num >= 0 && num <= Math.max(maxX, maxY);
}

function isPositiveNumber(value) {
    const num = parseFloat(value);
    return !isNaN(num) && num > 0;
}

function validateOperation(type, operation) {
    const errors = [];

    if (type === 'drill') {
        if (!isValidCoordinate(operation.x, MACHINE.max_x, MACHINE.max_y)) {
            errors.push('Invalid X coordinate');
        }
        if (!isValidCoordinate(operation.y, MACHINE.max_x, MACHINE.max_y)) {
            errors.push('Invalid Y coordinate');
        }
    }

    // ... more validation by type

    return errors;
}

function validateProject(project) {
    const errors = [];
    // Check for at least one operation
    const opCount = project.operations.drill_holes.length +
                    project.operations.circular_cuts.length +
                    project.operations.hexagonal_cuts.length +
                    project.operations.line_cuts.length;
    if (opCount === 0) {
        errors.push('Project must have at least one operation');
    }
    return errors;
}
```

### Project Editor (`static/js/project-editor.js`)

Main controller class:

```javascript
class ProjectEditor {
    constructor(projectId, projectData, materials, tools, machine) {
        this.projectId = projectId;
        this.project = projectData;
        this.materials = materials;
        this.tools = tools;
        this.machine = machine;
        this.lastSavedData = JSON.stringify(projectData.operations);

        this.init();
    }

    init() {
        this.renderOperations();
        this.bindEvents();
        this.refreshPreview();
    }

    renderOperations() {
        const container = document.getElementById('operations-list');
        container.innerHTML = '';

        // Render drill holes
        this.project.operations.drill_holes.forEach((op, i) => {
            container.appendChild(this.createOperationCard('drill', op, i));
        });

        // Render other operation types...
    }

    createOperationCard(type, operation, index, sequenceNum, isFirst, isLast) {
        // Renders operation with:
        // - Sequence number badge (#1, #2, etc.)
        // - Type badge (Drill, Circle, Hex, Line)
        // - Operation summary
        // - Reorder buttons (up/down arrows) for cut operations
        // - Edit button (for line operations)
        // - Delete button
    }

    moveOperation(type, index, direction) {
        // Swap operation with adjacent one
        // direction: -1 = up, +1 = down
        // Refreshes preview after reordering
    }

    bindEvents() {
        // Add operation buttons
        document.querySelectorAll('[data-add-operation]').forEach(btn => {
            btn.addEventListener('click', (e) => this.openAddModal(e.target.dataset.type));
        });

        // Delete operation buttons
        document.addEventListener('click', (e) => {
            if (e.target.classList.contains('delete-op')) {
                this.deleteOperation(e.target.dataset.type, e.target.dataset.index);
            }
        });

        // Save button
        document.getElementById('save-btn')?.addEventListener('click', () => this.save());

        // Download button
        document.getElementById('download-btn').addEventListener('click', () => this.download());
    }

    async addOperation(type, data) {
        const operation = {
            id: this.generateId(),
            type: data.pattern_type || 'single',
            ...data
        };

        const arrayName = this.getArrayName(type);
        this.project.operations[arrayName].push(operation);

        this.renderOperations();
        await this.refreshPreview();
        this.markDirty();
    }

    deleteOperation(type, index) {
        const arrayName = this.getArrayName(type);
        this.project.operations[arrayName].splice(index, 1);

        this.renderOperations();
        this.refreshPreview();
        this.markDirty();
    }

    async refreshPreview() {
        try {
            const data = await apiPost(`/api/projects/${this.projectId}/preview`, {
                operations: this.project.operations
            });
            document.getElementById('preview-container').innerHTML = data.svg;
        } catch (err) {
            console.error('Preview error:', err);
        }
    }

    async save() {
        try {
            const data = await apiPost(`/api/projects/${this.projectId}/save`, {
                operations: this.project.operations,
                tube_void_skip: this.project.tube_void_skip
            });
            this.lastSavedData = JSON.stringify(this.project.operations);
            this.markClean();
            showToast('Project saved');
        } catch (err) {
            showToast('Save failed: ' + err.message, 'error');
        }
    }

    async download() {
        // Validate first
        try {
            const result = await apiPost(`/api/projects/${this.projectId}/validate`, {});
            if (result.errors && result.errors.length > 0) {
                this.showValidationErrors(result.errors);
                return;
            }
        } catch (err) {
            this.showValidationErrors([err.message]);
            return;
        }

        // Trigger download
        window.location.href = `/api/projects/${this.projectId}/download`;
    }

    // ... helper methods
}

// Initialize on page load
document.addEventListener('DOMContentLoaded', () => {
    if (typeof PROJECT_ID !== 'undefined') {
        window.editor = new ProjectEditor(
            PROJECT_ID, PROJECT_DATA, MATERIALS, TOOLS, MACHINE
        );
    }
});
```

### Unsaved Changes Tracker (`static/js/unsaved-changes.js`)

Dirty state tracking:

```javascript
class UnsavedChangesTracker {
    constructor(editor) {
        this.editor = editor;
        this.indicator = document.getElementById('unsaved-indicator');

        window.addEventListener('beforeunload', (e) => {
            if (this.isDirty()) {
                e.preventDefault();
                e.returnValue = '';
            }
        });
    }

    isDirty() {
        const current = JSON.stringify(this.editor.project.operations);
        return current !== this.editor.lastSavedData;
    }

    markDirty() {
        this.indicator?.classList.remove('d-none');
    }

    markClean() {
        this.indicator?.classList.add('d-none');
    }
}
```

## Styling

### Custom Colors (`static/css/styles.css`)

CSS variables override Bootstrap:

```css
:root {
    --bs-primary: #2F055A;      /* Purple - main brand, drill badges */
    --bs-info: #5a7a8a;         /* Teal - circle badges */
    --bs-warning: #c9a87c;      /* Amber - hexagon badges */
    --bs-success: #5a8a6e;      /* Green - line badges */
    --bs-danger: #a85a6e;       /* Pink - delete buttons */
}

/* Brand font for logo */
@font-face {
    font-family: 'GPRO-Brand';
    src: url('../fonts/gpro-brand.ttf') format('truetype');
}

.brand-text {
    font-family: 'GPRO-Brand', sans-serif;
    font-size: 1.5rem;
}

/* System font stack */
body {
    font-family: 'Avenir', 'Nunito', -apple-system, sans-serif;
}
```

### Operation Badge Colors

Each operation type has a distinct color:

| Type | Color | CSS Class |
|------|-------|-----------|
| Sequence # | Gray | `bg-secondary` |
| Drill | Purple | `bg-primary` |
| Circle | Teal | `bg-info` |
| Hexagon | Amber | `bg-warning` |
| Line | Green | `bg-success` |

### Operation Controls

Each operation item includes:
- **Sequence number**: Shows machining order (#1, #2, etc.)
- **Type badge**: Color-coded operation type
- **Summary**: Brief description of the operation
- **Reorder buttons**: Up/down arrows (cut operations only)
- **Edit button**: Opens edit modal (line operations only)
- **Delete button**: Removes the operation

### Card Styling

```css
.operation-card {
    background: #f8f9fa;
    transition: background 0.2s;
}

.operation-card:hover {
    background: #e9ecef;
}

.card-header {
    background: rgba(47, 5, 90, 0.1);
    font-weight: 600;
}
```

## Data Flow: Frontend → Backend

### Adding an Operation

1. User clicks "+ Drill" → Modal opens
2. User fills form, clicks "Add"
3. JavaScript validates input (`validation.js`)
4. `ProjectEditor.addOperation()` adds to local state
5. `refreshPreview()` POSTs to `/api/projects/<id>/preview`
6. Server expands patterns, generates SVG
7. SVG inserted into `#preview-container`
8. Dirty state indicator shows

### Saving Project

1. User clicks "Save"
2. `ProjectEditor.save()` POSTs to `/api/projects/<id>/save`
3. Server updates database, returns `modified_at`
4. `lastSavedData` updated, dirty indicator hidden
5. Toast notification shows success

### Downloading G-Code

1. User clicks "Download G-Code"
2. `ProjectEditor.download()` POSTs to `/api/projects/<id>/validate`
3. If errors, display in `#validation-errors`
4. If valid, redirect to `/api/projects/<id>/download`
5. Server generates G-code, returns ZIP
6. Browser downloads file

## Key Patterns

1. **Server-Side Rendering + AJAX**: Pages rendered by Jinja2, interactivity via fetch API.

2. **Data Embedding**: Server data passed to JavaScript via `<script>` tags with `| tojson`.

3. **Single Controller**: `ProjectEditor` class manages all editor state and UI.

4. **Dirty Tracking**: Compare current state to last saved to detect unsaved changes.

5. **Consistent Badge Colors**: Each operation type has a semantic color throughout the UI.

6. **Modal Forms**: Bootstrap modals for add/edit operations, keeping main page uncluttered.
