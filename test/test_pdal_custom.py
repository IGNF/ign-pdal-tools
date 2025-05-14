import os

import pdal
import pytest

TEST_PATH = os.path.dirname(os.path.abspath(__file__))


# this test only works with PDAL compiled on a custom fork and branch, so we mark it to avoid running it.
@pytest.mark.pdal_custom
def test_pdal_read_severals_extra_dims():
    test_file = os.path.join(TEST_PATH, "data/las_with_several_extra_byte_bloc.laz")

    pipeline = pdal.Reader.las(filename=test_file).pipeline()
    metadata = pipeline.quickinfo["readers.las"]

    # dimensions should contains 'Deviation' and 'confidence'
    assert "Deviation" in metadata["dimensions"]
    assert "confidence" in metadata["dimensions"]

    # Test Python PDAL bindings
    pipeline = pdal.Reader.las(filename=test_file).pipeline()
    num_points = pipeline.execute()
    assert num_points > 0
