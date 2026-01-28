"""Seed script to populate default settings data."""
from app import create_app
from web.extensions import db
from web.models import Material, MachineSettings, GeneralSettings, Tool


def seed_materials():
    """Seed default materials with G-code standards."""
    if Material.query.first():
        print("Materials already seeded, skipping...")
        return

    # Aluminum 6061-T6 gcode standards (midpoint values)
    aluminum_gcode_standards = {
        'drill': {
            '0.125': {'spindle_speed': 7000, 'feed_rate': 5.0, 'plunge_rate': 2.5, 'pecking_depth': 0.04},
            '0.1875': {'spindle_speed': 6000, 'feed_rate': 6.5, 'plunge_rate': 3.5, 'pecking_depth': 0.065},
            '0.25': {'spindle_speed': 5000, 'feed_rate': 8.0, 'plunge_rate': 4.5, 'pecking_depth': 0.09}
        },
        'end_mill_1flute': {
            '0.125': {'spindle_speed': 11000, 'feed_rate': 25.0, 'plunge_rate': 6.5, 'pass_depth': 0.045},
            '0.25': {'spindle_speed': 9000, 'feed_rate': 37.5, 'plunge_rate': 10.0, 'pass_depth': 0.0925}
        },
        'end_mill_2flute': {
            '0.125': {'spindle_speed': 11000, 'feed_rate': 37.5, 'plunge_rate': 6.5, 'pass_depth': 0.045},
            '0.1875': {'spindle_speed': 10000, 'feed_rate': 45.0, 'plunge_rate': 8.0, 'pass_depth': 0.0675},
            '0.25': {'spindle_speed': 9000, 'feed_rate': 57.5, 'plunge_rate': 10.0, 'pass_depth': 0.0925}
        }
    }

    # Polycarbonate gcode standards (midpoint values)
    polycarbonate_gcode_standards = {
        'drill': {
            '0.125': {'spindle_speed': 9000, 'feed_rate': 20.0, 'plunge_rate': 10.0, 'pecking_depth': 0.125},
            '0.1875': {'spindle_speed': 7000, 'feed_rate': 25.0, 'plunge_rate': 12.5, 'pecking_depth': 0.175},
            '0.25': {'spindle_speed': 6000, 'feed_rate': 32.5, 'plunge_rate': 15.0, 'pecking_depth': 0.225}
        },
        'end_mill_1flute': {
            '0.125': {'spindle_speed': 14000, 'feed_rate': 50.0, 'plunge_rate': 17.5, 'pass_depth': 0.0925},
            '0.25': {'spindle_speed': 12000, 'feed_rate': 80.0, 'plunge_rate': 25.0, 'pass_depth': 0.1875}
        },
        'end_mill_2flute': {
            '0.125': {'spindle_speed': 14000, 'feed_rate': 75.0, 'plunge_rate': 17.5, 'pass_depth': 0.0925},
            '0.1875': {'spindle_speed': 13000, 'feed_rate': 95.0, 'plunge_rate': 21.5, 'pass_depth': 0.13875},
            '0.25': {'spindle_speed': 12000, 'feed_rate': 115.0, 'plunge_rate': 25.0, 'pass_depth': 0.1875}
        }
    }

    materials = [
        {
            'id': 'aluminum_sheet_0125',
            'display_name': 'Aluminum Sheet 1/8"',
            'base_material': 'aluminum',
            'form': 'sheet',
            'thickness': 0.125,
            'gcode_standards': aluminum_gcode_standards
        },
        {
            'id': 'aluminum_sheet_025',
            'display_name': 'Aluminum Sheet 1/4"',
            'base_material': 'aluminum',
            'form': 'sheet',
            'thickness': 0.25,
            'gcode_standards': aluminum_gcode_standards
        },
        {
            'id': 'polycarbonate_sheet_025',
            'display_name': 'Polycarbonate Sheet 1/4"',
            'base_material': 'polycarbonate',
            'form': 'sheet',
            'thickness': 0.25,
            'gcode_standards': polycarbonate_gcode_standards
        },
        {
            'id': 'aluminum_tube_2x1_0125',
            'display_name': 'Aluminum Tube 2x1 (0.125 wall)',
            'base_material': 'aluminum',
            'form': 'tube',
            'outer_width': 2.0,
            'outer_height': 1.0,
            'wall_thickness': 0.125,
            'gcode_standards': aluminum_gcode_standards
        }
    ]

    for data in materials:
        material = Material(**data)
        db.session.add(material)

    db.session.commit()
    print(f"Seeded {len(materials)} materials")


