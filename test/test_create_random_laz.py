import os
import tempfile
import pytest
import numpy as np
import laspy

from pdaltools.create_random_laz import create_random_laz

TEST_PATH = os.path.dirname(os.path.abspath(__file__))
TMP_PATH = os.path.join(TEST_PATH, "tmp")


def setup_module(module):
    try:
        os.makedirs(TMP_PATH, exist_ok=True)
    except FileNotFoundError:
        pass


def test_create_random_laz_basic():
    """Test basic functionality without extra dimensions"""
    output_file = os.path.join(TMP_PATH, "test_basic.laz")
    create_random_laz(output_file, num_points=50, extra_dims=[])
    
    # Check file exists
    assert os.path.isfile(output_file)
    
    # Check file can be read
    with laspy.open(output_file) as las_file:
        las = las_file.read()
        assert len(las.points) == 50
        assert "X" in las.point_format.dimension_names
        assert "Y" in las.point_format.dimension_names
        assert "Z" in las.point_format.dimension_names
        assert "intensity" in las.point_format.dimension_names
        assert "classification" in las.point_format.dimension_names


def test_create_random_laz_invalid_type():
    """Test error handling for invalid dimension type"""
    output_file = os.path.join(TMP_PATH, "test_invalid_type.laz")
    extra_dims = [("height", "invalid_type")]
    
    with pytest.raises(ValueError):
        create_random_laz(output_file, num_points=50, extra_dims=extra_dims)


def test_create_random_laz_all_types():
    """Test all supported dimension types"""
    output_file = os.path.join(TMP_PATH, "test_all_types.laz")
    extra_dims = [
        ("float32_dim", "float32"),
        ("float64_dim", "float64"),
        ("int8_dim", "int8"),
        ("int16_dim", "int16"),
        ("int32_dim", "int32"),
        ("int64_dim", "int64"),
        ("uint8_dim", "uint8"),
        ("uint16_dim", "uint16"),
        ("uint32_dim", "uint32"),
        ("uint64_dim", "uint64"),
    ]
    
    create_random_laz(output_file, num_points=25, extra_dims=extra_dims)
    
    # Check file exists
    assert os.path.isfile(output_file)
    
    # Check file can be read and has correct dimensions
    with laspy.open(output_file) as las_file:
        las = las_file.read()
        assert len(las.points) == 25
        
        # Check that all extra dimensions exist
        for dim_name, _ in extra_dims:
            assert dim_name in las.point_format.dimension_names


def test_create_random_laz_data_ranges():
    """Test that generated data is within expected ranges for different types"""
    output_file = os.path.join(TMP_PATH, "test_data_ranges.laz")
    extra_dims = [
        ("float_dim", "float32"),
        ("int_dim", "int32"),
        ("uint_dim", "uint8"),
    ]
    
    create_random_laz(output_file, num_points=1000, extra_dims=extra_dims)
    
    with laspy.open(output_file) as las_file:
        las = las_file.read()
        
        # Check float data is in expected range (0-10)
        assert np.all(las.float_dim >= 0)
        assert np.all(las.float_dim <= 10)
        
        # Check int data is in expected range (-100 to 100)
        assert np.all(las.int_dim >= -100)
        assert np.all(las.int_dim <= 100)
        
        # Check uint data is in expected range (0 to 100)
        assert np.all(las.uint_dim >= 0)
        assert np.all(las.uint_dim <= 100)


if __name__ == "__main__":
    pytest.main([__file__]) 