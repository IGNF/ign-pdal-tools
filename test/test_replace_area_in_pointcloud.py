import os
import shutil
import test.utils as tu

import laspy
import numpy as np
import pdal
import pytest

from pdaltools.count_occurences.count_occurences_for_attribute import (
    compute_count_one_file,
)
from pdaltools.las_info import list_dims
from pdaltools.replace_area_in_pointcloud import (
    argument_parser,
    pipeline_read_from_cloud,
    pipeline_read_from_DSM,
    replace_area,
)

TEST_PATH = os.path.dirname(os.path.abspath(__file__))
TMP_PATH = os.path.join(TEST_PATH, "tmp/replace_area_in_pointcloud")
INPUT_DIR = os.path.join(TEST_PATH, "data/replace_area_in_pointcloud")

TARGET_CLOUD = os.path.join(INPUT_DIR, "target_cloud_crop.laz")
REPLACE_AREA = os.path.join(INPUT_DIR, "replace_area.geojson")

# source may be a cloud
SOURCE_CLOUD = os.path.join(INPUT_DIR, "source_cloud_crop.laz")

# source may be a digital surface model
SOURCE_DSM = os.path.join(INPUT_DIR, "DSM.tif")
SOURCE_GROUND_MASK = os.path.join(INPUT_DIR, "ground_mask.tif")
SOURCE_CLASSIF = 68

TMP_EXTRA_DIMS = os.path.join(TMP_PATH, "input_with_extra_dims")
TARGET_EXTRA_DIM = os.path.join(TMP_EXTRA_DIMS, "target_cloud_crop_extra_dim.laz")


def setup_module(module):
    try:
        shutil.rmtree(TMP_PATH)

    except FileNotFoundError:
        pass
    os.mkdir(TMP_PATH)

    # target file with extra dims is used is severals tests.
    generate_target_extra_dim()


def generate_extra_dim(input, output, new_dims):
    pipeline = pdal.Pipeline() | pdal.Reader.las(input)
    for dim in new_dims.keys():
        pipeline |= pdal.Filter.ferry(dimensions=f"=>{dim}")
        pipeline |= pdal.Filter.assign(assignment=f"{dim}[:]=1")

    extra_dims = ",".join(f"{k}={v}" for k, v in new_dims.items())
    pipeline |= pdal.Writer.las(output, forward="all", extra_dims=extra_dims)
    pipeline.execute()


def generate_target_extra_dim():
    """generate target with an extra dim target with value 1, and target2"""

    os.makedirs(TMP_EXTRA_DIMS)
    generate_extra_dim(input=TARGET_CLOUD, output=TARGET_EXTRA_DIM, new_dims={"target": "uint16", "target2": "uint8"})

    target_dims = list_dims(TARGET_EXTRA_DIM)
    assert "target" in target_dims, "target should have 'target' dimension"
    assert "target2" in target_dims, "target should have 'target2' dimension"


# Utils functions
def get_nb_points(path):
    """Get number of points in a las file"""
    with laspy.open(path) as f:
        nb_points = f.header.point_count

    return nb_points


def test_replace_area_base():
    output_file = os.path.join(TMP_PATH, "test_replace_area", "replaced.laz")
    os.makedirs(os.path.dirname(output_file))

    replace_area(
        target_cloud=TARGET_CLOUD,
        pipeline_source=pipeline_read_from_cloud(SOURCE_CLOUD),
        replacement_area=REPLACE_AREA,
        output_cloud=output_file,
    )
    # Check that we have the expected number of points in the output
    assert get_nb_points(output_file) == 6461

    # Check that there are only points from the target pointcloud outside the replacement geometry
    output_file_outside_geometry = os.path.join(os.path.dirname(output_file), "replaced_outside_area.laz")
    pipeline = pdal.Pipeline()
    pipeline |= pdal.Reader.las(filename=output_file)
    pipeline |= pdal.Filter.ferry(dimensions="=> geometryFid")
    pipeline |= pdal.Filter.assign(assignment="geometryFid[:]=-1")
    pipeline |= pdal.Filter.overlay(column="fid", dimension="geometryFid", datasource=REPLACE_AREA)
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
    pipeline |= pdal.Filter.overlay(column="fid", dimension="geometryFid", datasource=REPLACE_AREA)
    pipeline |= pdal.Filter.expression(expression="geometryFid>=0")
    pipeline |= pdal.Writer.las(filename=output_file_in_area)
    pipeline.execute()
    counts_in_area = compute_count_one_file(output_file_in_area, "Classification")

    assert counts_in_area == {"0": 265}

    # Check output dimensions are the same as input dimensions
    target_dimensions = tu.get_pdal_infos_summary(TARGET_CLOUD)["summary"]["dimensions"].split(",")
    output_dimensions = tu.get_pdal_infos_summary(output_file)["summary"]["dimensions"].split(",")

    assert output_dimensions == target_dimensions


