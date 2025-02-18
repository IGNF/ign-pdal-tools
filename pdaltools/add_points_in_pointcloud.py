import argparse

import geopandas as gpd
import laspy
import numpy as np
from shapely.geometry import box

from pdaltools.las_info import get_tile_origin_using_header_info


def parse_args(argv=None):
    parser = argparse.ArgumentParser("TODO")
    parser.add_argument("--input_geojson", "-ig", type=str, required=True, help="Input GeoJSON file")
    parser.add_argument("--input_las", "-i", type=str, required=True, help="Input las file")
    parser.add_argument("--output_las", "-o", type=str, required=False, default="", help="Output las file")
    parser.add_argument(
        "--virtual_points_classes",
        "-c",
        type=int,
        default=66,
        help="classification value to assign to those virtual points",
    )
    parser.add_argument(
        "--spatial_ref",
        type=str,
        default="EPSG:2154",
        help="spatial reference for the writer (required when running with a buffer)",
    )
    parser.add_argument(
        "--tile_width",
        type=int,
        default=1000,
        help="width of tiles in meters (required when running with a buffer)",
    )

    return parser.parse_args(argv)


def get_tile_bbox(input_las, tile_width=1000) -> tuple:
    """
    Get the theoretical bounding box (xmin, ymin, xmax, ymax) of a LIDAR tile
    using its origin and the predefined tile width.

    Args:
        input_las (str): Path to the LIDAR `.las/.laz` file.
        tile_width (int): Width of the tile in meters (default: 1000).

    Returns:
        tuple: Bounding box as (xmin, ymin, xmax, ymax).
    """
    origin_x, origin_y = get_tile_origin_using_header_info(input_las)
    bbox = (origin_x, origin_y - tile_width, origin_x + tile_width, origin_y)
    return bbox


def clip_3d_points_to_tile(input_points: str, input_las: str, crs: str, tile_width: int) -> gpd.GeoDataFrame:
    """
    Add points from a GeoJSON file in the LIDAR's tile.

    Args:
        input_points (str): Path to the input GeoJSON file with 3D points.
        input_las (str): Path to the LIDAR `.las/.laz` file.
        crs (str): CRS of the data, e.g., 'EPSG:2154'.
        tile_width (int): Width of the tile in meters (default: 1000).

    Return:
        gpd.GeoDataFrame: Points 2d with "Z" value
    """
    # Compute the bounding box of the LIDAR tile
    tile_bbox = get_tile_bbox(input_las, tile_width)

    # Read the input GeoJSON with 3D points
    points_gdf = gpd.read_file(input_points)

    # Ensure the CRS matches
    if crs:
        points_gdf = points_gdf.to_crs(crs)

    # Create a polygon from the bounding box
    bbox_polygon = box(*tile_bbox)

    # Clip the points to the bounding box
    clipped_points = points_gdf[points_gdf.intersects(bbox_polygon)].copy()

    return clipped_points


def add_points_to_las(
    input_points_with_z: gpd.GeoDataFrame, input_las: str, output_las: str, virtual_points_classes=66
):
    """Add points (3D points in LAZ format) by LIDAR tiles (tiling file)

    Args:
        input_points_with_z(gpd.GeoDataFrame): geometry columns (2D points) as encoded to WKT.
        input_las (str): Path to the LIDAR tiles (LAZ).
        output_las (str): Path to save the updated LIDAR file (LAS/LAZ format).
        virtual_points_classes (int): The classification value to assign to those virtual points (default: 66).
    """
    # Check if input points are empty
    if input_points_with_z.empty:
        raise ValueError("No points to add. The input GeoDataFrame is empty.")

    # Extract XYZ coordinates and additional attribute (classification)
    x_coords = input_points_with_z.geometry.x
    y_coords = input_points_with_z.geometry.y
    z_coords = input_points_with_z.RecupZ
    classes = virtual_points_classes * np.ones(len(input_points_with_z.index))

    # Read the existing LIDAR file
    with laspy.open(input_las, mode="r") as las:
        las_data = las.read()
        header = las.header

        # Create a new header if the original header is missing or invalid
        if header is None:
            header = laspy.LasHeader(point_format=6, version="1.4")  # Example format and version

        # Append the clipped points to the existing LIDAR data
        new_x = np.concatenate([las_data.x, x_coords])
        new_y = np.concatenate([las_data.y, y_coords])
        new_z = np.concatenate([las_data.z, z_coords])
        new_classes = np.concatenate([las_data.classification, classes])

        # Create a new LAS file with updated data
        updated_las = laspy.LasData(header)
        updated_las.x = new_x
        updated_las.y = new_y
        updated_las.z = new_z
        updated_las.classification = new_classes

        # Write the updated LAS file
        with laspy.open(output_las, mode="w", header=header, do_compress=True) as writer:
            writer.write_points(updated_las.points)


def add_points_from_geojson_to_las(
    input_geojson: str, input_las: str, output_las: str, virtual_points_classes: int, spatial_ref: str, tile_width: int
):
    """Add points with Z value(GeoJSON format) by LIDAR tiles (tiling file)

    Args:
        input_geojson (str): Path to the input GeoJSON file with 3D points.
        input_las (str): Path to the LIDAR `.las/.laz` file.
        output_las (str): Path to save the updated LIDAR file (LAS/LAZ format).
        virtual_points_classes (int): The classification value to assign to those virtual points (default: 66).
        spatial_ref (str): CRS of the data, e.g., 'EPSG:2154'.
        tile_width (int): Width of the tile in meters (default: 1000).
    """
    # Clip points from GeoJSON by LIDAR tile
    points_clipped = clip_3d_points_to_tile(input_geojson, input_las, spatial_ref, tile_width)

    # Add points by LIDAR tile and save the result
    add_points_to_las(points_clipped, input_las, output_las, virtual_points_classes)


if __name__ == "__main__":
    args = parse_args()
    add_points_from_geojson_to_las(**vars(args))
