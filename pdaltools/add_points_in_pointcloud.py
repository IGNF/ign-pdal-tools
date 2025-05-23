import argparse
from shutil import copy2
import tempfile

import geopandas as gpd
import laspy
import numpy as np
from pyproj import CRS
from pyproj.exceptions import CRSError
from shapely.geometry import MultiPoint, Point, box

from pdaltools.las_info import get_epsg_from_las, get_tile_bbox

import pdal


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
        default=0.25,
        help="spacing between generated points in meters (default. 25 cm)",
    )
    parser.add_argument(
        "--altitude_column",
        "-z",
        type=str,
        required=False,
        default=None,
        help="altitude column name from input geometry (use point.z if altitude_column is not set)",
    )

    return parser.parse_args(argv)


def clip_3d_lines_to_tile(
    input_lines: gpd.GeoDataFrame, input_las: str, crs: str, tile_width: int = 1000
) -> gpd.GeoDataFrame:
    """
    Select lines from a GeoDataFrame that intersect the the LIDAR tile.

    Args:
        input_lines (gpd.GeoDataFrame): GeoDataFrame with lines.
        input_las (str): Path to the LIDAR `.las/.laz` file.
        crs (str): CRS of the data.
        tile_width (int): Width of the tile in meters (default: 1000).

    Returns:
        gpd.GeoDataFrame: Lines that intersect with the tile.
    """
    # Compute the bounding box of the LIDAR tile
    tile_bbox = get_tile_bbox(input_las, tile_width)

    if crs:
        input_lines = input_lines.to_crs(crs)

    # Create a polygon from the bounding box
    bbox_polygon = box(*tile_bbox)

    # Clip the lines to the bounding box
    clipped_lines = input_lines[input_lines.intersects(bbox_polygon)]

    return clipped_lines


