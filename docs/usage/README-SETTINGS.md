# Settings Usage Guide

This guide explains how to configure GPRO's settings for your CNC machine and materials.

## Overview

GPRO settings are organized into four categories:

1. **Materials**: Define stock materials and cutting parameters
2. **Tools**: Manage drill bits and end mills
3. **Machine Settings**: Configure your CNC machine limits
4. **General Settings**: Set G-code generation defaults

Access settings from the **Settings** link in the navigation bar.

## Materials

Materials define the stock you're cutting and the G-code parameters for each tool combination.

### Material Properties

**Basic Info:**
- **ID**: Unique identifier (auto-generated or custom)
- **Display Name**: Human-readable name shown in dropdowns
- **Base Material**: Category (aluminum, polycarbonate, etc.)

**Form:**
- **Sheet**: Flat material with a thickness
- **Tube**: Hollow rectangular material

**Dimensions (Sheet):**
- **Thickness**: Material depth in inches

**Dimensions (Tube):**
- **Outer Width**: External width in inches
- **Outer Height**: External height in inches
- **Wall Thickness**: Tube wall thickness in inches

### G-Code Standards

Each material has cutting parameters for each tool type and size combination.

**Parameters:**
| Parameter | Description | Unit |
|-----------|-------------|------|
| Spindle Speed | RPM for the spindle | RPM |
| Feed Rate | Cutting speed (X/Y movement) | inches/min |
| Plunge Rate | Z-axis feed for plunging | inches/min |
| Pecking Depth | Depth per peck cycle (drill) | inches |
| Pass Depth | Depth per cutting pass (end mill) | inches |

**Tool Types:**
- `drill`: Standard drill bits
- `end_mill_1flute`: Single-flute end mills
- `end_mill_2flute`: Two-flute end mills

### Adding a Material

1. Go to **Settings > Materials**
2. Click **Add Material**
3. Fill in the form:
   - ID (lowercase, underscores, no spaces)
   - Display name
   - Base material
   - Form (sheet or tube)
   - Dimensions
4. Click **Create**
5. Edit the material to add G-code standards

### Editing G-Code Standards

1. Go to **Settings > Materials**
2. Click **Edit** on a material
3. Scroll to the **G-Code Standards** section
4. For each tool type and size combination:
   - Enter spindle speed, feed rate, plunge rate
   - For drills: enter pecking depth
   - For end mills: enter pass depth
5. Click **Save**

### Example: Aluminum Sheet 1/8"

```
ID: aluminum_sheet_0125
Display Name: Aluminum Sheet 1/8"
Base Material: aluminum
Form: sheet
Thickness: 0.125

G-Code Standards:
  drill:
    0.125" (1/8"):
      Spindle: 1000 RPM
      Feed: 5 in/min
      Plunge: 2 in/min
      Pecking: 0.05"

    0.1875" (3/16"):
      Spindle: 900 RPM
      Feed: 4.5 in/min
      Plunge: 1.8 in/min
      Pecking: 0.06"

  end_mill_1flute:
    0.125" (1/8"):
      Spindle: 12000 RPM
      Feed: 20 in/min
      Plunge: 5 in/min
      Pass Depth: 0.03"
```

### Deleting a Material

1. Go to **Settings > Materials**
2. Click **Delete** on the material
3. Confirm deletion

**Note:** Materials used by existing projects cannot be deleted. Delete or reassign those projects first.

## Tools

Tools are the drill bits and end mills available for projects.

### Tool Properties

- **Type**: drill, end_mill_1flute, or end_mill_2flute
- **Size**: Tool diameter
- **Size Unit**: inches (in) or millimeters (mm)
- **Description**: User-friendly label

### Adding a Tool

1. Go to **Settings > Tools**
2. Click **Add Tool**
3. Select the tool type
4. Enter the size and unit
5. Add a description (optional)
6. Click **Create**

### Common Tool Sizes

