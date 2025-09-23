import os

import pdal
import pytest

TEST_PATH = os.path.dirname(os.path.abspath(__file__))

#this test files concatenate somes tests on PDAL features
#it allows us to test the PDAL version used in the library is modern enough

def test_pdal_read_severals_extra_dims():
# test that we can read a las file with several extra dims
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
