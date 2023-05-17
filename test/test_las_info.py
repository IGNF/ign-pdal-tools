from collections import Counter
import json
import os
from pdaltools import las_info
import pytest
import shutil
from test.utils import get_pdal_infos_summary
from typing import Dict
import numpy as np


coord_x = 77055
coord_y = 627760
tile_width = 50
tile_coord_scale = 10
test_path = os.path.dirname(os.path.abspath(__file__))
tmp_path = os.path.join(test_path, "tmp")
input_dir = os.path.join(test_path, "data")
input_file = os.path.join(input_dir, f"test_data_{coord_x}_{coord_y}_LA93_IGN69_ground.las")
input_mins = [ 770550., 6277550.]
input_maxs = [ 770600., 6277600.]


def test_las_info_metadata():
    metadata = las_info.las_info_metadata(input_file)
    assert type(metadata) == dict
    assert bool(metadata)  # check that metadata dict is not empty


def test_las_info_pipeline():
    info = las_info.las_info_pipeline(input_file)
    assert type(info) == dict
    assert bool(info)  # check that info dict is not empty


def test_las_get_xy_bounds_no_buffer():
    bounds = las_info.las_get_xy_bounds(input_file)
    expected_xs = [input_mins[0], input_maxs[0]]
    expected_ys = [input_mins[1], input_maxs[1]]
    assert np.allclose(bounds, [expected_xs, expected_ys], rtol=1e-06)


def test_las_get_xy_bounds_with_buffer():
    buffer_width = 10
    bounds = las_info.las_get_xy_bounds(input_file, buffer_width=buffer_width)
    expected_xs = [input_mins[0] - buffer_width, input_maxs[0] + buffer_width]
    expected_ys = [input_mins[1] - buffer_width, input_maxs[1] + buffer_width]
    assert np.allclose(bounds, [expected_xs, expected_ys], rtol=1e-06)


def test_parse_filename():
    prefix, parsed_coord_x, parsed_coord_y, suffix = las_info.parse_filename(input_file)
    assert prefix == "test_data"
    assert suffix == "LA93_IGN69_ground.las"
    assert parsed_coord_x == coord_x
    assert parsed_coord_y == coord_y


def test_get_buffered_bounds_from_filename_no_buffer():
    xs, ys = las_info.get_buffered_bounds_from_filename(input_file, tile_width=tile_width,
                                                        tile_coord_scale=tile_coord_scale)
    assert xs == [770550, 770600]
    assert ys == [6277550, 6277600]


def test_get_buffered_bounds_from_filename_with_buffer():
    buffer_width = 10
    xs, ys = las_info.get_buffered_bounds_from_filename(input_file, tile_width=tile_width,
                                                        tile_coord_scale=tile_coord_scale,
                                                        buffer_width=buffer_width)
    assert xs == [770550 - buffer_width, 770600 + buffer_width]
    assert ys == [6277550 - buffer_width, 6277600 + buffer_width]