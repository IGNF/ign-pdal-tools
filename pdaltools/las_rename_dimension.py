"""
Rename dimensions in a LAS file using PDAL's Python API.

This script allows renaming dimensions in a LAS file while preserving all other data.
"""

import argparse
import pdal
import sys
from pathlib import Path
from pdaltools.las_remove_dimensions import remove_dimensions_from_points


def rename_dimension(input_file: str, output_file: str, old_dims: list[str], new_dims: list[str]):
    """
    Rename one or multiple dimensions in a LAS file using PDAL.

    Args:
        input_file: Path to the input LAS file
        output_file: Path to save the output LAS file
        old_dims: List of names of dimensions to rename
        new_dims: List of new names for the dimensions
    """

    # Validate dimensions
    if len(old_dims) != len(new_dims):
        raise ValueError("Number of old dimensions must match number of new dimensions")

    mandatory_dimensions = ["X", "Y", "Z", "x", "y", "z"]
    for dim in new_dims:
        if dim in mandatory_dimensions:
            raise ValueError(f"New dimension {dim} cannot be a mandatory dimension (X,Y,Z,x,y,z)")

    pipeline = pdal.Pipeline() | pdal.Reader.las(input_file)
    for old, new in zip(old_dims, new_dims):
        pipeline |= pdal.Filter.ferry(dimensions=f"{old} => {new}")
    pipeline |= pdal.Writer.las(output_file)
    pipeline.execute()
    points = pipeline.arrays[0]

    # Remove old dimensions
    remove_dimensions_from_points(points, pipeline.metadata, old_dims, output_file)


def main():
    parser = argparse.ArgumentParser(description="Rename dimensions in a LAS file")
    parser.add_argument("input_file", help="Input LAS file")
    parser.add_argument("output_file", help="Output LAS file")
    parser.add_argument(
        "--old-dims",
        nargs="+",
        required=True,
        help="Names of dimensions to rename (can specify multiple)",
    )
    parser.add_argument(
        "--new-dims",
        nargs="+",
        required=True,
        help="New names for the dimensions (must match --old-dims count)",
    )

    args = parser.parse_args()

    # Validate input file
    input_path = Path(args.input_file)
    if not input_path.exists():
        print(f"Error: Input file {args.input_file} does not exist", file=sys.stderr)
        sys.exit(1)

    # Validate output file
    output_path = Path(args.output_file)
    if output_path.exists():
        print(f"Warning: Output file {args.output_file} already exists. It will be overwritten.")

    rename_dimension(args.input_file, args.output_file, args.old_dims, args.new_dims)


if __name__ == "__main__":
    main()
