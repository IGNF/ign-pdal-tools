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
import pdal
from typing import Dict


STANDARD_PARAMETERS = dict(
    minor_version="4",  # Laz format version (pdal always write in 1.x format)
    global_encoding=17,  # store WKT projection in file
    compression="true",  # Save to compressed laz format
    extra_dims= [],  # Save no extra_dims
    scale_x=0.01, # Precision of the stored data
    scale_y=0.01,
    scale_z=0.01,
    offset_x='auto',  # To be confirmed
    offset_y='auto',  # To be confirmed
    offset_z='auto',  # To be confirmed
)

def parse_args():
    parser = argparse.ArgumentParser("Rewrite laz file with standard format.")
    parser.add_argument("--input_file",
                        type=str,
                        help="Laz input file.")
    parser.add_argument("--output_file",
                        type=str,
                        help="Laz output file")
    parser.add_argument("--record_format",
                        choices=[6, 8],
                        type=int,
                        help="Record format: 6 (no color) or 8 (4 color channels)")
    parser.add_argument("--projection",
                        default="EPSG:2154",
                        type=str,
                        help="Projection, eg. EPSG:2154")

    return parser.parse_args()


def rewrite_with_pdal(input_file: str, output_file: str, params_from_parser: Dict) -> None:
    params = STANDARD_PARAMETERS | params_from_parser
    print("params::", params)
    pipeline = pdal.Reader.las(input_file)
    pipeline |= pdal.Writer(filename=output_file, **params)
    pipeline.execute()


if __name__ == "__main__":
    args = parse_args()
    params_from_parser = dict(
        dataformat_id=args.record_format,
        a_srs=args.projection)
    rewrite_with_pdal(args.input_file, args.output_dile, params_from_parser)

