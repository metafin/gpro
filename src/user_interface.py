import os
from typing import List
from .gcode_generator import MachiningParameters, DrillParameters, CutParameters

def get_input_files() -> List[str]:
    """Get list of available input files."""
    input_dir = "input"
    if not os.path.exists(input_dir):
        return []
    
    files = [f for f in os.listdir(input_dir) if f.endswith('.txt')]
    return files

def select_input_file() -> str:
    """Prompt user to select an input file."""
    files = get_input_files()
    
    if not files:
        print("No input files found in the 'input' directory.")
        print("Please add a .txt file with your machining instructions.")
        exit(1)
    
    print("Available input files:")
    for i, file in enumerate(files, 1):
        print(f"{i}. {file}")
    
    while True:
        try:
            choice = int(input(f"\nSelect file (1-{len(files)}): ")) - 1
            if 0 <= choice < len(files):
                return os.path.join("input", files[choice])
            else:
                print(f"Please enter a number between 1 and {len(files)}")
        except ValueError:
            print("Please enter a valid number")

def get_machining_parameters() -> MachiningParameters:
    """Prompt user for machining parameters."""
    def get_float_input(prompt: str, default: float = None) -> float:
        while True:
            try:
                if default is not None:
                    user_input = input(f"{prompt} (default: {default}): ").strip()
                    if not user_input:
                        return default
                else:
                    user_input = input(f"{prompt}: ").strip()
                
                return float(user_input)
            except ValueError:
                print("Please enter a valid number")
    
    def get_int_input(prompt: str, default: int = None) -> int:
        while True:
            try:
                if default is not None:
                    user_input = input(f"{prompt} (default: {default}): ").strip()
                    if not user_input:
                        return default
                else:
                    user_input = input(f"{prompt}: ").strip()
                
                return int(user_input)
            except ValueError:
                print("Please enter a valid number")
    
    # Get drilling parameters
    print("\n=== DRILLING Parameters ===")
    print("Enter parameters for drilling operations:")
    
    drill_diameter = get_float_input("Drill bit diameter (inches)")
    drill_depth = get_float_input("Drill depth (inches)")
    drill_feed_rate = get_float_input("Drill feed rate (inches/min)", 2.0)
    drill_spindle_speed = get_int_input("Drill spindle speed (RPM)", 1000)
    drill_safe_height = get_float_input("Drill safe height above material (inches)", 0.2)
    drill_plunge_rate = get_float_input("Drill plunge rate (inches/min)", 1.0)
    
    drill_params = DrillParameters(
        drill_diameter=drill_diameter,
        material_depth=drill_depth,
        feed_rate=drill_feed_rate * 25.4,  # Convert to mm/min
        spindle_speed=drill_spindle_speed,
        safe_height=drill_safe_height * 25.4,  # Convert to mm
        plunge_rate=drill_plunge_rate * 25.4  # Convert to mm/min
    )
    
    # Get cutting parameters
    print("\n=== CUTTING Parameters ===")
    print("Enter parameters for cutting operations (circular cuts, hexagonal cuts, outlines):")
    
    mill_diameter = get_float_input("Mill bit diameter (inches)")
    cut_depth = get_float_input("Cut depth (inches)")
    path_depth = get_float_input("Path depth per pass (inches)", 0.02)
    cut_feed_rate = get_float_input("Cut feed rate (inches/min)", 3.0)
    cut_spindle_speed = get_int_input("Cut spindle speed (RPM)", 1200)
    cut_safe_height = get_float_input("Cut safe height above material (inches)", 0.2)
    cut_plunge_rate = get_float_input("Cut plunge rate (inches/min)", 1.5)
    
    cut_params = CutParameters(
        mill_diameter=mill_diameter,
        material_depth=cut_depth,
        path_depth=path_depth,
        feed_rate=cut_feed_rate * 25.4,  # Convert to mm/min
        spindle_speed=cut_spindle_speed,
        safe_height=cut_safe_height * 25.4,  # Convert to mm
        plunge_rate=cut_plunge_rate * 25.4  # Convert to mm/min
    )
    
    return MachiningParameters(
        drill_params=drill_params,
        cut_params=cut_params
    )

def display_summary(input_file: str, params: MachiningParameters, drill_file: str, cut_file: str):
    """Display a summary of the operation."""
    print(f"\n=== Operation Summary ===")
    print(f"Input file: {input_file}")
    print(f"Drill G-code file: {drill_file}")
    print(f"Cut G-code file: {cut_file}")
    
    print(f"\nDrilling Parameters:")
    print(f"  Drill diameter: {params.drill_params.drill_diameter} inches")
    print(f"  Drill depth: {params.drill_params.material_depth} inches")
    print(f"  Feed rate: {params.drill_params.feed_rate / 25.4:.2f} inches/min")
    print(f"  Spindle speed: {params.drill_params.spindle_speed} RPM")
    print(f"  Safe height: {params.drill_params.safe_height / 25.4:.2f} inches")
    print(f"  Plunge rate: {params.drill_params.plunge_rate / 25.4:.2f} inches/min")
    
    print(f"\nCutting Parameters:")
    print(f"  Mill diameter: {params.cut_params.mill_diameter} inches")
    print(f"  Cut depth: {params.cut_params.material_depth} inches")
    print(f"  Path depth per pass: {params.cut_params.path_depth} inches")
    print(f"  Feed rate: {params.cut_params.feed_rate / 25.4:.2f} inches/min")
    print(f"  Spindle speed: {params.cut_params.spindle_speed} RPM")
    print(f"  Safe height: {params.cut_params.safe_height / 25.4:.2f} inches")
    print(f"  Plunge rate: {params.cut_params.plunge_rate / 25.4:.2f} inches/min")
    
    confirm = input("\nProceed with G-code generation? (y/n): ").lower().strip()
    return confirm in ['y', 'yes']