"""Project management service."""
from datetime import datetime, UTC
from typing import Dict, List, Optional
import uuid

from web.extensions import db
from web.models import Project


# Empty operations structure
EMPTY_OPERATIONS = {
    'drill_holes': [],
    'circular_cuts': [],
    'hexagonal_cuts': [],
    'line_cuts': []
}


class ProjectService:
    """Service for managing projects."""

    @staticmethod
    def get_all() -> List[Project]:
        """Get all projects, ordered by modified_at descending."""
        return Project.query.order_by(Project.modified_at.desc()).all()

    @staticmethod
    def get(project_id: str) -> Optional[Project]:
        """Get a single project by UUID."""
        return Project.query.get(project_id)

    @staticmethod
    def get_as_dict(project_id: str) -> Optional[Dict]:
        """Get a project as dict for JSON serialization."""
        project = ProjectService.get(project_id)
        if not project:
            return None

        return {
            'id': project.id,
            'name': project.name,
            'project_type': project.project_type,
            'material_id': project.material_id,
            'drill_tool_id': project.drill_tool_id,
            'end_mill_tool_id': project.end_mill_tool_id,
            'operations': project.operations or EMPTY_OPERATIONS.copy(),
            'tube_void_skip': project.tube_void_skip,
            'working_length': project.working_length,
            'tube_orientation': project.tube_orientation,
            'created_at': project.created_at.isoformat() if project.created_at else None,
            'modified_at': project.modified_at.isoformat() if project.modified_at else None
        }

    @staticmethod
    def create(data: Dict) -> Project:
        """Create a new project with empty operations."""
        project = Project(
            id=str(uuid.uuid4()),
            name=data['name'],
            project_type=data['project_type'],
            material_id=data.get('material_id'),
            drill_tool_id=data.get('drill_tool_id'),
            end_mill_tool_id=data.get('end_mill_tool_id'),
            operations=EMPTY_OPERATIONS.copy(),
            tube_void_skip=data.get('tube_void_skip', False),
            working_length=data.get('working_length'),
            tube_orientation=data.get('tube_orientation')
        )
        db.session.add(project)
        db.session.commit()
        return project

    @staticmethod
    def save(project_id: str, data: Dict) -> Optional[Project]:
        """Update a project from editor data."""
        project = Project.query.get(project_id)
        if not project:
            return None

        if 'name' in data:
            project.name = data['name']
        if 'project_type' in data:
            project.project_type = data['project_type']
        if 'material_id' in data:
            project.material_id = data['material_id']
        if 'drill_tool_id' in data:
            project.drill_tool_id = data['drill_tool_id']
        if 'end_mill_tool_id' in data:
            project.end_mill_tool_id = data['end_mill_tool_id']
        if 'operations' in data:
            project.operations = data['operations']
        if 'tube_void_skip' in data:
            project.tube_void_skip = data['tube_void_skip']
        if 'working_length' in data:
            project.working_length = data['working_length']
        if 'tube_orientation' in data:
            project.tube_orientation = data['tube_orientation']

        project.modified_at = datetime.now(UTC)
        db.session.commit()
        return project

    @staticmethod
    def delete(project_id: str) -> bool:
        """Delete a project."""
        project = Project.query.get(project_id)
        if not project:
            return False

        db.session.delete(project)
        db.session.commit()
        return True

    @staticmethod
    def duplicate(project_id: str, new_name: Optional[str] = None) -> Optional[Project]:
        """Deep copy a project with a new UUID."""
        source = Project.query.get(project_id)
        if not source:
            return None

        # Generate new name
        name = new_name if new_name else f"{source.name} (Copy)"

        # Deep copy operations
        import copy
        operations_copy = copy.deepcopy(source.operations) if source.operations else EMPTY_OPERATIONS.copy()

        # Create new project
        project = Project(
            id=str(uuid.uuid4()),
            name=name,
            project_type=source.project_type,
            material_id=source.material_id,
            drill_tool_id=source.drill_tool_id,
            end_mill_tool_id=source.end_mill_tool_id,
            operations=operations_copy,
            tube_void_skip=source.tube_void_skip,
            working_length=source.working_length,
            tube_orientation=source.tube_orientation
        )
        db.session.add(project)
        db.session.commit()
        return project
