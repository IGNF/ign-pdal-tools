import os
from pathlib import Path

from pdaltools import add_points_in_pointcloud

TEST_PATH = os.path.dirname(os.path.abspath(__file__))
TMP_PATH = os.path.join(TEST_PATH, "data/output")
DATA_LIDAR_PATH = os.path.join(TEST_PATH, "data/classified_laz")
DATA_POINTS_PATH = os.path.join(TEST_PATH, "data/points_3d")

INPUT_FILE = os.path.join(DATA_LIDAR_PATH, "test_semis_2023_0292_6833_LA93_IGN69.laz")
INPUT_POINTS = os.path.join(DATA_POINTS_PATH, "Points_virtuels.geojson")
OUTPUT_FILE = os.path.join(TMP_PATH, "test_semis_2023_0292_6833_LA93_IGN69.laz")


def setup_module(module):
    os.makedirs("test/data/output", exist_ok=True)


def test_get_tile_bbox():
    bbox = add_points_in_pointcloud.get_tile_bbox(INPUT_FILE, 1000)
    assert bbox == (292000.0, 6832000.0, 293000.0, 6833000.0)


def test_clip_3d_points_to_tile():
    points_clipped = add_points_in_pointcloud.clip_3d_points_to_tile(INPUT_POINTS, INPUT_FILE, "EPSG:2154")
    assert len(points_clipped) == 678


def test_add_line_to_lidar():
    points_clipped = add_points_in_pointcloud.clip_3d_points_to_tile(INPUT_POINTS, INPUT_FILE, "EPSG:2154")

    add_points_in_pointcloud.add_points_to_las(points_clipped, INPUT_FILE, OUTPUT_FILE, 66)
    assert Path(OUTPUT_FILE).exists()
