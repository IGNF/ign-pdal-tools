"""Replace values of a gien attribute in a las/laz file"""

import argparse
from collections import Counter
import json
import logging
import os
import pdal
from typing import List, Dict


def parse_args():
    parser = argparse.ArgumentParser("Count points with each value of an attribute.")
    parser.add_argument("--input_file",
                        type=str,
                        help="Laz input file")
    parser.add_argument("--output_file",
                        type=str,
                        help="Laz output file.")
    parser.add_argument("--attribute",
                        type=str,
                        default="Classification",
                        help="Attribute on which to count values")
    parser.add_argument("--replacement_map_path",
                        type=str,
                        help="Path to a json file that contains the values that we want to " +
                        "replace. It should contain a dict like " +
                        "{new_value1: [value_to_replace1, value_to_replace2], " +
                        "new_value2: [value_to_replace3, ...]}")


    return parser.parse_args()


def check_duplicate_values(d: Dict) -> None:
    """Check that a dict that contains lists of values, eg d = {k1: [value1, value2], k2: [value3]}
    has no duplicate values
    """
    all_values = [elt for value in d.values() for elt in value]
    occurences = Counter(all_values)
    for val, count in occurences.items():
        if count > 1:
            raise ValueError(f"Duplicate value {val} provided more than once (count={count})")


def dict_to_pdal_assign_list(d: Dict,
                             output_attribute: str="Classification",
                             input_attribute: str="tmp") -> List:
    """Create an assignment list (to be passed to pdal) from a dictionary of type
    d = {
        output_val1: [input_val1, input_val2],
        output_val2: [input_val3],
    }
    that maps values of input_attribute to the values to assign to output_attribute
    """
    check_duplicate_values(d)
    assignment_list = []
    for output_val, input_values in d.items():
        for input_val in input_values:
            assignment_list.append(
                f"{output_attribute} = {output_val} WHERE {input_attribute} == {input_val}"
            )

    return assignment_list


def replace_values(input_file: str,
                   output_file: str,
                   replacement_map: Dict,
                   attribute: str="Classification") -> None:
    temp_attribute = "tmp"
    assignment_list = dict_to_pdal_assign_list(replacement_map, attribute, temp_attribute)
    pipeline = pdal.Reader.las(input_file)
    pipeline |= pdal.Filter.ferry(dimensions=f"{attribute} => {temp_attribute}")
    pipeline |= pdal.Filter.assign(value=assignment_list)
    # the temp_attribute dimension should not be written as the writer has no "extra_dims" parameter
    pipeline |= pdal.Writer(filename=output_file)

    pipeline.execute()


def main():
    args = parse_args()
    with open(args.replacement_map_path, 'r') as f:
        replacement_map = json.load(f)

    replace_values(args.input_file, args.output_file, replacement_map, args.attribute)


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    main()
