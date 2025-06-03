import pytest
import tempfile
import numpy as np
from pathlib import Path
import laspy
from pdaltools.las_compare_classification import compare_las_classification

def create_test_las_file(points: int, classification: np.ndarray = None) -> Path:
    """Helper function to create a test LAS file with specified classification"""
    with tempfile.NamedTemporaryFile(suffix='.las', delete=False) as temp:
        las = laspy.create(point_format=3, file_version="1.4")
        
        # Create sample points
        x = np.random.rand(points) * 1000
        y = np.random.rand(points) * 1000
        z = np.random.rand(points) * 100
        
        # Use provided classification or create random one
        if classification is None:
            classification = np.random.randint(0, 10, points)
        
        las.x = x
        las.y = y
        las.z = z
        las.classification = classification
        
        las.write(temp.name)
        return Path(temp.name)

def test_identical_classification():
    """Test that identical classification returns True"""
    # Create two identical LAS files
    points = 100
    classification = np.random.randint(0, 10, points)
    
    file1 = create_test_las_file(points, classification)
    file2 = create_test_las_file(points, classification)
    
    result = compare_las_classification(file1, file2)
    assert result is True, "Files with identical classification should return True"
    
    # Clean up
    file1.unlink()
    file2.unlink()

def test_different_classification():
    """Test that different classification returns False"""
    # Create two LAS files with different classification
    points = 100
    
    file1 = create_test_las_file(points)
    file2 = create_test_las_file(points)
    
    result = compare_las_classification(file1, file2)
    assert result is False, "Files with different classification should return False"
    
    # Clean up
    file1.unlink()
    file2.unlink()

def test_different_number_of_points():
    """Test that different number of points returns False"""
    # Create LAS files with different number of points
    file1 = create_test_las_file(100)
    file2 = create_test_las_file(101)
    
    result = compare_las_classification(file1, file2)
    assert result is False, "Files with different number of points should return False"
    
    # Clean up
    file1.unlink()
    file2.unlink()

def test_one_empty_file():
    """Test with one empty file"""
    # Create one empty and one non-empty file
    file1 = create_test_las_file(0)
    file2 = create_test_las_file(100)
    
    result = compare_las_classification(file1, file2)
    assert result is False, "One empty file should return False"
    
    # Clean up
    file1.unlink()
    file2.unlink()

def test_both_empty_files():
    """Test with two empty files"""
    # Create two empty files
    file1 = create_test_las_file(0)
    file2 = create_test_las_file(0)
    
    result = compare_las_classification(file1, file2)
    assert result is True, "Two empty files should return True"
    
    # Clean up
    file1.unlink()
    file2.unlink()

def test_single_point():
    """Test with single point files"""
    # Create two files with single point
    file1 = create_test_las_file(1, np.array([1]))
    file2 = create_test_las_file(1, np.array([1]))
    
    result = compare_las_classification(file1, file2)
    assert result is True, "Single point files with same classification should return True"
    
    # Clean up
    file1.unlink()
    file2.unlink()

def test_different_single_point():
    """Test with single point files having different classification"""
    # Create two files with single point but different classification
    file1 = create_test_las_file(1, np.array([1]))
    file2 = create_test_las_file(1, np.array([2]))
    
    result = compare_las_classification(file1, file2)
    assert result is False, "Single point files with different classification should return False"
    
    # Clean up
    file1.unlink()
    file2.unlink()


def test_main_function():
    """Test the main function with direct sys.argv"""
    import sys
    from io import StringIO
    from contextlib import redirect_stdout
    from pdaltools.las_compare_classification import main
    
    # Test with identical files
    points = 100
    classification = np.random.randint(0, 10, points)
    
    file1 = create_test_las_file(points, classification)
    file2 = create_test_las_file(points, classification)
    
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
