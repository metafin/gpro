import re
from typing import List, Tuple, Dict, Any
from dataclasses import dataclass

class ParseError(Exception):
    """Custom exception for parsing errors."""
    pass

@dataclass
class DrillPoint:
    x: float
    y: float

@dataclass
class CircularCut:
    x: float
    y: float
    diameter: float

@dataclass
class HexagonalCut:
    x: float
    y: float
    diameter: float

@dataclass
class OutlinePoint:
    x: float
    y: float

@dataclass
class ParsedInstructions:
    drill_holes: List[DrillPoint]
    circular_cuts: List[CircularCut]
    hexagonal_cuts: List[HexagonalCut]
    outline_points: List[OutlinePoint]

def parse_input_file(file_path: str) -> ParsedInstructions:
    """Parse the input file and extract all machining instructions."""
    try:
        with open(file_path, 'r') as f:
            content = f.read()
    except FileNotFoundError:
        raise ParseError(f"Input file not found: {file_path}")
    except Exception as e:
        raise ParseError(f"Error reading file {file_path}: {str(e)}")
    
    if not content.strip():
        raise ParseError("Input file is empty")
    
    drill_holes = []
    circular_cuts = []
    hexagonal_cuts = []
    outline_points = []
    errors = []
    
    # Split on lines that start with known section headers
    section_headers = ['Drill Holes', 'Circular cut', 'Hexagonal cut', 'Outline points']
    
    # Find section boundaries
    lines = content.strip().split('\n')
    sections = []
    current_section = []
    
    for line in lines:
        line = line.strip()
        if not line:
            continue
            
        # Check if this line is a section header
        is_header = any(header.lower() in line.lower() for header in section_headers)
        
        if is_header and current_section:
            # Start of new section, save the previous one
            sections.append('\n'.join(current_section))
            current_section = [line]
        elif is_header:
            # First section
            current_section = [line]
        else:
            # Add to current section
            current_section.append(line)
    
    # Don't forget the last section
    if current_section:
        sections.append('\n'.join(current_section))
    
    for section_num, section in enumerate(sections, 1):
        lines = [line.strip() for line in section.split('\n') if line.strip()]
        if not lines:
            continue
            
        header = lines[0].lower()
        
        try:
            if 'drill holes' in header:
                if len(lines) < 3:
                    errors.append(f"Section '{lines[0]}': Missing coordinate data (expected X,Y header and coordinates)")
                    continue
                drill_holes = _parse_coordinate_section(lines[2:], DrillPoint, f"Drill Holes section")
            elif 'circular cut' in header:
                if len(lines) < 4:
                    errors.append(f"Section '{lines[0]}': Missing diameter or coordinate data")
                    continue
                diameter = _extract_diameter(lines[1], f"Circular cut section")
                coords = _parse_coordinate_section(lines[3:], lambda x, y: CircularCut(x, y, diameter), f"Circular cut section")
                circular_cuts.extend(coords)
            elif 'hexagonal cut' in header:
                if len(lines) < 4:
                    errors.append(f"Section '{lines[0]}': Missing diameter or coordinate data")
                    continue
                diameter = _extract_diameter(lines[1], f"Hexagonal cut section")
                coords = _parse_coordinate_section(lines[3:], lambda x, y: HexagonalCut(x, y, diameter), f"Hexagonal cut section")
                hexagonal_cuts.extend(coords)
            elif 'outline points' in header:
                if len(lines) < 3:
                    errors.append(f"Section '{lines[0]}': Missing coordinate data (expected X,Y header and coordinates)")
                    continue
                outline_points = _parse_coordinate_section(lines[2:], OutlinePoint, f"Outline points section")
            else:
                errors.append(f"Unknown section type: '{lines[0]}'. Expected: 'Drill Holes', 'Circular cut', 'Hexagonal cut', or 'Outline points'")
        except ParseError as e:
            errors.append(str(e))
    
    if errors:
        error_msg = "Errors found in input file:\n" + "\n".join(f"- {error}" for error in errors)
        raise ParseError(error_msg)
    
    # Validate that we have at least some operations
    total_ops = len(drill_holes) + len(circular_cuts) + len(hexagonal_cuts) + len(outline_points)
    if total_ops == 0:
        raise ParseError("No valid machining operations found in input file")
    
    return ParsedInstructions(drill_holes, circular_cuts, hexagonal_cuts, outline_points)

def _extract_diameter(line: str, section_name: str = "section") -> float:
    """Extract diameter value from a line like 'Diameter: 0.8'."""
    match = re.search(r'diameter:\s*([\d.]+)', line.lower())
    if match:
        try:
            return float(match.group(1))
        except ValueError:
            raise ParseError(f"{section_name}: Invalid diameter value '{match.group(1)}' - must be a number")
    raise ParseError(f"{section_name}: Could not find diameter in line '{line}'. Expected format: 'Diameter: 0.8'")

def _parse_coordinate_section(lines: List[str], point_class, section_name: str = "section") -> List:
    """Parse coordinate lines and create point objects."""
    points = []
    errors = []
    
    valid_coord_lines = 0
    for line_num, line in enumerate(lines, 1):
        if line.startswith('X,Y'):
            continue  # Skip header line
        
        if ',' not in line:
            continue  # Skip non-coordinate lines
        
        valid_coord_lines += 1
        try:
            parts = line.split(',')
            if len(parts) != 2:
                errors.append(f"Line {line_num} in {section_name}: Expected 2 coordinates (X,Y), got {len(parts)} in '{line}'")
                continue
            
            x_str, y_str = parts
            x = float(x_str.strip())
            y = float(y_str.strip())
            points.append(point_class(x, y))
        except ValueError as e:
            errors.append(f"Line {line_num} in {section_name}: Invalid coordinate '{line}' - coordinates must be numbers")
    
    if errors:
        raise ParseError("\n".join(errors))
    
    if valid_coord_lines == 0:
        raise ParseError(f"{section_name}: No coordinate lines found. Expected format: 'X,Y' header followed by coordinate pairs like '1.25,0.5'")
    
    if len(points) == 0:
        raise ParseError(f"{section_name}: No valid coordinates found")
    
    return points