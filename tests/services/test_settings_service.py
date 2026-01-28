"""Tests for SettingsService."""
import pytest

from web.services.settings_service import SettingsService
from web.models import Material, MachineSettings, GeneralSettings, Tool


class TestMaterialMethods:
    """Tests for material-related methods."""

    def test_get_all_materials_empty(self, app):
        """Test getting materials when none exist."""
        with app.app_context():
            materials = SettingsService.get_all_materials()
            assert materials == []

    def test_get_all_materials(self, app, sample_material):
        """Test getting all materials."""
        with app.app_context():
            materials = SettingsService.get_all_materials()
            assert len(materials) == 1
            assert materials[0].id == 'test_aluminum_0125'

    def test_get_material(self, app, sample_material):
        """Test getting a single material by ID."""
        with app.app_context():
            material = SettingsService.get_material('test_aluminum_0125')
            assert material is not None
            assert material.display_name == 'Test Aluminum 1/8"'
            assert material.form == 'sheet'

    def test_get_material_not_found(self, app):
        """Test getting a non-existent material."""
        with app.app_context():
            material = SettingsService.get_material('nonexistent')
            assert material is None

    def test_get_materials_dict(self, app, sample_material):
        """Test getting materials as dict for JSON."""
        with app.app_context():
            materials_dict = SettingsService.get_materials_dict()
            assert 'test_aluminum_0125' in materials_dict
            assert materials_dict['test_aluminum_0125']['display_name'] == 'Test Aluminum 1/8"'
            assert materials_dict['test_aluminum_0125']['thickness'] == 0.125

    def test_create_material(self, app):
        """Test creating a new material."""
        with app.app_context():
            data = {
                'id': 'new_material',
                'display_name': 'New Material',
                'base_material': 'polycarbonate',
                'form': 'sheet',
                'thickness': 0.25,
                'gcode_standards': {'drill': {'0.125': {'spindle_speed': 2000}}}
            }
            material = SettingsService.create_material(data)
            assert material.id == 'new_material'
            assert material.display_name == 'New Material'

            # Verify it's in database
            fetched = SettingsService.get_material('new_material')
            assert fetched is not None

    def test_update_material(self, app, sample_material):
        """Test updating a material."""
        with app.app_context():
            updated = SettingsService.update_material('test_aluminum_0125', {
                'display_name': 'Updated Name',
                'thickness': 0.25
            })
            assert updated is not None
            assert updated.display_name == 'Updated Name'
            assert updated.thickness == 0.25

    def test_update_material_not_found(self, app):
        """Test updating a non-existent material."""
        with app.app_context():
            result = SettingsService.update_material('nonexistent', {'display_name': 'Test'})
            assert result is None

    def test_delete_material(self, app, sample_material):
        """Test deleting a material."""
        with app.app_context():
            result = SettingsService.delete_material('test_aluminum_0125')
            assert result is True
            assert SettingsService.get_material('test_aluminum_0125') is None

    def test_delete_material_in_use(self, app, sample_project):
        """Test that materials in use cannot be deleted."""
        with app.app_context():
            result = SettingsService.delete_material('test_aluminum_0125')
            assert result is False
            # Material should still exist
            assert SettingsService.get_material('test_aluminum_0125') is not None


class TestMachineSettingsMethods:
    """Tests for machine settings methods."""

    def test_get_machine_settings_creates_default(self, app):
        """Test that get_machine_settings creates defaults if missing."""
        with app.app_context():
            settings = SettingsService.get_machine_settings()
            assert settings is not None
            assert settings.id == 1
            assert settings.name == 'OMIO CNC'
            assert settings.max_x == 15.0

    def test_get_machine_settings_existing(self, app, machine_settings):
        """Test getting existing machine settings."""
        with app.app_context():
            settings = SettingsService.get_machine_settings()
            assert settings.name == 'Test CNC'

    def test_update_machine_settings(self, app, machine_settings):
        """Test updating machine settings."""
        with app.app_context():
            updated = SettingsService.update_machine_settings({
                'name': 'Updated CNC',
                'max_x': 20.0,
                'supports_subroutines': False
            })
            assert updated.name == 'Updated CNC'
            assert updated.max_x == 20.0
            assert updated.supports_subroutines is False

    def test_get_machine_settings_dict(self, app, machine_settings):
        """Test getting machine settings as dict."""
        with app.app_context():
            settings_dict = SettingsService.get_machine_settings_dict()
            assert settings_dict['name'] == 'Test CNC'
            assert settings_dict['max_x'] == 15.0
            assert settings_dict['supports_subroutines'] is True
            assert 'gcode_base_path' in settings_dict


