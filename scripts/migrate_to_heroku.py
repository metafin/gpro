#!/usr/bin/env python3
"""Migrate local data to Heroku PostgreSQL."""

import os
import sys

# Add parent directory to path for imports
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app import create_app
from web.extensions import db
from web.models import Tool, Material, MachineSettings, GeneralSettings, Project

# Data exported from local database

TOOLS = [
    {"id": 11, "tool_type": "drill", "size": 0.125, "size_unit": "in", "description": '1/8" drill bit', "tip_compensation": None},
    {"id": 12, "tool_type": "drill", "size": 0.1875, "size_unit": "in", "description": '3/16" drill bit', "tip_compensation": None},
    {"id": 13, "tool_type": "drill", "size": 0.25, "size_unit": "in", "description": '1/4" drill bit', "tip_compensation": None},
    {"id": 20, "tool_type": "drill", "size": 0.14, "size_unit": "in", "description": "9/16 bit", "tip_compensation": None},
    {"id": 21, "tool_type": "drill", "size": 0.156, "size_unit": "in", "description": '5/32"', "tip_compensation": 0.05},
    {"id": 14, "tool_type": "end_mill_1flute", "size": 0.125, "size_unit": "in", "description": '1/8" 1-flute carbide (12mm cut, DLC)', "tip_compensation": None},
    {"id": 17, "tool_type": "end_mill_2flute", "size": 0.125, "size_unit": "in", "description": '1/8" 2-flute carbide (3/8" cut) 8829A12', "tip_compensation": None},
    {"id": 18, "tool_type": "end_mill_2flute", "size": 0.1875, "size_unit": "in", "description": '3/16" 2-flute carbide (9/16" cut) 8829A16', "tip_compensation": None},
    {"id": 19, "tool_type": "end_mill_2flute", "size": 0.25, "size_unit": "in", "description": '1/4" 2-flute carbide (3/8" cut) 8829A19', "tip_compensation": None},
]