| Size (inches) | Fraction | Common Use |
|---------------|----------|------------|
| 0.125 | 1/8" | Small holes, fine detail |
| 0.1875 | 3/16" | Medium holes |
| 0.25 | 1/4" | Large holes, structural |
| 0.375 | 3/8" | Very large holes |
| 0.5 | 1/2" | Maximum for OMIO |

### Tool Type Selection

| Type | Best For |
|------|----------|
| drill | Making holes (faster than end mill) |
| end_mill_1flute | Cutting plastics (better chip evacuation) |
| end_mill_2flute | Cutting metals (general purpose) |

### Deleting a Tool

1. Go to **Settings > Tools**
2. Click **Delete** on the tool
3. Confirm deletion

**Note:** Ensure no projects are using this tool before deletion.

## Machine Settings

Configure your CNC machine's capabilities and limits.

### Settings

| Setting | Description | Default |
|---------|-------------|---------|
| Machine Name | Identifier for your machine | OMIO CNC |
| Max X Travel | Maximum X-axis movement | 12.0" |
| Max Y Travel | Maximum Y-axis movement | 8.0" |
| Units | Working units | inches |
| Controller Type | CNC controller software | mach3 |
| Supports Subroutines | M98 support | Yes |
| Supports Canned Cycles | G81/G83 support | Yes |
| G-Code Base Path | Output directory | C:\Mach3\GCode |

### Controller Types

| Type | Description |
|------|-------------|
| mach3 | Mach3 CNC controller |
| mach4 | Mach4 CNC controller |
| grbl | GRBL-based controllers |
| linuxcnc | LinuxCNC |

Different controllers may have different subroutine syntax. Currently, only Mach3 M98 syntax is fully implemented.

### G-Code Base Path

The base path is prepended to project names for subroutine file references.

**Example:**
- Base path: `C:\Mach3\GCode`
- Project name: `MyGusset`
- Subroutine path: `C:\Mach3\GCode\MyGusset\1000.nc`

**Important:** This must match where you actually place the G-code files on your CNC computer.

### Editing Machine Settings

1. Go to **Settings > Machine**
2. Modify settings as needed
3. Click **Save**

Machine settings are global and affect all projects.

## General Settings

Configure G-code generation defaults.

### Settings

| Setting | Description | Default |
|---------|-------------|---------|
| Safety Height | Z height for safe moves | 0.5" |
| Travel Height | Z height during rapids | 0.2" |
| Spindle Warmup | Dwell after spindle start | 3 seconds |
| Lead-In Type | Entry method for profile cuts | Ramp |
| Lead-In Distance | Approach distance for ramped entry | 0.25" |

### Height Definitions

**Safety Height:**
The Z position used when moving to a completely safe location (start of program, between major operations). Should clear all clamps, fixtures, and workholding.

**Travel Height:**
The Z position used when moving between nearby operations. Should clear the material surface and any chips but can be lower than safety height for efficiency.

### Spindle Warmup

A G4 dwell command is inserted after the spindle starts (M03) to allow it to reach full speed before cutting begins.

**Recommendation:** 2-5 seconds for most spindles.

### Lead-In Settings

Lead-in controls how the tool enters profile cuts (circles, hexagons, line cuts). This setting does **not** affect drill operations.

**Lead-In Type:**

| Type | Description |
|------|-------------|
| **Ramp** (recommended) | Tool descends gradually while approaching the profile start. Eliminates shock loading that can snap end mills. |
| **None** | Traditional vertical plunge followed by immediate lateral cut. May cause tool breakage with aggressive parameters. |

**Lead-In Distance:**
The distance from the profile start where the ramped approach begins. The tool rapids to this point, then ramps down while moving toward the profile.

**Recommendations:**
- **0.25"** (default): Good balance for most operations
- **0.125"**: Tighter spaces with limited waste area
- **0.5"**: More gradual entry for aggressive cuts

**Example:**
For a circle cut at center (5, 5) with a 1" diameter and 0.25" lead-in:
1. Tool rapids to lead-in point: (5.6875, 5) - outside the circle
2. Tool ramps from (5.6875, 5, Z0) to (5.4375, 5, Z-0.0625) - descending while approaching
3. Tool cuts the full circle at depth
4. Tool returns to lead-in point, ready for next pass

