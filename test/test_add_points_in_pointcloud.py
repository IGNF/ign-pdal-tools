import inspect
import os
from pathlib import Path

import geopandas as gpd
import laspy
import numpy as np
import pytest
from shapely.geometry import LineString, MultiPoint, Point

from pdaltools import add_points_in_pointcloud
from pdaltools.count_occurences.count_occurences_for_attribute import (
    compute_count_one_file,
)

TEST_PATH = os.path.dirname(os.path.abspath(__file__))
TMP_PATH = os.path.join(TEST_PATH, "tmp/add_points_in_pointcloud")
DATA_LIDAR_PATH = os.path.join(TEST_PATH, "data/decimated_laz")
DATA_POINTS_3D_PATH = os.path.join(TEST_PATH, "data/points_3d")
DATA_LIGNES_PATH = os.path.join(TEST_PATH, "data/lignes_3d")

INPUT_PCD = os.path.join(DATA_LIDAR_PATH, "test_semis_2023_0292_6833_LA93_IGN69.laz")
INPUT_POINTS_2D = os.path.join(DATA_POINTS_3D_PATH, "Points_virtuels_2d_with_value_z_0292_6833.geojson")
INPUT_POINTS_3D = os.path.join(DATA_POINTS_3D_PATH, "Points_virtuels_0292_6833.geojson")
INPUT_LIGNES_2D_GEOJSON = os.path.join(DATA_LIGNES_PATH, "Lignes_2d_0292_6833.geojson")
INPUT_LIGNES_3D_GEOJSON = os.path.join(DATA_LIGNES_PATH, "Lignes_3d_0292_6833.geojson")
INPUT_LIGNES_SHAPE = os.path.join(DATA_LIGNES_PATH, "Lignes_3d_0292_6833.shp")
OUTPUT_FILE = os.path.join(TMP_PATH, "test_semis_2023_0292_6833_LA93_IGN69.laz")
INPUT_EMPTY_POINTS_2D = os.path.join(DATA_POINTS_3D_PATH, "Points_virtuels_2d_empty.geojson")

# Cropped las tile used to test adding points that belong to the theorical tile but not to the
# effective las file extent
INPUT_PCD_CROPPED = os.path.join(DATA_LIDAR_PATH, "test_semis_2021_0382_6565_LA93_IGN69_cropped.laz")
INPUT_POINTS_2D_FOR_CROPPED_PCD = os.path.join(
    DATA_POINTS_3D_PATH, "Points_virtuels_2d_with_value_z_0382_6565.geojson"
)
INPUT_POINTS_3D_FOR_CROPPED_PCD = os.path.join(DATA_POINTS_3D_PATH, "Points_virtuels_0382_6565.geojson")
OUTPUT_FILE_CROPPED_PCD = os.path.join(TMP_PATH, "test_semis_2021_0382_6565_LA93_IGN69.laz")


def setup_module(module):
    os.makedirs(TMP_PATH, exist_ok=True)


@pytest.mark.parametrize(
    "input_file, epsg",
    [
        (INPUT_POINTS_2D, "EPSG:2154"),  # should work when providing an epsg value + GeoJSON POINTS 2D
        (INPUT_POINTS_3D, "EPSG:2154"),  # should work when providing an epsg value + GeoJSON POINTS 3D
        (INPUT_POINTS_2D, None),  # Should also work with no epsg value (get from las file) + GeoJSON POINTS 2D
        (INPUT_POINTS_3D, None),  # Should also work with no epsg value (get from las file) + GeoJSON POINTS 3D
    ],
)
def test_clip_3d_points_to_tile(input_file, epsg):
    points_input = gpd.read_file(input_file)
    points_clipped = add_points_in_pointcloud.clip_3d_points_to_tile(points_input, INPUT_PCD, epsg, 1000)
    assert len(points_clipped) == 678  # check the entity's number of points


@pytest.mark.parametrize(
    "input_file, epsg",
    # Test on the same geomtries contained in various geometry formats
    [
        (INPUT_LIGNES_SHAPE, "EPSG:2154"),  # should work when providing an epsg value + shapefile
        (INPUT_LIGNES_2D_GEOJSON, "EPSG:2154"),  # should work when providing an epsg value + GeoJSON 2D
        (INPUT_LIGNES_3D_GEOJSON, "EPSG:2154"),  # should work when providing an epsg value + GeoJSON 3D
        (INPUT_LIGNES_SHAPE, None),  # Should also work with no epsg value (get from las file) + shapefile
        (INPUT_LIGNES_2D_GEOJSON, None),  # Should also work with no epsg value (get from las file) + GeoJSON 2D
        (INPUT_LIGNES_3D_GEOJSON, None),  # Should also work with no epsg value (get from las file) + GeoJSON 3D
    ],
)
def test_clip_3d_lines_to_tile(input_file, epsg):
    # With lines contained in the LIDAR tile
    lines_input = gpd.read_file(input_file)
    lines_clipped = add_points_in_pointcloud.clip_3d_lines_to_tile(lines_input, INPUT_PCD, epsg, 1000)
    assert len(lines_clipped) == 22  # check the entity's number of lines

    # Without lines contained in the LIDAR tile
    lines_input = gpd.read_file(input_file)
    lines_clipped = add_points_in_pointcloud.clip_3d_lines_to_tile(lines_input, INPUT_PCD_CROPPED, epsg, 1000)
    assert len(lines_clipped) == 0  # check the entity's number of lines


