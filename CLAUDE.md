# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview
A Python application that generates G-code for OMIO CNC machines from text-based coordinate files. Built for FIRST Robotics teams to create custom metal parts.

## Development Environment
- Python virtual environment located in `.venv/`
- PyCharm IDE configuration in `.idea/`
- Python 3.13 is the target version
- Dependencies: matplotlib, numpy

## Common Commands

```bash
# Activate virtual environment
source .venv/bin/activate

# Install dependencies
pip install -r requirements.txt

# Run the main application
python main.py

# Format code (if black is installed)
black .

# Lint code (if flake8/pylint is installed)
flake8 .
```

## Project Structure

```
├── input/           # Text files with machining instructions
├── output/          # Generated G-code and preview plots
├── src/             # Source code modules
│   ├── file_parser.py      # Parse input text files
│   ├── gcode_generator.py  # Generate G-code from instructions
│   ├── user_interface.py   # Interactive parameter prompts
│   └── visualizer.py       # Plot toolpath previews
└── main.py          # Main application entry point
```

## Input File Format
Text files support these operations:
- **Drill Holes**: X,Y coordinates for drilling
- **Circular cut**: Diameter + X,Y center coordinates
- **Hexagonal cut**: Diameter + X,Y center coordinates  
- **Outline points**: X,Y coordinates for cutting path

## Architecture Notes
- `file_parser.py` handles input validation with detailed error messages
- `gcode_generator.py` converts coordinates from inches to mm and generates CNC commands
- `visualizer.py` creates matplotlib plots for toolpath verification
- Main application flow includes error handling and user confirmation steps
- All coordinates in input files are expected in inches
- G-code output uses millimeters (standard for OMIO CNC)