def seed_machine_settings():
    """Seed default machine settings."""
    if MachineSettings.query.first():
        print("Machine settings already seeded, skipping...")
        return

    settings = MachineSettings(
        id=1,
        name='OMIO CNC',
        max_x=15.0,
        max_y=15.0,
        units='inches',
        controller_type='mach3',
        supports_subroutines=True,
        supports_canned_cycles=True,
        gcode_base_path='C:\\Mach3\\GCode'
    )
    db.session.add(settings)
    db.session.commit()
    print("Seeded machine settings")


def seed_general_settings():
    """Seed default general settings."""
    if GeneralSettings.query.first():
        print("General settings already seeded, skipping...")
        return

    settings = GeneralSettings(
        id=1,
        safety_height=0.5,
        travel_height=0.2,
        spindle_warmup_seconds=2,
        # Lead-in types per cut shape
        circle_lead_in_type='helical',
        hexagon_lead_in_type='helical',
        line_lead_in_type='ramp',
        # Lead-in parameters
        ramp_angle=3.0,
        helix_pitch=0.04,
        # Safety features
        first_pass_feed_factor=0.7,
        max_stepdown_factor=0.5,
        corner_slowdown_enabled=True,
        corner_feed_factor=0.5,
        arc_slowdown_enabled=True,
        arc_feed_factor=0.8,
        # Bounds
        allow_negative_coordinates=False,
        cut_through_buffer=0.01
    )
    db.session.add(settings)
    db.session.commit()
    print("Seeded general settings")


def seed_tools():
    """Seed default tools. Only adds tools that don't already exist (by type+size)."""
    tools = [
        # Drills (tip_compensation accounts for drill point geometry - ~0.3x diameter for 118° points)
        {'tool_type': 'drill', 'size': 0.125, 'size_unit': 'in', 'description': '1/8" drill bit', 'tip_compensation': 0.038},
        {'tool_type': 'drill', 'size': 0.1875, 'size_unit': 'in', 'description': '3/16" drill bit', 'tip_compensation': 0.056},
        {'tool_type': 'drill', 'size': 0.25, 'size_unit': 'in', 'description': '1/4" drill bit', 'tip_compensation': 0.075},
        # Single flute end mills - 1/8" DLC coated (12mm cut length)
        {'tool_type': 'end_mill_1flute', 'size': 0.125, 'size_unit': 'in', 'description': '1/8" 1-flute carbide (12mm cut, DLC)'},
        # Double flute end mills - McMaster carbide for aluminum
        {'tool_type': 'end_mill_2flute', 'size': 0.125, 'size_unit': 'in', 'description': '1/8" 2-flute carbide (3/8" cut) 8829A12'},
        {'tool_type': 'end_mill_2flute', 'size': 0.1875, 'size_unit': 'in', 'description': '3/16" 2-flute carbide (9/16" cut) 8829A16'},
        {'tool_type': 'end_mill_2flute', 'size': 0.25, 'size_unit': 'in', 'description': '1/4" 2-flute carbide (3/8" cut) 8829A19'},
    ]

    added_count = 0
    for data in tools:
        # Check if tool already exists by type and size
        existing = Tool.query.filter_by(
            tool_type=data['tool_type'],
            size=data['size']
        ).first()
        if not existing:
            tool = Tool(**data)
            db.session.add(tool)
            added_count += 1

    if added_count > 0:
        db.session.commit()
        print(f"Seeded {added_count} new tools")
    else:
        print("All tools already exist, none added")


def seed_all():
    """Run all seed functions."""
    print("Starting database seeding...")
    seed_machine_settings()
    seed_general_settings()
    seed_materials()
    seed_tools()
    print("Database seeding complete!")


if __name__ == '__main__':
    app = create_app()
    with app.app_context():
        seed_all()
