import argparse
import shutil

import geopandas as gpd
import laspy
import numpy as np
from pyproj import CRS
from pyproj.exceptions import CRSError
from shapely.geometry import box

from pdaltools.las_info import get_epsg_from_las, get_tile_bbox


def parse_args(argv=None):
    parser = argparse.ArgumentParser("Add points from GeoJSON in LIDAR tile")
    parser.add_argument("--input_geojson", "-ig", type=str, required=True, help="Input GeoJSON file")
    parser.add_argument("--input_las", "-i", type=str, required=True, help="Input las file")
    parser.add_argument("--output_las", "-o", type=str, required=True, default="", help="Output las file")
    parser.add_argument(
        "--virtual_points_classes",
        "-c",
        type=int,
        default=66,
        help="classification value to assign to the added virtual points",
    )
    parser.add_argument(
        "--spatial_ref",
        type=str,
        required=False,
        help="spatial reference for the writer",
    )
    parser.add_argument(
        "--tile_width",
        type=int,
        default=1000,
        help="width of tiles in meters",
    )

    return parser.parse_args(argv)


def clip_3d_points_to_tile(input_points: str, input_las: str, crs: str, tile_width: int) -> gpd.GeoDataFrame:
    """
    Add points from a GeoJSON file in the LIDAR's tile.

    Args:
        input_points (str): Path to the input GeoJSON file with 3D points.
        input_las (str): Path to the LIDAR `.las/.laz` file.
        crs (str): CRS of the data.
        tile_width (int): Width of the tile in meters (default: 1000).

    Return:
        gpd.GeoDataFrame: Points 2d with "Z" value
    """
    # Compute the bounding box of the LIDAR tile
    tile_bbox = get_tile_bbox(input_las, tile_width)

    # Read the input GeoJSON with 3D points
    points_gdf = gpd.read_file(input_points)

    if crs:
        points_gdf = points_gdf.to_crs(crs)

    # Create a polygon from the bounding box
    bbox_polygon = box(*tile_bbox)

    # Clip the points to the bounding box
    clipped_points = points_gdf[points_gdf.intersects(bbox_polygon)].copy()

    return clipped_points


def add_points_to_las(
    input_points_with_z: gpd.GeoDataFrame, input_las: str, output_las: str, crs: str, virtual_points_classes=66
):
    """Add points (3D points in LAZ format) by LIDAR tiles (tiling file)

    Args:
        input_points_with_z(gpd.GeoDataFrame): geometry columns (2D points) as encoded to WKT.
        input_las (str): Path to the LIDAR tiles (LAZ).
        output_las (str): Path to save the updated LIDAR file (LAS/LAZ format).
        crs (str): CRS of the data.
        virtual_points_classes (int): The classification value to assign to those virtual points (default: 66).
    """

    if input_points_with_z.empty:
        print(
            "No points to add. All points of the geojson file are outside the tile. Copying the input file to output"
        )
        shutil.copy(input_las, output_las)

        return

    # Extract XYZ coordinates and additional attribute (classification)
    x_coords = input_points_with_z.geometry.x
    y_coords = input_points_with_z.geometry.y
    z_coords = input_points_with_z.RecupZ
    classes = virtual_points_classes * np.ones(len(input_points_with_z.index))

    with laspy.open(input_las, mode="r") as las:
        las_data = las.read()
        header = las.header

        if not header:
            header = laspy.LasHeader(point_format=8, version="1.4")
        if crs:
            try:
                crs_obj = CRS.from_user_input(crs)  # Convert to a pyproj.CRS object
            except CRSError:
                raise ValueError(f"Invalid CRS: {crs}")
            header.add_crs(crs_obj)

        # Append new points
        new_x = np.concatenate([las_data.x, x_coords])
        new_y = np.concatenate([las_data.y, y_coords])
        new_z = np.concatenate([las_data.z, z_coords])
        new_classes = np.concatenate([las_data.classification, classes])

        updated_las = laspy.LasData(header)
        updated_las.x = new_x
        updated_las.y = new_y
        updated_las.z = new_z
        updated_las.classification = new_classes

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
        spatial_ref (str): CRS of the data.
        tile_width (int): Width of the tile in meters (default: 1000).

    Raises:
        RuntimeError: If the input LAS file has no valid EPSG code.
    """
    if not spatial_ref:
        spatial_ref = get_epsg_from_las(input_las)
        if spatial_ref is None:
            raise RuntimeError(f"LAS file {input_las} does not have a valid EPSG code.")

    # Clip points from GeoJSON by LIDAR tile
    points_clipped = clip_3d_points_to_tile(input_geojson, input_las, spatial_ref, tile_width)

    # Add points by LIDAR tile and save the result
    add_points_to_las(points_clipped, input_las, output_las, spatial_ref, virtual_points_classes)


if __name__ == "__main__":
    args = parse_args()
    add_points_from_geojson_to_las(**vars(args))
