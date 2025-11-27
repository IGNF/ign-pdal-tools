import tempfile
from pathlib import Path
from typing import Tuple

import laspy
import numpy as np
import pytest

from pdaltools.las_comparison import compare_las_dimensions, main


def create_test_las_file(x: np.ndarray, y: np.ndarray, z: np.ndarray, dimensions: dict = None) -> Path:
    """Helper function to create a test LAS file with specified dimensions"""
    with tempfile.NamedTemporaryFile(suffix=".las", delete=False) as temp:
        las = laspy.create(point_format=3, file_version="1.4")

        # Use provided dimensions or create default ones
        if dimensions is None:
            dimensions = {
                "classification": np.random.randint(0, 10, len(x)),
                "intensity": np.random.randint(0, 255, len(x)),
                "return_number": np.random.randint(1, 5, len(x)),
            }

        las.x = x
        las.y = y
        las.z = z

        # Set all specified dimensions
        for dim_name, dim_data in dimensions.items():
            setattr(las, dim_name, dim_data)

        las.write(temp.name)
        return Path(temp.name)


def get_random_points(points: int) -> Tuple[np.ndarray, np.ndarray, np.ndarray]:
    x = np.random.rand(points) * 1000
    y = np.random.rand(points) * 1000
    z = np.random.rand(points) * 100
    return x, y, z


def test_identical_dimensions():
    """Test that identical dimensions return True"""
    points = 10
    x, y, z = get_random_points(points)
    dimensions = {
        "classification": np.random.randint(0, 10, points),
        "intensity": np.random.randint(0, 255, points),
        "return_number": np.random.randint(1, 5, points),
    }

    file1 = create_test_las_file(x, y, z, dimensions)
    file2 = create_test_las_file(x, y, z, dimensions)

    try:
        # Test with specific dimensions
        result, nb_diff, percentage = compare_las_dimensions(file1, file2, ["classification", "intensity"])
        assert result is True, "Files with identical dimensions should return True"
        assert nb_diff == 0, "Files with identical dimensions should have 0 different points"
        assert percentage == 0, "Files with identical dimensions should have 0% different points"

        # Test with identical files
        result, nb_diff, percentage = compare_las_dimensions(file1, file2)
        assert result is True, "Files with identical dimensions should return True"
    finally:
        # Clean up
        file1.unlink()
        file2.unlink()


def test_identical_dimensions_not_sorted():
    """Test that identical dimensions return True"""
    points = 10
    x, y, z = get_random_points(points)
    dimensions = {
        "classification": np.random.randint(0, 10, points),
        "intensity": np.random.randint(0, 255, points),
        "return_number": np.random.randint(1, 5, points),
    }
    dimensions2 = {
        "classification": dimensions["classification"][::-1],
        "intensity": dimensions["intensity"][::-1],
        "return_number": dimensions["return_number"][::-1],
    }

    file1 = create_test_las_file(x, y, z, dimensions)
    file2 = create_test_las_file(x[::-1], y[::-1], z[::-1], dimensions2)

    try:
        # Test with specific dimensions
        result, _, _ = compare_las_dimensions(file1, file2, ["classification", "intensity"])
        assert result is True, "Files with identical dimensions should return True"

        # Test with identical files
        result, _, _ = compare_las_dimensions(file1, file2)
        assert result is True, "Files with identical dimensions should return True"
    finally:
        # Clean up
        file1.unlink()
        file2.unlink()


def test_different_dimensions_random():
    """Test that files with random dimensions return False"""
    points = 100
    x, y, z = get_random_points(points)

    # Create file1 with random dimensions
    dimensions1 = {
        "classification": np.random.randint(0, 10, points),
        "intensity": np.random.randint(0, 255, points),
        "return_number": np.random.randint(1, 5, points),
    }
    file1 = create_test_las_file(x, y, z, dimensions1)

    # Create file2 with different dimensions
    dimensions2 = {
        "classification": np.random.randint(0, 10, points),  # Different classification
        "intensity": dimensions1["intensity"],  # Same intensity
        "return_number": dimensions1["return_number"],  # Same return_number
    }
    file2 = create_test_las_file(x, y, z, dimensions2)

    try:
        # Test full comparison (should be different)
        result, _, _ = compare_las_dimensions(file1, file2)
        assert result is False, "Files with different classification should return False"

        # Test specific dimensions (should be identical)
        result, _, _ = compare_las_dimensions(file1, file2, ["intensity", "return_number"])
        assert result is True, "Files with identical intensity and return_number should return True"
    finally:
        # Clean up
        file1.unlink()
        file2.unlink()


