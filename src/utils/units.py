"""Unit conversion utilities."""


def inches_to_mm(value: float) -> float:
    """Convert inches to millimeters."""
    return value * 25.4


def mm_to_inches(value: float) -> float:
    """Convert millimeters to inches."""
    return value / 25.4
