import logging
import os
from pathlib import Path
from typing import List, Union

import json
from typing import Any, Dict, List, Optional, Tuple, Union

import laspy
import numpy as np
import numpy.typing as npt
import pdal
from shapely import Polygon, contains_xy, from_geojson, geometry

from pdaltools.las_info import parse_filename


def create_filenames(file: str, tile_width: int = 1000, tile_coord_scale: int = 1000):
    """Generate the name of the tiles around the input LIDAR tile
    It supposes that the file names are formatted as {prefix1}_{prefix2}_{coordx}_{coordy}_{suffix}
    with coordx and coordy having at least 4 digits

    For example Semis_2021_0000_1111_LA93_IGN69.las

    Args:
        file(str): name of LIDAR file
        tile width (int): width of tiles in meters (usually 1000m)
        tile_coord_scale (int) : scale used in the filename to describe coordinates in meters
                (usually 1000m)
    Returns:
        list_input(list): List of LIDAR's name
    """

    # Create name of LIDAR tiles who cercle the tile
    # # Parameters
    _prefix, coord_x, coord_y, _suffix = parse_filename(file)
    offset = int(tile_width / tile_coord_scale)
    # On left
    _tile_hl = f"{_prefix}_{(coord_x - offset):04d}_{(coord_y + offset):04d}_{_suffix}"
    _tile_ml = f"{_prefix}_{(coord_x - offset):04d}_{coord_y:04d}_{_suffix}"
    _tile_bl = f"{_prefix}_{(coord_x - offset):04d}_{(coord_y - offset):04d}_{_suffix}"
    # On Right
    _tile_hr = f"{_prefix}_{(coord_x + offset):04d}_{(coord_y + offset):04d}_{_suffix}"
    _tile_mr = f"{_prefix}_{(coord_x + offset):04d}_{coord_y:04d}_{_suffix}"
    _tile_br = f"{_prefix}_{(coord_x + offset):04d}_{(coord_y - offset):04d}_{_suffix}"
    # Above
    _tile_a = f"{_prefix}_{coord_x:04d}_{(coord_y + offset):04d}_{_suffix}"
    # Below
    _tile_b = f"{_prefix}_{coord_x:04d}_{(coord_y - offset):04d}_{_suffix}"
    # Return the severals tile's names
    return _tile_hl, _tile_ml, _tile_bl, _tile_a, _tile_b, _tile_hr, _tile_mr, _tile_br


def check_tiles_exist(list_las: list):
    """Check if pointclouds exist
    Args:
        list_las (list): Filenames of the tiles around the LIDAR tile

    Returns:
        li(List): Pruned list of filenames with only existing files
    """
    li = []
    for i in list_las:
        if not os.path.exists(i):
            logging.info(f"NOK : {i}")
            pass
        else:
            li.append(i)
    return li


def create_list(las_dir, input_file, tile_width=1000, tile_coord_scale=1000):
    """Return the paths of 8 tiles around the tile + the input tile
    Args:
        las_dir (str): directory of pointclouds
        input_file (str): path to queried LIDAR tile
        tile_width (int): Width of a tile(in the reference unit: 1m)
        tile_coord_scale (int): Scale used in filename to describe coordinates (usually kilometers)
        1000 * 1m (with 1m being the reference)

    Returns:
        list_files(li): list of tiles
    """

    # Return list 8 tiles around the tile
    list_input = create_filenames(os.path.basename(input_file), tile_width, tile_coord_scale)
    # List pointclouds
    li = [os.path.join(las_dir, e) for e in list_input]
    # Keep only existing files
    li = check_tiles_exist(li)
    # Appending queried tile to list
    li.append(input_file)

    return li


