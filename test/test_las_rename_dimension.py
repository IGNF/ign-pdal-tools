import os
import pytest
import tempfile
import numpy as np
import laspy
import sys
from pdaltools.las_rename_dimension import rename_dimension, main
from pyproj import CRS

def create_test_las_file():
    """Create a temporary LAS file with test data."""
    with tempfile.NamedTemporaryFile(suffix='.las', delete=False) as tmp_file:
        # Create a LAS file with some test points
        header = laspy.LasHeader(point_format=3, version="1.4")
        header.add_extra_dim(laspy.ExtraBytesParams(name="test_dim", type=np.float32))
        header.add_extra_dim(laspy.ExtraBytesParams(name="test_dim2", type=np.int32))
        
        las = laspy.LasData(header)

        crs_pyproj = CRS.from_string("epsg:4326")
        las.header.add_crs(crs_pyproj)

        # Add some test points
        las.x = np.array([1.0, 2.0, 3.0])
        las.y = np.array([4.0, 5.0, 6.0])
        las.z = np.array([7.0, 8.0, 9.0])
        las.test_dim = np.array([10.0, 11.0, 12.0])
        las.test_dim2 = np.array([12, 13, 14])
        
        las.write(tmp_file.name)
        return tmp_file.name

def test_rename_dimension():
    """Test renaming a dimension in a LAS file."""
    # Create a temporary input LAS file
    input_file = create_test_las_file()
    
    # Create temporary output file
    with tempfile.NamedTemporaryFile(suffix='.las', delete=False) as tmp_file:
        output_file = tmp_file.name
    
    try:
        # Rename dimension using direct function call
        rename_dimension(input_file, output_file, ["test_dim", "test_dim2"], ["new_test_dim", "new_test_dim2"])
        
        # Verify the dimension was renamed
        with laspy.open(output_file) as las_file:
            las = las_file.read()
            assert "new_test_dim" in las.point_format.dimension_names
            assert "test_dim" not in las.point_format.dimension_names
            assert "new_test_dim2" in las.point_format.dimension_names
            assert "test_dim2" not in las.point_format.dimension_names
            
            # Verify the data is preserved
            np.testing.assert_array_equal(las.x, [1.0, 2.0, 3.0])
            np.testing.assert_array_equal(las.y, [4.0, 5.0, 6.0])
            np.testing.assert_array_equal(las.z, [7.0, 8.0, 9.0])
            np.testing.assert_array_equal(las["new_test_dim"], [10.0, 11.0, 12.0])
            np.testing.assert_array_equal(las["new_test_dim2"], [12, 13, 14])
    finally:
        # Clean up temporary files
        try:
            os.unlink(input_file)
            os.unlink(output_file)
        except:
            pass

def test_rename_nonexistent_dimension():
    """Test attempting to rename a dimension that doesn't exist."""
    input_file = create_test_las_file()
    
    with tempfile.NamedTemporaryFile(suffix='.las', delete=False) as tmp_file:
        output_file = tmp_file.name
    
    try:
        with pytest.raises(RuntimeError):
            rename_dimension(input_file, output_file, ["nonexistent_dim"], ["new_dim"])
    finally:
        os.unlink(input_file)
        os.unlink(output_file)

def test_rename_to_existing_dimension():
    """Test attempting to rename to an existing dimension."""
    input_file = create_test_las_file()
    
    with tempfile.NamedTemporaryFile(suffix='.las', delete=False) as tmp_file:
        output_file = tmp_file.name
    
    try:
        with pytest.raises(ValueError):
            rename_dimension(input_file, output_file, ["test_dim"], ["x"])
    finally:
        os.unlink(input_file)
        os.unlink(output_file)

def test_rename_dimension_case_sensitive():
    """Test that dimension renaming is case-sensitive."""
    input_file = create_test_las_file()
    
    with tempfile.NamedTemporaryFile(suffix='.las', delete=False) as tmp_file:
        output_file = tmp_file.name
    
    try:
        with pytest.raises(RuntimeError):
            rename_dimension(input_file, output_file, ["TEST_DIM"], ["new_dim"])
    finally:
        os.unlink(input_file)
        os.unlink(output_file)


def test_rename_dimension_main():
    """Test renaming dimensions using the main() function."""
    # Create a temporary input LAS file
    input_file = create_test_las_file()
    
    # Create temporary output file
    with tempfile.NamedTemporaryFile(suffix='.las', delete=False) as tmp_file:
        output_file = tmp_file.name
    
    try:
        # Save original sys.argv
        original_argv = sys.argv
        
        # Mock command-line arguments
        sys.argv = [
            "las_rename_dimension.py",  # script name
            input_file,
            output_file,
            "--old-dims", "test_dim", "test_dim2",
            "--new-dims", "new_test_dim", "new_test_dim2"
        ]
        
        # Call main() function
        main()
        
        # Restore original sys.argv
        sys.argv = original_argv
        
        # Verify the dimension was renamed
        with laspy.open(output_file) as las_file:
            las = las_file.read()
            assert "new_test_dim" in las.point_format.dimension_names
            assert "test_dim" not in las.point_format.dimension_names
            assert "new_test_dim2" in las.point_format.dimension_names
            assert "test_dim2" not in las.point_format.dimension_names
            
            # Verify the data is preserved
            np.testing.assert_array_equal(las.x, [1.0, 2.0, 3.0])
            np.testing.assert_array_equal(las.y, [4.0, 5.0, 6.0])
            np.testing.assert_array_equal(las.z, [7.0, 8.0, 9.0])
            np.testing.assert_array_equal(las["new_test_dim"], [10.0, 11.0, 12.0])
            np.testing.assert_array_equal(las["new_test_dim2"], [12, 13, 14])
    finally:
        # Clean up temporary files
        try:
            os.unlink(input_file)
            os.unlink(output_file)
        except:
            pass