import inspect
import os
from pathlib import Path

import geopandas as gpd
import pytest
from shapely.geometry import LineString, MultiPoint, Point

from pdaltools import add_points_in_pointcloud
from pdaltools.count_occurences.count_occurences_for_attribute import (
    compute_count_one_file,
)

TEST_PATH = os.path.dirname(os.path.abspath(__file__))
TMP_PATH = os.path.join(TEST_PATH, "tmp/add_points_in_pointcloud")
DATA_LIDAR_PATH = os.path.join(TEST_PATH, "data/decimated_laz")
DATA_POINTS_PATH = os.path.join(TEST_PATH, "data/points_3d")
DATA_LIGNES_PATH = os.path.join(TEST_PATH, "data/lignes_2_5d")

INPUT_PCD = os.path.join(DATA_LIDAR_PATH, "test_semis_2023_0292_6833_LA93_IGN69.laz")
INPUT_POINTS = os.path.join(DATA_POINTS_PATH, "Points_virtuels_0292_6833.geojson")
INPUT_LIGNES_GEOJSON = os.path.join(DATA_LIGNES_PATH, "Lignes_3d_0292_6833.geojson")
INPUT_LIGNES_SHAPE = os.path.join(DATA_LIGNES_PATH, "Lignes_3d_0292_6833.shp")
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
    points_gdf = gpd.read_file(INPUT_POINTS)
    points_clipped = add_points_in_pointcloud.clip_3d_points_to_tile(points_gdf, INPUT_PCD, epsg, 1000)
    assert len(points_clipped) == 678  # check the entity's number of points


@pytest.mark.parametrize(
    "epsg",
    [
        "EPSG:2154",  # should work when providing an epsg value
        None,  # Should also work with no epsg value (get from las file)
    ],
)
def test_clip_3d_lines_to_tile(epsg):
    # With EPSG
    lines_gdf = gpd.read_file(INPUT_LIGNES_SHAPE)
    lines_clipped = add_points_in_pointcloud.clip_3d_lines_to_tile(lines_gdf, INPUT_PCD, epsg, 1000)
    assert len(lines_clipped) == 22  # check the entity's number of lines


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
    "line, spacing, z_value",
    [
        (LineString([(0, 0), (10, 0), (10, 10)]), 2.5, 0.5),
    ],
)
def test_line_to_multipoint(line, spacing, z_value):
    multipoint = add_points_in_pointcloud.line_to_multipoint(line, spacing, z_value)

    # Check the result
    expected_points = [
        Point(0, 0, z_value),
        Point(2.5, 0, z_value),
        Point(5.0, 0, z_value),
        Point(7.5, 0, z_value),
        Point(10, 0, z_value),
        Point(10, 2.5, z_value),
        Point(10, 5.0, z_value),
        Point(10, 7.5, z_value),
        Point(10, 10, z_value),
    ]
    assert multipoint.equals(MultiPoint(expected_points))


@pytest.mark.parametrize(
    "lines_gdf, spacing, altitude_column",
    [
        (
            gpd.GeoDataFrame(
                {"geometry": [LineString([(0, 0), (10, 0)]), LineString([(10, 0), (10, 10)])], "RecupZ": [5.0, 10.0]},
                crs="EPSG:2154",
            ),
            2.5,
            "RecupZ",
        ),
    ],
)
def test_generate_3d_points_from_lines(lines_gdf, spacing, altitude_column):
    points_gdf = add_points_in_pointcloud.generate_3d_points_from_lines(lines_gdf, spacing, altitude_column)

    # Check the result
    expected_points = [
        Point(0, 0, 5.0),
        Point(2.5, 0, 5.0),
        Point(5.0, 0, 5.0),
        Point(7.5, 0, 5.0),
        Point(10, 0, 5.0),
        Point(10, 2.5, 10.0),
        Point(10, 5.0, 10.0),
        Point(10, 7.5, 10.0),
        Point(10, 10, 10.0),
    ]
    assert points_gdf.geometry.tolist() == expected_points


@pytest.mark.parametrize(
    "input_file, input_points, epsg, expected_nb_points, spacing, altitude_column",
    [
        (INPUT_PCD, INPUT_POINTS, None, 678, 0, "RecupZ"),  # should add only points within tile extent
        (INPUT_PCD_CROPPED, INPUT_POINTS_FOR_CROPPED_PCD, None, 186, 0, "RecupZ"),
        (
            INPUT_PCD_CROPPED,
            INPUT_POINTS_FOR_CROPPED_PCD,
            None,
            186,
            0,
            "RecupZ",
        ),  # Should add no points when there is only points outside the tile extent
        (
            INPUT_PCD_CROPPED,
            INPUT_POINTS_FOR_CROPPED_PCD,
            "EPSG:2154",
            186,
            0,
            "RecupZ",
        ),  # Should work with or without an input epsg
        (
            INPUT_PCD,
            INPUT_LIGNES_GEOJSON,
            "EPSG:2154",
            678,
            0.25,
            "RecupZ",
        ),  # should add only lignes (.GeoJSON) within tile extend
        (INPUT_PCD, INPUT_LIGNES_GEOJSON, None, 678, 0.25, "RecupZ"),  # Should work with or without an input epsg
        (
            INPUT_PCD,
            INPUT_LIGNES_SHAPE,
            "EPSG:2154",
            678,
            0.25,
            "RecupZ",
        ),  # should add only lignes (.shp) within tile extend
        (INPUT_PCD, INPUT_LIGNES_SHAPE, None, 678, 0.25, "RecupZ"),  # Should work with or without an input epsg
    ],
)
def test_add_points_from_geometry_to_las(input_file, input_points, epsg, expected_nb_points, spacing, altitude_column):
    # Ensure the output file doesn't exist before the test
    if Path(OUTPUT_FILE).exists():
        os.remove(OUTPUT_FILE)

    add_points_in_pointcloud.add_points_from_geometry_to_las(
        input_points, input_file, OUTPUT_FILE, 68, epsg, 1000, spacing, altitude_column
    )
    assert Path(OUTPUT_FILE).exists()  # check output exists
    point_count = compute_count_one_file(OUTPUT_FILE)["68"]
    assert point_count == expected_nb_points  # Add all points from geojson


def test_parse_args():
    # sanity check for arguments parsing
    args = add_points_in_pointcloud.parse_args(
        [
            "--input_geometry",
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
            "--spacing",
            "0",
            "--altitude_column",
            "RecupZ",
        ]
    )
    parsed_args_keys = args.__dict__.keys()
    main_parameters = inspect.signature(add_points_in_pointcloud.add_points_from_geometry_to_las).parameters.keys()
    assert set(parsed_args_keys) == set(main_parameters)
