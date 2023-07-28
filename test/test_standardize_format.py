import os
import pytest
import shutil
from pdaltools.standardize_format import rewrite_with_pdal, standardize, exec_las2las
import logging
from test.utils import get_pdal_infos_summary
import pdal
import subprocess as sp

# Note: tile 77050_627760 is cropped to simulate missing data in neighbors during merge
test_path = os.path.dirname(os.path.abspath(__file__))
tmp_path = os.path.join(test_path, "tmp")
input_dir = os.path.join(test_path, "data")

coord_x = 77055
coord_y = 627760
input_file = os.path.join(input_dir, f"test_data_{coord_x}_{coord_y}_LA93_IGN69_ground.las")
output_file = os.path.join(tmp_path, "formatted.laz")
multiple_params = [
    {"dataformat_id": 6, "a_srs": "EPSG:2154"},
    {"dataformat_id": 8, "a_srs": "EPSG:4326"},
]

expected_dims = {
    6: set(["X", "Y", "Z", "Intensity", "ReturnNumber", "NumberOfReturns", "ClassFlags",
           "ScanChannel", "ScanDirectionFlag", "EdgeOfFlightLine", "Classification",
           "UserData", "ScanAngleRank", "PointSourceId", "GpsTime"]),
    8: set(["X", "Y", "Z", "Intensity", "ReturnNumber", "NumberOfReturns", "ClassFlags",
           "ScanChannel", "ScanDirectionFlag", "EdgeOfFlightLine", "Classification",
           "UserData", "ScanAngleRank", "PointSourceId", "GpsTime",
           "Red", "Green", "Blue", "Infrared"]),
}


def setup_module(module):
    try:
        shutil.rmtree(tmp_path)

    except (FileNotFoundError):
        pass
    os.mkdir(tmp_path)


def _test_standardize_format_one_params_set(params):
    rewrite_with_pdal(
        input_file, output_file, params)
    # check file exists
    assert os.path.isfile(output_file)
    # check values from metadata
    json_info = get_pdal_infos_summary(output_file)
    if pdal.info.version < "2.5":
        raise NotImplementedError("This test is not implemented for pdal < 2.5")
    elif pdal.info.version <= "2.5.2":
        metadata = json_info["summary"]["metadata"][1]
    else :
        metadata = json_info["summary"]["metadata"]
    assert metadata["compressed"] == True
    assert metadata["minor_version"] == 4
    assert metadata["global_encoding"] == 17
    assert metadata["dataformat_id"] == params["dataformat_id"]
    # Check that there is no extra dim
    dimensions = set([d.strip() for d in json_info["summary"]["dimensions"].split(",")])
    assert dimensions == expected_dims[params["dataformat_id"]]

    # TODO: Check srs
    # TODO: check precision


def test_standardize_format():
    for params in multiple_params:
        _test_standardize_format_one_params_set(params)


def exec_lasinfo(input_file: str):
    r = sp.run(["lasinfo", "-stdout", input_file], stderr=sp.PIPE, stdout=sp.PIPE)
    if r.returncode == 1:
        msg = r.stderr.decode()
        print(msg)
        raise RuntimeError(msg)

    output = r.stdout.decode()
    return output


def assert_lasinfo_no_warning(input_file: str):
    errors = [ line for line in exec_lasinfo(input_file).splitlines() if 'WARNING' in line]

    for line in errors:
        print(line)

    assert errors == [], errors


def test_exec_las2las_error():
    with pytest.raises(RuntimeError):
        exec_las2las("not_existing_input_file", "output_file")


def test_standardize_does_NOT_produce_any_warning_with_Lasinfo():
    # bad file on the store (44 Mo)
    # input_file = "/var/data/store-lidarhd/developpement/standaLAS/demo_standardization/Semis_2022_0584_6880_LA93_IGN69.laz"

    input_file = os.path.join(test_path, "data/classified_laz/test_data_77050_627755_LA93_IGN69.laz")
    output_file = os.path.join(tmp_path, "test_standardize_produce_no_warning_with_lasinfo.las")

    # if you want to see input_file warnings
    # assert_lasinfo_no_warning(input_file)

    standardize(input_file, output_file, multiple_params[0])
    assert_lasinfo_no_warning(output_file)


def test_standardize_malformed_laz():
    input_file = os.path.join(test_path, 'data/test_pdalfail_0643_6319_LA93_IGN69.laz')
    output_file = os.path.join(tmp_path, 'standardize_pdalfail_0643_6319_LA93_IGN69.laz')
    standardize(input_file, output_file, multiple_params[0])
    assert os.path.isfile(output_file)


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    test_standardize_format()