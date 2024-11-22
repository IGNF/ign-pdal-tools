import argparse

import geopandas
import numpy as np
import pdal

from pdaltools.las_info import get_writer_parameters_from_reader_metadata, las_info_metadata, get_bounds_from_header_info


def extract_points_from_geo(input_geo: str):
    file = open(input_geo)
    df = geopandas.read_file(file)
    return df.get_coordinates(ignore_index=True, include_z=True)

def point_in_bound(bound_minx, bound_maxx, bound_miny, bound_maxy, pt_x, pt_y):
    return pt_x >= bound_minx and  pt_x <= bound_maxx and pt_y >= bound_miny and  pt_y <= bound_maxy

def add_points_in_las(input_las: str, input_geo: str, output_las: str, inside_las: bool, values_dimensions: {}):
    points_geo = extract_points_from_geo(input_geo)
    pipeline = pdal.Pipeline() | pdal.Reader.las(input_las)
    pipeline.execute()
    points_las = pipeline.arrays[0]
    dimensions = list(points_las.dtype.fields.keys())

    if inside_las:
        mtd = las_info_metadata(input_las)
        bound_minx, bound_maxx, bound_miny, bound_maxy = get_bounds_from_header_info(mtd)

    for i in points_geo.index:
        if inside_las :
            if not point_in_bound(bound_minx, bound_maxx, bound_miny, bound_maxy, points_geo["x"][i], points_geo["y"][i]):
                continue
        pt_las = np.empty(1, dtype=points_las.dtype)
        pt_las[0][dimensions.index("X")] = points_geo["x"][i]
        pt_las[0][dimensions.index("Y")] = points_geo["y"][i]
        pt_las[0][dimensions.index("Z")] = points_geo["z"][i]
        for val in values_dimensions:
            pt_las[0][dimensions.index(val)] = values_dimensions[val]
        points_las = np.append(points_las, pt_las, axis=0)

    params = get_writer_parameters_from_reader_metadata(pipeline.metadata)
    pipeline_end = pdal.Pipeline(arrays=[points_las])
    pipeline_end |= pdal.Writer.las(output_las, forward="all", **params)
    pipeline_end.execute()


def parse_args():
    parser = argparse.ArgumentParser("Add points from geometry file in a las/laz file.")
    parser.add_argument("--input_file", "-i", type=str, help="Las/Laz input file")
    parser.add_argument("--output_file", "-o", type=str, help="Las/Laz output file.")
    parser.add_argument("--input_geo_file", "-g", type=str, help="Geometry input file.")
    parser.add_argument("--inside_las", "-l", type=str, help="Keep points only inside the las boundary.")
    parser.add_argument(
        "--dimensions",
        "-d",
        metavar="KEY=VALUE",
        nargs="+",
        help="Set a number of key-value pairs corresponding to value "
        "needed in points added in the output las; key should be included in the input las.",
    )
    return parser.parse_args()


def is_nature(value, nature):
    if value is None:
        return False
    try:
        nature(value)
        return True
    except:
        return False


def parse_var(s):
    items = s.split("=")
    key = items[0].strip()
    if len(items) > 1:
        value = "=".join(items[1:])
        if is_nature(value, int):
            value = int(value)
        elif is_nature(value, float):
            value = float(value)
    return (key, value)


def parse_vars(items):
    d = {}
    if items:
        for item in items:
            key, value = parse_var(item)
            d[key] = value
    return d


if __name__ == "__main__":
    args = parse_args()
    added_dimensions = parse_vars(args.dimensions)
    add_points_in_las(
        input_las=args.input_file,
        input_geo=args.input_geo_file,
        output_las=args.input_file if args.output_file is None else args.output_file,
        inside_las=args.inside_las,
        values_dimensions=added_dimensions,
    )
