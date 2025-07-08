import laspy
from pathlib import Path
import numpy as np
import argparse
from typing import Tuple


def compare_las_dimensions(file1: Path, file2: Path, dimensions: list = None) -> Tuple[bool, int, float]:
    """
    Compare specified dimensions between two LAS files.
    If no dimensions are specified, compares all available dimensions.
    Sorts points by x,y,z,gps_time coordinates before comparison to ensure point order consistency.

    Args:
        file1: Path to the first LAS file
        file2: Path to the second LAS file
        dimensions: List of dimension names to compare (optional)

    Returns:
        bool: True if all specified dimensions are identical, False otherwise
        int: Number of points with different dimensions
        float: Percentage of points with different dimensions
    """
    try:
        # Read both LAS files
        las1 = laspy.read(file1)
        las2 = laspy.read(file2)

        # Check if files have the same number of points
        if len(las1) != len(las2):
            print(f"Files have different number of points: {len(las1)} vs {len(las2)}")
            return False, 0, 0
        print(f"Files have the same number of points: {len(las1)} vs {len(las2)}")

        # Sort points by x,y,z,gps_time coordinates
        # Create sorting indices
        sort_idx1 = np.lexsort((las1.z, las1.y, las1.x, las1.gps_time))
        sort_idx2 = np.lexsort((las2.z, las2.y, las2.x, las2.gps_time))

        # If no dimensions specified, compare all dimensions
        dimensions_las1 = sorted(las1.point_format.dimension_names)
        dimensions_las2 = sorted(las2.point_format.dimension_names)

        if dimensions is None:
            if dimensions_las1 != dimensions_las2:
                print("Files have different dimensions")
                return False, 0, 0
            dimensions = dimensions_las1
        else:
            for dim in dimensions:
                if dim not in dimensions_las1 or dim not in dimensions_las2:
                    print(
                        f"Dimension '{dim}' is not found in one or both files.\n"
                        f"Available dimensions: {las1.point_format.dimension_names}"
                    )
                    return False, 0, 0

        # Compare each dimension
        for dim in dimensions:
            try:
                # Get sorted dimension arrays
                dim1 = np.array(las1[dim])[sort_idx1]
                dim2 = np.array(las2[dim])[sort_idx2]

                # Compare dimensions
                if not np.array_equal(dim1, dim2):
                    # Find differences
                    diff_indices = np.where(dim1 != dim2)[0]
                    print(f"Found {len(diff_indices)} points with different {dim}:")
                    for idx in diff_indices[:10]:  # Show first 10 differences
                        print(f"Point {idx}: file1={dim1[idx]}, file2={dim2[idx]}")
                    if len(diff_indices) > 10:
                        print(f"... and {len(diff_indices) - 10} more differences")
                    return False, len(diff_indices), 100 * len(diff_indices) / len(las1)

            except KeyError:
                print(f"Dimension '{dim}' not found in one or both files")
                return False, 0, 0

        return True, 0, 0

    except laspy.errors.LaspyException as e:
        print(f"LAS file error: {str(e)}")
        return False, 0, 0
    except FileNotFoundError as e:
        print(f"File not found: {str(e)}")
        return False, 0, 0
    except ValueError as e:
        print(f"Value error: {str(e)}")
        return False, 0, 0


# Update main function to use the new compare function
def main():
    parser = argparse.ArgumentParser(description="Compare dimensions between two LAS files")
    parser.add_argument("file1", type=str, help="Path to first LAS file")
    parser.add_argument("file2", type=str, help="Path to second LAS file")
    parser.add_argument(
        "--dimensions", nargs="*", help="List of dimensions to compare. If not specified, compares all dimensions."
    )

    args = parser.parse_args()

    file1 = Path(args.file1)
    file2 = Path(args.file2)

    if not file1.exists() or not file2.exists():
        print("Error: One or both files do not exist")
        exit(1)

    result = compare_las_dimensions(file1, file2, args.dimensions)
    print(f"Dimensions comparison result: {'identical' if result[0] else 'different'}")
    return result


if __name__ == "__main__":
    main()
