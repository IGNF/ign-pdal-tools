import os

from pdaltools import add_points_in_pointcloud

TEST_PATH = os.path.dirname(os.path.abspath(__file__))
TMP_PATH = os.path.join(TEST_PATH, "data/output")
DATA_LIDAR_PATH = os.path.join(TEST_PATH, "data/pointcloud")
DATA_POINTS_PATH = os.path.join(TEST_PATH, "data/points_3d")

INPUT_FILE = os.path.join(DATA_LIDAR_PATH, "Semis_2023_0292_6833_LA93_IGN69.laz")
INPUT_POINTS = os.path.join(DATA_POINTS_PATH, "Points_virtuels.geojson")
OUTPUT_FILE = os.path.join(TMP_PATH, "Semis_2023_0292_6833_LA93_IGN69.laz")


def test_test_add_line_to_lidar():
    print(DATA_POINTS_PATH)
    add_points_in_pointcloud.clip_3d_points_to_tile(INPUT_POINTS, INPUT_FILE, "EPSG:2154", OUTPUT_FILE)