def las_merge(las_dir, input_file, merge_file, tile_width=1000, tile_coord_scale=1000):
    """Merge LIDAR tiles around input_file tile
    Args:
        las_dir (str): directory of pointclouds (to look for neigboprs)
        input_file (str): name of query LIDAR file (with extension)
        output_file (str): path to output
        tile_width (int): Width of a tile(in the reference unit: 1m)
        tile_coord_scale (int): Scale used in filename to describe coordinates (usually kilometers)
        1000 * 1m (with 1m being the reference)
    """
    # List files to merge
    files = create_list(las_dir, input_file, tile_width, tile_coord_scale)
    if len(files) > 0:
        # Merge
        pipeline = pdal.Pipeline()
        for f in files:
            pipeline |= pdal.Reader.las(filename=f)
        pipeline |= pdal.Filter.merge()
        pipeline |= pdal.Writer.las(filename=merge_file, forward="all")
        pipeline.execute()
    else:
        raise ValueError("List of valid tiles is empty : stop processing")




def _load_geojson_polygons(geojson_path: Union[str, Path]) -> List[Polygon]:
    """Load polygons from a GeoJSON file.
    
    Args:
        geojson_path: Path to the GeoJSON file
        
    Returns:
        List of Shapely Polygons
        
    Raises:
        FileNotFoundError: If the GeoJSON file doesn't exist
        ValueError: If the GeoJSON doesn't contain any polygons or is invalid
    """
    geojson_path = Path(geojson_path)
    if not geojson_path.exists():
        raise FileNotFoundError(f"GeoJSON file not found: {geojson_path}")
    
    with open(geojson_path) as f:
        try:
            data = json.load(f)
        except json.JSONDecodeError as e:
            raise ValueError(f"Invalid GeoJSON file: {e}")
    
    polygons = []
    
    def process_geometry(geom: Dict[str, Any]) -> None:
        if geom["type"] == "Polygon":
            # For Polygon, the first ring is the exterior, rest are holes
            exterior = geom["coordinates"][0]
            if len(exterior) >= 3:  # Need at least 3 points for a valid polygon
                polygons.append(Polygon(exterior))
        elif geom["type"] == "MultiPolygon":
            # For MultiPolygon, process each polygon
            for polygon_coords in geom["coordinates"]:
                if polygon_coords and len(polygon_coords[0]) >= 3:
                    polygons.append(Polygon(polygon_coords[0]))
        elif geom["type"] == "FeatureCollection":
            # For FeatureCollection, process each feature
            for feature in geom.get("features", []):
                if "geometry" in feature:
                    process_geometry(feature["geometry"])
        elif geom["type"] == "Feature" and "geometry" in geom:
            # For single Feature
            process_geometry(geom["geometry"])
    
    # Start processing from the root level
    if "type" in data:
        process_geometry(data)
    
    if not polygons:
        raise ValueError("No valid polygons found in the GeoJSON file")
    
    return polygons


def get_points_in_polygons(
    input_file: Union[str, Path],
    geojson_file: Union[str, Path],
    output_file: Optional[Union[str, Path]] = None,
    return_points: bool = False,
) -> Optional[laspy.LasData]:
    """Extract points from a LAS/LAZ file that fall within polygons from a GeoJSON file.
    
    Args:
        input_file: Path to the input LAS/LAZ file
        geojson_file: Path to the GeoJSON file containing one or more polygons
        output_file: Optional path to save the filtered points. If None, the points
                   are not saved to disk.
        return_points: If True, returns the filtered points as a LasData object.
                     If False and output_file is None, raises a ValueError.
    
    Returns:
        Optional[laspy.LasData]: If return_points is True, returns the filtered points.
                               Otherwise returns None.
    
    Raises:
        FileNotFoundError: If the input LAS/LAZ or GeoJSON file doesn't exist
        ValueError: If the GeoJSON doesn't contain any valid polygons or if both 
                  output_file and return_points are None
    """
    input_file = Path(input_file)
    if not input_file.exists():
        raise FileNotFoundError(f"Input file not found: {input_file}")
    
    # Load polygons from GeoJSON
    try:
        polygons = _load_geojson_polygons(geojson_file)
    except Exception as e:
        raise ValueError(f"Error loading polygons from GeoJSON: {e}")
    
    if not polygons:
        raise ValueError("No valid polygons found in the GeoJSON file")
    
    # Read the LAS file
    las = laspy.read(input_file)
    points = np.vstack((las.x, las.y)).T
    
    # Create a mask for points inside any of the polygons
    mask = np.zeros(len(points), dtype=bool)
    for polygon in polygons:
        # Convert polygon to a single polygon if it's a MultiPolygon
        if hasattr(polygon, 'geoms'):  # It's a MultiPolygon
            for poly in polygon.geoms:
                mask |= contains_xy(poly, points[:, 0], points[:, 1])
        else:  # It's a single Polygon
            mask |= contains_xy(polygon, points[:, 0], points[:, 1])
    
    if not np.any(mask):
        logging.warning("No points found inside any of the specified polygons")
        return None
    
    # Create a new LAS file with only the filtered points
    if output_file is not None or return_points:
        filtered_las = laspy.LasData(las.header)
        
        # Copy only the filtered points
        for dim in las.point_format.dimension_names:
            setattr(filtered_las, dim, getattr(las, dim)[mask])
        
        filtered_las.update_header()
        
        # Save to file if output path is provided
        if output_file is not None:
            output_file = Path(output_file)
            output_file.parent.mkdir(parents=True, exist_ok=True)
            filtered_las.write(output_file)
            logging.info(f"Saved {np.sum(mask)} points to {output_file}")
        
        return filtered_las if return_points else None
    
    return None