MATERIALS = [
    {
        "id": "aluminum_sheet_025",
        "display_name": 'Aluminum Sheet 1/4"',
        "base_material": "aluminum",
        "form": "sheet",
        "thickness": 0.25,
        "outer_width": None,
        "outer_height": None,
        "wall_thickness": None,
        "gcode_standards": {"drill": {"0.125": {"spindle_speed": 7000, "feed_rate": 5.0, "plunge_rate": 2.5, "pecking_depth": 0.04}, "0.14": {"spindle_speed": 6000, "feed_rate": 6.0, "plunge_rate": 3.0, "pecking_depth": 0.05}, "0.156": {"spindle_speed": 7000, "feed_rate": 6.0, "plunge_rate": 10.0, "pecking_depth": 0.13}, "0.1875": {"spindle_speed": 6000, "feed_rate": 6.5, "plunge_rate": 3.5, "pecking_depth": 0.065}, "0.25": {"spindle_speed": 6000, "feed_rate": 17.0, "plunge_rate": 6.0, "pecking_depth": 0.1}}, "end_mill_1flute": {"0.125": {"spindle_speed": 11000, "feed_rate": 25.0, "plunge_rate": 6.5, "pass_depth": 0.045}}, "end_mill_2flute": {"0.125": {"spindle_speed": 11000, "feed_rate": 37.5, "plunge_rate": 6.5, "pass_depth": 0.045}, "0.1875": {"spindle_speed": 10000, "feed_rate": 45.0, "plunge_rate": 8.0, "pass_depth": 0.0675}, "0.25": {"spindle_speed": 6500, "feed_rate": 22.0, "plunge_rate": 10.0, "pass_depth": 0.0405}}}
    },
    {
        "id": "aluminum_sheet_0125",
        "display_name": 'Aluminum Sheet 1/8"',
        "base_material": "aluminum",
        "form": "sheet",
        "thickness": 0.125,
        "outer_width": None,
        "outer_height": None,
        "wall_thickness": None,
        "gcode_standards": {"drill": {"0.125": {"spindle_speed": 7000, "feed_rate": 5.0, "plunge_rate": 2.5, "pecking_depth": 0.04}, "0.1875": {"spindle_speed": 6000, "feed_rate": 6.5, "plunge_rate": 3.5, "pecking_depth": 0.065}, "0.25": {"spindle_speed": 5000, "feed_rate": 8.0, "plunge_rate": 4.5, "pecking_depth": 0.09}}, "end_mill_1flute": {"0.125": {"spindle_speed": 11000, "feed_rate": 25.0, "plunge_rate": 6.5, "pass_depth": 0.045}, "0.25": {"spindle_speed": 9000, "feed_rate": 37.5, "plunge_rate": 10.0, "pass_depth": 0.0925}}, "end_mill_2flute": {"0.125": {"spindle_speed": 11000, "feed_rate": 37.5, "plunge_rate": 6.5, "pass_depth": 0.045}, "0.1875": {"spindle_speed": 10000, "feed_rate": 45.0, "plunge_rate": 8.0, "pass_depth": 0.0675}, "0.25": {"spindle_speed": 9000, "feed_rate": 57.5, "plunge_rate": 10.0, "pass_depth": 0.0925}}}
    },
    {
        "id": "polycarbonate_sheet_025",
        "display_name": 'Polycarbonate Sheet 1/4"',
        "base_material": "polycarbonate",
        "form": "sheet",
        "thickness": 0.25,
        "outer_width": None,
        "outer_height": None,
        "wall_thickness": None,
        "gcode_standards": {"drill": {"0.125": {"spindle_speed": 9000, "feed_rate": 20.0, "plunge_rate": 10.0, "pecking_depth": 0.125}, "0.1875": {"spindle_speed": 7000, "feed_rate": 25.0, "plunge_rate": 12.5, "pecking_depth": 0.175}, "0.25": {"spindle_speed": 6000, "feed_rate": 32.5, "plunge_rate": 15.0, "pecking_depth": 0.225}}, "end_mill_1flute": {"0.125": {"spindle_speed": 14000, "feed_rate": 50.0, "plunge_rate": 17.5, "pass_depth": 0.0925}, "0.25": {"spindle_speed": 12000, "feed_rate": 80.0, "plunge_rate": 25.0, "pass_depth": 0.1875}}, "end_mill_2flute": {"0.125": {"spindle_speed": 14000, "feed_rate": 75.0, "plunge_rate": 17.5, "pass_depth": 0.0925}, "0.1875": {"spindle_speed": 13000, "feed_rate": 95.0, "plunge_rate": 21.5, "pass_depth": 0.13875}, "0.25": {"spindle_speed": 12000, "feed_rate": 115.0, "plunge_rate": 25.0, "pass_depth": 0.1875}}}
    },
    {
        "id": "aluminum_tube_2x1_0125",
        "display_name": "Aluminum Tube 2x1 (0.125 wall)",
        "base_material": "aluminum",
        "form": "tube",
        "thickness": None,
        "outer_width": 2.0,
        "outer_height": 1.0,
        "wall_thickness": 0.125,
        "gcode_standards": {"drill": {"0.125": {"spindle_speed": 7000, "feed_rate": 5.0, "plunge_rate": 2.5, "pecking_depth": 0.04}, "0.1875": {"spindle_speed": 6000, "feed_rate": 6.5, "plunge_rate": 3.5, "pecking_depth": 0.065}, "0.25": {"spindle_speed": 5000, "feed_rate": 8.0, "plunge_rate": 4.5, "pecking_depth": 0.09}}, "end_mill_1flute": {"0.125": {"spindle_speed": 11000, "feed_rate": 25.0, "plunge_rate": 6.5, "pass_depth": 0.045}, "0.25": {"spindle_speed": 9000, "feed_rate": 37.5, "plunge_rate": 10.0, "pass_depth": 0.0925}}, "end_mill_2flute": {"0.125": {"spindle_speed": 11000, "feed_rate": 37.5, "plunge_rate": 6.5, "pass_depth": 0.045}, "0.1875": {"spindle_speed": 10000, "feed_rate": 45.0, "plunge_rate": 8.0, "pass_depth": 0.0675}, "0.25": {"spindle_speed": 9000, "feed_rate": 57.5, "plunge_rate": 10.0, "pass_depth": 0.0925}}}
    },
    {
        "id": "polycarb_sheet_1_8",
        "display_name": 'Polycarbonate Sheet 1/8"',
        "base_material": "polycarbonate",
        "form": "sheet",
        "thickness": None,
        "outer_width": 0.001,
        "outer_height": None,
        "wall_thickness": None,
        "gcode_standards": {"end_mill_1flute": {"0.125": {"spindle_speed": 10000, "feed_rate": 40.0, "plunge_rate": 10.0, "pass_depth": 0.07}}}
    },
]

