"""G-code formatting utilities.

IMPORTANT: No function in this module generates comments.
All output is pure G-code for Mach3 compatibility.
"""
import re
from typing import List, Optional


def format_coordinate(value: float, precision: int = 4) -> str:
    """
    Format a coordinate value with appropriate decimal places.

    Args:
        value: The coordinate value
        precision: Number of decimal places (default 4)

    Returns:
        Formatted string representation
    """
    return f"{value:.{precision}f}"


def generate_header(
    spindle_speed: int,
    warmup_seconds: int,
    safety_height: float
) -> List[str]:
    """
    Generate standard G-code header lines.

    Args:
        spindle_speed: Spindle RPM
        warmup_seconds: Dwell time after spindle start
        safety_height: Z height for safe positioning

    Returns:
        List of G-code header lines (no comments)
    """
    return [
        "G20 G90",
        "G00 X0 Y0 Z0",
        f"G00 Z{format_coordinate(safety_height)}",
        f"M03 S{spindle_speed}",
        f"G04 P{warmup_seconds}",
    ]


def generate_footer(safety_height: float) -> List[str]:
    """
    Generate standard G-code footer lines.

    Args:
        safety_height: Z height for safe positioning

    Returns:
        List of G-code footer lines (no comments)
    """
    return [
        "M05",
        f"G00 Z{format_coordinate(safety_height)}",
        "G00 X0 Y0",
        "M30",
    ]


def generate_rapid_move(
    x: Optional[float] = None,
    y: Optional[float] = None,
    z: Optional[float] = None
) -> str:
    """
    Generate a G00 rapid move command.

    Args:
        x: X coordinate (optional)
        y: Y coordinate (optional)
        z: Z coordinate (optional)

    Returns:
        G00 command string
    """
    parts = ["G00"]
    if x is not None:
        parts.append(f"X{format_coordinate(x)}")
    if y is not None:
        parts.append(f"Y{format_coordinate(y)}")
    if z is not None:
        parts.append(f"Z{format_coordinate(z)}")
    return " ".join(parts)


def generate_linear_move(
    x: Optional[float] = None,
    y: Optional[float] = None,
    z: Optional[float] = None,
    feed: Optional[float] = None
) -> str:
    """
    Generate a G01 linear move command.

    Args:
        x: X coordinate (optional)
        y: Y coordinate (optional)
        z: Z coordinate (optional)
        feed: Feed rate (optional)

    Returns:
        G01 command string
    """
    parts = ["G01"]
    if x is not None:
        parts.append(f"X{format_coordinate(x)}")
    if y is not None:
        parts.append(f"Y{format_coordinate(y)}")
    if z is not None:
        parts.append(f"Z{format_coordinate(z)}")
    if feed is not None:
        parts.append(f"F{format_coordinate(feed, 1)}")
    return " ".join(parts)


def generate_arc_move(
    direction: str,
    x: float,
    y: float,
    i: float,
    j: float,
    feed: Optional[float] = None,
    z: Optional[float] = None
) -> str:
    """
    Generate a G02/G03 arc move command.

    Supports helical interpolation when Z is provided, enabling spiral
    descent into material (helical lead-in).

    Args:
        direction: "G02" for CW, "G03" for CCW
        x: Destination X coordinate
        y: Destination Y coordinate
        i: I offset (X distance to arc center)
        j: J offset (Y distance to arc center)
        feed: Feed rate (optional)
        z: Destination Z coordinate (optional, for helical interpolation)

    Returns:
        Arc command string
    """
    parts = [
        direction,
        f"X{format_coordinate(x)}",
        f"Y{format_coordinate(y)}"
    ]
    if z is not None:
        parts.append(f"Z{format_coordinate(z)}")
    parts.append(f"I{format_coordinate(i)}")
    parts.append(f"J{format_coordinate(j)}")
    if feed is not None:
        parts.append(f"F{format_coordinate(feed, 1)}")
    return " ".join(parts)


def generate_subroutine_call(file_path: str, loop_count: int) -> str:
    """
    Generate an M98 subroutine call command.

    Uses Mach3-required syntax with hyphen after opening parenthesis.

    Args:
        file_path: Full absolute path to subroutine file
        loop_count: Number of times to execute (L parameter)

    Returns:
        M98 command string
    """
    return f"M98 (-{file_path}) L{loop_count}"


def generate_subroutine_end() -> List[str]:
    """
    Generate subroutine end lines.

    Returns:
        List containing M99 and % (required for L parameter to work)
    """
    return ["M99", "%"]


def sanitize_project_name(name: str) -> str:
    """
    Clean project name for filesystem use.

    - Replace spaces with underscores
    - Remove special characters except underscores and hyphens
    - Truncate to 50 characters max

    Args:
        name: Original project name

    Returns:
        Sanitized name safe for filesystem
    """
    # Replace spaces with underscores
    sanitized = name.replace(" ", "_")

    # Remove special characters except underscores, hyphens, and alphanumerics
    sanitized = re.sub(r'[^a-zA-Z0-9_-]', '', sanitized)

    # Truncate to 50 characters
    return sanitized[:50]