@pytest.mark.parametrize(
    "input_file, epsg, input_points_2d, expected_nb_points",
    [
        (INPUT_PCD, "EPSG:2154", INPUT_POINTS_2D, 2423),  # should work when providing an epsg value
        (INPUT_PCD, None, INPUT_POINTS_2D, 2423),  # Should also work with no epsg value (get from las file)
        (INPUT_PCD_CROPPED, None, INPUT_POINTS_2D_FOR_CROPPED_PCD, 451),
        # Should also work if there is no points (direct copy of the input file)
        (INPUT_PCD_CROPPED, None, INPUT_EMPTY_POINTS_2D, 0),
    ],
)
def test_add_points_to_las(input_file, epsg, input_points_2d, expected_nb_points):
    # Ensure the output file doesn't exist before the test
    if Path(OUTPUT_FILE).exists():
        os.remove(OUTPUT_FILE)

    points = gpd.read_file(input_points_2d)
    add_points_in_pointcloud.add_points_to_las(points, input_file, OUTPUT_FILE, epsg, 68)
    assert Path(OUTPUT_FILE).exists()  # check output exists

    point_count = compute_count_one_file(OUTPUT_FILE)["68"]
    assert point_count == expected_nb_points  # Add all points from geojson

    # Read original and updated point clouds
    original_las = laspy.read(input_file)
    updated_las = laspy.read(OUTPUT_FILE)

    original_count = len(original_las.points)
    added_count = len(points)

    # Check total point count
    assert len(updated_las.points) == original_count + added_count

    default_zero_fields = [
        "gps_time",
        "intensity",
        "return_number",
        "number_of_returns",
        "scan_direction_flag",
        "edge_of_flight_line",
        "R",
        "G",
        "B",
    ]
    # Ensure original points retain their values (gps_tme, intensity, etc)
    for field in default_zero_fields:
        if hasattr(updated_las, field):
            values = getattr(updated_las, field)
            original_values = getattr(original_las, field)
            assert np.all(values[:original_count] == original_values[:original_count])

    # Ensure added points have zero values for gps_time, intensity, etc
    for field in default_zero_fields:
        if hasattr(updated_las, field):
            values = getattr(updated_las, field)
            assert np.all(values[original_count:] == 0)


@pytest.mark.parametrize(
    "line, spacing, z_value, expected_points",
    [
        # End point is a multiple of spacing, z_value is provided
        (
            LineString([(0, 0), (4, 0)]),
            2,
            0.5,
            [
                Point(0, 0, 0.5),
                Point(2, 0, 0.5),
                Point(4, 0, 0.5),
            ],
        ),
        # End point is not a multiple of spacing, z_value is provided
        (
            LineString([(9, 0), (9, 9)]),
            5,
            0.5,
            [Point(9, 0, 0.5), Point(9, 5, 0.5), Point(9, 9, 0.5)],
        ),
        # End point is not a multiple of spacing, z_value is provided in point.z instead of z_value
        (
            LineString([(0, 0, 1), (4, 0, 1)]),
            2,
            0.5,
            [
                Point(0, 0, 1),
                Point(2, 0, 1),
                Point(4, 0, 1),
            ],
        ),
    ],
)
def test_line_to_multipoint(line, spacing, z_value, expected_points):
    multipoint = add_points_in_pointcloud.line_to_multipoint(line, spacing, z_value)
    assert multipoint.equals(MultiPoint(expected_points))


