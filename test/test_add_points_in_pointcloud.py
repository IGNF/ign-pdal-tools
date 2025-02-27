import inspect
import os
from pathlib import Path

import pdal
import pytest

import pdaltools.las_info
from pdaltools import add_points_in_pointcloud

TEST_PATH = os.path.dirname(os.path.abspath(__file__))
TMP_PATH = os.path.join(TEST_PATH, "data/output")
DATA_LIDAR_PATH = os.path.join(TEST_PATH, "data/decimated_laz")
DATA_POINTS_PATH = os.path.join(TEST_PATH, "data/points_3d")

INPUT_FILE = os.path.join(DATA_LIDAR_PATH, "test_semis_2023_0292_6833_LA93_IGN69.laz")
INPUT_POINTS = os.path.join(DATA_POINTS_PATH, "Points_virtuels_0292_6833.geojson")
OUTPUT_FILE = os.path.join(TMP_PATH, "test_semis_2023_0292_6833_LA93_IGN69.laz")

INPUT_FILE_SMALL = os.path.join(DATA_LIDAR_PATH, "test_semis_2021_0382_6565_LA93_IGN69.laz")
INPUT_POINTS_SMALL = os.path.join(DATA_POINTS_PATH, "Points_virtuels_0382_6565.geojson")
OUTPUT_FILE_SMALL = os.path.join(TMP_PATH, "test_semis_2021_0382_6565_LA93_IGN69.laz")


def setup_module(module):
    os.makedirs("test/data/output", exist_ok=True)


def test_clip_3d_points_to_tile():
    # With EPSG
    points_clipped = add_points_in_pointcloud.clip_3d_points_to_tile(INPUT_POINTS, INPUT_FILE, "EPSG:2154", 1000)
    assert len(points_clipped) == 678  # chech the entity's number of points


def test_clip_3d_points_to_tile_from_epsg_none():
    points_clipped = add_points_in_pointcloud.clip_3d_points_to_tile(INPUT_POINTS, INPUT_FILE, None, 1000)
    assert len(points_clipped) == 678  # chech the entity's number of points


def test_add_line_to_lidar():
    # Ensure the output file doesn't exist before the test
    if Path(OUTPUT_FILE).exists():
        os.remove(OUTPUT_FILE)

    points_clipped = add_points_in_pointcloud.clip_3d_points_to_tile(INPUT_POINTS, INPUT_FILE, "EPSG:2154", 1000)

    add_points_in_pointcloud.add_points_to_las(points_clipped, INPUT_FILE, OUTPUT_FILE, "EPSG:2154", 68)
    assert Path(OUTPUT_FILE).exists()  # check output exists

    # Filter pointcloud by classes
    pipeline = (
        pdal.Reader.las(filename=OUTPUT_FILE, nosrs=True)
        | pdal.Filter.range(
            limits="Classification[68:68]",
        )
        | pdal.Filter.stats()
    )
    pipeline.execute()
    metadata = pipeline.metadata
    # Count the pointcloud's number from classe "68"
    point_count = metadata["metadata"]["filters.stats"]["statistic"][0]["count"]
    assert point_count == 678


def test_add_line_to_lidar_from_epsg_none():
    # Ensure the output file doesn't exist before the test
    if Path(OUTPUT_FILE).exists():
        os.remove(OUTPUT_FILE)

    points_clipped = add_points_in_pointcloud.clip_3d_points_to_tile(INPUT_POINTS, INPUT_FILE, None, 1000)

    add_points_in_pointcloud.add_points_to_las(points_clipped, INPUT_FILE, OUTPUT_FILE, None, 68)
    assert Path(OUTPUT_FILE).exists()  # check output exists

    # Filter pointcloud by classes
    pipeline = (
        pdal.Reader.las(filename=OUTPUT_FILE, nosrs=True)
        | pdal.Filter.range(
            limits="Classification[68:68]",
        )
        | pdal.Filter.stats()
    )
    pipeline.execute()
    metadata = pipeline.metadata
    # Count the pointcloud's number from classe "68"
    point_count = metadata["metadata"]["filters.stats"]["statistic"][0]["count"]
    assert point_count == 678


def test_get_tile_bbox_small():
    # Tile is not complete (NOT 1km * 1km)
    bbox = pdaltools.las_info.get_tile_bbox(INPUT_FILE_SMALL, 1000)
    assert bbox == (382000.0, 6564000.0, 383000.0, 6565000.0)  # return BBOX 1km * 1km


def test_add_line_to_lidar_small():
    # Ensure the output file doesn't exist before the test
    if Path(OUTPUT_FILE_SMALL).exists():
        os.remove(OUTPUT_FILE_SMALL)

    # Tile is not complete (NOT 1km * 1km)
    points_clipped = add_points_in_pointcloud.clip_3d_points_to_tile(
        INPUT_POINTS_SMALL, INPUT_FILE_SMALL, "EPSG:2154", 1000
    )

    add_points_in_pointcloud.add_points_to_las(points_clipped, INPUT_FILE_SMALL, OUTPUT_FILE_SMALL, "EPSG:2154", 68)
    assert Path(OUTPUT_FILE).exists()  # check output exists

    # Filter pointcloud by classes
    pipeline = (
        pdal.Reader.las(filename=OUTPUT_FILE_SMALL, nosrs=True)
        | pdal.Filter.range(
            limits="Classification[68:68]",
        )
        | pdal.Filter.stats()
    )
    pipeline.execute()
    metadata = pipeline.metadata
    # Count the pointcloud's number from classe "68"
    point_count = metadata["metadata"]["filters.stats"]["statistic"][0]["count"]
    assert point_count == 186


def test_add_points_from_geojson_to_las():
    # Ensure the output file doesn't exist before the test
    if Path(OUTPUT_FILE).exists():
        os.remove(OUTPUT_FILE)

    add_points_in_pointcloud.add_points_from_geojson_to_las(
        INPUT_POINTS, INPUT_FILE, OUTPUT_FILE, 68, "EPSG:2154", 1000
    )
    assert Path(OUTPUT_FILE).exists()  # check output exists


def test_add_points_from_geojson_to_las_no_epsg():
    # Ensure the output file doesn't exist before the test
    if Path(OUTPUT_FILE).exists():
        os.remove(OUTPUT_FILE)

    INPUT_FILE_WITHOUT_EPSG = os.path.join(TEST_PATH, "data/test_noepsg_043500_629205_IGN69.laz")

    with pytest.raises(RuntimeError, match="does not have a valid EPSG code"):
        add_points_in_pointcloud.add_points_from_geojson_to_las(
            INPUT_POINTS, INPUT_FILE_WITHOUT_EPSG, OUTPUT_FILE, 68, None, 1000
        )


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