def merge_two_las_files(
    input_file1: Union[str, Path],
    geojson_file1: Union[str, Path],
    input_file2: Union[str, Path],
    geojson_file2: Union[str, Path],
    output_file: Union[str, Path],
    in_place: bool = False,
) -> None:
    """Merge two LAS/LAZ files into a single output file using laspy.
    
    Args:
        input_file1: Path to the first input LAS/LAZ file
        input_file2: Path to the second input LAS/LAZ file
        output_file: Path where the merged file will be saved
        in_place: If True, modify the first file in place (overwrite input_file1)
    
    Raises:
        FileNotFoundError: If either input file doesn't exist
        ValueError: If the input files have incompatible point formats
    """
    input_file1 = Path(input_file1)
    input_file2 = Path(input_file2)
    geojson_file1 = Path(geojson_file1)
    geojson_file2 = Path(geojson_file2)

    if not input_file1.exists():
        raise FileNotFoundError(f"Input file not found: {input_file1}")
    if not input_file2.exists():
        raise FileNotFoundError(f"Input file not found: {input_file2}")
    if not geojson_file1.exists():
        raise FileNotFoundError(f"GeoJSON file not found: {geojson_file1}")
    if not geojson_file2.exists():
        raise FileNotFoundError(f"GeoJSON file not found: {geojson_file2}")


    # Read both input files
    las1 = laspy.read(input_file1)
    las2 = laspy.read(input_file2)

    # Check if point formats are compatible
    if las1.point_format != las2.point_format:
        raise ValueError("Input files have different point formats and cannot be merged")

    # Filter points based on GeoJSON
    filtered_las1 = get_points_in_polygons(input_file1, geojson_file1)
    filtered_las2 = get_points_in_polygons(input_file2, geojson_file2)

    # Create a new header with combined bounds
    header = las1.header
    
    # Create a new LasData object with the combined header
    merged = laspy.LasData(header)
    
    # Concatenate all dimensions
    for dimension in las1.point_format.dimension_names:
        if dimension == 'point_source_id':
            # Handle point_source_id specially to avoid potential conflicts
            max_id1 = np.max(filtered_las1.point_source_id) if len(filtered_las1.point_source_id) > 0 else 0
            max_id2 = np.max(filtered_las2.point_source_id) if len(filtered_las2.point_source_id) > 0 else 0
            setattr(merged, dimension, np.concatenate([
                filtered_las1.point_source_id,
                filtered_las2.point_source_id + max_id1 + 1
            ]))
        else:
            # Concatenate all other dimensions normally
            setattr(merged, dimension, np.concatenate([
                getattr(filtered_las1, dimension),
                getattr(filtered_las2, dimension)
            ]))
    
    # Update header information
    merged.update_header()
    
    # Write the merged file
    if in_place:
        output_file = input_file1
    
    # Ensure the output directory exists
    output_file = Path(output_file)
    output_file.parent.mkdir(parents=True, exist_ok=True)
    
    # Save the merged file
    merged.write(output_file)
    logging.info(f"Merged {input_file1} and {input_file2} into {output_file}")