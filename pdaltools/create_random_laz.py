import numpy as np
import laspy
from pathlib import Path
import argparse
from pyproj import CRS
from typing import List, Tuple


def create_random_laz(
    output_file: str,
    point_format: int = 3,
    num_points: int = 100,
    crs: int = 2154,
    center: Tuple[float, float] = (650000, 6810000),
    extra_dims: List[Tuple[str, str]] = [],
):
    """
    Create a test LAZ file with EPSG code and additional dimensions.

    Args:
        output_file: Path to save the LAZ file
        point_format: Point format of the LAZ file (default: 3)
        num_points: Number of points to generate
        crs: EPSG code of the CRS (default: 2154)
        center: Tuple of floats (x, y) of the center of the area to generate points in
                (default: (650000, 6810000) ; around Paris)
        extra_dims: List of tuples (dimension_name, dimension_type) where type can be:
                   'float32', 'float64', 'int8', 'int16', 'int32', 'int64', 'uint8', 'uint16', 'uint32', 'uint64'
    """

    # Create a new point cloud
    header = laspy.LasHeader(point_format=point_format, version="1.4")

    # Map string types to numpy types
    type_mapping = {
        "float32": np.float32,
        "float64": np.float64,
        "int8": np.int8,
        "int16": np.int16,
        "int32": np.int32,
        "int64": np.int64,
        "uint8": np.uint8,
        "uint16": np.uint16,
        "uint32": np.uint32,
        "uint64": np.uint64,
    }

    for dim_name, dim_type in extra_dims:
        if dim_type not in type_mapping:
            raise ValueError(f"Unsupported dimension type: {dim_type}. Supported types: {list(type_mapping.keys())}")

        numpy_type = type_mapping[dim_type]
        header.add_extra_dim(laspy.ExtraBytesParams(name=dim_name, type=numpy_type))

        # Create point cloud
    las = laspy.LasData(header)
    las.header.add_crs(CRS.from_string(f"epsg:{crs}"))

    # Generate random points in a small area
    las.x = np.random.uniform(center[0] - 1000, center[0] + 1000, num_points)
    las.y = np.random.uniform(center[1] - 1000, center[1] + 1000, num_points)
    las.z = np.random.uniform(0, 200, num_points)

    # Generate random intensity values
    las.intensity = np.random.randint(0, 255, num_points)

    # Generate random classification values
    # 66 is the max value for classification of IGN LidarHD
    # cf. https://geoservices.ign.fr/sites/default/files/2022-05/DT_LiDAR_HD_1-0.pdf
    if point_format > 3:
        num_classifications = 66
    else:
        num_classifications = 10
    las.classification = np.random.randint(0, num_classifications, num_points)

    # Generate random values for each extra dimension
    for dim_name, dim_type in extra_dims:
        numpy_type = type_mapping[dim_type]

        # Generate appropriate random values based on the type
        if numpy_type in [np.float32, np.float64]:
            las[dim_name] = np.random.uniform(0, 10, num_points).astype(numpy_type)
        elif numpy_type in [np.int8, np.int16, np.int32, np.int64]:
            las[dim_name] = np.random.randint(-100, 100, num_points).astype(numpy_type)
        elif numpy_type in [np.uint8, np.uint16, np.uint32, np.uint64]:
            las[dim_name] = np.random.randint(0, 100, num_points).astype(numpy_type)

    # Write to file
    las.write(output_file)
    dimensions = list(las.point_format.dimension_names)
    return {
        "output_file": output_file,
        "num_points": num_points,
        "dimensions": dimensions,
    }


def test_output_file(result: dict, output_file: str):

    # Validate output file path
    output_path = Path(output_file)
    if not output_path.exists():
        raise ValueError(f"Error: Output file {output_file} does not exist")

    # Print results
    print(f"Successfully created test LAZ file at {result['output_file']}")
    print(f"Number of points: {result['num_points']}")
    print(f"Dimensions available: {result['dimensions']}")


def parse_args():
    # Parse arguments (assuming argparse is used)
    parser = argparse.ArgumentParser(description="Create a random LAZ file.")
    parser.add_argument("--output_file", type=str, help="Path to save the LAZ file")
    parser.add_argument("--point_format", type=int, default=3, help="Point format of the LAZ file")
    parser.add_argument("--num_points", type=int, default=100, help="Number of points to generate")
    parser.add_argument(
        "--extra_dims", type=str, nargs="*", default=[], help="Extra dimensions in the format name:type"
    )
    parser.add_argument("--crs", type=int, default=2154, help="Projection code")
    parser.add_argument(
        "--center", type=str, default="650000,6810000", help="Center of the area to generate points in"
    )
    return parser.parse_args()


def main():

    # Parse arguments
    args = parse_args()

    # Parse extra dimensions
    extra_dims = [tuple(dim.split(":")) for dim in args.extra_dims]

    # Parse center
    center = tuple(map(float, args.center.split(",")))

    # Call create_random_laz
    result = create_random_laz(args.output_file, args.point_format, args.num_points, args.crs, center, extra_dims)

    # Test output file
    test_output_file(result, args.output_file)


if __name__ == "__main__":
    main()
