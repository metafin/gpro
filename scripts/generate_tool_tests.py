#!/usr/bin/env python3
"""
Generate test G-code files for end mill calibration.

This script generates G-code for the "End Mill Tool Test" project using
three different parameter sets (very_safe, medium, optimal) for each
end mill tool. The output can be used to calibrate cutting parameters
by running actual cuts and observing the results.

Usage:
    python scripts/generate_tool_tests.py

Output:
    Creates G-code files in the configured gcode_base_path from machine settings.
    Each test generates a folder like: End_Mill_Tool_Test_1-8_2flute_very_safe/
"""
import os
import sys

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app import create_app
from web.models import Project, Tool
from web.services.gcode_service import GCodeService
from src.gcode_generator import ToolParams
from src.utils.file_manager import create_output_directory, write_main_file, write_subroutine_file


# Test parameters for each tool
# Format: {tool_id: {level: {spindle_speed, feed_rate, plunge_rate, pass_depth}}}
TEST_PARAMETERS = {
    # 1/8" Single Flute (0.125")
    14: {
        'very_safe': {
            'spindle_speed': 6000,
            'feed_rate': 5,
            'plunge_rate': 2,
            'pass_depth': 0.020,
        },
        'medium': {
            'spindle_speed': 9000,
            'feed_rate': 9,
            'plunge_rate': 3,
            'pass_depth': 0.035,
        },
        'optimal': {
            'spindle_speed': 11000,
            'feed_rate': 13,
            'plunge_rate': 5,
            'pass_depth': 0.050,
        },
    },
    # 1/8" 2-Flute (0.125")
    17: {
        'very_safe': {
            'spindle_speed': 6000,
            'feed_rate': 10,
            'plunge_rate': 3,
            'pass_depth': 0.020,
        },
        'medium': {
            'spindle_speed': 9000,
            'feed_rate': 18,
            'plunge_rate': 6,
            'pass_depth': 0.035,
        },
        'optimal': {
            'spindle_speed': 11000,
            'feed_rate': 26,
            'plunge_rate': 9,
            'pass_depth': 0.050,
        },
    },
    # 3/16" 2-Flute (0.1875")
    18: {
        'very_safe': {
            'spindle_speed': 5000,
            'feed_rate': 10,
            'plunge_rate': 3,
            'pass_depth': 0.030,
        },
        'medium': {
            'spindle_speed': 7500,
            'feed_rate': 20,
            'plunge_rate': 7,
            'pass_depth': 0.050,
        },
        'optimal': {
            'spindle_speed': 9500,
            'feed_rate': 30,
            'plunge_rate': 10,
            'pass_depth': 0.075,
        },
    },
    # 1/4" 2-Flute (0.25")
    19: {
        'very_safe': {
            'spindle_speed': 4000,
            'feed_rate': 8,
            'plunge_rate': 3,
            'pass_depth': 0.040,
        },
        'medium': {
            'spindle_speed': 6000,
            'feed_rate': 17,
            'plunge_rate': 6,
            'pass_depth': 0.070,
        },
        'optimal': {
            'spindle_speed': 8000,
            'feed_rate': 29,
            'plunge_rate': 10,
            'pass_depth': 0.100,
        },
    },
}

# Human-readable tool names
TOOL_NAMES = {
    14: '1-8_1flute',
    17: '1-8_2flute',
    18: '3-16_2flute',
    19: '1-4_2flute',
}

TEST_PROJECT_NAME = 'End Mill Tool Test'


