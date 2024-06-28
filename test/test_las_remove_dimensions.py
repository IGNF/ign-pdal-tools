import tempfile
import pdal
import numpy
import os
import logging
import pytest

from pdaltools import las_remove_dimensions

TEST_PATH = os.path.dirname(os.path.abspath(__file__))
INPUT_DIR = os.path.join(TEST_PATH, "data")


def get_points(input_las):
    pipeline_read_ini = pdal.Pipeline() | pdal.Reader.las(input_las)
    pipeline_read_ini.execute()
    return pipeline_read_ini.arrays[0]


def test_remove_dimension():
    ini_las = os.path.join(INPUT_DIR, "test_data_77055_627760_LA93_IGN69.laz")
    added_dimensions = ["DIM_1", "DIM_2"]

    # get initial data
    points_ini = get_points(ini_las)

    with tempfile.NamedTemporaryFile(suffix="_add.las") as tmp_las:
        # append dimensions
        pipeline = pdal.Pipeline()
        pipeline |= pdal.Reader.las(ini_las)
        pipeline |= pdal.Filter.ferry(dimensions="=>" + ", =>".join(added_dimensions))
        pipeline |= pdal.Writer.las(tmp_las.name, extra_dims="all", forward="all", )
        pipeline.execute()

        # remove all dimensions
        with tempfile.NamedTemporaryFile(suffix="_rm.las") as tmp_las_rm:
            las_remove_dimensions.remove_dimensions_from_las(tmp_las.name, added_dimensions, tmp_las_rm.name)
            points_end = get_points(tmp_las_rm.name)
            assert numpy.array_equal(points_ini, points_end)  # output data should be the same

        # remove one dimension
        with tempfile.NamedTemporaryFile(suffix="_rm.las") as tmp_las_rm:
            las_remove_dimensions.remove_dimensions_from_las(tmp_las.name, added_dimensions[:1] , tmp_las_rm.name)
            points_end = get_points(tmp_las_rm.name)
            with pytest.raises(Exception):
                numpy.array_equal(points_ini, points_end)  # output data should not be the same


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    test_remove_dimension()