@pytest.mark.parametrize(
    "lines_gdf, spacing, altitude_column, expected_points",
    [
        # Test case for 2D lines with Z values in "RecupZ"
        (
            gpd.GeoDataFrame(
                {"geometry": [LineString([(0, 0), (10, 0)]), LineString([(10, 0), (10, 10)])], "RecupZ": [5.0, 10.0]},
                crs="EPSG:2154",
            ),
            2.5,
            "RecupZ",
            [
                Point(0, 0, 5.0),
                Point(2.5, 0, 5.0),
                Point(5.0, 0, 5.0),
                Point(7.5, 0, 5.0),
                Point(10, 0, 5.0),
                Point(10, 2.5, 10.0),
                Point(10, 5.0, 10.0),
                Point(10, 7.5, 10.0),
                Point(10, 10, 10.0),
            ],
        ),
        # Test case for 3D lines
        (
            gpd.GeoDataFrame(
                {"geometry": [LineString([(0, 0, 3), (10, 0, 3)]), LineString([(10, 0, 6), (10, 10, 6)])]},
                crs="EPSG:2154",
            ),
            2.5,
            None,
            [
                Point(0, 0, 3.0),
                Point(2.5, 0, 3.0),
                Point(5.0, 0, 3.0),
                Point(7.5, 0, 3.0),
                Point(10, 0, 3.0),
                Point(10, 2.5, 6.0),
                Point(10, 5.0, 6.0),
                Point(10, 7.5, 6.0),
                Point(10, 10, 6.0),
            ],
        ),
    ],
)
def test_generate_3d_points_from_lines(lines_gdf, spacing, altitude_column, expected_points):
    points_gdf = add_points_in_pointcloud.generate_3d_points_from_lines(lines_gdf, spacing, altitude_column)

    # Check the result
    assert points_gdf.geometry.tolist() == expected_points


@pytest.mark.parametrize(
    "input_file, input_points, epsg, expected_nb_points, spacing, altitude_column",
    [
        (INPUT_PCD, INPUT_POINTS_2D, "EPSG:2154", 678, 0, "RecupZ"),  # should add only points 2.5D within tile extent
        (INPUT_PCD, INPUT_POINTS_3D, "EPSG:2154", 678, 0, None),  # should add only points 3D within tile extent
        (INPUT_PCD_CROPPED, INPUT_POINTS_3D_FOR_CROPPED_PCD, "EPSG:2154", 186, 0, None),
        (INPUT_PCD_CROPPED, INPUT_POINTS_2D_FOR_CROPPED_PCD, "EPSG:2154", 186, 0, "RecupZ"),
        (
            INPUT_PCD,
            INPUT_LIGNES_2D_GEOJSON,
            "EPSG:2154",
            678,
            0.25,
            "RecupZ",
        ),  # should add only lines (.GeoJSON) within tile extend
        (
            INPUT_PCD,
            INPUT_LIGNES_SHAPE,
            "EPSG:2154",
            678,
            0.25,
            "RecupZ",
        ),  # should add only lignes (.shp) within tile extend
        (INPUT_PCD, INPUT_LIGNES_SHAPE, None, 678, 0.25, "RecupZ"),  # Should work with or with an input epsg
        (
            INPUT_PCD,
            INPUT_LIGNES_3D_GEOJSON,
            None,
            678,
            0.25,
            None,
        ),  # Should work with or without an input epsg and without altitude_column
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
    
    # Read input and output files to compare headers
    input_las = laspy.read(input_file)
    output_las = laspy.read(OUTPUT_FILE)
    
    # Compare headers
    assert input_las.header.version == output_las.header.version
    assert input_las.header.system_identifier == output_las.header.system_identifier
    assert input_las.header.extra_header_bytes == output_las.header.extra_header_bytes
    assert input_las.header.extra_vlr_bytes == output_las.header.extra_vlr_bytes
    assert input_las.header.number_of_evlrs == output_las.header.number_of_evlrs
    assert input_las.header.point_format == output_las.header.point_format
    assert np.array_equal(input_las.header.scales, output_las.header.scales)
    assert np.array_equal(input_las.header.offsets, output_las.header.offsets)
    assert input_las.header.vlrs[0].string == output_las.header.vlrs[0].string
    
    point_count = compute_count_one_file(OUTPUT_FILE)["68"]
    assert point_count == expected_nb_points  # Add all points from geojson


@pytest.mark.parametrize(
    "input_file, input_points, epsg, spacing, altitude_column",
    [
        (INPUT_PCD, INPUT_LIGNES_SHAPE, None, 0, "RecupZ"),  # spacing <= 0
        (INPUT_PCD, INPUT_LIGNES_SHAPE, None, -5, "RecupZ"),  # spacing < 0
        (
            INPUT_PCD,
            INPUT_LIGNES_3D_GEOJSON,
            None,
            0,
            None,
        ),  # spacing <= 0
    ],
)
def test_add_points_from_geometry_to_las_nok(input_file, input_points, epsg, spacing, altitude_column):
    # Ensure the output file doesn't exist before the test
    if Path(OUTPUT_FILE).exists():
        os.remove(OUTPUT_FILE)

    with pytest.raises(NotImplementedError, match=".*LineString.*spacing.*"):
        add_points_in_pointcloud.add_points_from_geometry_to_las(
            input_points,
            input_file,
            OUTPUT_FILE,
            68,
            epsg,
            1000,
            spacing,
            altitude_column,
        )


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
