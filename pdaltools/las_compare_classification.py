import laspy
from pathlib import Path
import numpy as np
import logging
import argparse

def compare_las_dimensions(file1: Path, file2: Path, dimensions: list = None) -> bool:
    """
    Compare specified dimensions between two LAS files.
    If no dimensions are specified, compares all available dimensions.
    
    Args:
        file1: Path to the first LAS file
        file2: Path to the second LAS file
        dimensions: List of dimension names to compare (optional)
        
    Returns:
        bool: True if all specified dimensions are identical, False otherwise
    """
    try:
        # Read both LAS files
        las1 = laspy.read(file1)
        las2 = laspy.read(file2)
        
        # Check if files have the same number of points
        if len(las1) != len(las2):
            logging.error(f"Files have different number of points: {len(las1)} vs {len(las2)}")
            return False
            
        # If no dimensions specified, compare all dimensions
        if dimensions is None:
            dimensions = las1.point_format.dimension_names
            
        # Compare each dimension
        for dim in dimensions:
            try:
                # Get dimension arrays
                dim1 = np.array(las1[dim])
                dim2 = np.array(las2[dim])
                
                # Compare dimensions
                if not np.array_equal(dim1, dim2):
                    # Find differences
                    diff_indices = np.where(dim1 != dim2)[0]
                    logging.info(f"Found {len(diff_indices)} points with different {dim}:")
                    for idx in diff_indices[:10]:  # Show first 10 differences
                        logging.info(f"Point {idx}: file1={dim1[idx]}, file2={dim2[idx]}")
                    if len(diff_indices) > 10:
                        logging.info(f"... and {len(diff_indices) - 10} more differences")
                    return False
                    
            except KeyError:
                logging.error(f"Dimension '{dim}' not found in one or both files")
                return False
                
        logging.info("All specified dimensions are identical in both files")
        return True
        
    except Exception as e:
        logging.error(f"Error comparing LAS files: {str(e)}")
        return False

# Update main function to use the new compare function
def main():    
    parser = argparse.ArgumentParser(description='Compare dimensions between two LAS files')
    parser.add_argument('file1', type=str, help='Path to first LAS file')
    parser.add_argument('file2', type=str, help='Path to second LAS file')
    parser.add_argument('--dimensions', nargs='*', help='List of dimensions to compare. If not specified, compares all dimensions.')
    
    args = parser.parse_args()
    
    file1 = Path(args.file1)
    file2 = Path(args.file2)
    
    if not file1.exists() or not file2.exists():
        print("Error: One or both files do not exist")
        exit(1)
    
    result = compare_las_dimensions(file1, file2, args.dimensions)
    print(f"Dimensions comparison result: {'identical' if result else 'different'}")

if __name__ == "__main__":
    main()