# -*- coding: utf-8 -*-
# maintener : MDupays
# version : v.1 03/06/2025
# Compare classification between two LAS files

import laspy
from pathlib import Path
import numpy as np
import logging
import argparse

def compare_las_classification(file1: Path, file2: Path) -> bool:
    """
    Compare the classification of points between two LAS files.
    Returns True if the classification is identical for all points, False otherwise.
    
    Args:
        file1: Path to the first LAS file
        file2: Path to the second LAS file
        
    Returns:
        bool: True if classification is identical, False otherwise
    """
    try:
        # Read both LAS files
        las1 = laspy.read(file1)
        las2 = laspy.read(file2)
        
        # Check if files have the same number of points
        if len(las1) != len(las2):
            logging.error(f"Files have different number of points: {len(las1)} vs {len(las2)}")
            return False
            
        # Get classification arrays
        class1 = np.array(las1.classification)
        class2 = np.array(las2.classification)
        
        # Compare classifications
        if not np.array_equal(class1, class2):
            # Find differences
            diff_indices = np.where(class1 != class2)[0]
            logging.info(f"Found {len(diff_indices)} points with different classification:")
            for idx in diff_indices[:10]:  # Show first 10 differences
                logging.info(f"Point {idx}: file1={class1[idx]}, file2={class2[idx]}")
            if len(diff_indices) > 10:
                logging.info(f"... and {len(diff_indices) - 10} more differences")
            return False
            
        logging.info("Classification is identical in both files")
        return True
        
    except Exception as e:
        logging.error(f"Error comparing LAS files: {str(e)}")
        return False

def main():    
    parser = argparse.ArgumentParser(description='Compare classification between two LAS files')
    parser.add_argument('file1', type=str, help='Path to first LAS file')
    parser.add_argument('file2', type=str, help='Path to second LAS file')
    
    args = parser.parse_args()
    
    file1 = Path(args.file1)
    file2 = Path(args.file2)
    
    if not file1.exists() or not file2.exists():
        print("Error: One or both files do not exist")
        exit(1)
    
    result = compare_las_classification(file1, file2)
    print(f"Classification comparison result: {'identical' if result else 'different'}")

if __name__ == "__main__":
    main()