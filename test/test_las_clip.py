import numpy as np
import os
import pytest
import shutil
from pdaltools.las_clip import las_crop
import laspy
import logging


test_path = os.path.dirname(os.path.abspath(__file__))
tmp_path = os.path.join(test_path, "tmp")
input_dir =  os.path.join(test_path, "data")
output_file = os.path.join(tmp_path, "cropped.las")

coord_x = 77055
coord_y = 627760
input_file = os.path.join(input_dir, f"test_data_{coord_x}_{coord_y}_LA93_IGN69_ground.las")

input_nb_points = 22343
expected_output_nb_points = 6578
input_mins = [ 770550., 6277550.]
input_maxs = [ 770600., 6277600.]
expected_out_mins = [770560., 6277560.]
expected_out_maxs = [770590., 6277590.]


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
def test_las_crop():
    bounds = ([expected_out_mins[0], expected_out_maxs[0]],
              [expected_out_mins[1], expected_out_maxs[1]])
    las_crop(input_file, output_file, bounds)

    # check file exists
    assert os.path.isfile(output_file)

    # check difference in bbox
    in_mins, in_maxs = get_2d_bounding_box(input_file)
    out_mins, out_maxs = get_2d_bounding_box(output_file)

    assert np.all(out_mins == expected_out_mins)
    assert np.all(out_maxs == expected_out_maxs)

    # check number of points
    assert get_nb_points(output_file) == expected_output_nb_points


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    test_las_crop()