def test_replace_area_with_target_filter():
    filter = "Classification==2"
    output_file = os.path.join(TMP_PATH, "test_replace_with_target_filter", "replaced.laz")
    os.makedirs(os.path.dirname(output_file))
    replace_area(
        target_cloud=TARGET_CLOUD,
        pipeline_source=pipeline_read_from_cloud(SOURCE_CLOUD),
        replacement_area=REPLACE_AREA,
        output_cloud=output_file,
        target_pdal_filter=filter,
    )
    assert get_nb_points(output_file) == 2620


def test_replace_area_with_source_filter():
    filter = "Z>=2550"
    output_file = os.path.join(TMP_PATH, "test_replace_with_source_filter", "replaced.laz")
    os.makedirs(os.path.dirname(output_file))
    replace_area(
        target_cloud=TARGET_CLOUD,
        pipeline_source=pipeline_read_from_cloud(SOURCE_CLOUD),
        replacement_area=REPLACE_AREA,
        output_cloud=output_file,
        source_pdal_filter=filter,
    )
    assert get_nb_points(output_file) == 6390


def test_replace_area_two_datasources():
    target_file_class1 = os.path.join(INPUT_DIR, "target_cloud_crop_class1.laz")  # Classification=2
    source_file_class2 = os.path.join(INPUT_DIR, "source_cloud_crop_class2.laz")  # Classification=1
    output_file = os.path.join(TMP_PATH, "test_replace_two_datasources", "replaced.laz")
    os.makedirs(os.path.dirname(output_file))
    replace_area(
        target_cloud=target_file_class1,
        pipeline_source=pipeline_read_from_cloud(source_file_class2),
        replacement_area=REPLACE_AREA,
        output_cloud=output_file,
    )

    # Check if there is data from both input sources
    counts = compute_count_one_file(output_file, "Classification")

    assert counts == {"1": 6196, "2": 265}


def test_replace_area_extra_dims():
    tmp_extra_dim = os.path.join(TMP_PATH, "test_replace_extra_dims")
    os.makedirs(tmp_extra_dim)

    # generate source with an extra dim source
    source_file_extra_dim = os.path.join(tmp_extra_dim, "source_cloud_crop_extra_dim.laz")
    generate_extra_dim(input=SOURCE_CLOUD, output=source_file_extra_dim, new_dims={"source": "float"})

    source_dims = list_dims(source_file_extra_dim)
    assert "source" in source_dims, "source should have 'source' dimension"
    assert "target" not in source_dims, "source should not have 'target' dimension"

    output_file = os.path.join(tmp_extra_dim, "replaced.laz")

    replace_area(
        target_cloud=TARGET_EXTRA_DIM,
        pipeline_source=pipeline_read_from_cloud(source_file_extra_dim),
        replacement_area=REPLACE_AREA,
        output_cloud=output_file,
    )

    replaced_dims = list_dims(output_file)

    assert "target" in replaced_dims  # dimension from target cloud
    assert "target2" in replaced_dims  # dimension from target cloud
    assert "source" not in replaced_dims  # dimension from source cloud should not be kept

    # check dimensions dtype
    las = laspy.read(output_file)
    assert las["target"].dtype == np.uint16
    assert las["target2"].dtype == np.uint8


def test_replace_area_with_no_point_on_target():
    output_file = os.path.join(TMP_PATH, "test_replace_area_no_point_on_target", "replaced.laz")
    os.makedirs(os.path.dirname(output_file))

    replace_area(
        target_cloud=TARGET_EXTRA_DIM,
        pipeline_source=pipeline_read_from_cloud(SOURCE_CLOUD),
        replacement_area=REPLACE_AREA,
        output_cloud=output_file,
        target_pdal_filter="Classification==3",
    )
    assert get_nb_points(output_file) == 265

    # check dimensions dtype
    las = laspy.read(output_file)
    assert las["target"].dtype == np.uint16
    assert las["target2"].dtype == np.uint8


def test_replace_area_with_no_point_on_source():
    output_file = os.path.join(TMP_PATH, "test_replace_area_no_point_on_source", "replaced.laz")
    os.makedirs(os.path.dirname(output_file))

    replace_area(
        target_cloud=TARGET_EXTRA_DIM,
        pipeline_source=pipeline_read_from_cloud(SOURCE_CLOUD),
        replacement_area=REPLACE_AREA,
        output_cloud=output_file,
        source_pdal_filter="Classification==3",
    )
    assert get_nb_points(output_file) == 6196

    # check dimensions dtype
    las = laspy.read(output_file)
    assert las["target"].dtype == np.uint16
    assert las["target2"].dtype == np.uint8


