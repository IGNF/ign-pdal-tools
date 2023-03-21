from collections import Counter
import os
from pdaltools.replace_attribute_in_las import replace_values
from pdaltools.count_occurences_for_attribute import compute_count_one_file
import pytest
import shutil
from test.utils import get_pdal_infos_summary


test_path = os.path.dirname(os.path.abspath(__file__))
tmp_path = os.path.join(test_path, "tmp")
input_dir = os.path.join(test_path, "data/classified_laz")
input_file = os.path.join(input_dir, "test_data_0000_0000_LA93_IGN69.laz")
output_file = os.path.join(tmp_path, "replaced.las")
attribute = "Classification"
input_counts = Counter({
    '1': 2047,
    '2': 21172,
    '3': 226,
    '4': 1227,
    '5': 30392,
    '6': 29447,
    '64': 13,
})

expected_counts = Counter({
    '2': 21172,
    '3': 226,
    '4': 1227,
    '5': 30392,
    '64': 29447,
    '201': 2047 + 13
})

replacement_map_fail = {
    "201" : ["1", "64"],
    "6": ["64"],
}  # has duplicatevalue to replace

replacement_map_success = {
    "201" : ["1", "64"],
    "64": ["6"],
}


def setup_module(module):
    try:
        shutil.rmtree(tmp_path)

    except (FileNotFoundError):
        pass
    os.mkdir(tmp_path)


def test_replace_values():
    replace_values(input_file, output_file, replacement_map_success, attribute)
    count = compute_count_one_file(output_file, attribute)

    assert count == expected_counts
    check_dimensions(input_file, output_file)


def test_replace_values_duplicate_input():
    with pytest.raises(ValueError):
        replace_values(input_file, output_file, replacement_map_fail, attribute)


def check_dimensions(input_file, output_file):
    input_summary = get_pdal_infos_summary(input_file)
    input_dimensions = set(input_summary["summary"]["dimensions"])
    output_summary = get_pdal_infos_summary(output_file)
    output_dimensions = set(output_summary["summary"]["dimensions"])
    assert input_dimensions == output_dimensions