**Note:** Lead-in adds a small amount to the cutting area. Ensure there's material (not void or clamps) at the lead-in point.

### Editing General Settings

1. Go to **Settings > General**
2. Modify settings as needed
3. Click **Save**

## Setting Relationships

### Material + Tool = G-Code Parameters

When a project uses a specific material and tool combination, the G-code parameters come from:

```
Material.gcode_standards[tool_type][tool_size]
```

If this combination doesn't exist, validation will fail with "Tool size not in standards."

### Example Flow

1. Project uses "Aluminum Sheet 1/8"" material
2. Project uses 1/8" drill tool
3. System looks up: `aluminum_sheet_0125.gcode_standards.drill["0.125"]`
4. Returns: spindle_speed=1000, feed_rate=5, plunge_rate=2, pecking_depth=0.05

## Initial Setup Checklist

When setting up GPRO for a new machine:

1. **Machine Settings**
   - [ ] Set correct X and Y travel limits
   - [ ] Set controller type
   - [ ] Set G-code base path for your system
   - [ ] Enable/disable subroutine support

2. **Tools**
   - [ ] Add all drill bits you have
   - [ ] Add all end mills you have
   - [ ] Verify sizes are in correct units

3. **Materials**
   - [ ] Add each material type you use
   - [ ] For each material, add G-code standards for each tool
   - [ ] Use conservative parameters initially, optimize later

4. **General Settings**
   - [ ] Set appropriate safety and travel heights
   - [ ] Set spindle warmup time
   - [ ] Enable ramped lead-in (recommended for end mills)
   - [ ] Set appropriate lead-in distance for your workholding

## Troubleshooting

### "Tool size not in standards"

**Cause:** The selected tool size doesn't have parameters defined for the selected material.

**Fix:**
1. Go to Settings > Materials
2. Edit the material
3. Add G-code standards for the missing tool type/size combination

### "Point exceeds X/Y limit"

**Cause:** An operation's coordinates exceed machine travel limits.

**Fix:**
1. Check Machine Settings > Max X/Y values
2. Adjust operation coordinates to fit within limits
3. Or adjust machine limits if they were set incorrectly

### Subroutines Not Working

**Possible causes:**
1. Controller doesn't support M98 (disable in Machine Settings)
2. G-code base path doesn't match actual file location
3. Controller type mismatch

**Fix:**
1. Verify Machine Settings > Supports Subroutines
2. Check G-code base path matches where files are copied
3. Ensure controller type is correct

### Preview Not Updating

**Possible causes:**
1. Browser cache issue
2. JavaScript error

**Fix:**
1. Hard refresh the page (Ctrl+Shift+R / Cmd+Shift+R)
2. Check browser console for errors

### Lead-In Cutting Into Clamps/Void

**Cause:** The lead-in point extends beyond the material or into an area occupied by clamps.

**Fix:**
1. Reduce lead-in distance in General Settings
2. Reposition the operation to allow clearance for lead-in
3. If cutting near edge, disable lead-in (`None`) for that project

### End Mill Breaking on Plunge

**Cause:** Vertical plunge with immediate lateral cut creates shock loading.

**Fix:**
1. Enable ramped lead-in in General Settings
2. Reduce feed rate or pass depth in material G-code standards
3. Ensure proper chip evacuation

## Best Practices

### Material Parameters

- Start with conservative (slower) parameters
- Test on scrap material first
- Increase speeds gradually
- Document what works for your setup

### Tool Management

- Use consistent naming conventions
- Remove tools you don't use
- Keep size units consistent (prefer inches for US)

### Machine Settings

- Measure actual travel limits, don't guess
- Leave a safety margin on limits
- Test G-code path on your actual CNC computer

### Backup

Periodically export your database or note your settings. If the database is reset, you'll need to re-enter all materials and G-code standards.

```bash
# SQLite backup (development)
cp instance/gcode.db instance/gcode_backup.db

# PostgreSQL backup (production)
heroku pg:backups:capture
```
