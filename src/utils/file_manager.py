"""Output directory and file management utilities."""
import os
import io
import zipfile
from typing import Optional


def create_output_directory(base_path: str, project_name: str) -> str:
    """
    Create the output directory for a project's G-code files.

    Args:
        base_path: Base G-code directory path
        project_name: Sanitized project name

    Returns:
        Full path to the created directory
    """
    directory = os.path.join(base_path, project_name)
    os.makedirs(directory, exist_ok=True)
    return directory


def write_main_file(directory: str, content: str) -> str:
    """
    Write the main G-code file.

    Args:
        directory: Project output directory
        content: G-code content

    Returns:
        Full path to the written file
    """
    file_path = os.path.join(directory, "main.tap")
    with open(file_path, 'w') as f:
        f.write(content)
    return file_path


def write_subroutine_file(directory: str, number: int, content: str) -> str:
    """
    Write a subroutine file.

    Args:
        directory: Project output directory
        number: Subroutine number (used as filename)
        content: Subroutine content

    Returns:
        Full path to the written file
    """
    file_path = os.path.join(directory, f"{number}.nc")
    with open(file_path, 'w') as f:
        f.write(content)
    return file_path


def package_for_download(directory: str) -> bytes:
    """
    Create a zip archive of the G-code directory.

    Args:
        directory: Project output directory to zip

    Returns:
        Bytes of the zip archive
    """
    buffer = io.BytesIO()

    with zipfile.ZipFile(buffer, 'w', zipfile.ZIP_DEFLATED) as zf:
        for root, dirs, files in os.walk(directory):
            for file in files:
                file_path = os.path.join(root, file)
                # Use relative path in archive
                arcname = os.path.relpath(file_path, os.path.dirname(directory))
                zf.write(file_path, arcname)

    buffer.seek(0)
    return buffer.read()


def read_gcode_file(file_path: str) -> Optional[str]:
    """
    Read a G-code file.

    Args:
        file_path: Path to the G-code file

    Returns:
        File content as string, or None if file doesn't exist
    """
    if not os.path.exists(file_path):
        return None

    with open(file_path, 'r') as f:
        return f.read()


def list_project_files(directory: str) -> dict:
    """
    List all G-code files in a project directory.

    Args:
        directory: Project output directory

    Returns:
        Dict with 'main' path and 'subroutines' list of paths
    """
    result = {
        'main': None,
        'subroutines': []
    }

    if not os.path.exists(directory):
        return result

    for filename in os.listdir(directory):
        file_path = os.path.join(directory, filename)

        if filename == 'main.tap':
            result['main'] = file_path
        elif filename.endswith('.nc'):
            result['subroutines'].append(file_path)

    # Sort subroutines by number
    result['subroutines'].sort()

    return result


def cleanup_project_directory(directory: str) -> bool:
    """
    Remove a project's G-code directory and all files.

    Args:
        directory: Project output directory to remove

    Returns:
        True if successfully removed
    """
    import shutil

    if not os.path.exists(directory):
        return True

    try:
        shutil.rmtree(directory)
        return True
    except OSError:
        return False
