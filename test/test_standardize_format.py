import logging
import os
import shutil
import subprocess as sp
import platform
import json
from test.utils import EXPECTED_DIMS_BY_DATAFORMAT, get_pdal_infos_summary

import pdal
import pytest

from pdaltools.standardize_format import exec_las2las, rewrite_with_pdal, standardize, remove_points_from_class

TEST_PATH = os.path.dirname(os.path.abspath(__file__))
TMP_PATH = os.path.join(TEST_PATH, "tmp")
INPUT_DIR = os.path.join(TEST_PATH, "data")

MUTLIPLE_PARAMS = [
    {"dataformat_id": 6, "a_srs": "EPSG:2154", "extra_dims": []},
    {"dataformat_id": 8, "a_srs": "EPSG:4326", "extra_dims": []},
    {"dataformat_id": 8, "a_srs": "EPSG:2154", "extra_dims": ["dtm_marker=double", "dsm_marker=double"]},
    {"dataformat_id": 8, "a_srs": "EPSG:2154", "extra_dims": "all"},
]


def setup_module(module):
    try:
        shutil.rmtree(TMP_PATH)

    except FileNotFoundError:
        pass
    os.mkdir(TMP_PATH)


def _test_standardize_format_one_params_set(input_file, output_file, params):
    rewrite_with_pdal(input_file, output_file, params, [])
    # check file exists
    assert os.path.isfile(output_file)
    # check values from metadata
    json_info = get_pdal_infos_summary(output_file)
    if pdal.info.version < "2.5":
        raise NotImplementedError("This test is not implemented for pdal < 2.5")
    elif pdal.info.version <= "2.5.2":
        metadata = json_info["summary"]["metadata"][1]
    else:
        metadata = json_info["summary"]["metadata"]
    assert metadata["compressed"] is True
    assert metadata["minor_version"] == 4
    assert metadata["global_encoding"] == 17
    assert metadata["dataformat_id"] == params["dataformat_id"]
    # Check that there is no extra dim
    dimensions = set([d.strip() for d in json_info["summary"]["dimensions"].split(",")])
    if params["extra_dims"] == "all":
        assert EXPECTED_DIMS_BY_DATAFORMAT[params["dataformat_id"]].issubset(dimensions)
    else:
        extra_dims_names = [dim.split("=")[0] for dim in params["extra_dims"]]
        assert dimensions == EXPECTED_DIMS_BY_DATAFORMAT[params["dataformat_id"]].union(extra_dims_names)

    # TODO: Check srs
    # TODO: check precision


def test_standardize_format():
    input_file = os.path.join(INPUT_DIR, "test_data_77055_627755_LA93_IGN69_extra_dims.laz")
    output_file = os.path.join(TMP_PATH, "formatted.laz")
    for params in MUTLIPLE_PARAMS:
        _test_standardize_format_one_params_set(input_file, output_file, params)


def exec_lasinfo(input_file: str):
    if platform.processor() == "arm" and platform.architecture()[0] == "64bit":
        lasinfo = "lasinfo64"
    else:
        lasinfo = "lasinfo"
    r = sp.run([lasinfo, "-stdout", input_file], stderr=sp.PIPE, stdout=sp.PIPE)
    if r.returncode == 1:
        msg = r.stderr.decode()
        print(msg)
        raise RuntimeError(msg)

    output = r.stdout.decode()
    return output


def assert_lasinfo_no_warning(input_file: str):
    errors = [line for line in exec_lasinfo(input_file).splitlines() if "WARNING" in line]

    for line in errors:
        print(line)

    assert errors == [], errors


def test_exec_las2las_error():
    with pytest.raises(RuntimeError):
        exec_las2las("not_existing_input_file", "output_file")


def test_standardize_does_NOT_produce_any_warning_with_Lasinfo():
    # bad file on the store (44 Mo)
    # input_file = (
    #     "/var/data/store-lidarhd/developpement/standaLAS/demo_standardization/Semis_2022_0584_6880_LA93_IGN69.laz"
    # )

    input_file = os.path.join(TEST_PATH, "data/classified_laz/test_data_77050_627755_LA93_IGN69.laz")
    output_file = os.path.join(TMP_PATH, "test_standardize_produce_no_warning_with_lasinfo.las")

    # if you want to see input_file warnings
    # assert_lasinfo_no_warning(input_file)

    standardize(input_file, output_file, MUTLIPLE_PARAMS[0], [])
    assert_lasinfo_no_warning(output_file)


def test_standardize_malformed_laz():
    input_file = os.path.join(TEST_PATH, "data/test_pdalfail_0643_6319_LA93_IGN69.laz")
    output_file = os.path.join(TMP_PATH, "standardize_pdalfail_0643_6319_LA93_IGN69.laz")
    standardize(input_file, output_file, MUTLIPLE_PARAMS[0], [])
    assert os.path.isfile(output_file)


def get_pipeline_metadata_cross_plateform(pipeline):
    try:
        metadata = json.loads(pipeline.metadata)
    except TypeError:
        d_metadata = json.dumps(pipeline.metadata)
        metadata = json.loads(d_metadata)
    return metadata

def get_statistics_from_las_points(points):
    pipeline = pdal.Pipeline(arrays=[points])
    pipeline |= pdal.Filter.stats(dimensions="Classification", enumerate="Classification")
    pipeline.execute()
    metadata = get_pipeline_metadata_cross_plateform(pipeline)
    statistic = metadata["metadata"]["filters.stats"]["statistic"]
    return statistic[0]["count"], statistic[0]["values"]

@pytest.mark.parametrize(
    "classes_to_remove",
    [
        [2, 3],
        [2, 3, 4],
        [0, 1, 2, 3, 4, 5, 6],
    ],
)
def test_remove_points_from_class(classes_to_remove):
    input_file = os.path.join(TEST_PATH, "data/classified_laz/test_data_77050_627755_LA93_IGN69.laz")
    output_file = os.path.join(TMP_PATH, "test_remove_points_from_class.laz")

    # count points of class not in classes_to_remove (get the point we should have in fine)
    pipeline = pdal.Pipeline() | pdal.Reader.las(input_file)

    where = ' && '.join(["CLassification != " + str(cl) for cl in classes_to_remove])
    pipeline |= pdal.Filter.stats(dimensions="Classification", enumerate="Classification", where=where)
    pipeline.execute()

    points = pipeline.arrays[0]
    nb_points_before, class_before = get_statistics_from_las_points(points)

    metadata = get_pipeline_metadata_cross_plateform(pipeline)
    statistic = metadata["metadata"]["filters.stats"]["statistic"]
    nb_points_to_get = statistic[0]["count"]

    try:
        points = remove_points_from_class(points, classes_to_remove)
    except Exception as error:  # error because all points are removed
        assert nb_points_to_get == 0
        return

    nb_points_after, class_after = get_statistics_from_las_points(points)

    assert nb_points_before > 0
    assert nb_points_before > nb_points_after
    assert set(classes_to_remove).issubset(set(class_before))
    assert not set(classes_to_remove).issubset(set(class_after))
    assert nb_points_after == nb_points_to_get


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    test_standardize_format()