MACHINE_SETTINGS = {
    "id": 1,
    "name": "OMIO CNC",
    "max_x": 25.0,
    "max_y": 32.0,
    "units": "inches",
    "controller_type": "mach3",
    "supports_subroutines": True,
    "supports_canned_cycles": True,
    "gcode_base_path": r"C:\Mach3\GCode\FPRO"
}

GENERAL_SETTINGS = {
    "id": 1,
    "safety_height": 0.5,
    "travel_height": 0.2,
    "spindle_warmup_seconds": 2,
    "helix_pitch": 0.04,
    "first_pass_feed_factor": 0.7,
    "max_stepdown_factor": 0.5,
    "corner_slowdown_enabled": True,
    "corner_feed_factor": 0.5,
    "allow_negative_coordinates": True,
    "circle_lead_in_type": "helical",
    "hexagon_lead_in_type": "helical",
    "line_lead_in_type": "ramp",
    "cut_through_buffer": 0.02,
    "ramp_angle": 3.0,
    "arc_slowdown_enabled": True,
    "arc_feed_factor": 0.8
}

PROJECTS = [
    {
        "id": "5070ea26-87c2-4981-a88c-b800b7b07310",
        "name": "Base Plate Holes",
        "project_type": "drill",
        "material_id": "aluminum_sheet_025",
        "drill_tool_id": 21,
        "end_mill_tool_id": None,
        "tube_void_skip": False,
        "working_length": None,
        "tube_orientation": None,
        "tube_axis": None,
        "operations": {"drill_holes": [{"id": "op_1768958311883_d2rp68nxc", "type": "single", "x": 0.75, "y": 0.75}, {"id": "op_1768958326114_nph19vx4s", "type": "single", "x": 1.25, "y": 0.75}, {"id": "op_1768958334976_a79nsh99a", "type": "single", "x": 0.75, "y": 1.25}, {"id": "op_1768958391718_yz2jhujg2", "type": "single", "x": 4.25, "y": 0.75}, {"id": "op_1768958533104_wkvnuoq8d", "type": "pattern_grid", "start_x": 4.75, "start_y": 0.75, "x_spacing": 0.5, "y_spacing": 0.5, "x_count": 8, "y_count": 1}, {"id": "op_1768958619457_bf02yo3hd", "type": "single", "x": 7.75, "y": 1.75}, {"id": "op_1768958700051_1gmffenj2", "type": "pattern_grid", "start_x": 8.25, "start_y": 1.75, "x_spacing": 0.5, "y_spacing": 0.5, "x_count": 1, "y_count": 9}, {"id": "op_1768958789643_oje8fxzdc", "type": "single", "x": 0.75, "y": 4.25}, {"id": "op_1768958807611_3vvvfrzta", "type": "single", "x": 0.75, "y": 4.75}, {"id": "op_1768958823226_pbjeukr8r", "type": "single", "x": 1.25, "y": 4.75}, {"id": "op_1768958861528_wkliqypbr", "type": "pattern_grid", "start_x": 0.75, "start_y": 5.25, "x_spacing": 0.5, "y_spacing": 0.5, "x_count": 8, "y_count": 2}, {"id": "op_1768958980181_bnpklogge", "type": "pattern_linear", "start_x": 4.75, "start_y": 5.75, "axis": "x", "spacing": 0.5, "count": 6}, {"id": "op_1768959096029_289wqjinr", "type": "pattern_grid", "start_x": 7.25, "start_y": 5.25, "x_spacing": 0.5, "y_spacing": 0.5, "x_count": 2, "y_count": 2}, {"id": "op_1768959944135_ndz7w4x9e", "type": "pattern_grid", "start_x": 0.75, "start_y": 24.75, "x_spacing": 0.5, "y_spacing": 0.5, "x_count": 8, "y_count": 2}, {"id": "op_1768960012751_afdewv3bk", "type": "pattern_linear", "start_x": 0.75, "start_y": 25.75, "axis": "x", "spacing": 0.5, "count": 2}, {"id": "op_1768960136079_vwnbq3lvw", "type": "single", "x": 0.75, "y": 26.25}, {"id": "op_1768960214153_6e9uf5q0v", "type": "pattern_linear", "start_x": 4.75, "start_y": 24.75, "axis": "x", "spacing": 0.5, "count": 6}, {"id": "op_1768960263348_up0iocl6q", "type": "single", "x": 7.75, "y": 24.75}, {"id": "op_1768960295053_as8msb9hb", "type": "pattern_linear", "start_x": 8.25, "start_y": 24.75, "axis": "y", "spacing": 0.5, "count": 9}, {"id": "op_1768960343651_63ibf83gw", "type": "single", "x": 0.75, "y": 29.25}, {"id": "op_1768960543201_acw3xxtn7", "type": "pattern_linear", "start_x": 0.75, "start_y": 29.75, "axis": "x", "spacing": 0.5, "count": 2}, {"id": "op_1768960601839_x8ph9hxzc", "type": "pattern_linear", "start_x": 4.25, "start_y": 29.75, "axis": "x", "spacing": 0.5, "count": 9}, {"id": "op_1768960695205_8zgzme04a", "type": "pattern_linear", "start_x": 4.75, "start_y": 29.25, "axis": "x", "spacing": 0.5, "count": 2}, {"id": "op_1768960792902_1txux7dqx", "type": "pattern_linear", "start_x": 7.25, "start_y": 25.25, "axis": "x", "spacing": 0.5, "count": 2}, {"id": "op_1769211934157_hhwhu02o2", "type": "pattern_linear", "start_x": 4.75, "start_y": 1.25, "axis": "x", "spacing": 0.5, "count": 2}, {"id": "op_1769211984844_im7pthykm", "type": "pattern_linear", "start_x": 6.75, "start_y": 1.25, "axis": "x", "spacing": 0.5, "count": 4}, {"id": "op_1769214003004_21n373d57", "type": "pattern_linear", "start_x": 6.75, "start_y": 29.25, "axis": "x", "spacing": 0.5, "count": 4}, {"id": "op_1769214064537_py8dt6o4a", "type": "single", "x": 7.75, "y": 28.75}, {"id": "op_1769214096844_fsti815dm", "type": "single", "x": 7.75, "y": 25.75}], "circular_cuts": [], "hexagonal_cuts": [], "line_cuts": []}
    },
    {
        "id": "95e8bb54-445c-4cd9-b1be-b6f294a54a6d",
        "name": "Base Plate Holes 2",
        "project_type": "drill",
        "material_id": "aluminum_sheet_025",
        "drill_tool_id": 21,
        "end_mill_tool_id": None,
        "tube_void_skip": False,
        "working_length": None,
        "tube_orientation": None,
        "tube_axis": "x",
        "operations": {"drill_holes": [{"id": "op_1769025192604_2rx1v2s3w", "type": "pattern_grid", "start_x": 0.75, "start_y": 6.25, "x_spacing": 0.5, "y_spacing": 0.5, "x_count": 16, "y_count": 37}], "circular_cuts": [], "hexagonal_cuts": [], "line_cuts": []}
    },
    {
        "id": "973a8b90-59c5-4787-818c-4ebb9c434aeb",
        "name": "Base Plate Holes 3",
        "project_type": "drill",
        "material_id": "aluminum_sheet_025",
        "drill_tool_id": 21,
        "end_mill_tool_id": None,
        "tube_void_skip": False,
        "working_length": None,
        "tube_orientation": None,
        "tube_axis": "x",
        "operations": {"drill_holes": [{"id": "op_1769025249230_dn9eiptn6", "type": "pattern_grid", "start_x": 8.75, "start_y": 0.75, "x_spacing": 0.5, "y_spacing": 0.5, "x_count": 8, "y_count": 59}], "circular_cuts": [], "hexagonal_cuts": [], "line_cuts": []}
    },
    {
        "id": "9bf95685-eb02-424f-84ca-d96538fdd46b",
        "name": "V Feed Prototype 2",
        "project_type": "cut",
        "material_id": "polycarb_sheet_1_8",
        "drill_tool_id": None,
        "end_mill_tool_id": 14,
        "tube_void_skip": False,
        "working_length": None,
        "tube_orientation": None,
        "tube_axis": "x",
        "operations": {"drill_holes": [], "circular_cuts": [{"id": "op_1769557972230_olb9a9v3r", "diameter": 1.125, "compensation": "interior", "hold_time": 0, "lead_in_mode": "auto", "type": "single", "center_x": 1.766, "center_y": 2.137}, {"id": "op_1769558010240_iurkeanup", "diameter": 1.125, "compensation": "interior", "hold_time": 0, "lead_in_mode": "auto", "type": "single", "center_x": 3.587, "center_y": 3.212}, {"id": "op_1769558041244_twlzs9yve", "diameter": 1.125, "compensation": "interior", "hold_time": 0, "lead_in_mode": "auto", "type": "single", "center_x": 1.5, "center_y": 8.25}, {"id": "op_1769558061514_pbkorvzjm", "diameter": 1.125, "compensation": "interior", "hold_time": 0, "lead_in_mode": "auto", "type": "single", "center_x": 6.694, "center_y": 1.125}, {"id": "op_1769558083674_956hooikd", "diameter": 1.125, "compensation": "interior", "hold_time": 0, "lead_in_mode": "auto", "type": "single", "center_x": 8.625, "center_y": 1.125}, {"id": "op_1769558119194_1o0prv1hn", "diameter": 1.125, "compensation": "interior", "hold_time": 0, "lead_in_mode": "auto", "type": "single", "center_x": 8.625, "center_y": 8.25}], "hexagonal_cuts": [], "line_cuts": [{"id": "op_1769557152000_3q7xmolom", "points": [{"x": 5, "y": 0, "line_type": "start"}, {"x": 10.125, "y": 0, "line_type": "straight"}, {"x": 10.125, "y": 9.375, "line_type": "straight"}, {"x": 0, "y": 9.375, "line_type": "straight"}, {"x": 0, "y": 0, "line_type": "straight"}, {"x": 5, "y": 0, "line_type": "straight"}], "compensation": "exterior", "hold_time": 0, "lead_in_mode": "manual", "lead_in_type": "ramp", "lead_in_approach_angle": 270}]}
    },
    {
        "id": "fb6bc0f3-570e-407c-a9e4-49882c4fa50a",
        "name": "Base Plate Cut Real",
        "project_type": "cut",
        "material_id": "aluminum_sheet_025",
        "drill_tool_id": None,
        "end_mill_tool_id": 19,
        "tube_void_skip": False,
        "working_length": None,
        "tube_orientation": None,
        "tube_axis": "x",
        "operations": {"drill_holes": [], "circular_cuts": [], "hexagonal_cuts": [], "line_cuts": [{"id": "op_1769289471426_a2emz7xgg", "points": [{"x": 4.482, "y": 1.333, "line_type": "start"}, {"x": 3.881, "y": 4.339, "line_type": "arc", "arc_center_x": 5.625, "arc_center_y": 3.125, "arc_direction": "ccw"}, {"x": 4.482, "y": 1.333, "line_type": "arc", "arc_center_x": 2.5, "arc_center_y": 2.5, "arc_direction": "ccw"}], "compensation": "interior", "lead_in_mode": "manual", "lead_in_type": "ramp", "lead_in_approach_angle": 310, "hold_time": 10}, {"id": "op_1769239745774_xtl0noc4q", "points": [{"x": 4.482, "y": 28.667, "line_type": "start"}, {"x": 3.881, "y": 25.661, "line_type": "arc", "arc_center_x": 2.5, "arc_center_y": 27.5, "arc_direction": "ccw"}, {"x": 4.482, "y": 28.667, "line_type": "arc", "arc_center_x": 5.625, "arc_center_y": 26.875, "arc_direction": "ccw"}], "compensation": "interior", "lead_in_mode": "manual", "lead_in_type": "ramp", "lead_in_approach_angle": 160, "hold_time": 10}, {"id": "op_1769239538870_4imrfvwmb", "points": [{"x": 5, "y": 0.1, "line_type": "start"}, {"x": 11.975, "y": 0.1, "line_type": "straight"}, {"x": 12.225, "y": 0.25, "line_type": "straight"}, {"x": 12.225, "y": 29.75, "line_type": "straight"}, {"x": 11.975, "y": 29.9, "line_type": "straight"}, {"x": 0.25, "y": 29.9, "line_type": "straight"}, {"x": 0.1, "y": 29.75, "line_type": "arc", "arc_center_x": 0.25, "arc_center_y": 29.75, "arc_direction": "ccw"}, {"x": 0.1, "y": 0.25, "line_type": "straight"}, {"x": 0.25, "y": 0.1, "line_type": "arc", "arc_center_x": 0.25, "arc_center_y": 0.25, "arc_direction": "ccw"}, {"x": 5, "y": 0.1, "line_type": "straight"}], "compensation": "exterior", "lead_in_mode": "manual", "lead_in_type": "ramp", "lead_in_approach_angle": 270, "hold_time": 20}]}
    },
]