def generate_test_files():
    """Generate all test G-code files."""
    app = create_app()

    with app.app_context():
        # Load the test project
        project = Project.query.filter_by(name=TEST_PROJECT_NAME).first()
        if not project:
            print(f"Error: Project '{TEST_PROJECT_NAME}' not found")
            print("Please create the test project first via the web UI")
            return False

        print(f"Loaded project: {project.name}")
        print(f"  Type: {project.project_type}")
        print(f"  Material: {project.material.display_name if project.material else 'None'}")
        print()

        # Get machine settings for output path
        from web.services.settings_service import SettingsService
        machine = SettingsService.get_machine_settings()
        base_path = machine.gcode_base_path

        files_generated = []

        for tool_id, levels in TEST_PARAMETERS.items():
            tool = Tool.query.get(tool_id)
            if not tool:
                print(f"Warning: Tool ID {tool_id} not found, skipping")
                continue

            tool_name = TOOL_NAMES.get(tool_id, f'tool_{tool_id}')
            print(f"Generating for {tool.description} ({tool_name}):")

            for level, params in levels.items():
                # Build ToolParams with test values
                cut_params = ToolParams(
                    spindle_speed=params['spindle_speed'],
                    feed_rate=params['feed_rate'],
                    plunge_rate=params['plunge_rate'],
                    pass_depth=params['pass_depth'],
                    tool_diameter=tool.size
                )

                # Generate project name suffix
                suffix = f"_{tool_name}_{level}"

                try:
                    # Generate G-code using the real service with custom params
                    result = GCodeService.generate_with_params(
                        project=project,
                        cut_params=cut_params,
                        project_name_suffix=suffix,
                        skip_validation=True  # Skip validation since we're using custom params
                    )

                    # Create output directory
                    output_dir = create_output_directory(base_path, result.project_name)

                    # Write main file
                    main_path = write_main_file(output_dir, result.main_gcode)

                    # Write subroutines
                    for number, content in result.subroutines.items():
                        write_subroutine_file(output_dir, number, content)

                    files_generated.append({
                        'tool': tool.description,
                        'level': level,
                        'path': output_dir,
                        'params': params
                    })

                    print(f"  {level}: {output_dir}")

                    if result.warnings:
                        for warning in result.warnings:
                            print(f"    Warning: {warning}")

                except Exception as e:
                    print(f"  {level}: ERROR - {e}")

            print()

        # Print summary
        print("=" * 60)
        print("SUMMARY")
        print("=" * 60)
        print(f"Generated {len(files_generated)} test files in {base_path}")
        print()

        # Print parameter table for reference
        print("Test Parameters:")
        print("-" * 60)
        print(f"{'Tool':<20} {'Level':<12} {'RPM':<8} {'Feed':<8} {'Plunge':<8} {'DOC':<8}")
        print("-" * 60)

        for item in files_generated:
            p = item['params']
            print(f"{TOOL_NAMES[list(TOOL_NAMES.keys())[list(TOOL_NAMES.values()).index(item['tool'].split()[0].replace('\"', '').replace('/', '-') + '_' + ('1flute' if '1-flute' in item['tool'] else '2flute'))]] if False else item['tool'][:18]:<20} "
                  f"{item['level']:<12} "
                  f"{p['spindle_speed']:<8} "
                  f"{p['feed_rate']:<8} "
                  f"{p['plunge_rate']:<8} "
                  f"{p['pass_depth']:<8}")

        return True


def print_test_order():
    """Print recommended test order."""
    print()
    print("=" * 60)
    print("RECOMMENDED TEST ORDER")
    print("=" * 60)
    print("""
For each tool, run tests in this order:

1. VERY SAFE first
   - Observe: chip formation, sound, surface finish
   - Should be: quiet, small chips, possibly slow

2. MEDIUM second
   - Compare to very_safe results
   - Should be: reasonable chips, moderate sound

3. OPTIMAL last
   - Only if medium looked good
   - Watch for: chatter, excessive noise, tool deflection

Signs of problems:
- High-pitched squeal = rubbing (feed too slow or spindle too fast)
- Deep chatter = too aggressive (reduce feed or DOC)
- Dust instead of chips = feed too slow
- Gummy buildup on tool = spindle too slow or no coolant/air

After testing, update the material's gcode_standards in the database
with your preferred parameters.
""")


if __name__ == '__main__':
    print("=" * 60)
    print("END MILL TOOL TEST GENERATOR")
    print("=" * 60)
    print()

    success = generate_test_files()

    if success:
        print_test_order()
