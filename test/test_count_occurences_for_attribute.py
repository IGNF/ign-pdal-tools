from collections import Counter
import logging
import os
from pdaltools.count_occurences_for_attribute import compute_count
import pytest


test_path = os.path.dirname(os.path.abspath(__file__))
tmp_path = os.path.join(test_path, "tmp")
input_dir = os.path.join(test_path, "data/classified_laz")
input_files = [os.path.join(input_dir, f) for f in os.listdir(input_dir) if f.endswith(("las", "laz"))]

attribute = "Classification"
expected_counts = Counter({
    '1': 6830,
    '2': 54740,
    '3': 605,
    '4': 2160,
    '5': 42546,
    '6': 33595,
    '64': 83,
})


def test_count_by_attribute_values():
    count = compute_count(input_files, attribute)
    assert count == expected_counts


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    test_count_by_attribute_values()