def test_different_number_of_points():
    """Test that files with different number of points return False"""
    points = 100
    x1, y1, z1 = get_random_points(points)
    x2, y2, z2 = get_random_points(points + 1)
    file1 = create_test_las_file(x1, y1, z1)
    file2 = create_test_las_file(x2, y2, z2)

    try:
        result, _, _ = compare_las_dimensions(file1, file2)
        assert result is False, "Files with different number of points should return False"
    finally:
        # Clean up
        file1.unlink()
        file2.unlink()


def test_different_dimensions_number():
    """Test that files with different number of dimensions return False"""
    points = 100
    x, y, z = get_random_points(points)

    # Create file1 with random dimensions
    dimensions1 = {
        "classification": np.random.randint(0, 10, points),
        "intensity": np.random.randint(0, 255, points),
        "return_number": np.random.randint(1, 5, points),
    }
    file1 = create_test_las_file(x, y, z, dimensions1)

    # Create file2 only 2 dimensions
    dimensions2 = {
        "classification": np.random.randint(0, 10, points),  # Different classification
        "intensity": dimensions1["intensity"],  # Same intensity
    }
    file2 = create_test_las_file(x, y, z, dimensions2)

    try:
        # Test full comparison (should be different)
        result, _, _ = compare_las_dimensions(file1, file2)
        assert result is False, "Files with different dimensions should return False"
    finally:
        # Clean up
        file1.unlink()
        file2.unlink()


def test_one_empty_file():
    """Test that one empty file returns False"""
    points = 100
    x = np.random.rand(points) * 1000
    y = np.random.rand(points) * 1000
    z = np.random.rand(points) * 100
    file1 = create_test_las_file(x, y, z)
    file2 = create_test_las_file(np.array([]), np.array([]), np.array([]))

    try:
        result, _, _ = compare_las_dimensions(file1, file2)
        assert result is False, "One empty file should return False"
    finally:
        # Clean up
        file1.unlink()
        file2.unlink()


def test_both_empty_files():
    """Test that two empty files return True"""
    file1 = create_test_las_file(np.array([]), np.array([]), np.array([]))
    file2 = create_test_las_file(np.array([]), np.array([]), np.array([]))

    try:
        result, _, _ = compare_las_dimensions(file1, file2)
        assert result is True, "Two empty files should return True"
    finally:
        # Clean up
        file1.unlink()
        file2.unlink()


def test_single_point():
    """Test with single point files"""
    points = 1
    x = np.random.rand(points) * 1000
    y = np.random.rand(points) * 1000
    z = np.random.rand(points) * 100
    dimensions = {"classification": np.array([1]), "intensity": np.array([100]), "return_number": np.array([1])}
    file1 = create_test_las_file(x, y, z, dimensions)
    file2 = create_test_las_file(x, y, z, dimensions)

    try:
        result, _, _ = compare_las_dimensions(file1, file2)
        assert result is True, "Single point files with same dimensions should return True"
    finally:
        # Clean up
        file1.unlink()
        file2.unlink()


def test_precision_within_tolerance():
    """Test that precision argument works when values are within tolerance"""
    points = 10
    x, y, z = get_random_points(points)
    
    # Create custom float dimension with small differences (within tolerance)
    custom_dim1 = np.random.rand(points) * 100.0
    custom_dim2 = custom_dim1 + 0.05  # Small difference, within 0.1 tolerance

    # Create files with custom dimension
    with tempfile.NamedTemporaryFile(suffix=".las", delete=False) as temp1:
        las1 = laspy.create(point_format=3, file_version="1.4")
        las1.x = x
        las1.y = y
        las1.z = z
        las1.add_extra_dim(laspy.ExtraBytesParams(name="custom_float", type=np.float64))
        las1.custom_float = custom_dim1
        las1.write(temp1.name)
        file1 = Path(temp1.name)
    
    with tempfile.NamedTemporaryFile(suffix=".las", delete=False) as temp2:
        las2 = laspy.create(point_format=3, file_version="1.4")
        las2.x = x
        las2.y = y
        las2.z = z
        las2.add_extra_dim(laspy.ExtraBytesParams(name="custom_float", type=np.float64))
        las2.custom_float = custom_dim2
        las2.write(temp2.name)
        file2 = Path(temp2.name)

    try:
        # Test without precision (should fail - exact comparison)
        result, _, _ = compare_las_dimensions(file1, file2, ["custom_float"])
        assert result is False, "Without precision, small differences should be detected"
        
        # Test with precision (should pass - within tolerance)
        precision = {"custom_float": 0.1}
        result, _, _ = compare_las_dimensions(file1, file2, ["custom_float"], precision)
        assert result is True, "With precision, values within tolerance should be considered equal"
    finally:
        # Clean up
        file1.unlink()
        file2.unlink()


