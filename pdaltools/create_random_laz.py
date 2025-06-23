import numpy as np
import laspy
from pathlib import Path
import sys
import argparse
import pdal
from pyproj import CRS
from typing import List, Tuple, Union

def create_random_laz(output_file: str, num_points: int = 100, extra_dims: Union[None, List[Tuple[str, str]]] = None):
    """
    Create a test LAZ file with EPSG 2154 and additional dimensions.
    
    Args:
        output_file: Path to save the LAZ file
        num_points: Number of points to generate
        extra_dims: List of tuples (dimension_name, dimension_type) where type can be:
                   'float32', 'float64', 'int8', 'int16', 'int32', 'int64', 'uint8', 'uint16', 'uint32', 'uint64'
    """
    
    # Create a new point cloud
    header = laspy.LasHeader(point_format=3, version="1.4")
        
    # Map string types to numpy types
    type_mapping = {
        'float32': np.float32,
        'float64': np.float64,
        'int8': np.int8,
        'int16': np.int16,
        'int32': np.int32,
        'int64': np.int64,
        'uint8': np.uint8,
        'uint16': np.uint16,
        'uint32': np.uint32,
        'uint64': np.uint64,
    }
        
    for dim_name, dim_type in extra_dims:
        if dim_type not in type_mapping:
            raise ValueError(f"Unsupported dimension type: {dim_type}. Supported types: {list(type_mapping.keys())}")
            
        numpy_type = type_mapping[dim_type]
        header.add_extra_dim(laspy.ExtraBytesParams(name=dim_name, type=numpy_type))
                
        # Create point cloud
    las = laspy.LasData(header)
    las.header.add_crs(CRS.from_string("epsg:2154"))
    
    # Generate random points in a small area (around Paris)
    las.x = np.random.uniform(640000, 660000, num_points)
    las.y = np.random.uniform(6800000, 6820000, num_points)
    las.z = np.random.uniform(0, 200, num_points)
        
    # Generate random intensity values
    las.intensity = np.random.randint(0, 255, num_points)
    
    # Generate random classification values
    las.classification = np.random.randint(0, 10, num_points)
        
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
    print(f"Successfully created test LAZ file at {output_file}")
    print(f"Number of points: {num_points}")
    print(f"Dimensions available: {list(las.point_format.dimension_names)}")
    
    # Print available dimensions
    print("\nAvailable dimensions in input file:")
    pipeline = pdal.Pipeline() | pdal.Reader.las(output_file)
    pipeline.execute()
    points = pipeline.arrays[0]
    dimensions = list(points.dtype.fields.keys())
    for dim in dimensions:
        print(f"- {dim}")


def main():
    parser = argparse.ArgumentParser(description="Create a test LAZ file with EPSG 2154 and extra dimensions")
    parser.add_argument("output_file", help="Path to save the output LAZ file")
    parser.add_argument(
        "--num-points",
        type=int,
        default=100,
        help="Number of points to generate (default: 100)"
    )
    parser.add_argument(
        "--extra-dims",
        type=str,
        default="",
        help="List of extra dimensions with types in format 'name:type,name:type' (e.g., 'height:float32,confidence:uint8')"
    )
    args = parser.parse_args()
    
    # Validate output file path
    output_path = Path(args.output_file)
    if output_path.exists():
        print(f"Error: Output file {args.output_file} already exists", file=sys.stderr)
        sys.exit(1)
    
    # Parse extra dimensions from string format to list of tuples
    extra_dims_list = []
    if args.extra_dims:
        for dim_spec in args.extra_dims.split(","):
            if ":" in dim_spec:
                name, dim_type = dim_spec.strip().split(":")
                extra_dims_list.append((name.strip(), dim_type.strip()))
            else:
                print(f"Warning: Skipping invalid dimension specification '{dim_spec}'. Use format 'name:type'", file=sys.stderr)
    
    create_random_laz(args.output_file, args.num_points, extra_dims_list)

if __name__ == "__main__":
    main()
