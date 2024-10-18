import argparse

import geopandas
import numpy as np
import pdal

from pdaltools.las_info import get_writer_parameters_from_reader_metadata

def extract_points_from_geo(input_geo: str):
    file = open(input_geo)
    df = geopandas.read_file(file)
    return df.get_coordinates(ignore_index=True, include_z=True)



def add_points_in_las(input_las: str, input_geo: str, output_las: str, values_dimensions: {}):
    points_geo = extract_points_from_geo(input_geo)
    pipeline = pdal.Pipeline() | pdal.Reader.las(input_las)
    pipeline.execute()
    points_las = pipeline.arrays[0]
    dimensions = list(points_las.dtype.fields.keys())

    for i in points_geo.index:
        pt_las = np.empty(1, dtype=points_las.dtype)
        pt_las[0][dimensions.index('X')] = points_geo["x"][i]
        pt_las[0][dimensions.index('Y')] = points_geo["y"][i]
        pt_las[0][dimensions.index('Z')] = points_geo["z"][i]
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
    parser.add_argument("--dimensions", "-d", metavar="KEY=VALUE", nargs='+',
                        help="Set a number of key-value pairs corresponding to value "
                             "needed in points added in the output las; key should be included in the input las.")
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
    items = s.split('=')
    key = items[0].strip()
    if len(items) > 1:
        value = '='.join(items[1:])
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
        values_dimensions=added_dimensions,
    )