def test_precision_outside_tolerance():
    """Test that precision argument works when values are outside tolerance"""
    points = 10
    x, y, z = get_random_points(points)
    
    # Create custom float dimension with differences outside tolerance
    custom_dim1 = np.random.rand(points) * 100.0
    custom_dim2 = custom_dim1 + 0.2  # Difference larger than 0.1 tolerance
    
    # Create files with custom dimension
    with tempfile.NamedTemporaryFile(suffix=".las", delete=False) as temp1:
        las1 = laspy.create(point_format=3, file_version="1.4")
        las1.x = x
        las1.y = y
        las1.z = z
        las1.add_extra_dim(laspy.ExtraBytesParams(name="custom_float", type=np.float64))
        las1.custom_float = custom_dim1
        las1.write(temp1.name)
        file1 = Path(temp1.name)
    
    with tempfile.NamedTemporaryFile(suffix=".las", delete=False) as temp2:
        las2 = laspy.create(point_format=3, file_version="1.4")
        las2.x = x
        las2.y = y
        las2.z = z
        las2.add_extra_dim(laspy.ExtraBytesParams(name="custom_float", type=np.float64))
        las2.custom_float = custom_dim2
        las2.write(temp2.name)
        file2 = Path(temp2.name)

    try:
        # Test with precision (should fail - outside tolerance)
        precision = {"custom_float": 0.1}
        result, nb_diff, percentage = compare_las_dimensions(file1, file2, ["custom_float"], precision)
        assert result is False, "With precision, values outside tolerance should be detected"
        assert nb_diff == points, "All points should be different"
        assert percentage == 100.0, "100% of points should be different"
    finally:
        # Clean up
        file1.unlink()
        file2.unlink()


def test_precision_multiple_dimensions():
    """Test precision argument with multiple dimensions"""
    points = 10
    x, y, z = get_random_points(points)
    
    # Create custom float dimensions with small differences
    custom_dim1_a = np.random.rand(points) * 100.0
    custom_dim1_b = np.random.rand(points) * 100.0
    custom_dim1_c = np.random.rand(points) * 100.0
    
    custom_dim2_a = custom_dim1_a + 0.05  # Within 0.1 tolerance
    custom_dim2_b = custom_dim1_b + 0.03  # Within 0.1 tolerance
    custom_dim2_c = custom_dim1_c + 0.2   # Outside 0.1 tolerance
    
    # Create files with custom dimensions
    with tempfile.NamedTemporaryFile(suffix=".las", delete=False) as temp1:
        las1 = laspy.create(point_format=3, file_version="1.4")
        las1.x = x
        las1.y = y
        las1.z = z
        las1.add_extra_dim(laspy.ExtraBytesParams(name="custom_float_a", type=np.float64))
        las1.add_extra_dim(laspy.ExtraBytesParams(name="custom_float_b", type=np.float64))
        las1.add_extra_dim(laspy.ExtraBytesParams(name="custom_float_c", type=np.float64))
        las1.custom_float_a = custom_dim1_a
        las1.custom_float_b = custom_dim1_b
        las1.custom_float_c = custom_dim1_c
        las1.write(temp1.name)
        file1 = Path(temp1.name)
    
    with tempfile.NamedTemporaryFile(suffix=".las", delete=False) as temp2:
        las2 = laspy.create(point_format=3, file_version="1.4")
        las2.x = x
        las2.y = y
        las2.z = z
        las2.add_extra_dim(laspy.ExtraBytesParams(name="custom_float_a", type=np.float64))
        las2.add_extra_dim(laspy.ExtraBytesParams(name="custom_float_b", type=np.float64))
        las2.add_extra_dim(laspy.ExtraBytesParams(name="custom_float_c", type=np.float64))
        las2.custom_float_a = custom_dim2_a
        las2.custom_float_b = custom_dim2_b
        las2.custom_float_c = custom_dim2_c
        las2.write(temp2.name)
        file2 = Path(temp2.name)

    try:
        # Test with precision for custom_float_a and custom_float_b (should pass)
        precision = {"custom_float_a": 0.1, "custom_float_b": 0.1}
        result, _, _ = compare_las_dimensions(file1, file2, ["custom_float_a", "custom_float_b"], precision)
        assert result is True, "custom_float_a and custom_float_b within tolerance should pass"
        
        # Test with precision for all three (should fail because custom_float_c is outside tolerance)
        precision = {"custom_float_a": 0.1, "custom_float_b": 0.1, "custom_float_c": 0.1}
        result, _, _ = compare_las_dimensions(file1, file2, ["custom_float_a", "custom_float_b", "custom_float_c"], precision)
        assert result is False, "custom_float_c outside tolerance should cause failure"
        
        # Test with larger precision for custom_float_c (should pass)
        precision = {"custom_float_a": 0.1, "custom_float_b": 0.1, "custom_float_c": 0.3}
        result, _, _ = compare_las_dimensions(file1, file2, ["custom_float_a", "custom_float_b", "custom_float_c"], precision)
        assert result is True, "All dimensions within their respective tolerances should pass"
    finally:
        # Clean up
        file1.unlink()
        file2.unlink()


