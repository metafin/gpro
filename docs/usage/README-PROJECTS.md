# Projects Usage Guide

This guide explains how to create and manage CNC projects in GPRO.

## Overview

A project in GPRO represents a single CNC machining job. Each project contains:

- Basic info (name, type, material)
- Tool selection
- Operations (drill holes, cuts)
- G-code generation settings

## Project Types

GPRO supports two project types:

### Drill Projects

For creating holes in material. Uses a drill bit.

**Operations available:**
- Drill holes (single points or patterns)

**Tool used:** Drill bit (selected at project creation)

### Cut Projects

For cutting shapes from material. Uses an end mill.

**Operations available:**
- Circular cuts (holes larger than the tool)
- Hexagonal cuts (hex-shaped holes)
- Line cuts (arbitrary paths)

**Tool used:** End mill (selected at project creation)

## Creating a Project

### From the Dashboard

1. Click **New Project** on the projects dashboard
2. Fill in the project details:
   - **Name**: Descriptive name for the project
   - **Type**: Choose "Drill" or "Cut"
   - **Material**: Select from configured materials
   - **Tool**: Choose the appropriate drill or end mill
3. Click **Create Project**

You'll be redirected to the project editor.

### Project Type Selection

Choose the type based on what operations you need:

| Need | Choose |
|------|--------|
| Only drill holes | Drill |
| Cut circles, hexagons, or paths | Cut |
| Both drilling and cutting | Create two separate projects |

## The Project Editor

The editor has two main areas:

### Left Panel: Operations

- **Project Info**: Name, type, material display
- **Operations List**: All defined operations
- **Add Buttons**: Create new operations by type

### Right Panel: Preview & Actions

- **Preview**: Visual representation of all operations
- **Validation Errors**: Issues that prevent G-code generation
- **Download Button**: Generate and download G-code

## Adding Operations

### Drill Holes

Click **+ Drill** to add drill operations.

**Single Point:**
- Enter X and Y coordinates
- One hole at the specified location

**Linear Pattern:**
- Enter starting X, Y coordinates
- Choose axis (X = horizontal, Y = vertical)
- Specify spacing between holes
- Specify count (number of holes)

**Grid Pattern:**
- Enter starting X, Y coordinates
- Specify X and Y spacing
- Specify X and Y count

Example: A 3x2 grid with 0.5" spacing creates 6 holes in a rectangular pattern.

### Circular Cuts

Click **+ Circle** to add circular cuts.

**Fields:**
- **Center X, Y**: Center point of the circle
- **Diameter**: Size of the hole to cut
- **Tool Compensation**: None, Interior (pocket), or Exterior (outside cut)
- **Lead-In Settings**: Auto (use global) or Manual (override)

**Lead-In Settings (Manual mode):**
- **Lead-In Type**: Helical (spiral), Ramp (linear), or None
- **Approach Angle**: 0-360° direction tool approaches from

The tool will make multiple passes at increasing depths, cutting a circular pocket.

**Pattern support:** Circles also support linear and grid patterns for multiple identical circles.

### Hexagonal Cuts

Click **+ Hexagon** to add hexagonal cuts.

**Fields:**
- **Center X, Y**: Center point of the hexagon
- **Flat-to-Flat**: Distance between parallel flat sides
- **Tool Compensation**: None, Interior (pocket), or Exterior (outside cut)
- **Lead-In Settings**: Auto (use global) or Manual (override)

**Lead-In Settings (Manual mode):**
- **Lead-In Type**: Helical (spiral), Ramp (linear), or None
- **Approach Angle**: 0-360° direction tool approaches from

Hexagons are **point-up** orientation (vertices at top and bottom, flats on sides).

**Pattern support:** Hexagons also support linear and grid patterns.

### Line Cuts

Click **+ Line** to add custom path cuts.

**Building a path:**
1. Add a **Start** point (where the tool enters)
2. Add **Straight** segments for linear moves
3. Add **Arc** segments for curved moves (specify arc center)
4. Optionally mark as **Closed** to return to start

**Arc segments** require the arc center point. The direction (clockwise or counterclockwise) is calculated automatically.

**Lead-In Settings:**
- **Auto**: Uses global settings, lead-in direction based on path geometry
- **Manual**: Override with custom approach angle (0-360°)

When using manual lead-in with an approach angle, the tool approaches from that direction regardless of the path's starting geometry.

### Approach Angle Reference

For all cut operations (circles, hexagons, lines), the approach angle uses this convention:

| Angle | Direction | Clock Position |
|-------|-----------|----------------|
| 0° | From top | 12 o'clock |
| 90° | From right | 3 o'clock (default) |
| 180° | From bottom | 6 o'clock |
| 270° | From left | 9 o'clock |

**When to customize approach angle:**
- **Avoid clamps**: Set angle to approach from the opposite side of your fixturing
- **Better finish**: Some materials cut cleaner when approached from a specific direction
- **Chip evacuation**: Direct chips away from critical features

#### Tool Compensation

Line cuts support automatic tool compensation to achieve precise dimensions:

| Option | Description | Use When |
|--------|-------------|----------|
| **None** | Tool center follows the exact path | Path already accounts for tool radius |
| **Interior** | Tool offsets inward | Cutting pockets, windows, or interior features |
| **Exterior** | Tool offsets outward | Cutting out shapes (the material inside stays) |

**How it works:**
- The system automatically offsets the toolpath by the tool radius
- Corner intersections are calculated to maintain sharp corners
- Arc segments adjust their radius accordingly

**Example - Cutting a 1" square:**
- Draw a 1" x 1" square path
- Select **Exterior** compensation
- With a 0.25" end mill, the tool will cut outside the path
- The finished part will be exactly 1" x 1"

