import logging
import os
import shutil
import test.utils as tu
from test.utils import assert_header_info_are_similar

import laspy
import numpy as np

from pdaltools.count_occurences.count_occurences_for_attribute import (
    compute_count_one_file,
)
from pdaltools.las_add_buffer import create_las_with_buffer

TEST_PATH = os.path.dirname(os.path.abspath(__file__))
TMP_PATH = os.path.join(TEST_PATH, "tmp")
INPUT_DIR = os.path.join(TEST_PATH, "data")


def setup_module(module):
    try:
        shutil.rmtree(TMP_PATH)

    except FileNotFoundError:
        pass
    os.mkdir(TMP_PATH)


# Utils functions
def get_nb_points(path):
    """Get number of points in a las file"""
    with laspy.open(path) as f:
        nb_points = f.header.point_count

    return nb_points


def get_2d_bounding_box(path):
    """Get bbox for a las file (x, y only)"""
    with laspy.open(path) as f:
        mins = f.header.mins
        maxs = f.header.maxs

    return mins[:2], maxs[:2]


# Tests
def test_create_las_with_buffer():
    output_file = os.path.join(TMP_PATH, "buffer.las")
    # Note: this tile does not have a tile at its bottom
    # And its left-side tile has been crop to have no data in the buffer area. This case must not generate any error
    input_file = os.path.join(INPUT_DIR, "test_data_77055_627755_LA93_IGN69.laz")
    tile_width = 50
    tile_coord_scale = 10
    input_nb_points = 72770
    expected_out_mins = [770545.0, 6277500.0]
    expected_out_maxs = [770605.0, 6277555.0]

    buffer_width = 5
    create_las_with_buffer(
        INPUT_DIR,
        input_file,
        output_file,
        buffer_width=buffer_width,
        tile_width=tile_width,
        tile_coord_scale=tile_coord_scale,
    )
    logging.info(get_nb_points(input_file))
    # check file exists
    assert os.path.isfile(output_file)

    # check difference in bbox
    in_mins, in_maxs = get_2d_bounding_box(input_file)
    out_mins, out_maxs = get_2d_bounding_box(output_file)

    # The following test does not work on the current test case as there is no tile on the left
    # and the top of the tile
    tu.allclose_absolute(out_mins, in_mins - buffer_width, 1e-3)
    tu.allclose_absolute(out_maxs, in_maxs + buffer_width, 1e-3)

    # check number of points
    assert get_nb_points(output_file) > input_nb_points

    # Check boundaries
    assert np.all(out_mins == expected_out_mins)
    assert np.all(out_maxs == expected_out_maxs)

    # Check the input header infos are preserved in the output
    assert_header_info_are_similar(output_file, input_file)

    # Check that classes are preserved (in particular classes over 31)
    # Warning: classification values > 31 exist only for las 1.4 with dataformat_id >= 6
    classes_counts = compute_count_one_file(output_file)

    assert set(classes_counts.keys()) == {"1", "2", "3", "4", "5", "6", "64"}


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    test_create_las_with_buffer()