class TestGeneralSettingsMethods:
    """Tests for general settings methods."""

    def test_get_general_settings_creates_default(self, app):
        """Test that get_general_settings creates defaults if missing."""
        with app.app_context():
            settings = SettingsService.get_general_settings()
            assert settings is not None
            assert settings.id == 1
            assert settings.safety_height == 0.5

    def test_get_general_settings_existing(self, app, general_settings):
        """Test getting existing general settings."""
        with app.app_context():
            settings = SettingsService.get_general_settings()
            assert settings.travel_height == 0.2

    def test_update_general_settings(self, app, general_settings):
        """Test updating general settings."""
        with app.app_context():
            updated = SettingsService.update_general_settings({
                'safety_height': 1.0,
                'spindle_warmup_seconds': 5
            })
            assert updated.safety_height == 1.0
            assert updated.spindle_warmup_seconds == 5

    def test_get_general_settings_dict(self, app, general_settings):
        """Test getting general settings as dict."""
        with app.app_context():
            settings_dict = SettingsService.get_general_settings_dict()
            assert settings_dict['safety_height'] == 0.5
            assert settings_dict['travel_height'] == 0.2
            assert settings_dict['spindle_warmup_seconds'] == 2


class TestToolMethods:
    """Tests for tool methods."""

    def test_get_all_tools_empty(self, app):
        """Test getting tools when none exist."""
        with app.app_context():
            tools = SettingsService.get_all_tools()
            assert tools == []

    def test_get_all_tools(self, app, sample_tool):
        """Test getting all tools."""
        with app.app_context():
            tools = SettingsService.get_all_tools()
            assert len(tools) == 1
            assert tools[0].tool_type == 'drill'

    def test_get_tools_by_type(self, app, sample_tool, sample_end_mill):
        """Test filtering tools by type."""
        with app.app_context():
            drills = SettingsService.get_tools_by_type('drill')
            assert len(drills) == 1
            assert drills[0].tool_type == 'drill'

            end_mills = SettingsService.get_tools_by_type('end_mill_1flute')
            assert len(end_mills) == 1

    def test_get_tools_as_list(self, app, sample_tool):
        """Test getting tools as list of dicts."""
        with app.app_context():
            tools_list = SettingsService.get_tools_as_list()
            assert len(tools_list) == 1
            assert tools_list[0]['tool_type'] == 'drill'
            assert tools_list[0]['size'] == 0.125
            assert 'id' in tools_list[0]

    def test_create_tool(self, app):
        """Test creating a new tool."""
        with app.app_context():
            tool = SettingsService.create_tool({
                'tool_type': 'drill',
                'size': 0.25,
                'size_unit': 'in',
                'description': '1/4" drill'
            })
            assert tool.id is not None
            assert tool.size == 0.25

    def test_delete_tool(self, app, sample_tool):
        """Test deleting a tool."""
        with app.app_context():
            tool_id = sample_tool.id
            result = SettingsService.delete_tool(tool_id)
            assert result is True

            # Verify deletion
            tools = SettingsService.get_all_tools()
            assert len(tools) == 0

    def test_delete_tool_not_found(self, app):
        """Test deleting non-existent tool."""
        with app.app_context():
            result = SettingsService.delete_tool(9999)
            assert result is False
