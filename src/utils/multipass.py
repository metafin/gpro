"""Multi-pass depth calculation utilities."""
import math
from typing import Iterator, List, Tuple


def iter_passes(total_depth: float, pass_depth: float) -> Iterator[Tuple[int, float, float]]:
    """
    Iterate over passes, yielding pass information.

    Args:
        total_depth: Total material depth to cut through (inches)
        pass_depth: Maximum depth per pass (inches)

    Yields:
        Tuple of (pass_num, cumulative_depth, per_pass_depth):
        - pass_num: Zero-indexed pass number
        - cumulative_depth: Total depth at end of this pass
        - per_pass_depth: Depth increment per pass (same for all passes)
    """
    num_passes = calculate_num_passes(total_depth, pass_depth)
    per_pass = total_depth / num_passes
    for i in range(num_passes):
        yield i, (i + 1) * per_pass, per_pass


def calculate_num_passes(total_depth: float, pass_depth: float) -> int:
    """
    Calculate the number of passes needed for a given depth.

    Args:
        total_depth: Total material depth to cut through (inches)
        pass_depth: Maximum depth per pass (inches)

    Returns:
        Number of passes required (at least 1)
    """
    if pass_depth <= 0:
        return 1
    return max(1, math.ceil(total_depth / pass_depth))


def calculate_pass_depths(total_depth: float, pass_depth: float) -> List[float]:
    """
    Calculate cumulative depths for each pass.

    Returns evenly distributed pass depths that sum to total_depth.

    Args:
        total_depth: Total material depth to cut through (inches)
        pass_depth: Maximum depth per pass (inches)

    Returns:
        List of cumulative depths for each pass
    """
    num_passes = calculate_num_passes(total_depth, pass_depth)
    actual_pass_depth = total_depth / num_passes

    depths = []
    for i in range(1, num_passes + 1):
        depths.append(i * actual_pass_depth)

    return depths


def get_material_depth(material) -> float:
    """
    Get the relevant depth for a material.

    Args:
        material: Material object with form, thickness, and wall_thickness attributes

    Returns:
        thickness for sheets, wall_thickness for tubes
    """
    if material.form == 'tube':
        return material.wall_thickness or 0.125
    return material.thickness or 0.125
