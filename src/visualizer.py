import matplotlib.pyplot as plt
import numpy as np
import math
from .file_parser import ParsedInstructions
from .gcode_generator import MachiningParameters

def plot_toolpath_preview(instructions: ParsedInstructions, params: MachiningParameters, 
                         output_file: str = None, dpi: int = 300, font_size: int = 8):
    """
    Generate a visual preview of the CNC toolpath based on parsed instructions.
    
    Args:
        instructions: Parsed machining instructions
        params: Machining parameters for scaling/display
        output_file: Optional path to save the plot
        dpi: Plot resolution
        font_size: Font size for annotations
    """
    fig, ax = plt.subplots(figsize=(10, 8), dpi=dpi)
    
    # Convert all coordinates to mm for consistent plotting
    def inches_to_mm(val):
        return val * 25.4
    
    # Plot outline/toolpath if available
    if instructions.outline_points:
        outline_coords = [(inches_to_mm(p.x), inches_to_mm(p.y)) for p in instructions.outline_points]
        x_vals, y_vals = zip(*outline_coords)
        ax.plot(x_vals, y_vals, marker='o', linestyle='-', color='blue', 
                markersize=4, linewidth=2, label="Outline Cut")
        
        # Annotate outline points
        for i, (x, y) in enumerate(outline_coords):
            ax.text(x, y + 2, f"({instructions.outline_points[i].x:.2f}, {instructions.outline_points[i].y:.2f})", 
                   fontsize=font_size, verticalalignment='bottom', horizontalalignment='center',
                   rotation=0, color='blue')
    
    # Plot circular cuts
    if instructions.circular_cuts:
        for i, cut in enumerate(instructions.circular_cuts):
            cx_mm = inches_to_mm(cut.x)
            cy_mm = inches_to_mm(cut.y)
            radius_mm = inches_to_mm(cut.diameter / 2)
            
            circle = plt.Circle((cx_mm, cy_mm), radius_mm, color='red', fill=False, 
                              linewidth=2, linestyle='--',
                              label="Circular Cuts" if i == 0 else "")
            ax.add_patch(circle)
            
            # Add center point
            ax.plot(cx_mm, cy_mm, 'r+', markersize=8, markeredgewidth=2)
            
            # Annotate
            ax.text(cx_mm, cy_mm + radius_mm + 3, 
                   f"⊕{cut.diameter:.2f}\" at ({cut.x:.2f}, {cut.y:.2f})", 
                   fontsize=font_size, verticalalignment='bottom', horizontalalignment='center',
                   color='red')
    
    # Plot hexagonal cuts
    if instructions.hexagonal_cuts:
        for i, cut in enumerate(instructions.hexagonal_cuts):
            cx_mm = inches_to_mm(cut.x)
            cy_mm = inches_to_mm(cut.y)
            radius_mm = inches_to_mm(cut.diameter / 2)
            
            # Calculate hexagon vertices
            hex_x = []
            hex_y = []
            for j in range(7):  # 7 points to close the hexagon
                angle = j * math.pi / 3
                x = cx_mm + radius_mm * math.cos(angle)
                y = cy_mm + radius_mm * math.sin(angle)
                hex_x.append(x)
                hex_y.append(y)
            
            ax.plot(hex_x, hex_y, color='green', linewidth=2, linestyle='-.',
                   label="Hexagonal Cuts" if i == 0 else "")
            
            # Add center point
            ax.plot(cx_mm, cy_mm, 'g+', markersize=8, markeredgewidth=2)
            
            # Annotate
            ax.text(cx_mm, cy_mm + radius_mm + 3, 
                   f"⬡{cut.diameter:.2f}\" at ({cut.x:.2f}, {cut.y:.2f})", 
                   fontsize=font_size, verticalalignment='bottom', horizontalalignment='center',
                   color='green')
    
    # Plot drill holes
    if instructions.drill_holes:
        drill_radius_mm = inches_to_mm(params.drill_params.drill_diameter / 2)
        
        for hole in instructions.drill_holes:
            dx_mm = inches_to_mm(hole.x)
            dy_mm = inches_to_mm(hole.y)
            
            # Draw drill hole as filled circle
            drill_circle = plt.Circle((dx_mm, dy_mm), drill_radius_mm, 
                                    color='black', alpha=0.7)
            ax.add_patch(drill_circle)
            
            # Add center cross
            ax.plot(dx_mm, dy_mm, 'w+', markersize=6, markeredgewidth=1)
        
        # Add single label for all drill holes
        if instructions.drill_holes:
            ax.scatter([], [], s=100, color='black', alpha=0.7, 
                     label=f"Drill Holes (⌀{params.drill_params.drill_diameter:.3f}\")")
    
    # Set up the plot
    ax.set_xlabel("X-axis (mm)", fontsize=font_size + 2)
    ax.set_ylabel("Y-axis (mm)", fontsize=font_size + 2)
    ax.set_title(f"CNC Toolpath Preview\nDrill: ⌀{params.drill_params.drill_diameter:.3f}\" (depth: {params.drill_params.material_depth:.3f}\"), Mill: ⌀{params.cut_params.mill_diameter:.3f}\" (depth: {params.cut_params.material_depth:.3f}\")", 
                fontsize=font_size + 4)
    ax.legend(fontsize=font_size)
    ax.grid(True, alpha=0.3)
    ax.set_aspect('equal', adjustable='datalim')
    
    # Add some padding around the plot
    ax.margins(0.1)
    
    # Add coordinate system indicator
    ax.text(0.02, 0.98, "Origin (0,0)", transform=ax.transAxes, 
           fontsize=font_size, verticalalignment='top', horizontalalignment='left',
           bbox=dict(boxstyle="round,pad=0.3", facecolor="yellow", alpha=0.7))
    
    # Add statistics text box
    stats_text = f"Operations Summary:\n"
    if instructions.drill_holes:
        stats_text += f"• {len(instructions.drill_holes)} drill holes\n"
    if instructions.circular_cuts:
        stats_text += f"• {len(instructions.circular_cuts)} circular cuts\n"
    if instructions.hexagonal_cuts:
        stats_text += f"• {len(instructions.hexagonal_cuts)} hexagonal cuts\n"
    if instructions.outline_points:
        stats_text += f"• {len(instructions.outline_points)} outline points"
    
    ax.text(0.02, 0.02, stats_text, transform=ax.transAxes, 
           fontsize=font_size, verticalalignment='bottom', horizontalalignment='left',
           bbox=dict(boxstyle="round,pad=0.5", facecolor="lightblue", alpha=0.8))
    
    plt.tight_layout()
    
    if output_file:
        plt.savefig(output_file, dpi=dpi, bbox_inches='tight')
        print(f"Plot saved to: {output_file}")
    
    plt.show()

def save_plot_preview(instructions: ParsedInstructions, params: MachiningParameters, 
                     base_filename: str):
    """
    Save a plot preview to the output directory.
    
    Args:
        instructions: Parsed machining instructions
        params: Machining parameters
        base_filename: Base name for the output file (without extension)
    """
    import os
    output_dir = "output"
    plot_filename = os.path.join(output_dir, f"{base_filename}_preview.png")
    
    # Create the plot without showing it
    plt.ioff()  # Turn off interactive mode
    plot_toolpath_preview(instructions, params, plot_filename, dpi=150, font_size=10)
    plt.ion()  # Turn interactive mode back on
    
    return plot_filename