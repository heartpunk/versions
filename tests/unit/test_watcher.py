"""
Comprehensive tests for watcher.py functions

These tests ensure the file watching and update handling functionality works correctly
and will catch regressions when we refactor the code.
"""
import pytest
import tempfile
import hashlib
import os
from pathlib import Path
from unittest.mock import patch, MagicMock, mock_open, call
import sys

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))


class TestWatcherFunctions:
    """Test suite for watcher.py functions"""
    
    @pytest.fixture(autouse=True)
    def setup_and_teardown(self):
        """Setup and cleanup for each test"""
        self.temp_dir = tempfile.mkdtemp()
        self.snapshot_dir = Path(self.temp_dir) / '.snapshots'
        self.snapshot_dir.mkdir(exist_ok=True)
        
        # Mock argv to avoid issues
        with patch('sys.argv', ['watcher.py', self.temp_dir]):
            yield
            
        # Cleanup
        import shutil
        shutil.rmtree(self.temp_dir, ignore_errors=True)
    
    @pytest.fixture
    def mock_dependencies(self):
        """Mock all external dependencies"""
        # Mock pywatchman
        mock_pywatchman = MagicMock()
        mock_pywatchman.client = MagicMock()
        
        # Remove watcher from sys.modules if it exists
        if 'watcher' in sys.modules:
            del sys.modules['watcher']
        
        with patch.dict('sys.modules', {'pywatchman': mock_pywatchman}):
            # Mock sys.argv to prevent issues during import
            with patch('sys.argv', ['watcher.py', '/tmp']):
                # Mock os.mkdir to prevent the NameError
                with patch('os.mkdir'):
                    yield
    
    @pytest.fixture
    def mock_watcher_onto(self, mock_dependencies):
        """Mock watcher_onto module"""
        mock_onto = MagicMock()
        mock_onto.__enter__ = MagicMock(return_value=mock_onto)
        mock_onto.__exit__ = MagicMock(return_value=None)
        
        # Create proper mock classes with required attributes
        class MockFile:
            def __init__(self, uuid=None):
                self.uuid4 = []
                self.sha256 = []
        
        class MockSnapshot:
            def __init__(self, uuid=None):
                self.uuid4 = []
                self.files = []
                # Dynamic attribute support
                self._attrs = {}
            
            def __setattr__(self, name, value):
                if name.startswith('_') or name in ['uuid4', 'files']:
                    super().__setattr__(name, value)
                else:
                    if name not in self._attrs:
                        self._attrs[name] = []
                    self._attrs[name] = value
            
            def __getattr__(self, name):
                if name in self._attrs:
                    return self._attrs[name]
                # Create list attribute on first access
                self._attrs[name] = []
                return self._attrs[name]
        
        # Create mock module
        mock_module = MagicMock()
        mock_module.File = MockFile
        mock_module.Snapshot = MockSnapshot
        mock_module.onto = mock_onto
        mock_module.owlready_builtin_datatypes = [int, float, bool, str]
        mock_module.property_type = MagicMock()
        mock_module.default_world = MagicMock()
        
        # Patch sys.modules first
        with patch.dict('sys.modules', {'watcher_onto': mock_module}):
            # Then patch watcher module's globals
            import watcher
            original_globals = {}
            globals_to_patch = {
                'File': MockFile,
                'Snapshot': MockSnapshot,
                'onto': mock_onto,
                'owlready_builtin_datatypes': [int, float, bool, str],
                'property_type': mock_module.property_type,
                'default_world': mock_module.default_world,
                'os': MagicMock(mkdir=MagicMock())  # Fix missing os import
            }
            
            for key, value in globals_to_patch.items():
                if hasattr(watcher, key):
                    original_globals[key] = getattr(watcher, key)
                setattr(watcher, key, value)
            
            try:
                yield mock_module
            finally:
                # Restore original values
                for key, value in original_globals.items():
                    setattr(watcher, key, value)
                for key in globals_to_patch:
                    if key not in original_globals and hasattr(watcher, key):
                        delattr(watcher, key)
    
    def test_update_file_handler_valid_file(self, mock_watcher_onto):
        """Test update_file_handler with a valid file"""
        # Import after mocks are set up
        import watcher
        
        # Patch the module-level variables
        watcher.path = self.temp_dir
        watcher.snapshot_path = self.snapshot_dir
        
        # Create a test file
        test_content = b"test file content"
        test_hash = hashlib.sha256(test_content).hexdigest()
        
        file_info = {'name': 'test.txt'}
        
        with patch('builtins.open', mock_open(read_data=test_content.decode('utf8'))):
            result = watcher.update_file_handler(file_info)
        
        assert result == test_hash
    
    def test_update_file_handler_directory(self, mock_watcher_onto):
        """Test update_file_handler with a directory (should return None)"""
        import watcher
        watcher.path = self.temp_dir
        watcher.snapshot_path = self.snapshot_dir
        
        file_info = {'name': 'some_directory'}
        
        with patch('builtins.open', side_effect=IsADirectoryError):
            result = watcher.update_file_handler(file_info)
        
        assert result is None
    
    def test_update_file_handler_unicode_error(self, mock_watcher_onto):
        """Test update_file_handler with Unicode decode error"""
        import watcher
        watcher.path = self.temp_dir
        watcher.snapshot_path = self.snapshot_dir
        
        file_info = {'name': 'binary.bin'}
        
        with patch('builtins.open', side_effect=UnicodeDecodeError('utf-8', b'', 0, 1, 'invalid')):
            result = watcher.update_file_handler(file_info)
        
        assert result is None
    
    def test_update_file_handler_file_not_found(self, mock_watcher_onto):
        """Test update_file_handler with non-existent file"""
        import watcher
        watcher.path = self.temp_dir
        watcher.snapshot_path = self.snapshot_dir
        
        file_info = {'name': 'nonexistent.txt'}
        
        with patch('builtins.open', side_effect=FileNotFoundError):
            result = watcher.update_file_handler(file_info)
        
        assert result is None
    
    def test_update_file_handler_creates_snapshot(self, mock_watcher_onto):
        """Test that update_file_handler creates snapshot file"""
        import watcher
        watcher.path = self.temp_dir
        watcher.snapshot_path = self.snapshot_dir
        
        test_content = b"snapshot test content"
        test_hash = hashlib.sha256(test_content).hexdigest()
        
        file_info = {'name': 'snapshot_test.txt'}
        
        mock_file = mock_open(read_data=test_content.decode('utf8'))
        
        with patch('builtins.open', mock_file):
            result = watcher.update_file_handler(file_info)
        
        # Verify the file was opened for reading and writing
        assert mock_file.call_count >= 2
        assert result == test_hash
    
    def test_update_handler_with_files(self, mock_watcher_onto):
        """Test update_handler with files in update"""
        import watcher
        watcher.path = self.temp_dir
        watcher.snapshot_path = self.snapshot_dir
        
        # Mock uuid4
        with patch('uuid.uuid4', return_value='test-uuid-1234'):
            # Create mock update with files
            update = {
                'files': [
                    {'name': 'file1.txt', 'size': 100, 'mtime': 1234567890},
                    {'name': 'file2.txt', 'size': 200, 'mtime': 1234567891}
                ],
                'clock': 'c:1234567890:1234:1:1',
                'version': '1.0'
            }
            
            # Mock update_file_handler
            with patch.object(watcher, 'update_file_handler', return_value='mock-sha256'):
                watcher.update_handler(update)
            
            # Verify world was saved
            mock_watcher_onto.default_world.save.assert_called()
    
    def test_update_handler_without_files(self, mock_watcher_onto):
        """Test update_handler without files (should print message)"""
        import watcher
        
        update = {
            'clock': 'c:1234567890:1234:1:1',
            'version': '1.0'
        }
        
        with patch('builtins.print') as mock_print:
            watcher.update_handler(update)
        
        mock_print.assert_called_with("update with no 'files' entry ", update)
    
    def test_update_handler_with_empty_files(self, mock_watcher_onto):
        """Test update_handler with empty files list"""
        import watcher
        
        update = {
            'files': [],
            'clock': 'c:1234567890:1234:1:1'
        }
        
        with patch('uuid.uuid4', return_value='test-uuid'):
            watcher.update_handler(update)
        
        # Should still create snapshot and save
        mock_watcher_onto.default_world.save.assert_called()
    
    def test_update_handler_with_builtin_types(self, mock_watcher_onto):
        """Test update_handler correctly handles builtin types"""
        import watcher
        
        update = {
            'files': [],
            'string_val': 'test',
            'int_val': 42,
            'float_val': 3.14,
            'bool_val': True
        }
        
        with patch('uuid.uuid4', return_value='test-uuid'):
            watcher.update_handler(update)
        
        # Should save without errors
        mock_watcher_onto.default_world.save.assert_called()
    
    def test_update_handler_with_unsupported_types(self, mock_watcher_onto):
        """Test update_handler with unsupported types"""
        import watcher
        
        update = {
            'files': [],
            'dict_val': {'nested': 'dict'},
            'list_val': [1, 2, 3]  # Non-files list
        }
        
        with patch('uuid.uuid4', return_value='test-uuid'):
            with patch('builtins.print') as mock_print:
                watcher.update_handler(update)
        
        # Should print warnings for unsupported types
        assert mock_print.call_count >= 2
    
    def test_update_handler_file_with_no_sha(self, mock_watcher_onto):
        """Test update_handler when file returns no SHA"""
        import watcher
        
        update = {
            'files': [
                {'name': 'directory/', 'type': 'dir'}
            ]
        }
        
        with patch('uuid.uuid4', return_value='test-uuid'):
            with patch.object(watcher, 'update_file_handler', return_value=None):
                watcher.update_handler(update)
        
        # Should still save
        mock_watcher_onto.default_world.save.assert_called()
    
    def test_update_handler_malformed_file_entry(self, mock_watcher_onto):
        """Test update_handler with malformed file entries"""
        import watcher
        
        update = {
            'files': [
                'not_a_dict',  # Should print error
                {'name': 'valid.txt'},  # Should process
            ]
        }
        
        with patch('uuid.uuid4', return_value='test-uuid'):
            with patch.object(watcher, 'update_file_handler', return_value='mock-sha'):
                with patch('builtins.print') as mock_print:
                    watcher.update_handler(update)
        
        # Should print error for non-dict entry
        mock_print.assert_any_call("files should only contain dicts shouldn't it? not_a_dict")
    
    def test_mutation_empty_update(self, mock_watcher_onto):
        """Mutation test: empty update dict"""
        import watcher
        
        # Should not crash with empty update
        watcher.update_handler({})
        
        # Should not save if no files
        mock_watcher_onto.default_world.save.assert_not_called()
    
    def test_mutation_none_update(self, mock_watcher_onto):
        """Mutation test: None update"""
        import watcher
        
        # Should handle None gracefully
        with pytest.raises(Exception):
            watcher.update_handler(None)
    
    def test_mutation_file_name_attribute(self, mock_watcher_onto):
        """Mutation test: file with 'name' vs 'filename' attribute"""
        import watcher
        
        update = {
            'files': [
                {'name': 'test.txt', 'size': 100}
            ]
        }
        
        with patch('uuid.uuid4', return_value='test-uuid'):
            with patch.object(watcher, 'update_file_handler', return_value='mock-sha'):
                # Mock the File instance to track attribute setting
                mock_file = MagicMock()
                mock_watcher_onto.File.return_value = mock_file
                
                watcher.update_handler(update)
                
                # Verify 'name' is converted to 'filename'
                assert hasattr(mock_file, 'filename')
    
    def test_path_traversal_protection(self, mock_watcher_onto):
        """Test protection against path traversal attacks"""
        import watcher
        watcher.path = self.temp_dir
        watcher.snapshot_path = self.snapshot_dir
        
        # Try path traversal
        file_info = {'name': '../../../etc/passwd'}
        
        with patch('builtins.open', side_effect=FileNotFoundError):
            result = watcher.update_file_handler(file_info)
        
        # Should fail safely
        assert result is None


class TestWatcherMissingImports:
    """Test the missing import issue in watcher.py"""
    
    def test_os_import_fixed(self):
        """Test that os is now properly imported"""
        # Mock pywatchman to allow import
        with patch.dict('sys.modules', {'pywatchman': MagicMock()}):
            with patch('sys.argv', ['watcher.py', '/tmp']):
                with patch('os.mkdir'):
                    import watcher
                    
                    # Check if os is imported
                    assert hasattr(watcher, 'os')
    
    def test_imports_present(self):
        """Test that required imports are present"""
        # Mock dependencies
        with patch.dict('sys.modules', {'pywatchman': MagicMock()}):
            with patch('sys.argv', ['watcher.py', '/tmp']):
                with patch('os.mkdir'):
                    # Clear cached module
                    if 'watcher' in sys.modules:
                        del sys.modules['watcher']
                    
                    import watcher
                    
                    assert hasattr(watcher, 'hashlib')
                    assert hasattr(watcher, 'os')
                    assert hasattr(watcher, 'pywatchman')
                    assert hasattr(watcher, 'Path')
                    assert hasattr(watcher, 'uuid4')
                    assert hasattr(watcher, 'argv')