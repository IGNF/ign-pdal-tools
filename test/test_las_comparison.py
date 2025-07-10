import pytest
import tempfile
import numpy as np
from pathlib import Path
import laspy
from pdaltools.las_comparison import compare_las_dimensions, main
from typing import Tuple


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


def test_main_function():
    """Test the main function with direct sys.argv"""
    import sys
    from io import StringIO
    from contextlib import redirect_stdout

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


if __name__ == "__main__":
    pytest.main()
