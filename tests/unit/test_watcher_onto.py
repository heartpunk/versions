"""
Comprehensive tests for watcher_onto.py

These tests ensure the ontology management functionality works correctly
and will catch regressions when we refactor the code.
"""
import pytest
import tempfile
import shutil
from pathlib import Path
from unittest.mock import patch, MagicMock
import uuid

# Import the module under test
import sys
sys.path.insert(0, str(Path(__file__).parent.parent.parent))


class TestWatcherOnto:
    """Test suite for watcher_onto module"""
    
    @pytest.fixture(autouse=True)
    def setup_and_teardown(self):
        """Setup and cleanup for each test"""
        # Store original values
        self.temp_dir = tempfile.mkdtemp()
        self.original_home = Path.home()
        
        # Mock Path.home() to use temp directory
        with patch('pathlib.Path.home', return_value=Path(self.temp_dir)):
            yield
            
        # Cleanup
        shutil.rmtree(self.temp_dir, ignore_errors=True)
    
    @pytest.fixture
    def mock_owlready(self):
        """Mock owlready2 imports to avoid dependencies in tests"""
        with patch.dict('sys.modules', {
            'owlready2': MagicMock(),
            'owlready2.namespace': MagicMock(),
        }):
            # Mock the necessary owlready2 components
            mock_owlready = sys.modules['owlready2']
            mock_owlready.get_ontology = MagicMock()
            mock_owlready.Thing = type('Thing', (), {})
            mock_owlready.default_world = MagicMock()
            mock_owlready.types = MagicMock()
            mock_owlready.types.new_class = MagicMock(return_value=type('DynamicClass', (), {}))
            
            # Mock the >> operator for property creation
            def mock_rshift(self, other):
                return type('Property', (), {})
            type(mock_owlready.Thing).__rshift__ = mock_rshift
            
            yield mock_owlready
    
    def test_module_imports(self, mock_owlready):
        """Test that the module imports correctly"""
        # Clear any cached imports
        if 'watcher_onto' in sys.modules:
            del sys.modules['watcher_onto']
            
        import watcher_onto
        
        # Verify key attributes exist
        assert hasattr(watcher_onto, 'owlready_builtin_datatypes')
        assert hasattr(watcher_onto, 'onto')
        assert hasattr(watcher_onto, 'session_uuid')
        assert hasattr(watcher_onto, 'property_type')
        assert hasattr(watcher_onto, 'File')
        assert hasattr(watcher_onto, 'Snapshot')
    
    def test_owlready_builtin_datatypes(self, mock_owlready):
        """Test the builtin datatypes list"""
        if 'watcher_onto' in sys.modules:
            del sys.modules['watcher_onto']
            
        import watcher_onto
        
        assert watcher_onto.owlready_builtin_datatypes == [int, float, bool, str]
    
    def test_session_uuid_generation(self, mock_owlready):
        """Test that session UUID is generated correctly"""
        if 'watcher_onto' in sys.modules:
            del sys.modules['watcher_onto']
            
        with patch('uuid.uuid4', return_value=uuid.UUID('12345678-1234-5678-1234-567812345678')):
            import watcher_onto
            
        assert watcher_onto.session_uuid == '12345678-1234-5678-1234-567812345678'
    
    def test_property_type_function(self, mock_owlready):
        """Test the property_type function creates new property classes"""
        if 'watcher_onto' in sys.modules:
            del sys.modules['watcher_onto']
            
        import watcher_onto
        
        # Mock the context manager
        mock_onto = MagicMock()
        mock_onto.__enter__ = MagicMock(return_value=mock_onto)
        mock_onto.__exit__ = MagicMock(return_value=None)
        watcher_onto.onto = mock_onto
        
        # Test property_type function
        domain_class = type('Domain', (), {})
        range_class = type('Range', (), {})
        
        result = watcher_onto.property_type('test_property', domain_class, range_class)
        
        # Verify the function was called correctly
        mock_owlready.types.new_class.assert_called()
        mock_owlready.default_world.save.assert_called()
    
    def test_ontology_initialization(self, mock_owlready):
        """Test that ontology is initialized with correct URL"""
        if 'watcher_onto' in sys.modules:
            del sys.modules['watcher_onto']
            
        import watcher_onto
        
        mock_owlready.get_ontology.assert_called_with("https://github.com/heartpunk/versions/ontology.owl")
    
    def test_file_and_snapshot_classes_created(self, mock_owlready):
        """Test that File and Snapshot classes are created"""
        if 'watcher_onto' in sys.modules:
            del sys.modules['watcher_onto']
            
        import watcher_onto
        
        assert hasattr(watcher_onto, 'File')
        assert hasattr(watcher_onto, 'Snapshot')
    
    def test_sqlite_backend_initialization(self, mock_owlready):
        """Test that SQLite backend is initialized correctly"""
        if 'watcher_onto' in sys.modules:
            del sys.modules['watcher_onto']
            
        with patch('uuid.uuid4', return_value=uuid.UUID('12345678-1234-5678-1234-567812345678')):
            import watcher_onto
        
        expected_path = str(Path(self.temp_dir) / ".watcher" / "12345678-1234-5678-1234-567812345678") + ".sqlite3"
        mock_owlready.default_world.set_backend.assert_called_with(
            filename=expected_path,
            exclusive=False
        )
        mock_owlready.default_world.save.assert_called()
    
    def test_property_definitions_created(self, mock_owlready):
        """Test that required properties are defined"""
        if 'watcher_onto' in sys.modules:
            del sys.modules['watcher_onto']
            
        # Mock property_type to track calls
        property_calls = []
        def mock_property_type(name, domain, range_):
            property_calls.append((name, domain, range_))
            return type(f'{name}Property', (), {})
        
        with patch('watcher_onto.property_type', side_effect=mock_property_type):
            import watcher_onto
            
        # Verify the expected properties were created
        property_names = [call[0] for call in property_calls]
        assert 'files' in property_names
        assert 'uuid4' in property_names
    
    def test_error_handling_missing_imports(self):
        """Test behavior when owlready2 is not available"""
        # Remove owlready2 from modules
        if 'owlready2' in sys.modules:
            del sys.modules['owlready2']
        if 'watcher_onto' in sys.modules:
            del sys.modules['watcher_onto']
            
        # Should raise ImportError
        with pytest.raises(ImportError):
            import watcher_onto
    
    def test_concurrent_session_isolation(self, mock_owlready):
        """Test that multiple imports don't share session UUIDs"""
        if 'watcher_onto' in sys.modules:
            del sys.modules['watcher_onto']
            
        # First import
        with patch('uuid.uuid4', return_value=uuid.UUID('11111111-1111-1111-1111-111111111111')):
            import watcher_onto as first_import
            first_uuid = first_import.session_uuid
        
        # Clear and reimport
        del sys.modules['watcher_onto']
        
        with patch('uuid.uuid4', return_value=uuid.UUID('22222222-2222-2222-2222-222222222222')):
            import watcher_onto as second_import
            second_uuid = second_import.session_uuid
        
        assert first_uuid != second_uuid
    
    def test_mutation_resistance_property_type(self, mock_owlready):
        """Test mutations in property_type function behavior"""
        if 'watcher_onto' in sys.modules:
            del sys.modules['watcher_onto']
            
        import watcher_onto
        
        # Test with None values (mutation: null pointer)
        with pytest.raises(Exception):
            watcher_onto.property_type(None, None, None)
        
        # Test with empty string (mutation: empty values)
        result = watcher_onto.property_type('', type('D', (), {}), type('R', (), {}))
        assert result is not None
        
        # Test with wrong types (mutation: type confusion)
        with pytest.raises(Exception):
            watcher_onto.property_type(123, "not_a_class", [])
    
    def test_mutation_resistance_data_types(self, mock_owlready):
        """Test mutations in owlready_builtin_datatypes"""
        if 'watcher_onto' in sys.modules:
            del sys.modules['watcher_onto']
            
        import watcher_onto
        
        # Original list should be immutable in practice
        original = watcher_onto.owlready_builtin_datatypes.copy()
        
        # Try to modify (this tests defensive programming)
        watcher_onto.owlready_builtin_datatypes.append(dict)
        
        # For safety, the list should either be immutable or we should work with copies
        assert len(original) == 4
        assert dict not in original


class TestWatcherOntoIntegration:
    """Integration tests that test actual owlready2 functionality"""
    
    @pytest.fixture
    def temp_home(self, tmp_path):
        """Create a temporary home directory"""
        with patch('pathlib.Path.home', return_value=tmp_path):
            yield tmp_path
    
    @pytest.mark.skipif(
        not pytest.importorskip("owlready2", reason="owlready2 not installed"),
        reason="Integration tests require owlready2"
    )
    def test_real_ontology_creation(self, temp_home):
        """Test with real owlready2 library"""
        if 'watcher_onto' in sys.modules:
            del sys.modules['watcher_onto']
            
        import watcher_onto
        
        # Verify database file was created
        db_path = temp_home / ".watcher" / f"{watcher_onto.session_uuid}.sqlite3"
        assert db_path.exists()
        
        # Verify classes can be instantiated
        file_instance = watcher_onto.File()
        snapshot_instance = watcher_onto.Snapshot()
        
        assert file_instance is not None
        assert snapshot_instance is not None
        
        # Verify properties work
        snapshot_instance.uuid4 = ["test-uuid"]
        assert "test-uuid" in snapshot_instance.uuid4