import inspect
import os
from pathlib import Path

import geopandas as gpd
import pytest

from pdaltools import add_points_in_pointcloud
from pdaltools.count_occurences.count_occurences_for_attribute import (
    compute_count_one_file,
)

TEST_PATH = os.path.dirname(os.path.abspath(__file__))
TMP_PATH = os.path.join(TEST_PATH, "tmp/add_points_in_pointcloud")
DATA_LIDAR_PATH = os.path.join(TEST_PATH, "data/decimated_laz")
DATA_POINTS_PATH = os.path.join(TEST_PATH, "data/points_3d")

INPUT_PCD = os.path.join(DATA_LIDAR_PATH, "test_semis_2023_0292_6833_LA93_IGN69.laz")
INPUT_POINTS = os.path.join(DATA_POINTS_PATH, "Points_virtuels_0292_6833.geojson")
OUTPUT_FILE = os.path.join(TMP_PATH, "test_semis_2023_0292_6833_LA93_IGN69.laz")

# Cropped las tile used to test adding points that belong to the theorical tile but not to the
# effective las file extent
INPUT_PCD_CROPPED = os.path.join(DATA_LIDAR_PATH, "test_semis_2021_0382_6565_LA93_IGN69_cropped.laz")
INPUT_POINTS_FOR_CROPPED_PCD = os.path.join(DATA_POINTS_PATH, "Points_virtuels_0382_6565.geojson")
OUTPUT_FILE_CROPPED_PCD = os.path.join(TMP_PATH, "test_semis_2021_0382_6565_LA93_IGN69.laz")


def setup_module(module):
    os.makedirs(TMP_PATH, exist_ok=True)


@pytest.mark.parametrize(
    "epsg",
    [
        "EPSG:2154",  # should work when providing an epsg value
        None,  # Should also work with no epsg value (get from las file)
    ],
)
def test_clip_3d_points_to_tile(epsg):
    # With EPSG
    points_clipped = add_points_in_pointcloud.clip_3d_points_to_tile(INPUT_POINTS, INPUT_PCD, epsg, 1000)
    assert len(points_clipped) == 678  # check the entity's number of points


@pytest.mark.parametrize(
    "input_file, epsg, expected_nb_points",
    [
        (INPUT_PCD, "EPSG:2154", 2423),  # should work when providing an epsg value
        (INPUT_PCD, None, 2423),  # Should also work with no epsg value (get from las file)
        (INPUT_PCD_CROPPED, None, 2423),
    ],
)
def test_add_points_to_las(input_file, epsg, expected_nb_points):
    # Ensure the output file doesn't exist before the test
    if Path(OUTPUT_FILE).exists():
        os.remove(OUTPUT_FILE)

    points = gpd.read_file(INPUT_POINTS)
    add_points_in_pointcloud.add_points_to_las(points, input_file, OUTPUT_FILE, epsg, 68)
    assert Path(OUTPUT_FILE).exists()  # check output exists

    point_count = compute_count_one_file(OUTPUT_FILE)["68"]
    assert point_count == expected_nb_points  # Add all points from geojson


@pytest.mark.parametrize(
    "input_file, input_points, epsg, expected_nb_points",
    [
        (INPUT_PCD, INPUT_POINTS, None, 678),  # should add only points within tile extent
        (INPUT_PCD_CROPPED, INPUT_POINTS_FOR_CROPPED_PCD, None, 186),
        (
            INPUT_PCD_CROPPED,
            INPUT_POINTS,
            None,
            0,
        ),  # Should add no points when there is only points outside the tile extent
        (
            INPUT_PCD_CROPPED,
            INPUT_POINTS_FOR_CROPPED_PCD,
            "EPSG:2154",
            186,
        ),  # Should work with or without an input epsg
    ],
)
def test_add_points_from_geojson_to_las(input_file, input_points, epsg, expected_nb_points):
    # Ensure the output file doesn't exist before the test
    if Path(OUTPUT_FILE).exists():
        os.remove(OUTPUT_FILE)

    add_points_in_pointcloud.add_points_from_geojson_to_las(input_points, input_file, OUTPUT_FILE, 68, epsg, 1000)
    assert Path(OUTPUT_FILE).exists()  # check output exists
    point_count = compute_count_one_file(OUTPUT_FILE)["68"]
    assert point_count == expected_nb_points  # Add all points from geojson


def test_parse_args():
    # sanity check for arguments parsing
    args = add_points_in_pointcloud.parse_args(
        [
            "--input_geojson",
            "data/points_3d/Points_virtuels_0292_6833.geojson",
            "--input_las",
            "data/decimated_laz/test_semis_2023_0292_6833_LA93_IGN69.laz",
            "--output_las",
            "data/output/test_semis_2023_0292_6833_LA93_IGN69.laz",
            "--virtual_points_classes",
            "68",
            "--spatial_ref",
            "EPSG:2154",
            "--tile_width",
            "1000",
        ]
    )
    parsed_args_keys = args.__dict__.keys()
    main_parameters = inspect.signature(add_points_in_pointcloud.add_points_from_geojson_to_las).parameters.keys()
    assert set(parsed_args_keys) == set(main_parameters)
