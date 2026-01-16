#!/usr/bin/env python3

import os
import sys
from src.file_parser import parse_input_file, ParseError
from src.gcode_generator import GCodeGenerator
from src.user_interface import select_input_file, get_machining_parameters, display_summary
from src.visualizer import plot_toolpath_preview, save_plot_preview

def main():
    """Main application entry point."""
    print("=== FIRST Robotics G-code Generator ===")
    print("Generate G-code for OMIO CNC from coordinate files\n")
    
    # Ensure output directory exists
    os.makedirs("output", exist_ok=True)
    
    while True:  # Loop to allow retry on parse errors
        try:
            # Select input file
            input_file = select_input_file()
            print(f"\nSelected input file: {input_file}")
            
            # Parse the input file
            print("Parsing input file...")
            instructions = parse_input_file(input_file)
            
            # Display what was found
            print("\nFound operations:")
            if instructions.drill_holes:
                print(f"- {len(instructions.drill_holes)} drill holes")
            if instructions.circular_cuts:
                print(f"- {len(instructions.circular_cuts)} circular cuts")
            if instructions.hexagonal_cuts:
                print(f"- {len(instructions.hexagonal_cuts)} hexagonal cuts")
            if instructions.outline_points:
                print(f"- {len(instructions.outline_points)} outline points")
            
            break  # Successfully parsed, exit retry loop
            
        except ParseError as e:
            print(f"\n❌ ERROR: Problem with input file format:")
            print(f"{str(e)}")
            print(f"\nPlease fix the input file and try again.")
            
            retry = input("\nWould you like to select a different file or retry? (y/n): ").lower().strip()
            if retry not in ['y', 'yes']:
                print("Exiting...")
                sys.exit(1)
            continue
        
        except Exception as e:
            print(f"\n❌ Unexpected error: {str(e)}")
            sys.exit(1)
    
    # Get machining parameters
    params = get_machining_parameters()
    
    # Generate output filenames
    input_filename = os.path.basename(input_file)
    base_name = os.path.splitext(input_filename)[0]
    drill_filename = f"{base_name}_drill.gcode"
    cut_filename = f"{base_name}_cut.gcode"
    drill_file = os.path.join("output", drill_filename)
    cut_file = os.path.join("output", cut_filename)
    
    # Display summary and confirm
    if not display_summary(input_file, params, drill_file, cut_file):
        print("Operation cancelled.")
        return
    
    try:
        # Generate G-code
        print("\nGenerating G-code...")
        generator = GCodeGenerator(params)
        
        # Generate drill G-code
        drill_gcode = generator.generate_drill_gcode(instructions)
        cut_gcode = generator.generate_cut_gcode(instructions)
        
        files_generated = []
        
        # Save drill G-code if there are drill operations
        if drill_gcode:
            with open(drill_file, 'w') as f:
                f.write(drill_gcode)
            print(f"✅ Drill G-code generated: {drill_file}")
            files_generated.append(("drill", drill_file, drill_gcode))
        else:
            print("ℹ️  No drill operations found - skipping drill G-code file")
        
        # Save cut G-code if there are cut operations
        if cut_gcode:
            with open(cut_file, 'w') as f:
                f.write(cut_gcode)
            print(f"✅ Cut G-code generated: {cut_file}")
            files_generated.append(("cut", cut_file, cut_gcode))
        else:
            print("ℹ️  No cut operations found - skipping cut G-code file")
        
        if not files_generated:
            print("❌ No operations found - no G-code files generated")
            return
        
        # Generate and optionally show visual preview
        show_plot = input("\nWould you like to see a visual preview of the toolpath? (y/n): ").lower().strip()
        if show_plot in ['y', 'yes']:
            try:
                print("Generating visual preview...")
                plot_filename = save_plot_preview(instructions, params, base_name)
                print(f"Plot saved to: {plot_filename}")
                
                # Show interactive plot
                plot_toolpath_preview(instructions, params)
            except ImportError:
                print("⚠️  Visual preview requires matplotlib. Install with: pip install matplotlib")
            except Exception as e:
                print(f"⚠️  Could not generate visual preview: {str(e)}")
        
        print(f"\nYou can now load the G-code files into your OMIO CNC machine.")
        print("Note: Run drill operations first, then change to the mill bit for cut operations.")
        
        # Optionally display the first few lines of G-code
        show_gcode_preview = input("\nWould you like to see a preview of the generated G-code text? (y/n): ").lower().strip()
        if show_gcode_preview in ['y', 'yes']:
            for operation_type, filename, gcode in files_generated:
                lines = gcode.split('\n')
                print(f"\n--- {operation_type.upper()} G-code Preview (first 10 lines) ---")
                for i, line in enumerate(lines[:10]):
                    print(f"{i+1:2d}: {line}")
                if len(lines) > 10:
                    print(f"... ({len(lines) - 10} more lines)")
                print()
        
    except Exception as e:
        print(f"\n❌ Error generating G-code: {str(e)}")
        sys.exit(1)

if __name__ == "__main__":
    main()