**Example - Cutting a 1" square pocket:**
- Draw a 1" x 1" square path
- Select **Interior** compensation
- With a 0.25" end mill, the tool will cut inside the path
- The finished pocket will be exactly 1" x 1"

**Note:** If an arc segment is too small for the selected compensation (interior compensation on a tiny arc), a warning is generated and that operation is skipped.

## Editing Operations

### Viewing Details

Click on an operation in the list to expand its details.

**Line cut summary format:** `N points [compensation]`
- Example: `5 points [exterior]` - A 5-point path with exterior compensation
- For closed paths, include a final point returning to start

### Modifying

Click the **Edit** button on an operation to open the edit modal. Make changes and save.

### Deleting

Click the **Delete** button (×) on an operation to remove it.

### Reordering

Operations are processed in the order listed. Each cut operation (circles, hexagons, lines) has up/down arrow buttons to change its position in the sequence:

- **Up Arrow**: Move operation earlier in the sequence
- **Down Arrow**: Move operation later in the sequence

The sequence number (#1, #2, #3...) shown on each operation updates automatically when you reorder.

**Note:** Drill operations are always processed first and cannot be reordered relative to cut operations.

## Preview

The preview shows a visual representation of all operations:

| Element | Color | Description |
|---------|-------|-------------|
| Drill holes | Purple dots | Single drill points |
| Circles | Teal circles | Circular cut paths |
| Hexagons | Amber hexagons | Hexagonal cut paths |
| Lines | Green paths | Line cut paths (straight and arc segments) |
| Machine bounds | Gray rectangle | Work area limits |
| Material | Light fill | Material dimensions (if tube) |
| **Sequence numbers** | Matching color | Order of operations (1, 2, 3...) |

**Note:** Arc segments in line cuts are displayed as curved paths in the preview, accurately representing the G02/G03 arc moves that will be generated.

Each operation displays a sequence number indicating the order it will be machined. Numbers appear:
- Next to drill points (offset to upper-right)
- At the center of circles and hexagons
- At the centroid of line cut paths

The preview updates automatically when operations change or are reordered.

## Validation

Before downloading G-code, the project is validated:

### Common Errors

| Error | Cause | Fix |
|-------|-------|-----|
| "No material selected" | Material not chosen | Select a material in project settings |
| "No tool selected" | Tool not chosen | Select appropriate tool |
| "Point exceeds X/Y limit" | Operation outside machine bounds | Adjust coordinates |
| "No operations defined" | Empty project | Add at least one operation |
| "Tool size not in standards" | Tool/material combo has no cutting parameters | Add G-code standards for this combination |
| "Arc radius too small for compensation" | Interior compensation on small arc | Use larger arc or reduce tool size |
| "Line point outside bounds" | Compensated path extends beyond machine limits | Adjust coordinates or use smaller tool |

### Validation Flow

1. Click **Download G-Code**
2. System validates project
3. If errors: displayed in red alert, download blocked
4. If valid: G-code generated and downloaded

## Downloading G-Code

When validation passes:

1. Click **Download G-Code**
2. A ZIP file downloads containing:
   - `main.nc` - Main G-code program
   - `1000.nc`, `1100.nc`, etc. - Subroutine files (if patterns used)

### File Structure

```
MyProject.zip
├── main.nc          # Main program
├── 1000.nc          # Drill subroutine (if linear pattern)
├── 1100.nc          # Circle subroutine
├── 1200.nc          # Hexagon subroutine
└── 1300.nc          # Line subroutine
```

### Using the G-Code

1. Extract the ZIP file to your CNC controller's G-code directory
   - Default for Mach3: `C:\Mach3\GCode\ProjectName\`
2. Open `main.nc` in your CNC controller
3. Run the program

The main program uses M98 calls to reference subroutines by full path.

## Tube Void Skip

For tube materials, the **Tube Void Skip** option skips operations that fall entirely within the hollow center of the tube.

**When to use:**
- Material is a hollow tube
- Some operations would cut only air (inside the void)

**How it works:**
1. Enable **Tube Void Skip** in project settings
2. System calculates void boundaries from tube dimensions
3. Operations entirely within void are excluded from G-code
4. Preview shows which operations are skipped (grayed out)

## Saving Projects

### Auto-Save Indicator

A floating indicator shows when you have unsaved changes.

### Manual Save

Click the **Save** button to save changes. The indicator disappears when saved.

### Unsaved Warning

If you try to leave the page with unsaved changes, a browser warning appears.

## Managing Projects

### From the Dashboard

Each project card shows:
- Project name
- Type badge (Drill/Cut)
- Material name
- Last modified date

**Actions:**
- **Edit**: Open project editor
- **Download**: Generate and download G-code directly
- **Duplicate**: Create a copy with a new name
- **Delete**: Remove project (confirmation required)

### Duplicating

1. Click **Duplicate** on a project
2. Enter a new name
3. Click **Duplicate**

The new project copies all operations and settings.

### Deleting

1. Click **Delete** on a project
2. Confirm deletion

Deleted projects cannot be recovered.

## Best Practices

### Naming Conventions

Use descriptive names that identify:
- Part being made
- Material
- Version/revision

Example: `Gusset_Aluminum_v2`

### Operation Organization

- Group related operations
- Use patterns for repeated holes
- Consider tool path efficiency

### Validation Before Cutting

Always:
1. Review the preview carefully
2. Check all coordinates are correct
3. Verify tool selection matches your setup
4. Ensure material dimensions are accurate

### Backup

Export important projects by downloading G-code, even if you won't run it immediately. The G-code serves as a backup of the project definition.
