# G-Code Safety Features

This document describes the safety features implemented to prevent end mill breakage during G-code generation.

## Overview

End mills can break due to several factors:
- **Shock loading**: Vertical plunge followed by immediate lateral cut
- **Aggressive stepdown**: Pass depth too deep relative to tool diameter
- **High feed at corners**: Sharp direction changes stress the tool
- **First pass stress**: Initial engagement with material is most demanding
- **Arc dynamics**: Curved toolpaths have different cutting dynamics than straight lines

The safety features address each of these risks through configurable settings in the General Settings page.

## Feature Summary

| Feature | Default | Purpose |
|---------|---------|---------|
| Helical lead-in | Enabled | Spiral descent eliminates shock loading |
| First pass feed reduction | 70% | Reduces stress during initial engagement |
| Stepdown validation | 50% of tool diameter | Warns about aggressive pass depths |
| Corner slowdown | Enabled, 50% | Reduces feed at sharp direction changes |
| Arc slowdown | Enabled, 80% | Reduces feed on curved toolpaths |
| Input validation | Enabled | Warns about risky configurations |

---

## Modular Architecture

Safety features are implemented as a modular, composable system in `src/utils/safety/`. This architecture allows:

- **Independent testing**: Each feature has its own tests
- **Easy extension**: New safety features can be added without modifying core generator code
- **Settings-driven**: Each feature reads its own configuration
- **Composable**: Features chain together through a coordinator

### Module Structure

```
src/utils/safety/
├── __init__.py              # Public exports
├── base.py                  # FeedAdjuster protocol, FeedContext, SafetyCoordinator
├── first_pass.py            # First pass feed reduction
├── corner_slowdown.py       # Corner detection & slowdown
└── arc_slowdown.py          # Arc feed reduction
```

### FeedAdjuster Protocol

Each safety feature implements the `FeedAdjuster` protocol:

```python
class FeedAdjuster(Protocol):
    def adjust_feed(self, feed: float, context: FeedContext) -> float:
        """Return adjusted feed rate."""
        ...

    def is_enabled(self) -> bool:
        """Check if this adjuster is enabled."""
        ...
```

### FeedContext

All adjusters receive a `FeedContext` with information for their decision:

```python
@dataclass
class FeedContext:
    base_feed: float      # Original feed rate
    pass_num: int         # Zero-indexed pass number
    is_arc: bool = False  # True for G02/G03 moves
    corner_factor: float = 1.0  # Pre-calculated corner severity
```

### SafetyCoordinator

The coordinator chains adjusters and applies them in sequence:

```python
coordinator = create_safety_coordinator(settings)
context = FeedContext(base_feed=45.0, pass_num=0, is_arc=True)
adjusted_feed = coordinator.get_adjusted_feed(45.0, context)
```

Adjusters are applied in order: First Pass → Corner → Arc. Only enabled adjusters apply their reduction.

---

## Helical Lead-In

### What It Does

Instead of plunging vertically into the material, the tool spirals down in a helix pattern. This distributes the cutting forces and eliminates the shock of transitioning from vertical to lateral movement.

### Lead-In Types

| Type | Best For | Description |
|------|----------|-------------|
| **Helical** | Circles, Hexagons | Spiral descent using G02/G03 with Z movement |
| **Ramp** | Lines | Linear approach with simultaneous XY and Z |
| **None** | Not recommended | Vertical plunge (highest risk) |

### How Helical Works

