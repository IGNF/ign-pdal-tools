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
import tempfile
from typing import Dict, List

import pdal

from pdaltools.unlock_file import copy_and_hack_decorator
from pdaltools.las_rename_dimension import rename_dimension

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
    input_file: str, output_file: str, params_from_parser: Dict, classes_to_remove: List = [], rename_dims: List = []
) -> None:
    params = get_writer_parameters(params_from_parser)

    # Create temporary file for dimension renaming if needed
    if rename_dims:
        with tempfile.NamedTemporaryFile(suffix=".laz", delete=False) as tmp_file:
            tmp_file_name = tmp_file.name

            # Rename dimensions
            old_dims = rename_dims[::2]
            new_dims = rename_dims[1::2]
            rename_dimension(input_file, tmp_file_name, old_dims, new_dims)

            # Use renamed file as input
            input_file = tmp_file_name
    else:
        tmp_file_name = input_file

    pipeline = pdal.Pipeline()
    pipeline |= pdal.Reader.las(tmp_file_name)
    if classes_to_remove:
        expression = "&&".join([f"Classification != {c}" for c in classes_to_remove])
        pipeline |= pdal.Filter.expression(expression=expression)
    pipeline |= pdal.Writer(filename=output_file, forward="all", **params)
    pipeline.execute()


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
