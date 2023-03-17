"""Count occurences of each value of a given attribute in a set of pointclouds.
Eg. to count points of each class in classified point clouds """

import argparse
from collections import Counter
import logging
import os
import pdal
from typing import List


def parse_args():
    parser = argparse.ArgumentParser("Count points with each value of an attribute.")
    parser.add_argument("--input_files",
                        nargs="+",
                        type=str,
                        help="Laz input files.")
    parser.add_argument("--attribute",
                        type=str,
                        default="Classification",
                        help="Attribute on which to count values")

    return parser.parse_args()


def compute_count_one_file(filepath: str, attribute: str="Classification") -> Counter:
    pipeline = pdal.Reader.las(filepath)
    pipeline |= pdal.Filter.stats(dimensions=attribute, count=attribute)
    pipeline.execute()
    # List of "class/count" on the only dimension that is counted
    raw_counts = pipeline.metadata["metadata"]["filters.stats"]["statistic"][0]["counts"]
    split_counts = [c.split("/") for c in raw_counts]
    try:
        counts = Counter({str(int(float(k))): int(v) for k, v in split_counts})
    except ValueError as e:
        counts = Counter({k: int(v) for k, v in split_counts})

    return counts


def compute_count(input_files: List[str], attribute: str="Classification"):
    all_counts = Counter()
    for f in input_files:
        logging.debug(f"Counting values of {attribute} for {os.path.basename(f)}")
        all_counts += compute_count_one_file(f, attribute)

    text = ["Number of point per class:"] + [f"Class {k} :: {v:,d}" for k, v in all_counts.items()]
    logging.info("\n".join(text))

    return all_counts


def main():
    args = parse_args()
    compute_count(args.input_files, args.attribute)


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    main()
