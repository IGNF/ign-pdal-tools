import logging
import os
import platform
import shutil
import subprocess as sp
from test.utils import EXPECTED_DIMS_BY_DATAFORMAT, get_pdal_infos_summary
import laspy
import pdal
import pytest
import tempfile
import sys

from pdaltools.count_occurences.count_occurences_for_attribute import (
    compute_count_one_file,
)
from pdaltools.standardize_format import exec_las2las, rewrite_with_pdal, standardize, main

TEST_PATH = os.path.dirname(os.path.abspath(__file__))
TMP_PATH = os.path.join(TEST_PATH, "tmp")
INPUT_DIR = os.path.join(TEST_PATH, "data")

DEFAULT_PARAMS = {"dataformat_id": 6, "a_srs": "EPSG:2154", "extra_dims": []}
DEFAULT_PARAMS_WITH_ALL_EXTRA_DIMS = {"dataformat_id": 6, "a_srs": "EPSG:2154", "extra_dims": "all"}

MUTLIPLE_PARAMS = [
    DEFAULT_PARAMS,
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


@pytest.mark.parametrize(
    "params",
    [
        DEFAULT_PARAMS,
        DEFAULT_PARAMS_WITH_ALL_EXTRA_DIMS,
        {"dataformat_id": 8, "a_srs": "EPSG:4326", "extra_dims": []},
        {"dataformat_id": 8, "a_srs": "EPSG:2154", "extra_dims": ["dtm_marker=double", "dsm_marker=double"]},
    ],
)
def test_rewrite_with_pdal_format(params):
    input_file = os.path.join(INPUT_DIR, "test_data_77055_627755_LA93_IGN69_extra_dims.laz")
    output_file = os.path.join(TMP_PATH, "formatted.laz")
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

    # Check that there is the expected number of points for each class
    expected_points_counts = compute_count_one_file(input_file)

    output_points_counts = compute_count_one_file(output_file)
    assert output_points_counts == expected_points_counts

    # TODO: Check srs
    # TODO: check precision

@pytest.mark.parametrize(
    "params, rename_dims",
    [
        (DEFAULT_PARAMS_WITH_ALL_EXTRA_DIMS, []),  # No renaming
        (DEFAULT_PARAMS, ["dtm_marker", "new_dtm_marker"]),  # Single dimension rename
        (DEFAULT_PARAMS_WITH_ALL_EXTRA_DIMS, ["dtm_marker", "new_dtm_marker"]),  # Single dimension rename
        (DEFAULT_PARAMS_WITH_ALL_EXTRA_DIMS, ["dtm_marker", "new_dtm_marker", "dsm_marker", "new_dsm_marker"]),  # Multiple dimensions rename
    ],
)
def test_rewrite_with_pdal_rename_dimensions(params, rename_dims):
    input_file = os.path.join(INPUT_DIR, "test_data_77055_627755_LA93_IGN69_extra_dims.laz")
    output_file = os.path.join(TMP_PATH, "formatted_with_rename.laz")
    
    # Check if we export all extra dims
    export_with_all_extra_dims = params["extra_dims"] == "all"

    # Get original dimensions
    with laspy.open(input_file) as las_file:
        las = las_file.read()
        original_dims = las.point_format.dimension_names
    
    # Standardize with dimension renaming
    rewrite_with_pdal(input_file, output_file, params, [], rename_dims)
    
    # Verify dimensions were renamed
    with laspy.open(output_file) as las_file:
        las = las_file.read()

        for i in range(0, len(rename_dims), 2):
            old_dim = rename_dims[i]
            new_dim = rename_dims[i + 1]
            if export_with_all_extra_dims:
                assert new_dim in las.point_format.dimension_names
                assert old_dim not in las.point_format.dimension_names
            else:
                assert new_dim not in las.point_format.dimension_names
                assert old_dim not in las.point_format.dimension_names

        new_dims = las.point_format.dimension_names

        # Make dimensions case-insensitive (ex : red => Red with pdal transform)
        new_dims_lowercase = [dim.casefold() for dim in new_dims]
        original_dims_lowercase = [dim.casefold() for dim in original_dims]

        # Check that other dimensions are preserved
        if export_with_all_extra_dims:
            for dim in original_dims_lowercase:
                old_dims_renammed = rename_dims[::2]
                # If dimension wasn't renamed and is not NIR (wich is 'infrared' in Some las files)
                if dim not in old_dims_renammed and dim != 'nir':  
                    assert dim in new_dims_lowercase, f"Original dimension {dim} was removed unexpectedly"


    # Verify points count is preserved
    original_count = compute_count_one_file(input_file)
    new_count = compute_count_one_file(output_file)
    assert original_count == new_count, "Points count changed unexpectedly"


@pytest.mark.parametrize(
    "classes_to_remove",
    [
        [],
        [2, 3],
        [1, 2, 3, 4, 5, 6, 64],  # remove all classes
    ],
)
def test_standardize_classes(classes_to_remove):
    input_file = os.path.join(INPUT_DIR, "test_data_77055_627755_LA93_IGN69_extra_dims.laz")
    output_file = os.path.join(TMP_PATH, "formatted.laz")
    rewrite_with_pdal(input_file, output_file, DEFAULT_PARAMS, classes_to_remove)
    # Check that there is the expected number of points for each class
    expected_points_counts = compute_count_one_file(input_file)
    for cl in classes_to_remove:
        expected_points_counts.pop(str(cl))

    output_points_counts = compute_count_one_file(output_file)
    assert output_points_counts == expected_points_counts


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

def test_standardize_with_all_options():
    """
    Test standardize with all option
    """
    input_file = os.path.join(INPUT_DIR, "test_data_77055_627755_LA93_IGN69_extra_dims.laz")
    output_file = os.path.join(TMP_PATH, "test_standardize_with_all_extra_dims.laz")
    
    rename_dims = ["dtm_marker", "new_dtm_marker", "dsm_marker", "new_dsm_marker"]
    remove_classes = ["64"]

    # Standardize with all extra dimensions
    params = DEFAULT_PARAMS_WITH_ALL_EXTRA_DIMS
    standardize(input_file, output_file, params, remove_classes, rename_dims)
    
    # Check that there is the expected number of points for each class
    expected_points_counts = compute_count_one_file(input_file)
    for cl in remove_classes:
        expected_points_counts.pop(str(cl))
    output_points_counts = compute_count_one_file(output_file)
    assert output_points_counts == expected_points_counts

    # Get original dimensions
    with laspy.open(input_file) as las_file:
        original_las = las_file.read()
        original_dims = original_las.point_format.dimension_names

    # Verify all extra dimensions are preserved and renamed if needed
    with laspy.open(output_file) as las_file:
        las = las_file.read()
        new_dims = las.point_format.dimension_names
        
        # Make dimensions case-insensitive (ex : red => Red with pdal transform)
        new_dims_lowercase = [dim.casefold() for dim in new_dims]
        original_dims_lowercase = [dim.casefold() for dim in original_dims]
        
        # Verify all original dimensions are present
        for dim in original_dims_lowercase:
            old_dims_renammed = rename_dims[::2]
            # If dimension wasn't renamed and is not NIR (wich is 'infrared' in Some las files)
            if dim not in old_dims_renammed and dim != 'nir':
                assert dim in new_dims_lowercase, f"Original dimension {dim} was removed unexpectedly"
                    

def test_standardize_does_NOT_produce_any_warning_with_Lasinfo():
    # bad file on the store (44 Mo)
    # input_file = (
    #     "/var/data/store-lidarhd/developpement/standaLAS/demo_standardization/Semis_2022_0584_6880_LA93_IGN69.laz"
    # )

    input_file = os.path.join(TEST_PATH, "data/classified_laz/test_data_77050_627755_LA93_IGN69.laz")
    output_file = os.path.join(TMP_PATH, "test_standardize_produce_no_warning_with_lasinfo.las")

    # if you want to see input_file warnings
    # assert_lasinfo_no_warning(input_file)

    standardize(input_file, output_file, DEFAULT_PARAMS, [], [])
    assert_lasinfo_no_warning(output_file)


def test_standardize_malformed_laz():
    input_file = os.path.join(TEST_PATH, "data/test_pdalfail_0643_6319_LA93_IGN69.laz")
    output_file = os.path.join(TMP_PATH, "standardize_pdalfail_0643_6319_LA93_IGN69.laz")
    standardize(input_file, output_file, DEFAULT_PARAMS, [], [])
    assert os.path.isfile(output_file)


def test_main_with_rename_dimensions():
    """
    Test the main function with dimension renaming
    """
    input_file = os.path.join(INPUT_DIR, "test_data_77055_627755_LA93_IGN69_extra_dims.laz")
    output_file = os.path.join(TMP_PATH, "test_main_with_rename.laz")
    
    # Save original sys.argv
    original_argv = sys.argv
    
    try:
        # Set up mock command-line arguments
        sys.argv = [
            "standardize_format",
            "--input_file", input_file,
            "--output_file", output_file,
            "--record_format", "6",
            "--projection", "EPSG:2154",
            "--extra_dims", "all",
            "--rename_dims", "dtm_marker", "new_dtm_marker", "dsm_marker", "new_dsm_marker"
        ]
        
        # Run main function
        main()
        
        # Verify output file exists
        assert os.path.isfile(output_file)
        
        # Verify dimensions were renamed
        with laspy.open(output_file) as las_file:
            las = las_file.read()
            assert "new_dsm_marker" in las.point_format.dimension_names
            assert "new_dtm_marker" in las.point_format.dimension_names
            assert "dtm_marker" not in las.point_format.dimension_names
            assert "dsm_marker" not in las.point_format.dimension_names
            
    finally:
        # Restore original sys.argv
        sys.argv = original_argv


def test_main_with_class_points_removed():
    """
    Test the main function with class points removed
    """
    input_file = os.path.join(INPUT_DIR, "test_data_77055_627755_LA93_IGN69_extra_dims.laz")
    output_file = os.path.join(TMP_PATH, "test_main_with_class_remove.laz")
    
    # Save original sys.argv
    original_argv = sys.argv
    
    try:
        # Set up mock command-line arguments
        sys.argv = [
            "standardize_format",
            "--input_file", input_file,
            "--output_file", output_file,
            "--record_format", "6",
            "--projection", "EPSG:2154",
            "--class_points_removed", "64"
        ]
        
        # Run main function
        main()
        
        # Verify output file exists
        assert os.path.isfile(output_file)
        
        # Verify points count is reduced
        original_count = compute_count_one_file(input_file)
        new_count = compute_count_one_file(output_file)
        assert new_count < original_count, "Points count should be reduced after removing class 64"
        
    finally:
        # Restore original sys.argv
        sys.argv = original_argv


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    test_standardize_format()