**For Circles:**
1. Tool positions at helix start (3 o'clock position, inside the cut)
2. Spirals down using G02 arcs with Z movement
3. Arcs tangentially onto the circle profile at cutting depth
4. Cuts the full circle
5. Returns to helix position for next pass

**For Hexagons:**
1. Tool positions at helix start (center of hexagon + helix radius)
2. Spirals down using G02 arcs with Z movement
3. Linear move to first vertex at cutting depth
4. Cuts around all 6 vertices
5. Returns to helix position for next pass

### G-Code Output Example (Circle)

```gcode
G00 X2.1875 Y3.0000 Z0.2    ; Rapid to helix start
G00 Z0                       ; To surface
G02 X2.1875 Y3.0000 Z-0.04 I-0.1875 J0 F8.0  ; Helix revolution 1
G02 X2.1875 Y3.0000 Z-0.0625 I-0.1875 J0 F8.0  ; Helix to depth
G02 X2.5000 Y3.0000 I-0.1875 J0 F8.0  ; Arc onto profile
G02 I-0.5000 J0 F45.0        ; Cut circle
```

### Settings

| Setting | Default | Description |
|---------|---------|-------------|
| `lead_in_type` | `helical` | Entry strategy: 'helical', 'ramp', or 'none' |
| `lead_in_distance` | 0.25" | Distance for ramp approach (ramp mode only) |
| `helix_pitch` | 0.04" | Z descent per revolution |

### Fallback Behavior

If a circle or hexagon is too small for helical entry (helix radius would be < 0.05"), the system automatically falls back to ramp lead-in and adds a warning to the generation result.

### Per-Operation Lead-In Settings

Individual operations can override the global lead-in settings to customize the approach direction.

**Available Fields:**

| Field | Values | Description |
|-------|--------|-------------|
| `lead_in_mode` | `auto` / `manual` | Use global settings or override |
| `lead_in_type` | `helical` / `ramp` / `none` | Entry strategy (manual only) |
| `lead_in_approach_angle` | 0-360° | Direction tool approaches from (manual only) |

**Approach Angle Convention:**

| Angle | Position | Clock Position |
|-------|----------|----------------|
| 0° | Top | 12 o'clock |
| 90° | Right | 3 o'clock (default) |
| 180° | Bottom | 6 o'clock |
| 270° | Left | 9 o'clock |

The default 90° (3 o'clock) matches the original hardcoded behavior, ensuring backward compatibility.

**Use Cases:**

- Avoid clamping: Set approach angle to avoid collision with clamps or fixtures
- Material grain: Approach from a specific direction for better surface finish
- Obstruction avoidance: Route lead-in away from other features

**Example:**

To have a circle's lead-in approach from the top (12 o'clock):
1. Edit the circle operation
2. Change "Lead-In Settings" from "Auto" to "Manual"
3. Set "Approach Angle" to 0°

**How It Works:**

When `lead_in_mode` is `manual`:
- The profile start point is positioned at the approach angle on the circle/hexagon
- The lead-in point (for ramp) or helix start (for helical) is calculated based on that angle
- I/J offsets for G02/G03 arcs are adjusted accordingly

**Lines and Approach Angle:**

For line cuts with manual lead-in, the approach angle **fully overrides** the automatic path-based direction. The tool will approach from the specified angle regardless of path geometry.

### Implementation Files

- `src/utils/lead_in.py` - Helical calculation functions, angle conversion
- `src/utils/subroutine_generator.py` - Helical preamble for subroutines
- `src/gcode_generator.py` - Integration in circle/hexagon/line generation
- `tests/src/test_lead_in_angle.py` - Unit tests for angle calculations

---

## First Pass Feed Reduction

### What It Does

Reduces the cutting feed rate on the first pass of each operation. The first pass encounters the most resistance as the tool initially engages the material.

### How It Works

The `FirstPassAdjuster` checks if `pass_num == 0` and applies the reduction factor:

```python
class FirstPassAdjuster:
    def adjust_feed(self, feed: float, context: FeedContext) -> float:
        if context.pass_num == 0:
            return feed * self.settings.first_pass_feed_factor
        return feed
```

### Settings

| Setting | Default | Range | Description |
|---------|---------|-------|-------------|
| `first_pass_feed_factor` | 0.7 | 0.3-1.0 | Multiply feed by this on first pass |

### Applies To

- Circle cuts (inline and subroutine)
- Hexagon cuts (inline and subroutine)
- Line cuts (inline and subroutine)

### Implementation

- `src/utils/safety/first_pass.py` - FirstPassAdjuster class

---

## Stepdown Validation

### What It Does

Validates that the pass depth (stepdown) isn't dangerously aggressive relative to the tool diameter. Aggressive stepdowns can snap end mills.

### Validation Rules

| Condition | Result | Action |
|-----------|--------|--------|
| `pass_depth > tool_diameter` | **ERROR** | Blocks G-code generation |
| `pass_depth > tool_diameter * max_stepdown_factor` | **WARNING** | Allows generation with warning |
| `pass_depth <= tool_diameter * max_stepdown_factor` | OK | No message |

### Example

With a 0.125" end mill and `max_stepdown_factor = 0.5`:
- Pass depth 0.05" → OK (40% of tool diameter)
- Pass depth 0.08" → WARNING (64% of tool diameter)
- Pass depth 0.15" → ERROR (120% of tool diameter)

### Settings

| Setting | Default | Range | Description |
|---------|---------|-------|-------------|
| `max_stepdown_factor` | 0.5 | 0.25-1.0 | Warn if pass_depth exceeds this × tool_diameter |

### Implementation

- `src/utils/validators.py` - `validate_stepdown()` function
- `web/services/gcode_service.py` - Called during validation

---

## Corner Feed Reduction

### What It Does

Automatically reduces feed rate at sharp corners in line cuts. Sharp direction changes stress the tool and can cause deflection or breakage.

### How Corners Are Detected

The system analyzes the path to find points where consecutive segments change direction by more than a threshold angle (default 120°).

For each point in the path:
1. Calculate incoming direction (line or arc tangent)
2. Calculate outgoing direction (line or arc tangent)
3. Measure angle between directions
4. If angle < 120°, mark as corner with severity-based feed factor

### Corner Severity and Feed Factors

| Angle Range | Severity | Feed Factor |
|-------------|----------|-------------|
| 90-120° | Mild | 75% |
| 60-90° | Moderate | 50% |
| 30-60° | Sharp | 40% |
| < 30° | Very sharp | 30% |

The `CornerSlowdownAdjuster` applies: `feed × corner_feed_factor × severity_factor`

### Example

With `corner_feed_factor = 0.5` and a 60° corner (moderate, factor=0.5):
- Base feed: 45 in/min
- Corner feed: 45 × 0.5 × 0.5 = 11.25 in/min

### Settings

| Setting | Default | Description |
|---------|---------|-------------|
| `corner_slowdown_enabled` | true | Enable/disable corner detection |
| `corner_feed_factor` | 0.5 | Base feed reduction at corners |

### Applies To

- Line cuts with multiple segments
- Both straight-to-straight and arc-to-line transitions

### Note on Hexagons

Hexagons have fixed 120° internal angles (60° direction changes at each vertex). With the default threshold of 120°, hexagon corners are at the boundary and may not trigger slowdown. If needed, adjust settings for your specific use case.

### Implementation

- `src/utils/corner_detection.py` - Corner analysis functions
- `src/utils/safety/corner_slowdown.py` - CornerSlowdownAdjuster class

---

## Arc Feed Reduction

### What It Does

Automatically reduces feed rate on arc moves (G02/G03) to account for different cutting dynamics on curved toolpaths.

### Why Arcs Need Different Feed

Arcs have different cutting dynamics than straight lines:
- **Curved path**: The tool direction constantly changes
- **Chip load variation**: On interior cuts, the effective feed at the cutting edge can be higher
- **Engagement differences**: On exterior cuts, the tool may engage more material on one side
- **Machine dynamics**: Some machines handle rapid direction changes better at lower speeds

### How It Works

The `ArcSlowdownAdjuster` checks if the move is an arc and applies the reduction:

```python
class ArcSlowdownAdjuster:
    def adjust_feed(self, feed: float, context: FeedContext) -> float:
        if context.is_arc:
            return feed * self.settings.arc_feed_factor
        return feed
```

### Example

With `arc_feed_factor = 0.8`:
- Base feed: 45 in/min
- Arc feed: 45 × 0.8 = 36 in/min

### Settings

| Setting | Default | Range | Description |
|---------|---------|-------|-------------|
| `arc_slowdown_enabled` | true | - | Enable/disable arc slowdown |
| `arc_feed_factor` | 0.8 | 0.5-1.0 | Feed reduction on arcs (0.8 = 80% of normal) |

### Applies To

- Arc segments in line cuts (line_type='arc')
- Both G02 (CW) and G03 (CCW) arcs

### Combined with Other Safety Features

Arc slowdown combines with other safety features. For a first-pass arc at a corner:

```
base_feed × first_pass_factor × corner_factor × arc_factor
45 × 0.7 × 0.5 × 0.8 = 12.6 in/min
```

### Implementation

- `src/utils/safety/arc_slowdown.py` - ArcSlowdownAdjuster class

---

## Input Validation Warnings

### What It Does

Provides warnings for configurations that may be risky but don't prevent generation.

### Warnings Generated

| Condition | Warning Message |
|-----------|-----------------|
| Lead-in disabled for profile cuts | "Lead-in is disabled... increases risk of end mill breakage" |
| Plunge rate > feed rate | "Plunge rate exceeds feed rate - verify this is intentional" |
| Stepdown > 50% of tool diameter | "Pass depth is X% of tool diameter. Consider reducing." |

### When Warnings Appear

Warnings are collected during G-code generation and returned in the `GenerationResult.warnings` list. They're displayed to the user but don't block generation.

### Implementation

- `src/utils/validators.py` - `validate_feed_rates()` function
- `web/services/gcode_service.py` - `get_validation_warnings()` method

---

## UI Settings

All safety features are configurable in **Settings → General Settings**.

### Lead-In Settings Section

- **Lead-In Type**: Dropdown (Helical/Ramp/None) per cut type
- **Ramp Angle**: Input for ramp entry angle
- **Helix Pitch**: Input for Z drop per revolution

### Feed Rate Safety Section

- **First Pass Feed Reduction**: Factor input (0.3-1.0)
- **Max Stepdown Factor**: Factor input (0.25-1.0)

### Corner Slowdown Section

- **Enable Corner Slowdown**: Toggle switch
- **Corner Feed Factor**: Factor input (0.2-1.0)

### Arc Slowdown Section

- **Enable Arc Slowdown**: Toggle switch
- **Arc Feed Factor**: Factor input (0.5-1.0)

---

## Database Schema

Columns in `GeneralSettings` model:

```python
# Lead-in settings (per cut type)
circle_lead_in_type = db.Column(db.String(20), default='helical')
hexagon_lead_in_type = db.Column(db.String(20), default='helical')
line_lead_in_type = db.Column(db.String(20), default='ramp')
ramp_angle = db.Column(db.Float, default=3.0)
helix_pitch = db.Column(db.Float, default=0.04)

# First pass feed reduction
first_pass_feed_factor = db.Column(db.Float, default=0.7)

# Stepdown validation
max_stepdown_factor = db.Column(db.Float, default=0.5)

# Corner slowdown
corner_slowdown_enabled = db.Column(db.Boolean, default=True)
corner_feed_factor = db.Column(db.Float, default=0.5)

# Arc slowdown
arc_slowdown_enabled = db.Column(db.Boolean, default=True)
arc_feed_factor = db.Column(db.Float, default=0.8)
```

---

## Testing

Safety modules have comprehensive tests in `tests/src/test_safety/`:

```bash
# Run all safety tests
pytest tests/src/test_safety/ -v

# Run individual adjuster tests
pytest tests/src/test_safety/test_first_pass.py -v
pytest tests/src/test_safety/test_corner_slowdown.py -v
pytest tests/src/test_safety/test_arc_slowdown.py -v
pytest tests/src/test_safety/test_coordinator.py -v
```

---

## Best Practices

1. **Always use helical lead-in** for circles and hexagons
2. **Start with conservative settings** (defaults are good)
3. **Monitor warnings** - they indicate potential issues
4. **Test with air cuts** before cutting material
5. **Reduce stepdown** if you hear unusual sounds during cutting
6. **Enable arc slowdown** for paths with many arc segments

## Troubleshooting

| Issue | Possible Cause | Solution |
|-------|---------------|----------|
| "Too small for helical" warning | Feature diameter < tool + clearance | Use ramp lead-in or smaller tool |
| Excessive pass warnings | Aggressive material settings | Reduce pass_depth in material G-code standards |
| Slow cutting at corners | Corner slowdown too aggressive | Increase `corner_feed_factor` |
| Tool chatter on first pass | First pass still too fast | Decrease `first_pass_feed_factor` |
| Poor arc finish quality | Arc feed too high | Decrease `arc_feed_factor` |
| Arcs cutting too slowly | Arc feed too conservative | Increase `arc_feed_factor` |

## Extending Safety Features

To add a new safety feature:

1. Create a new file in `src/utils/safety/` (e.g., `new_feature.py`)
2. Implement the `FeedAdjuster` protocol with `adjust_feed()` and `is_enabled()` methods
3. Add the corresponding settings to `GeneralSettings` model and `GenerationSettings` dataclass
4. Register the adjuster in `create_safety_coordinator()` in `base.py`
5. Add UI controls to `templates/settings/general.html`
6. Write tests in `tests/src/test_safety/`
