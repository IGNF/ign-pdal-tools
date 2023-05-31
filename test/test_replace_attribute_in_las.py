from collections import Counter
import json
import os
from pdaltools.replace_attribute_in_las import replace_values, replace_values_clean, parse_replacement_map_from_path_or_json_string
from pdaltools.count_occurences.count_occurences_for_attribute import compute_count_one_file
from pdaltools.standardize_format import get_writer_parameters
import pytest
import shutil
from test.utils import get_pdal_infos_summary
from typing import Dict
from test.test_standardize_format import assert_lasinfo_no_warning

test_path = os.path.dirname(os.path.abspath(__file__))
tmp_path = os.path.join(test_path, "tmp")
input_dir = os.path.join(test_path, "data/classified_laz")
input_file = os.path.join(input_dir, "test_data_77050_627755_LA93_IGN69.laz")
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

# test replacement map parsing
input_parsing_correct = '{ "201" : ["1", "64"],  "64": ["6"]}'
input_parsing_incorrect = '"201" : ["1", "64"],  "64": ["6"]'
input_parsing_file = os.path.join(test_path, "data", "example_replacement_map.json")


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


def test_replace_values_clean():
    replace_values_clean(input_file, output_file, replacement_map_success, attribute, get_writer_parameters({}))
    assert_lasinfo_no_warning(output_file)


def test_replace_values_duplicate_input():
    with pytest.raises(ValueError):
        replace_values(input_file, output_file, replacement_map_fail, attribute)


def check_dimensions(input_file, output_file):
    input_summary = get_pdal_infos_summary(input_file)
    input_dimensions = set(input_summary["summary"]["dimensions"])
    output_summary = get_pdal_infos_summary(output_file)
    output_dimensions = set(output_summary["summary"]["dimensions"])
    assert input_dimensions == output_dimensions


def test_parse_replacement_map_from_path_or_json_string_path_ok():
    assert isinstance(parse_replacement_map_from_path_or_json_string(input_parsing_file), Dict)


def test_parse_replacement_map_from_path_or_json_string_json_ok():
    assert isinstance(parse_replacement_map_from_path_or_json_string(input_parsing_correct), Dict)


def test_parse_replacement_map_from_path_or_json_string_other_nok():
    with pytest.raises(json.decoder.JSONDecodeError):
        parse_replacement_map_from_path_or_json_string(input_parsing_incorrect)