@pytest.mark.filterwarnings("ignore")
def test_replace_area_with_no_output_point_base():
    output_file = os.path.join(TMP_PATH, "test_replace_area_no_point_at_all", "replaced.laz")
    os.makedirs(os.path.dirname(output_file))

    replace_area(
        target_cloud=TARGET_CLOUD,
        pipeline_source=pipeline_read_from_cloud(SOURCE_CLOUD),
        replacement_area=REPLACE_AREA,
        output_cloud=output_file,
        source_pdal_filter="Classification==3",
        target_pdal_filter="Classification==3",
    )
    assert get_nb_points(output_file) == 0


@pytest.mark.xfail(reason="when PDAL write empty LAS, extra dims are not written")
@pytest.mark.filterwarnings("ignore")
def test_replace_area_with_no_output_point_with_extra_dims():
    output_file = os.path.join(TMP_PATH, "test_replace_area_no_point_at_all_with_extra_dims", "replaced.laz")
    os.makedirs(os.path.dirname(output_file))

    replace_area(
        target_cloud=TARGET_EXTRA_DIM,
        pipeline_source=pipeline_read_from_cloud(SOURCE_CLOUD),
        replacement_area=REPLACE_AREA,
        output_cloud=output_file,
        source_pdal_filter="Classification==3",
        target_pdal_filter="Classification==3",
    )
    assert get_nb_points(output_file) == 0

    # check dimensions dtype
    las = laspy.read(output_file)
    assert las["target"].dtype == np.uint16
    assert las["target2"].dtype == np.uint8


def test_pipeline_read_from_DSM():
    cloud_from_DSM = os.path.join(TMP_PATH, "las_from_DSM.laz")

    pipeline = pipeline_read_from_DSM(dsm=SOURCE_DSM, ground_mask=SOURCE_GROUND_MASK, classification=SOURCE_CLASSIF)
    pipeline |= pdal.Writer.las(cloud_from_DSM, forward="all", extra_dims="all")
    pipeline.execute()

    # we have 27 col of points on 3 lines
    num_points = get_nb_points(cloud_from_DSM)
    assert num_points == 27 * 3

    # point are classed in class 68
    counts = compute_count_one_file(cloud_from_DSM, "Classification")
    assert counts == {str(SOURCE_CLASSIF): 27 * 3}

    # no_data have been filtered
    stats_Z = compute_count_one_file(cloud_from_DSM, "Z", type=float)
    assert stats_Z["-9999.0"] == 0


def test_main_from_cloud_base():
    output_file = os.path.join(TMP_PATH, "main_from_cloud", "output_main_from_cloud.laz")
    os.makedirs(os.path.dirname(output_file))
    cmd = f"from_cloud -s {SOURCE_CLOUD} -t {TARGET_CLOUD} -r {REPLACE_AREA} -o {output_file}".split()
    args = argument_parser().parse_args(cmd)
    args.func(args)

    # Check that we have the expected number of points in the output
    assert get_nb_points(output_file) == 6461


def test_main_from_cloud_with_filter():
    output_file = os.path.join(TMP_PATH, "main_from_cloud_with_filter", "output_main_from_cloud.laz")
    os.makedirs(os.path.dirname(output_file))
    cmd = (f"from_cloud -s {SOURCE_CLOUD} -t {TARGET_CLOUD} -r {REPLACE_AREA} -o {output_file} " "-f Z>=2550").split()

    args = argument_parser().parse_args(cmd)
    args.func(args)

    # Check that we have the expected number of points in the output
    assert get_nb_points(output_file) == 6390


def test_main_from_DSM():
    output_file = os.path.join(TMP_PATH, "main_from_DSM", "output_main_from_DSM.laz")
    os.makedirs(os.path.dirname(output_file))
    cmd = (
        f"from_DSM -d {SOURCE_DSM} -g {SOURCE_GROUND_MASK} -c {SOURCE_CLASSIF} -t {TARGET_CLOUD} -r {REPLACE_AREA}"
        f" -o {output_file}"
    ).split()
    args = argument_parser().parse_args(cmd)
    args.func(args)

    # same result as test_from_DMS
    counts = compute_count_one_file(output_file, "Classification")
    assert counts == {"1": 3841, "2": 2355, str(SOURCE_CLASSIF): 45}
