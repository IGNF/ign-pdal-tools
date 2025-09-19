import os
import shutil
import test.utils as tu

import laspy
import numpy as np
import pdal

from pdaltools.count_occurences.count_occurences_for_attribute import (
    compute_count_one_file,
)
from pdaltools.las_info import list_dims
from pdaltools.replace_area_in_pointcloud import get_writer_params, replace_area

TEST_PATH = os.path.dirname(os.path.abspath(__file__))
TMP_PATH = os.path.join(TEST_PATH, "tmp/replace_area_in_pointcloud")
INPUT_DIR = os.path.join(TEST_PATH, "data/replace_area_in_pointcloud")
TARGET_FILE = os.path.join(INPUT_DIR, "target_cloud_crop.laz")
SOURCE_FILE = os.path.join(INPUT_DIR, "source_cloud_crop.laz")
SHAPEFILE = os.path.join(INPUT_DIR, "ground_area.shp")
WRITER_PARAMS = get_writer_params(TARGET_FILE)


def setup_module(module):
    try:
        shutil.rmtree(TMP_PATH)

    except FileNotFoundError:
        pass
    os.mkdir(TMP_PATH)


# Utils functions
def get_nb_points(path):
    """Get number of points in a las file"""
    with laspy.open(path) as f:
        nb_points = f.header.point_count

    return nb_points


def test_replace_area_base():
    output_file = os.path.join(TMP_PATH, "test_replace_area", "replaced.laz")
    os.makedirs(os.path.dirname(output_file))
    replace_area(TARGET_FILE, SOURCE_FILE, SHAPEFILE, output_file, WRITER_PARAMS)
    # Check that we have the expected number of points in the output
    assert get_nb_points(output_file) == 6461

    # Check that there are only points from the target pointcloud outside the replacement geometry
    output_file_outside_geometry = os.path.join(os.path.dirname(output_file), "replaced_outside_area.laz")
    pipeline = pdal.Pipeline()
    pipeline |= pdal.Reader.las(filename=output_file)
    pipeline |= pdal.Filter.ferry(dimensions="=> geometryFid")
    pipeline |= pdal.Filter.assign(assignment="geometryFid[:]=-1")
    pipeline |= pdal.Filter.overlay(column="fid", dimension="geometryFid", datasource=SHAPEFILE)
    pipeline |= pdal.Filter.expression(expression="geometryFid==-1")
    pipeline |= pdal.Writer.las(filename=output_file_outside_geometry)
    pipeline.execute()
    counts_outside_area = compute_count_one_file(output_file_outside_geometry, "Classification")
    assert counts_outside_area == {"1": 3841, "2": 2355}

    # Check that there are only points from the source pointcloud inside the replacement geometry
    output_file_in_area = os.path.join(os.path.dirname(output_file), "replaced_in_area.laz")
    pipeline = pdal.Pipeline()
    pipeline |= pdal.Reader.las(filename=output_file)
    pipeline |= pdal.Filter.ferry(dimensions="=> geometryFid")
    pipeline |= pdal.Filter.assign(assignment="geometryFid[:]=-1")
    pipeline |= pdal.Filter.overlay(column="fid", dimension="geometryFid", datasource=SHAPEFILE)
    pipeline |= pdal.Filter.expression(expression="geometryFid>=0")
    pipeline |= pdal.Writer.las(filename=output_file_in_area)
    pipeline.execute()
    counts_in_area = compute_count_one_file(output_file_in_area, "Classification")

    assert counts_in_area == {"0": 265}

    # Check output dimensions are the same as input dimensions
    target_dimensions = tu.get_pdal_infos_summary(TARGET_FILE)["summary"]["dimensions"].split(",")
    output_dimensions = tu.get_pdal_infos_summary(output_file)["summary"]["dimensions"].split(",")

    assert output_dimensions == target_dimensions


def test_replace_with_filter():
    filter = "Classification==2"
    output_file = os.path.join(TMP_PATH, "test_replace_with_filter", "replaced.laz")
    os.makedirs(os.path.dirname(output_file))
    replace_area(TARGET_FILE, SOURCE_FILE, SHAPEFILE, output_file, WRITER_PARAMS, filter)
    assert get_nb_points(output_file) == 2620


def test_replace_two_datasources():
    target_file_class1 = os.path.join(INPUT_DIR, "target_cloud_crop_class1.laz")  # Classification=2
    source_file_class2 = os.path.join(INPUT_DIR, "source_cloud_crop_class2.laz")  # Classification=1
    writer_params = get_writer_params(target_file_class1)
    output_file = os.path.join(TMP_PATH, "test_replace_two_datasources", "replaced.laz")
    os.makedirs(os.path.dirname(output_file))
    replace_area(target_file_class1, source_file_class2, SHAPEFILE, output_file, writer_params)

    # Check if there is data from both input sources
    counts = compute_count_one_file(output_file, "Classification")

    assert counts == {"1": 6196, "2": 265}


def test_replace_extra_dims():
    tmp_extra_dim = os.path.join(TMP_PATH, "test_replace_extra_dims")
    os.makedirs(tmp_extra_dim)

    # generate target with an extra dim target with value 1, and target2
    target_file_extra_dim = os.path.join(tmp_extra_dim, "target_cloud_crop_extra_dim.laz")
    writer_params = get_writer_params(TARGET_FILE)
    pipeline = pdal.Pipeline() | pdal.Reader.las(TARGET_FILE)
    pipeline |= pdal.Filter.ferry(dimensions="=>target")
    pipeline |= pdal.Filter.assign(assignment="target[:]=1")

    pipeline |= pdal.Filter.ferry(dimensions="=>target2")
    pipeline |= pdal.Filter.assign(assignment="target2[:]=1")

    pipeline |= pdal.Writer.las(target_file_extra_dim, forward="all", extra_dims="target=uint16,target2=uint8")
    pipeline.execute()

    target_dims = list_dims(target_file_extra_dim)
    assert "target" in target_dims, "target should have 'target' dimension"
    assert "target2" in target_dims, "target should have 'target2' dimension"

    # generate source with an extra dim source
    source_file_extra_dim = os.path.join(tmp_extra_dim, "source_cloud_crop_extra_dim.laz")
    writer_params = get_writer_params(SOURCE_FILE)
    pipeline = pdal.Pipeline() | pdal.Reader.las(SOURCE_FILE)
    pipeline |= pdal.Filter.ferry(dimensions="=>source")
    pipeline |= pdal.Writer.las(source_file_extra_dim, forward="all", extra_dims="all")
    pipeline.execute()

    source_dims = list_dims(source_file_extra_dim)
    assert "source" in source_dims, "source should have 'source' dimension"
    assert "target" not in source_dims, "source should not have 'target' dimension"

    writer_params = get_writer_params(target_file_extra_dim)
    output_file = os.path.join(tmp_extra_dim, "replaced.laz")
    replace_area(target_file_extra_dim, source_file_extra_dim, SHAPEFILE, output_file, writer_params)

    replaced_dims = list_dims(output_file)

    assert "target" in replaced_dims  # dimension from target cloud
    assert "target2" in replaced_dims  # dimension from target cloud
    assert "source" not in replaced_dims  # dimension from source cloud should not be kept

    # check dimensions dtype
    las = laspy.read(output_file)
    assert las["target"].dtype == np.uint16
    assert las["target2"].dtype == np.uint8
