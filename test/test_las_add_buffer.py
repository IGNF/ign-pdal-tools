import numpy as np
import os
import pytest
import shutil
from pdaltools.las_add_buffer import create_las_with_buffer
import laspy
import logging


test_path = os.path.dirname(os.path.abspath(__file__))
tmp_path = os.path.join(test_path, "tmp")
input_dir = os.path.join(test_path, "data")
output_file = os.path.join(tmp_path, "cropped.las")

coord_x = 77055
coord_y = 627760
# Note: neighbor tile 77050_627760 is cropped to simulate missing data in neighbors during merge
input_file = os.path.join(input_dir, f"test_data_{coord_x}_{coord_y}_LA93_IGN69_ground.las")
tile_width = 50
tile_coord_scale = 10

input_nb_points = 22343
expected_output_nb_points = 40177
expected_out_mins = [770540.01, 6277540.]
expected_out_maxs = [770610., 6277600.]



def setup_module(module):
    try:
        shutil.rmtree(tmp_path)

    except (FileNotFoundError):
        pass
    os.mkdir(tmp_path)


## Utils functions
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


## Tests
def test_create_las_with_buffer():
    buffer_width = 10
    create_las_with_buffer(
        input_dir, input_file, output_file, buffer_width=buffer_width,
        tile_width=tile_width,tile_coord_scale=tile_coord_scale)
    logging.info(get_nb_points(input_file))
    # check file exists
    assert os.path.isfile(output_file)

    # check difference in bbox
    in_mins, in_maxs = get_2d_bounding_box(input_file)
    out_mins, out_maxs = get_2d_bounding_box(output_file)

    # The following test does not work on the current test case as there is no tile on the left
    # and the top of the tile
    assert np.all(np.isclose(out_mins,  in_mins - buffer_width))
    assert np.all(np.isclose(out_maxs, in_maxs + buffer_width))

    # check number of points
    assert get_nb_points(output_file) == expected_output_nb_points

    # Check contre valeur attendue
    assert np.all(out_mins == expected_out_mins)
    assert np.all(out_maxs == expected_out_maxs)


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    test_create_las_with_buffer()