def test_precision_partial_dimensions():
    """Test that precision only applies to specified dimensions"""
    points = 10
    x, y, z = get_random_points(points)
    
    # Create custom float dimensions with small differences
    custom_dim1_a = np.random.rand(points) * 100.0
    custom_dim1_b = np.random.rand(points) * 100.0
    
    custom_dim2_a = custom_dim1_a + 0.05  # Within 0.1 tolerance
    custom_dim2_b = custom_dim1_b + 0.05  # Within 0.1 tolerance but no precision specified
    
    # Create files with custom dimensions
    with tempfile.NamedTemporaryFile(suffix=".las", delete=False) as temp1:
        las1 = laspy.create(point_format=3, file_version="1.4")
        las1.x = x
        las1.y = y
        las1.z = z
        las1.add_extra_dim(laspy.ExtraBytesParams(name="custom_float_a", type=np.float64))
        las1.add_extra_dim(laspy.ExtraBytesParams(name="custom_float_b", type=np.float64))
        las1.custom_float_a = custom_dim1_a
        las1.custom_float_b = custom_dim1_b
        las1.write(temp1.name)
        file1 = Path(temp1.name)
    
    with tempfile.NamedTemporaryFile(suffix=".las", delete=False) as temp2:
        las2 = laspy.create(point_format=3, file_version="1.4")
        las2.x = x
        las2.y = y
        las2.z = z
        las2.add_extra_dim(laspy.ExtraBytesParams(name="custom_float_a", type=np.float64))
        las2.add_extra_dim(laspy.ExtraBytesParams(name="custom_float_b", type=np.float64))
        las2.custom_float_a = custom_dim2_a
        las2.custom_float_b = custom_dim2_b
        las2.write(temp2.name)
        file2 = Path(temp2.name)

    try:
        # Test with precision only for custom_float_a (custom_float_b should use exact comparison)
        precision = {"custom_float_a": 0.1}
        result, _, _ = compare_las_dimensions(file1, file2, ["custom_float_a", "custom_float_b"], precision)
        assert result is False, "custom_float_b without precision should use exact comparison and fail"
        
        # Test with precision for both
        precision = {"custom_float_a": 0.1, "custom_float_b": 0.1}
        result, _, _ = compare_las_dimensions(file1, file2, ["custom_float_a", "custom_float_b"], precision)
        assert result is True, "Both dimensions with precision should pass"
    finally:
        # Clean up
        file1.unlink()
        file2.unlink()


def test_main_function():
    """Test the main function with direct sys.argv"""
    import sys
    from contextlib import redirect_stdout
    from io import StringIO

    # Test with identical files
    points = 100
    x = np.random.rand(points) * 1000
    y = np.random.rand(points) * 1000
    z = np.random.rand(points) * 100
    classification = np.random.randint(0, 10, points)

    file1 = create_test_las_file(x, y, z, {"classification": classification})
    file2 = create_test_las_file(x, y, z, {"classification": classification})
    file3 = create_test_las_file(x, y, z, {"classification": classification + 1})  # Different classification

    try:
        # Test with identical files
        sys.argv = ["script_name", str(file1), str(file2)]
        with redirect_stdout(StringIO()) as f:
            result, _, _ = main()
            assert result is True

        sys.argv = ["script_name", str(file1), str(file2), "--dimensions", "classification"]
        with redirect_stdout(StringIO()) as f:
            result, _, _ = main()
            assert result is True

        sys.argv = ["script_name", str(file1), str(file2), "--dimensions", "classification", "intensity"]
        with redirect_stdout(StringIO()) as f:
            result, _, _ = main()
            assert result is True

        # Test with different files
        sys.argv = ["script_name", str(file1), str(file3)]
        with redirect_stdout(StringIO()) as f:
            result, _, _ = main()
            assert result is False

    finally:
        # Clean up
        for f in [file1, file2, file3]:
            if f.exists():
                f.unlink()


