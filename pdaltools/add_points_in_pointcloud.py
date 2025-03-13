import argparse
import shutil

import geopandas as gpd
import laspy
import numpy as np
from pyproj import CRS
from pyproj.exceptions import CRSError
from shapely.geometry import Point, box

from pdaltools.las_info import get_epsg_from_las, get_tile_bbox


def parse_args(argv=None):
    parser = argparse.ArgumentParser("Add points from GeoJSON in LIDAR tile")
    parser.add_argument(
        "--input_geometry", "-ig", type=str, required=True, help="Input Geometry file (GeoJSON or Shapefile)"
    )
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
    parser.add_argument(
        "--spacing",
        type=float,
        default=0,
        help="spacing between generated points in meters",
    )
    parser.add_argument(
        "--altitude_name",
        "-z",
        type=str,
        required=True,
        default="RecupZ",
        help="altitude column name from input geometry",
    )

    return parser.parse_args(argv)


def clip_3d_points_to_tile(
    input_points: gpd.GeoDataFrame, input_las: str, crs: str, tile_width: int
) -> gpd.GeoDataFrame:
    """
    Add points from a GeoDataFrame in the LIDAR's tile.

    Args:
        input_points (gpd.GeoDataFrame): GeoDataFrame with 3D points.
        input_las (str): Path to the LIDAR `.las/.laz` file.
        crs (str): CRS of the data.
        tile_width (int): Width of the tile in meters (default: 1000).

    Return:
        gpd.GeoDataFrame: Points 2D with "Z" value
    """
    # Compute the bounding box of the LIDAR tile
    tile_bbox = get_tile_bbox(input_las, tile_width)

    # Ensure the input_points GeoDataFrame has a CRS set
    if input_points.crs is None:
        input_points.set_crs(crs, inplace=True)

    if crs:
        input_points = input_points.to_crs(crs)

    # Create a polygon from the bounding box
    bbox_polygon = box(*tile_bbox)

    # Clip the points to the bounding box
    clipped_points = input_points[input_points.intersects(bbox_polygon)].copy()

    return clipped_points


def add_points_to_las(
    input_points_with_z: gpd.GeoDataFrame, input_las: str, output_las: str, crs: str, virtual_points_classes=66
):
    """Add points (3D points in LAZ format) by LIDAR tiles (tiling file)

    Args:
        input_points_with_z (gpd.GeoDataFrame): geometry columns (3D points) as encoded to WKT.
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
    z_coords = input_points_with_z.geometry.z
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


def generate_3d_points_from_lines(geojson_line_path: str, spacing: float, altitude_name: str) -> gpd.GeoDataFrame:
    """
    Generate regularly spaced 3D points from 2.5D lines in a GeoJSON file.

    Args:
        geojson_line_path (str): Path to the input GeoJSON file with 2.5D lines.
        spacing (float): Spacing between generated points in meters.
        altitude_name (str): Altitude column name from input geometry

    Returns:
        gpd.GeoDataFrame: GeoDataFrame with generated 3D points.
    """
    # Read the input GeoJSON with 2.5D lines
    gdf = gpd.read_file(geojson_line_path)

    # Initialize lists to store the new points
    x_coords = []
    y_coords = []
    z_values = []

    # Generate 3D points
    for feature in gdf.itertuples():
        line = feature.geometry
        z_value = getattr(feature, altitude_name, None)
        length = line.length
        num_points = int(np.ceil(length / spacing))
        distances = np.linspace(0, length, num_points)
        points = [line.interpolate(distance) for distance in distances]

        # Append the coordinates and z values
        x_coords.extend([point.x for point in points])
        y_coords.extend([point.y for point in points])
        z_values.extend([z_value] * num_points)

    # Create a GeoDataFrame with the new points
    points_gdf = gpd.GeoDataFrame({"geometry": [Point(x, y, z) for x, y, z in zip(x_coords, y_coords, z_values)]})

    return points_gdf


def add_points_from_geometry_to_las(
    input_geometry: str,
    input_las: str,
    output_las: str,
    virtual_points_classes: int,
    spatial_ref: str,
    tile_width: int,
    spacing: float,
    altitude_name: str,
):
    """Add points with Z value by LIDAR tiles (tiling file)

    Args:
        input_geometry (str): Path to the input geometry file (GeoJSON or Shapefile) with 3D points.
        input_las (str): Path to the LIDAR `.las/.laz` file.
        output_las (str): Path to save the updated LIDAR file (LAS/LAZ format).
        virtual_points_classes (int): The classification value to assign to those virtual points (default: 66).
        spatial_ref (str): CRS of the data.
        tile_width (int): Width of the tile in meters (default: 1000).
        spacing (float): Spacing between generated points in meters.
        altitude_name (str): Altitude column name from input geometry

    Raises:
        RuntimeError: If the input LAS file has no valid EPSG code.
    """
    if not spatial_ref:
        spatial_ref = get_epsg_from_las(input_las)
        if spatial_ref is None:
            raise RuntimeError(f"LAS file {input_las} does not have a valid EPSG code.")

    # Read the input GeoJSON
    gdf = gpd.read_file(input_geometry)
    if gdf.crs is None:
        gdf.set_crs(epsg=spatial_ref, inplace=True)

    # Check the geometry type
    if gdf.geometry.geom_type.unique() == ["Point"] or gdf.geometry.geom_type.unique() == ["MultiPoint"]:
        # Add the Z dimension from the 'RecupZ' property
        gdf["geometry"] = gdf.apply(
            lambda row: Point(row["geometry"].x, row["geometry"].y, row[altitude_name]), axis=1
        )
        # If the geometry type is Point, use the points directly
        points_gdf = gdf[["geometry"]].copy()
    elif gdf.geometry.geom_type.unique() == ["LineString"] or gdf.geometry.geom_type.unique() == ["MultiLineString"]:
        # If the geometry type is LineString, generate 3D points
        points_gdf = generate_3d_points_from_lines(input_geometry, spacing, altitude_name)
    else:
        raise ValueError("Unsupported geometry type in the input Geometry file.")

    # Clip points from GeoJSON by LIDAR tile
    points_clipped = clip_3d_points_to_tile(points_gdf, input_las, spatial_ref, tile_width)

    # Add points by LIDAR tile and save the result
    add_points_to_las(points_clipped, input_las, output_las, spatial_ref, virtual_points_classes)


if __name__ == "__main__":
    args = parse_args()
    add_points_from_geometry_to_las(**vars(args))
