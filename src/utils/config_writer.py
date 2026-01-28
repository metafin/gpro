"""Config file generation for debugging G-code output."""
import os
import json
from datetime import datetime
from typing import Dict, Any


def write_config_file(directory: str, config_data: Dict[str, Any]) -> str:
    """
    Write a config.txt file with generation settings for debugging.

    Args:
        directory: Project output directory
        config_data: Dict containing all settings used for generation

    Returns:
        Full path to the written file
    """
    file_path = os.path.join(directory, "config.txt")
    content = format_config(config_data)

    with open(file_path, 'w') as f:
        f.write(content)

    return file_path


def format_config(config_data: Dict[str, Any]) -> str:
    """Format config data as readable text."""
    lines = []
    lines.append("=" * 60)
    lines.append("G-CODE GENERATION CONFIG")
    lines.append(f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    lines.append("=" * 60)
    lines.append("")

    _format_project_section(lines, config_data.get('project', {}))
    _format_material_section(lines, config_data.get('material', {}))
    _format_tool_section(lines, config_data.get('tool', {}))
    _format_gcode_params_section(lines, config_data.get('gcode_params', {}))
    _format_machine_section(lines, config_data.get('machine', {}))
    _format_general_section(lines, config_data.get('general', {}))
    _format_operations_section(lines, config_data.get('operations', {}))

    lines.append("=" * 60)
    lines.append("END CONFIG")
    lines.append("=" * 60)

    return '\n'.join(lines)


def _format_project_section(lines: list, project: Dict) -> None:
    """Format project info section."""
    lines.append("-" * 40)
    lines.append("PROJECT")
    lines.append("-" * 40)
    lines.append(f"Name: {project.get('name', 'N/A')}")
    lines.append(f"Type: {project.get('type', 'N/A')}")
    lines.append(f"Tube Void Skip: {project.get('tube_void_skip', False)}")
    lines.append("")


def _format_material_section(lines: list, material: Dict) -> None:
    """Format material info section."""
    lines.append("-" * 40)
    lines.append("MATERIAL")
    lines.append("-" * 40)
    lines.append(f"Name: {material.get('display_name', 'N/A')}")
    lines.append(f"Base Material: {material.get('base_material', 'N/A')}")
    lines.append(f"Form: {material.get('form', 'N/A')}")
    if material.get('form') == 'sheet':
        lines.append(f"Thickness: {material.get('thickness', 'N/A')} in")
    elif material.get('form') == 'tube':
        lines.append(f"Outer Width: {material.get('outer_width', 'N/A')} in")
        lines.append(f"Outer Height: {material.get('outer_height', 'N/A')} in")
        lines.append(f"Wall Thickness: {material.get('wall_thickness', 'N/A')} in")
    lines.append("")


def _format_tool_section(lines: list, tool: Dict) -> None:
    """Format tool info section."""
    lines.append("-" * 40)
    lines.append("TOOL")
    lines.append("-" * 40)
    lines.append(f"Type: {tool.get('tool_type', 'N/A')}")
    lines.append(f"Size: {tool.get('size', 'N/A')} {tool.get('size_unit', 'in')}")
    if tool.get('description'):
        lines.append(f"Description: {tool.get('description')}")
    if tool.get('tip_compensation'):
        lines.append(f"Tip Compensation: {tool.get('tip_compensation')} in")
    lines.append("")


def _format_gcode_params_section(lines: list, params: Dict) -> None:
    """Format G-code parameters section."""
    lines.append("-" * 40)
    lines.append("G-CODE PARAMETERS")
    lines.append("-" * 40)
    lines.append(f"Spindle Speed: {params.get('spindle_speed', 'N/A')} RPM")
    lines.append(f"Feed Rate: {params.get('feed_rate', 'N/A')} in/min")
    lines.append(f"Plunge Rate: {params.get('plunge_rate', 'N/A')} in/min")
    if params.get('pecking_depth'):
        lines.append(f"Pecking Depth: {params.get('pecking_depth')} in")
    if params.get('pass_depth'):
        lines.append(f"Pass Depth: {params.get('pass_depth')} in")
    lines.append(f"Material Depth: {params.get('material_depth', 'N/A')} in")
    lines.append("")


def _format_machine_section(lines: list, machine: Dict) -> None:
    """Format machine settings section."""
    lines.append("-" * 40)
    lines.append("MACHINE SETTINGS")
    lines.append("-" * 40)
    lines.append(f"Name: {machine.get('name', 'N/A')}")
    lines.append(f"Max X: {machine.get('max_x', 'N/A')} in")
    lines.append(f"Max Y: {machine.get('max_y', 'N/A')} in")
    lines.append(f"Controller: {machine.get('controller_type', 'N/A')}")
    lines.append(f"Supports Subroutines: {machine.get('supports_subroutines', 'N/A')}")
    lines.append(f"Supports Canned Cycles: {machine.get('supports_canned_cycles', 'N/A')}")
    lines.append(f"G-code Base Path: {machine.get('gcode_base_path', 'N/A')}")
    lines.append("")


def _format_general_section(lines: list, general: Dict) -> None:
    """Format general settings section."""
    lines.append("-" * 40)
    lines.append("GENERAL SETTINGS")
    lines.append("-" * 40)
    lines.append(f"Safety Height: {general.get('safety_height', 'N/A')} in")
    lines.append(f"Travel Height: {general.get('travel_height', 'N/A')} in")
    lines.append(f"Spindle Warmup: {general.get('spindle_warmup_seconds', 'N/A')} sec")
    lines.append("")


def _format_operations_section(lines: list, operations: Dict) -> None:
    """Format raw operations section."""
    lines.append("-" * 40)
    lines.append("RAW OPERATIONS (as entered)")
    lines.append("-" * 40)
    lines.append(json.dumps(operations, indent=2))
    lines.append("")