def test_main_function_with_precision():
    """Test the main function with precision argument"""
    import sys
    from io import StringIO
    from contextlib import redirect_stdout

    # Test with files having small differences in custom float dimension
    points = 10
    x, y, z = get_random_points(points)
    custom_dim1 = np.random.rand(points) * 100.0
    custom_dim2 = custom_dim1 + 0.05  # Small difference within 0.1 tolerance

    # Create files with custom dimension
    with tempfile.NamedTemporaryFile(suffix=".las", delete=False) as temp1:
        las1 = laspy.create(point_format=3, file_version="1.4")
        las1.x = x
        las1.y = y
        las1.z = z
        las1.add_extra_dim(laspy.ExtraBytesParams(name="custom_float", type=np.float64))
        las1.custom_float = custom_dim1
        las1.write(temp1.name)
        file1 = Path(temp1.name)
    
    with tempfile.NamedTemporaryFile(suffix=".las", delete=False) as temp2:
        las2 = laspy.create(point_format=3, file_version="1.4")
        las2.x = x
        las2.y = y
        las2.z = z
        las2.add_extra_dim(laspy.ExtraBytesParams(name="custom_float", type=np.float64))
        las2.custom_float = custom_dim2
        las2.write(temp2.name)
        file2 = Path(temp2.name)

    try:
        # Test without precision (should fail)
        sys.argv = ["script_name", str(file1), str(file2), "--dimensions", "custom_float"]
        with redirect_stdout(StringIO()) as f:
            result, _, _ = main()
            assert result is False, "Without precision, differences should be detected"

        # Test with precision (should pass)
        sys.argv = ["script_name", str(file1), str(file2), "--dimensions", "custom_float", "--precision", "custom_float=0.1"]
        with redirect_stdout(StringIO()) as f:
            result, _, _ = main()
            assert result is True, "With precision, values within tolerance should pass"

        # Test with multiple precision values
        custom_dim1_a = np.random.rand(points) * 100.0
        custom_dim1_b = np.random.rand(points) * 100.0
        custom_dim2_a = custom_dim1_a + 0.05
        custom_dim2_b = custom_dim1_b + 0.03
        
        # Create new files with multiple custom dimensions
        with tempfile.NamedTemporaryFile(suffix=".las", delete=False) as temp3:
            las3 = laspy.create(point_format=3, file_version="1.4")
            las3.x = x
            las3.y = y
            las3.z = z
            las3.add_extra_dim(laspy.ExtraBytesParams(name="custom_float_a", type=np.float64))
            las3.add_extra_dim(laspy.ExtraBytesParams(name="custom_float_b", type=np.float64))
            las3.custom_float_a = custom_dim1_a
            las3.custom_float_b = custom_dim1_b
            las3.write(temp3.name)
            file3 = Path(temp3.name)
        
        with tempfile.NamedTemporaryFile(suffix=".las", delete=False) as temp4:
            las4 = laspy.create(point_format=3, file_version="1.4")
            las4.x = x
            las4.y = y
            las4.z = z
            las4.add_extra_dim(laspy.ExtraBytesParams(name="custom_float_a", type=np.float64))
            las4.add_extra_dim(laspy.ExtraBytesParams(name="custom_float_b", type=np.float64))
            las4.custom_float_a = custom_dim2_a
            las4.custom_float_b = custom_dim2_b
            las4.write(temp4.name)
            file4 = Path(temp4.name)
        
        sys.argv = ["script_name", str(file3), str(file4), "--dimensions", "custom_float_a", "custom_float_b", 
                   "--precision", "custom_float_a=0.1", "custom_float_b=0.1"]
        with redirect_stdout(StringIO()) as f:
            result, _, _ = main()
            assert result is True, "Multiple precision values should work"
        
        # Clean up additional files
        file3.unlink()
        file4.unlink()

    finally:
        # Clean up
        for f in [file1, file2]:
            if f.exists():
                f.unlink()


if __name__ == "__main__":
    pytest.main()
