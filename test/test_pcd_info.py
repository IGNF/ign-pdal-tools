import os

import laspy
import numpy as np
import pytest

from pdaltools import pcd_info

TEST_PATH = os.path.dirname(os.path.abspath(__file__))
TMP_PATH = os.path.join(TEST_PATH, "tmp")
DATA_PATH = os.path.join(TEST_PATH, "data")


@pytest.mark.parametrize(
    "minx, maxx, miny, maxy, expected_origin",
    [
        (501, 999, 501, 999, (0, 1000)),  # points in the second half
        (1, 400, 1, 400, (0, 1000)),  # points in the first half
        (500, 1000, 500, 500, (0, 1000)),  # xmax on edge and xmin in the tile
        (0, 20, 500, 500, (0, 1000)),  # xmin on edge and xmax in the tile
        (950, 1000, 500, 500, (0, 1000)),  # xmax on edge and xmin in the tile
        (500, 500, 980, 1000, (0, 1000)),  # ymax on edge and ymin in the tile
        (500, 500, 0, 20, (0, 1000)),  # ymin on edge and ymax in the tile
        (0, 1000, 0, 1000, (0, 1000)),  # points at each corner
    ],
)
def test_infer_tile_origin_edge_cases(minx, maxx, miny, maxy, expected_origin):
    origin_x, origin_y = pcd_info.infer_tile_origin(minx, maxx, miny, maxy, tile_width=1000)
    assert (origin_x, origin_y) == expected_origin


@pytest.mark.parametrize(
    "minx, maxx, miny, maxy",
    [
        (0, 20, -1, 20),  # ymin slightly outside the tile
        (-1, 20, 0, 20),  # xmin slightly outside the tile
        (280, 1000, 980, 1001),  # ymax slightly outside the tile
        (980, 1001, 980, 1000),  # xmax slightly outside the tile
        (-1, 1000, 0, 1000),  # xmax on edge but xmin outside the tile
        (0, 1000, 0, 1001),  # ymin on edge but ymax outside the tile
        (0, 1001, 0, 1000),  # xmin on edge but xmax outside the tile
        (0, 1000, -1, 1000),  # ymax on edge but ymin outside the tile
    ],
)
def test_infer_tile_origin_edge_cases_fail(minx, maxx, miny, maxy):
    with pytest.raises(ValueError):
        pcd_info.infer_tile_origin(minx, maxx, miny, maxy, tile_width=1000)


@pytest.mark.parametrize(
    "input_points",
    [
        (np.array([[0, -1, 0], [20, 20, 0]])),  # ymin slightly outside the tile
        (np.array([[-1, 0, 0], [20, 20, 0]])),  # xmin slightly outside the tile
        (np.array([[980, 980, 0], [1000, 1001, 0]])),  # ymax slightly outside the tile
        (np.array([[980, 980, 0], [1001, 1000, 0]])),  # xmax slightly outside the tile
        (np.array([[-1, 0, 0], [1000, 1000, 0]])),  # xmax on edge but xmin outside the tile
        (np.array([[0, 0, 0], [1000, 1001, 0]])),  # ymin on edge but ymax outside the tile
        (np.array([[0, 0, 0], [1001, 1000, 0]])),  # xmin on edge but xmax outside the tile
        (np.array([[0, -1, 0], [1000, 1000, 0]])),  # ymax on edge but ymin outside the tile
    ],
)
def test_get_pointcloud_origin_edge_cases_fail(input_points):
    with pytest.raises(ValueError):
        pcd_info.get_pointcloud_origin_from_tile_width(points=input_points, tile_width=1000)


def test_get_pointcloud_origin_on_file():
    input_las = os.path.join(DATA_PATH, "test_data_77055_627760_LA93_IGN69.laz")
    expected_origin = (770550, 6277600)
    LAS = laspy.read(input_las)
    INPUT_POINTS = np.vstack((LAS.x, LAS.y, LAS.z)).transpose()

    origin_x, origin_y = pcd_info.get_pointcloud_origin_from_tile_width(points=INPUT_POINTS, tile_width=50)
    assert (origin_x, origin_y) == expected_origin
    origin_x_2, origin_y_2 = pcd_info.get_pointcloud_origin_from_tile_width(
        points=INPUT_POINTS, tile_width=10, buffer_size=20
    )
    assert (origin_x_2, origin_y_2) == (expected_origin[0] + 20, expected_origin[1] - 20)


def test_get_pointcloud_origin_fail_on_buffersize():
    with pytest.raises(ValueError):
        # Case when buffer size is bigger than the tile extremities (case not handled)
        points = np.array([[0, 0, 0], [20, 20, 0]])
        buffer_size = 30
        pcd_info.get_pointcloud_origin_from_tile_width(points=points, tile_width=1000, buffer_size=buffer_size)
