import os
import test.utils as tu

import pytest

from pdaltools import las_info

TEST_PATH = os.path.dirname(os.path.abspath(__file__))
TMP_PATH = os.path.join(TEST_PATH, "tmp")
DATA_PATH = os.path.join(TEST_PATH, "data")

# Description of the test data
COORD_X = 77055
COORD_Y = 627760

INPUT_FILE = os.path.join(DATA_PATH, f"test_data_{COORD_X}_{COORD_Y}_LA93_IGN69_ground.las")

TILE_WIDTH = 50
TILE_COORD_SCALE = 10
INPUT_MINS = [770550.0, 6277550.0]
INPUT_MAXS = [770600.0, 6277600.0]


def test_las_info_metadata():
    metadata = las_info.las_info_metadata(INPUT_FILE)
    assert isinstance(metadata, dict)
    assert bool(metadata)  # check that metadata dict is not empty


def test_las_info_pipeline():
    info = las_info.las_info_pipeline(INPUT_FILE)
    assert isinstance(info, dict)
    assert bool(info)  # check that info dict is not empty


def test_get_bounds_from_quickinfo_metadata():
    metadata = las_info.las_info_metadata(INPUT_FILE)
    bounds = las_info.get_bounds_from_header_info(metadata)
    assert bounds == (INPUT_MINS[0], INPUT_MAXS[0], INPUT_MINS[1], INPUT_MAXS[1])


def test_get_epsg_from_quickinfo_metadata_ok():
    metadata = las_info.las_info_metadata(INPUT_FILE)
    assert las_info.get_epsg_from_header_info(metadata) == "2154"


def test_get_epsg_from_quickinfo_metadata_no_epsg():
    input_file = os.path.join(DATA_PATH, "test_noepsg_043500_629205_IGN69.laz")

    metadata = las_info.las_info_metadata(input_file)
    with pytest.raises(RuntimeError):
        las_info.get_epsg_from_header_info(metadata)


def test_las_get_xy_bounds_no_buffer():
    bounds = las_info.las_get_xy_bounds(INPUT_FILE)
    expected_xs = [INPUT_MINS[0], INPUT_MAXS[0]]
    expected_ys = [INPUT_MINS[1], INPUT_MAXS[1]]
    assert tu.allclose_absolute(bounds, [expected_xs, expected_ys], 1e-3)


def test_las_get_xy_bounds_with_buffer():
    buffer_width = 10
    bounds = las_info.las_get_xy_bounds(INPUT_FILE, buffer_width=buffer_width)
    expected_xs = [INPUT_MINS[0] - buffer_width, INPUT_MAXS[0] + buffer_width]
    expected_ys = [INPUT_MINS[1] - buffer_width, INPUT_MAXS[1] + buffer_width]
    assert tu.allclose_absolute(bounds, [expected_xs, expected_ys], 1e-3)


def test_parse_filename():
    prefix, parsed_coord_x, parsed_coord_y, suffix = las_info.parse_filename(INPUT_FILE)
    assert prefix == "test_data"
    assert suffix == "LA93_IGN69_ground.las"
    assert parsed_coord_x == COORD_X
    assert parsed_coord_y == COORD_Y


def test_get_buffered_bounds_from_filename_no_buffer():
    xs, ys = las_info.get_buffered_bounds_from_filename(
        INPUT_FILE, tile_width=TILE_WIDTH, tile_coord_scale=TILE_COORD_SCALE
    )
    assert xs == [770550, 770600]
    assert ys == [6277550, 6277600]


def test_get_buffered_bounds_from_filename_with_buffer():
    buffer_width = 10
    xs, ys = las_info.get_buffered_bounds_from_filename(
        INPUT_FILE, tile_width=TILE_WIDTH, tile_coord_scale=TILE_COORD_SCALE, buffer_width=buffer_width
    )
    assert xs == [770550 - buffer_width, 770600 + buffer_width]
    assert ys == [6277550 - buffer_width, 6277600 + buffer_width]
