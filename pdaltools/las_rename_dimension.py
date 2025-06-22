"""
Rename dimensions in a LAS file using PDAL's Python API.

This script allows renaming dimensions in a LAS file while preserving all other data.
"""

import argparse
import pdal
import sys
from pathlib import Path
from pdaltools.las_remove_dimensions import remove_dimensions_from_points
from pdaltools.las_info import las_info_metadata


def list_available_dimensions(input_file: str):
    """
    List all available dimensions in a LAS file.

    Args:
        input_file: Path to the input LAS file
        
    Returns:
        List of dimension names available in the LAS file
    """
    metadata = las_info_metadata(input_file)
    dimensions = metadata['dimensions']
    return dimensions



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

    available_dims = list_available_dimensions(input_file)    

    # Reset pipeline for actual processing
    pipeline = pdal.Pipeline() | pdal.Reader.las(input_file)
    for old, new in zip(old_dims, new_dims):
        # Validate that old dimensions exist in the file, otherwise we don't do the renaming
        if old not in available_dims:
            print(f"Dimension '{old}' not found in input file. Available dimensions: {', '.join(available_dims)}")
            continue
        pipeline |= pdal.Filter.ferry(dimensions=f"{old} => {new}")
    pipeline |= pdal.Writer.las(output_file)
    pipeline.execute()
    points = pipeline.arrays[0]

    # Remove old dimensions
    remove_dimensions_from_points(points, pipeline.metadata, old_dims, output_file)


def main():
    parser = argparse.ArgumentParser(description="Rename dimensions in a LAS file")
    parser.add_argument("input_file", help="Input LAS file")
    parser.add_argument("output_file", nargs='?', help="Output LAS file (required for renaming)")
    parser.add_argument(
        "--old-dims",
        nargs="+",
        help="Names of dimensions to rename (can specify multiple)",
    )
    parser.add_argument(
        "--new-dims",
        nargs="+",
        help="New names for the dimensions (must match --old-dims count)",
    )


    args = parser.parse_args()

    # Validate input file
    input_path = Path(args.input_file)
    if not input_path.exists():
        print(f"Error: Input file {args.input_file} does not exist", file=sys.stderr)
        sys.exit(1)

    # For renaming, validate required arguments
    if not args.output_file:
        print("Error: Output file is required for renaming", file=sys.stderr)
        sys.exit(1)
    
    if not args.old_dims or not args.new_dims:
        print("Error: --old-dims and --new-dims are required for renaming", file=sys.stderr)
        sys.exit(1)

    # Validate output file
    output_path = Path(args.output_file)
    if output_path.exists():
        print(f"Warning: Output file {args.output_file} already exists. It will be overwritten.")

    rename_dimension(args.input_file, args.output_file, args.old_dims, args.new_dims)


if __name__ == "__main__":
    main()