def clip_3d_points_to_tile(
    input_points: gpd.GeoDataFrame, input_las: str, crs: str, tile_width: int = 1000
) -> gpd.GeoDataFrame:
    """
    Select points from a GeoDataFrame that intersect the LIDAR tile

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

    if crs:
        input_points = input_points.to_crs(crs)

    # Create a polygon from the bounding box
    bbox_polygon = box(*tile_bbox)

    # Clip the points to the bounding box
    clipped_points = input_points[input_points.intersects(bbox_polygon)]

    return clipped_points


def add_points_to_las(
    input_points_with_z: gpd.GeoDataFrame, input_las: str, output_las: str, crs: str, virtual_points_classes: int = 66
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
        copy2(input_las, output_las)
        return

    # Extract XYZ coordinates and additional attribute (classification)
    nb_points = len(input_points_with_z.geometry.x)
    x_coords = input_points_with_z.geometry.x
    y_coords = input_points_with_z.geometry.y
    z_coords = input_points_with_z.geometry.z
    classes = virtual_points_classes * np.ones(nb_points)

    # Open the input LAS file to check and possibly update the header of the output
    with laspy.open(input_las, "r") as las:
        header = las.header
        if not header:
            header = laspy.LasHeader(point_format=8, version="1.4")

    new_points = laspy.ScaleAwarePointRecord.zeros(nb_points, header=header)  # use header for input_las
    # then fill in the gaps (X, Y, Z an classification)
    new_points.x = x_coords.astype(new_points.x.dtype)
    new_points.y = y_coords.astype(new_points.y.dtype)
    new_points.z = z_coords.astype(new_points.z.dtype)
    new_points.classification = classes.astype(new_points.classification.dtype)

    with tempfile.NamedTemporaryFile(suffix="_new_points.las") as tmp:
        with laspy.open(tmp.name, mode="w", header=header) as las_file:
            las_file.write_points(new_points)

        if crs:
            a_srs = crs
        else:
            a_srs = get_epsg_from_las(input_las)

        # Use pdal to merge the new points with the existing points
        pipeline = pdal.Pipeline()
        pipeline |= pdal.Reader.las(filename=input_las)
        pipeline |= pdal.Reader.las(filename=tmp.name)
        pipeline |= pdal.Filter.merge()
        pipeline |= pdal.Writer.las(filename=output_las, forward="all", a_srs=a_srs)
        pipeline.execute()


def line_to_multipoint(line, spacing: float, z_value: float = None):
    """
    Convert a LineString to a MultiPoint with equally spaced points and a given Z value.

    Args:
        line (shapely.geometry.LineString): The input LineString.
        spacing (float): Spacing between generated points in meters.
        z_value (float): The Z value to assign to each point.

    Returns:
        shapely.geometry.MultiPoint: A MultiPoint geometry with the generated points.
    """
    # Create points along the line with spacing
    length = line.length
    distances = np.arange(0, length + spacing, spacing)
    points_nd = [line.interpolate(distance) for distance in distances]

    if line.has_z:
        multipoint = MultiPoint([Point(point.x, point.y, point.z) for point in points_nd])
    else:
        if z_value is None:
            raise ValueError("z_value must be provided for 2D lines.")
        multipoint = MultiPoint([Point(point.x, point.y, z_value) for point in points_nd])

    return multipoint


def generate_3d_points_from_lines(
    lines_gdf: gpd.GeoDataFrame, spacing: float, altitude_column: str = None
) -> gpd.GeoDataFrame:
    """
    Generate regularly spaced 3D points from 2.5D lines in a GeoJSON file.

    Args:
        lines_gdf (gpd.GeoDataFrame): GeoDataFrame with 2.5D lines.
        spacing (float): Spacing between generated points in meters.
        altitude_column (str, optional): Altitude column name from input geometry.
        If not provided, use Z from geometry.

    Returns:
        gpd.GeoDataFrame: GeoDataFrame with generated 3D points.

    Raises:
        ValueError: If altitude_column is not provided or not found in the GeoDataFrame
                    and Z coordinates are not available in the geometry.
    """
    # Check if altitude_column is provided and exists in the GeoDataFrame
    if altitude_column and (altitude_column not in lines_gdf.columns):
        raise ValueError("altitude_column must exist in the GeoDataFrame if provided.")

    if altitude_column:
        lines_gdf["geometry"] = lines_gdf.apply(
            lambda row: line_to_multipoint(row.geometry, spacing, row[altitude_column]), axis=1
        )
    else:
        # Check if geometries have Z values
        if lines_gdf.geometry.has_z.any():
            lines_gdf["geometry"] = lines_gdf.apply(
                lambda row: line_to_multipoint(row.geometry, spacing, None), axis=1
            )
        else:
            raise ValueError("Geometries do not have Z values and altitude_column is not provided.")

    # Explode the MultiPoint geometries into individual points
    points_gdf = lines_gdf.dissolve().explode(index_parts=False).reset_index(drop=True)

    return points_gdf


def add_points_from_geometry_to_las(
    input_geometry: str,
    input_las: str,
    output_las: str,
    virtual_points_classes: int,
    spatial_ref: str,
    tile_width: int,
    spacing: float,
    altitude_column: str,
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
        altitude_column (str): Altitude column name from input geometry

    Raises:
        RuntimeError: If the input LAS file has no valid EPSG code.
        ValueError: Unsupported geometry type in the input Geometry file OR
                    The parameters "spacing" <= 0.
    """
    if not spatial_ref:
        spatial_ref = get_epsg_from_las(input_las)
        if spatial_ref is None:
            raise RuntimeError(f"LAS file {input_las} does not have a valid EPSG code.")

    # Read the input GeoJSON
    gdf = gpd.read_file(input_geometry)

    if gdf.crs is None:
        gdf.set_crs(epsg=spatial_ref, inplace=True)

    # Check if both Z in geometries and altitude_column are provided
    if gdf.geometry.has_z.any() and altitude_column:
        raise ValueError("Both Z in geometries and altitude_column are provided. Please provide only one.")

    # Store the unique geometry type in a variable
    unique_geom_type = gdf.geometry.geom_type.unique()

    # Check the geometry type
    if len(unique_geom_type) != 1:
        raise ValueError("Several geometry types found in geometry file. This case is not handled.")

    if unique_geom_type in ["Point", "MultiPoint"]:
        gdf = gdf.explode(index_parts=False).reset_index(drop=True)
        if altitude_column:
            # Add the Z dimension from the 'RecupZ' property
            gdf["geometry"] = gdf.apply(
                lambda row: Point(row["geometry"].x, row["geometry"].y, row[altitude_column]), axis=1
            )
            # If the geometry type is Point, use the points directly
            points_gdf = gdf[["geometry"]]
        else:
            # Add the Z dimension from the Geometry Z
            gdf["geometry"] = gdf.apply(
                lambda row: Point(row["geometry"].x, row["geometry"].y, row["geometry"].z), axis=1
            )
            # If the geometry type is Point, use the points directly
            points_gdf = gdf[["geometry"]]
    elif unique_geom_type in ["LineString", "MultiLineString"]:
        gdf = gdf.explode(index_parts=False).reset_index(drop=True)
        gdf = clip_3d_lines_to_tile(gdf, input_las, spatial_ref, tile_width)
        # If the geometry type is LineString, generate 3D points
        if spacing <= 0:
            raise NotImplementedError(
                f"add_points_from_geometry_to_las requires spacing > 0 to run on (Multi)LineString geometries, \
                but the values provided are geometry type: {unique_geom_type} and spacing = {spacing} "
            )
        else:
            points_gdf = generate_3d_points_from_lines(gdf, spacing, altitude_column)
    else:
        raise ValueError("Unsupported geometry type in the input Geometry file.")

    # Clip points from GeoJSON by LIDAR tile
    points_clipped = clip_3d_points_to_tile(points_gdf, input_las, spatial_ref, tile_width)

    # Add points by LIDAR tile and save the result
    add_points_to_las(points_clipped, input_las, output_las, spatial_ref, virtual_points_classes)


if __name__ == "__main__":
    args = parse_args()
    add_points_from_geometry_to_las(**vars(args))
