import pytest
import tempfile
import numpy as np
from pathlib import Path
import laspy
import sys
from io import StringIO
from contextlib import redirect_stdout
from pdaltools.las_compare_classification import compare_las_dimensions, main

def create_test_las_file(points: int, dimensions: dict = None) -> Path:
    """Helper function to create a test LAS file with specified dimensions"""
    with tempfile.NamedTemporaryFile(suffix='.las', delete=False) as temp:
        las = laspy.create(point_format=3, file_version="1.4")
        
        # Create sample points
        x = np.random.rand(points) * 1000
        y = np.random.rand(points) * 1000
        z = np.random.rand(points) * 100
        
        # Use provided dimensions or create default ones
        if dimensions is None:
            dimensions = {
                'classification': np.random.randint(0, 10, points),
                'intensity': np.random.randint(0, 255, points),
                'return_number': np.random.randint(1, 5, points)
            }
        
        las.x = x
        las.y = y
        las.z = z
        
        # Set all specified dimensions
        for dim_name, dim_data in dimensions.items():
            setattr(las, dim_name, dim_data)
        
        las.write(temp.name)
        return Path(temp.name)

def test_identical_dimensions():
    """Test that identical dimensions return True"""
    # Create two identical LAS files
    points = 100
    dimensions = {
        'classification': np.random.randint(0, 10, points),
        'intensity': np.random.randint(0, 255, points),
        'return_number': np.random.randint(1, 5, points)
    }
    
    file1 = create_test_las_file(points, dimensions)
    file2 = create_test_las_file(points, dimensions)
    
    try:
        # Test with identical files
        result = compare_las_dimensions(file1, file2)
        assert result is True, "Files with identical dimensions should return True"
        
        # Test with specific dimensions
        result = compare_las_dimensions(file1, file2, ['classification', 'intensity'])
        assert result is True, "Files with identical dimensions should return True"
        
        # Clean up
        file1.unlink()
        file2.unlink()

def test_different_dimensions():
    """Test that different dimensions return False"""
    # Create two LAS files with different dimensions
    points = 100
    
    file1 = create_test_las_file(points)
    file2 = create_test_las_file(points)
    
    try:
        result = compare_las_dimensions(file1, file2)
        assert result is False, "Files with different dimensions should return False"
        
        # Clean up
        file1.unlink()
        file2.unlink()

def test_different_number_of_points():
    """Test that different number of points returns False"""
    # Create LAS files with different number of points
    file1 = create_test_las_file(100)
    file2 = create_test_las_file(101)
    
    try:
        result = compare_las_dimensions(file1, file2)
        assert result is False, "Files with different number of points should return False"
    finally:
        # Clean up
        file1.unlink()
        file2.unlink()

def test_one_empty_file():
    """Test with one empty file"""
    # Create one empty and one non-empty file
    file1 = create_test_las_file(0)
    file2 = create_test_las_file(100)
    
    try:
        result = compare_las_dimensions(file1, file2)
        assert result is False, "One empty file should return False"
    finally:
        # Clean up
        file1.unlink()
        file2.unlink()

def test_both_empty_files():
    """Test with two empty files"""
    # Create two empty files
    file1 = create_test_las_file(0)
    file2 = create_test_las_file(0)
    
    try:
        result = compare_las_dimensions(file1, file2)
        assert result is True, "Two empty files should return True"
    finally:
        # Clean up
        file1.unlink()
        file2.unlink()

def test_single_point():
    """Test with single point files"""
    # Create two files with single point
    dimensions = {
        'classification': np.array([1]),
        'intensity': np.array([100]),
        'return_number': np.array([1])
    }
    file1 = create_test_las_file(1, dimensions)
    file2 = create_test_las_file(1, dimensions)
    
    try:
        result = compare_las_dimensions(file1, file2)
        assert result is True, "Single point files with same dimensions should return True"
    finally:
        # Clean up
        file1.unlink()
        file2.unlink()

def test_different_single_point():
    """Test with single point files having different dimensions"""
    # Create two files with single point but different dimensions
    dimensions1 = {
        'classification': np.array([1]),
        'intensity': np.array([100]),
        'return_number': np.array([1])
    }
    dimensions2 = {
        'classification': np.random.randint(0, 10, points),  # Different classification
        'intensity': dimensions1['intensity'],  # Same intensity
        'return_number': dimensions1['return_number']  # Same return_number
    }
    file2 = create_test_las_file(points, dimensions2)
    
    try:
        # Test with different classification
        sys.argv = ['script_name', str(file1), str(file2)]
        with redirect_stdout(StringIO()) as f:
            main()
            assert f.getvalue().strip() == "Dimensions comparison result: different"
        
        # Test with specific dimensions (should be identical)
        sys.argv = ['script_name', str(file1), str(file2), '--dimensions', 'intensity', 'return_number']
        with redirect_stdout(StringIO()) as f:
            main()
            assert f.getvalue().strip() == "Dimensions comparison result: identical"
        
    finally:
        # Clean up
        for f in [file1, file2]:
            if f.exists():
                f.unlink()

def test_missing_dimension():
    """Test with a dimension that doesn't exist"""
    points = 100
    file1 = create_test_las_file(points)
    file2 = create_test_las_file(points)
    
    try:
        # Test with non-existent dimension
        sys.argv = ['script_name', str(file1), str(file2), '--dimensions', 'nonexistent']
        with pytest.raises(SystemExit) as pytest_wrapped_e:
            main()
        assert pytest_wrapped_e.type == SystemExit
        assert pytest_wrapped_e.value.code != 0
        
    finally:
        # Clean up
        for f in [file1, file2]:
            if f.exists():
                f.unlink()

def test_nonexistent_file():
    """Test with non-existent file"""
    points = 100
    file1 = create_test_las_file(points)
    
    try:
        # Test with non-existent file
        sys.argv = ['script_name', 'nonexistent.las', str(file1)]
        with pytest.raises(SystemExit) as pytest_wrapped_e:
            main()
        assert pytest_wrapped_e.type == SystemExit
        assert pytest_wrapped_e.value.code != 0
        
    finally:
        # Clean up
        if file1.exists():
            file1.unlink()

def test_main_function():
    """Test the main function with direct sys.argv"""
    import sys
    from io import StringIO
    from contextlib import redirect_stdout
    
    # Test with identical files
    points = 100
    classification = np.random.randint(0, 10, points)
    
    file1 = create_test_las_file(points, {'classification': classification})
    file2 = create_test_las_file(points, {'classification': classification})
    
    try:
        # Test with identical files
        sys.argv = ['script_name', str(file1), str(file2)]
        with redirect_stdout(StringIO()) as f:
            main()
            assert f.getvalue().strip() == "Classification comparison result: identical"
        
        # Test with different files
        file3 = create_test_las_file(points)  # Different classification
        sys.argv = ['script_name', str(file1), str(file3)]
        with redirect_stdout(StringIO()) as f:
            main()
            assert f.getvalue().strip() == "Classification comparison result: different"
        
        # Test with non-existent file
        sys.argv = ['script_name', 'nonexistent.las', str(file1)]
        with pytest.raises(SystemExit) as pytest_wrapped_e:
            main()
        assert pytest_wrapped_e.type == SystemExit
        assert pytest_wrapped_e.value.code != 0
            
    finally:
        # Clean up
        for f in [file1, file2, file3]:
            if f.exists():
                f.unlink()

if __name__ == "__main__":
    pytest.main()