def migrate():
    """Run the migration."""
    app = create_app()

    with app.app_context():
        print("Starting migration...")

        # Insert tools
        print(f"Inserting {len(TOOLS)} tools...")
        for tool_data in TOOLS:
            tool = Tool(**tool_data)
            db.session.merge(tool)
        db.session.commit()
        print("Tools inserted.")

        # Insert materials
        print(f"Inserting {len(MATERIALS)} materials...")
        for mat_data in MATERIALS:
            material = Material(**mat_data)
            db.session.merge(material)
        db.session.commit()
        print("Materials inserted.")

        # Insert machine settings
        print("Inserting machine settings...")
        machine = MachineSettings(**MACHINE_SETTINGS)
        db.session.merge(machine)
        db.session.commit()
        print("Machine settings inserted.")

        # Insert general settings
        print("Inserting general settings...")
        general = GeneralSettings(**GENERAL_SETTINGS)
        db.session.merge(general)
        db.session.commit()
        print("General settings inserted.")

        # Insert projects
        print(f"Inserting {len(PROJECTS)} projects...")
        for proj_data in PROJECTS:
            project = Project(**proj_data)
            db.session.merge(project)
        db.session.commit()
        print("Projects inserted.")

        print("Migration complete!")


if __name__ == "__main__":
    migrate()
