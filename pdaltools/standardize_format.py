"""Re-write las file with expected format:
- laz version
- [TODO] nomenclature ???
- record format
- global encoding
- projection
- precision
- no extra-dims
"""

import argparse
import os
import tempfile
from typing import Dict, List

import pdal

from pdaltools.las_rename_dimension import rename_dimension
from pdaltools.unlock_file import copy_and_hack_decorator

# Standard parameters to pass to the pdal writer
STANDARD_PARAMETERS = dict(
    major_version="1",
    minor_version="4",  # Laz format version (pdal always write in 1.x format)
    global_encoding=17,  # store WKT projection in file
    compression="true",  # Save to compressed laz format
    extra_dims=[],  # Save no extra_dims
    scale_x=0.01,  # Precision of the stored data
    scale_y=0.01,
    scale_z=0.01,
    offset_x=0,  # No offset
    offset_y=0,
    offset_z=0,
    dataformat_id=6,  # No color by default
    a_srs="EPSG:2154",
)


def parse_args():
    parser = argparse.ArgumentParser("Rewrite laz file with standard format.")
    parser.add_argument("--input_file", type=str, help="Laz input file.")
    parser.add_argument("--output_file", type=str, help="Laz output file")
    parser.add_argument(
        "--record_format", choices=[6, 8], type=int, help="Record format: 6 (no color) or 8 (4 color channels)"
    )
    parser.add_argument("--projection", default="EPSG:2154", type=str, help="Projection, eg. EPSG:2154")
    parser.add_argument(
        "--class_points_removed",
        default=[],
        nargs="*",
        type=str,
        help="List of classes number. Points of this classes will be removed from the file",
    )
    parser.add_argument(
        "--extra_dims",
        default=[],
        nargs="*",
        type=str,
        help="List of extra dims to keep in the output (default=[], use 'all' to keep all extra dims), "
        "extra_dims must be specified with their type (see pdal.writers.las documentation, eg 'dim1=double')",
    )
    parser.add_argument(
        "--rename_dims",
        default=[],
        nargs="*",
        type=str,
        help="Rename dimensions in pairs: --rename_dims old_name1 new_name1 old_name2 new_name2 ...",
    )
    return parser.parse_args()


def get_writer_parameters(new_parameters: Dict) -> Dict:
    """
    Get writer parameters from a set of standard parameters + a new set of parameters that can
    override the standard ones
    """
    params = STANDARD_PARAMETERS | new_parameters
    return params


@copy_and_hack_decorator
def standardize(
    input_file: str, 
    output_file: str, 
    params_from_parser: Dict, 
    classes_to_remove: List = [], 
    rename_dims: List = []
) -> None:
    """
    Standardize a LAS/LAZ file with improved error handling and resource management.
    
    Args:
        input_file: Input file path
        output_file: Output file path
        params_from_parser: Parameters for the PDAL writer
        classes_to_remove: List of classification classes to remove
        rename_dims: List of dimension names to rename (pairs of old_name, new_name)
    """
    params = get_writer_parameters(params_from_parser)
    tmp_file_name = None

    try:
        # Create temporary file for dimension renaming if needed
        if rename_dims:
            with tempfile.NamedTemporaryFile(suffix=".laz", delete=False) as tmp_file:
                tmp_file_name = tmp_file.name
                old_dims = rename_dims[::2]
                new_dims = rename_dims[1::2]
                rename_dimension(input_file, tmp_file_name, old_dims, new_dims)
                input_file = tmp_file_name

        pipeline = pdal.Pipeline()
        pipeline |= pdal.Reader.las(input_file)
        if classes_to_remove:
            expression = "&&".join([f"Classification != {c}" for c in classes_to_remove])
            pipeline |= pdal.Filter.expression(expression=expression)
        pipeline |= pdal.Writer(filename=output_file, forward="all", **params)
        pipeline.execute()

    finally:
        # Clean up temporary file
        if tmp_file_name and os.path.exists(tmp_file_name):
            os.remove(tmp_file_name)


def main():
    args = parse_args()
    params_from_parser = dict(
        dataformat_id=args.record_format,
        a_srs=args.projection,
        extra_dims=args.extra_dims,
    )
    standardize(args.input_file, args.output_file, params_from_parser, args.class_points_removed, args.rename_dims)


if __name__ == "__main__":
    main()
