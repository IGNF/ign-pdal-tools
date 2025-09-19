import argparse

import numpy as np
import pdal
from numpy.lib import recfunctions as rfn

from pdaltools.las_info import get_writer_parameters_from_reader_metadata


def parse_args():
    parser = argparse.ArgumentParser(
        "Replace points in a pointcloud with points from another pointcloud based on a area"
    )
    parser.add_argument("--target_cloud", "-t", type=str, help="filepath of target cloud to be modified")
    parser.add_argument("--source_cloud", "-s", type=str, help="filepath of source cloud to use for replacement")
    parser.add_argument("--replacement_area_file", "-r", type=str, help="filepath of file containing areas to replace")
    parser.add_argument("--filter", "-f", type=str, help="pdal filter expression to apply to target_cloud")
    parser.add_argument("--outfile", "-o", type=str, help="output file")
    return parser.parse_args()


def get_writer_params(input_file):
    pipeline = pdal.Pipeline()
    pipeline |= pdal.Reader.las(filename=input_file)
    pipeline.execute()
    params = get_writer_parameters_from_reader_metadata(pipeline.metadata)
    return params


def replace_area(target_cloud, source_cloud, replacement_area_file, outfile, writer_params, filter=""):
    crops = []
    # pipeline to read target_cloud and remove points inside the polygon
    pipeline_target = pdal.Pipeline()
    pipeline_target |= pdal.Reader.las(filename=target_cloud)
    pipeline_target |= pdal.Filter.ferry(dimensions="=> geometryFid")
    # Assign -1 to all points because overlay replaces values from 0 and more
    pipeline_target |= pdal.Filter.assign(assignment="geometryFid[:]=-1")
    if filter:
        pipeline_target |= pdal.Filter.expression(expression=filter)
    pipeline_target |= pdal.Filter.overlay(column="fid", dimension="geometryFid", datasource=replacement_area_file)
    # Keep only points out of the area
    pipeline_target |= pdal.Filter.expression(expression="geometryFid==-1", tag="A")
    pipeline_target.execute()

    input_dimensions = list(pipeline_target.arrays[0].dtype.fields.keys())
    # do not keep geometryFid
    output_dimensions = [dim for dim in input_dimensions if dim not in "geometryFid"]
    target_cloud_pruned = pipeline_target.arrays[0][output_dimensions]
    crops.append(target_cloud_pruned)

    # pipeline to read source_cloud and remove points outside the polygon
    pipeline_source = pdal.Pipeline()
    pipeline_source |= pdal.Reader.las(filename=source_cloud)
    pipeline_source |= pdal.Filter.ferry(dimensions="=> geometryFid")
    pipeline_source |= pdal.Filter.assign(assignment="geometryFid[:]=-1")
    pipeline_source |= pdal.Filter.overlay(column="fid", dimension="geometryFid", datasource=replacement_area_file)
    # Keep only points in the area
    pipeline_source |= pdal.Filter.expression(expression="geometryFid>=0", tag="B")

    pipeline_source.execute()

    # eventually add a dimensions in source to have same dimensions as target cloud
    # we do that in numpy (instead of PDAL filter) to keep dimension types
    source_cloud_crop = pipeline_source.arrays[0]
    nb_points = source_cloud_crop.shape[0]
    source_dims = source_cloud_crop.dtype.fields.keys()
    for dim_name, dim_type in pipeline_target.arrays[0].dtype.fields.items():
        if dim_name not in source_dims:
            source_cloud_crop = rfn.append_fields(
                base=source_cloud_crop, names=dim_name, data=np.zeros(nb_points, dtype=dim_type[0]), dtypes=dim_type[0]
            )

    source_cloud_pruned = source_cloud_crop[output_dimensions]
    crops.append(source_cloud_pruned)

    # Merge
    pipeline = pdal.Filter.merge().pipeline(*crops)
    pipeline |= pdal.Writer.las(filename=outfile, **writer_params)
    pipeline.execute()


def main():
    args = parse_args()

    writer_parameters = get_writer_params(args.target_cloud)
    # writer_parameters["extra_dims"] = "" # no extra-dim by default

    replace_area(
        args.target_cloud, args.source_cloud, args.replacement_area_file, args.outfile, writer_parameters, args.filter
    )


if __name__ == "__main__":
    main()
