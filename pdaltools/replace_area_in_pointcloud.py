import argparse
import warnings

import numpy as np
import pdal
from numpy.lib import recfunctions as rfn
from osgeo import gdal

from pdaltools.las_info import get_writer_parameters_from_reader_metadata


def argument_parser():
    parser = argparse.ArgumentParser(
        "Replace points in a pointcloud, based on an area. "
        "Source may come from from another pointcloud (command from_cloud), "
        "or may be derivated from a digital surface model (command from_DSM).\n"
    )
    subparsers = parser.add_subparsers(required=True)

    # first command is 'from_cloud'
    from_cloud = subparsers.add_parser("from_cloud", help="Source is a point cloud")
    from_cloud.add_argument("--source_cloud", "-s", required=True, type=str, help="path of source point cloud")
    add_common_options(from_cloud)
    from_cloud.set_defaults(func=from_cloud_func)

    # second command is 'from_DSM'
    from_DSM = subparsers.add_parser("from_DSM", help="Source is a digital surface model (DSM)")
    from_DSM.add_argument(
        "--source_dsm",
        "-d",
        required=True,
        type=str,
        help="path of the source digital surface model (DSM), used to generate source points",
    )
    from_DSM.add_argument(
        "--source_ground_mask",
        "-g",
        required=True,
        type=str,
        help=(
            "ground mask, a raster file used to filter source cloud. "
            "Pixel with value > 0 is considered as ground, and define the source cloud we keep. "
            "(tif or other raster format readable by GDAL)"
        ),
    )
    from_DSM.add_argument(
        "--source_classification",
        "-c",
        required=True,
        type=int,
        help="classification to apply to the points extracted from the DSM",
    )
    add_common_options(from_DSM)
    from_DSM.set_defaults(func=from_DSM_func)

    return parser


def add_common_options(parser):
    parser.add_argument(
        "--source_pdal_filter", "-f", type=str, help="pdal filter expression to apply to source point cloud"
    )
    parser.add_argument("--target_cloud", "-t", type=str, required=True, help="path of target cloud to be modified")
    parser.add_argument(
        "--replacement_area",
        "-r",
        required=True,
        type=str,
        help="area to replace (shapefile, geojson or other vector format readable by GDAL)",
    )
    parser.add_argument("--output_cloud", "-o", required=True, type=str, help="output cloud file")


def from_cloud_func(args):
    replace_area(
        target_cloud=args.target_cloud,
        pipeline_source=pipeline_read_from_cloud(args.source_cloud),
        replacement_area=args.replacement_area,
        output_cloud=args.output_cloud,
        source_pdal_filter=args.source_pdal_filter,
    )


def from_DSM_func(args):
    replace_area(
        target_cloud=args.target_cloud,
        pipeline_source=pipeline_read_from_DSM(
            dsm=args.source_dsm, ground_mask=args.source_ground_mask, classification=args.source_classification
        ),
        replacement_area=args.replacement_area,
        output_cloud=args.output_cloud,
        source_pdal_filter=args.source_pdal_filter,
    )


def get_writer_params(input_file):
    pipeline = pdal.Pipeline()
    pipeline |= pdal.Reader.las(filename=input_file)
    pipeline.execute()
    params = get_writer_parameters_from_reader_metadata(pipeline.metadata)
    return params


def pipeline_read_from_cloud(filename):
    pipeline_source = pdal.Pipeline()
    pipeline_source |= pdal.Reader.las(filename=filename)
    return pipeline_source


def pipeline_read_from_DSM(dsm, ground_mask, classification):
    # get nodata value
    ds = gdal.Open(dsm)
    band = ds.GetRasterBand(1)
    nodata_value = band.GetNoDataValue()
    ds.Close()

    pipeline = pdal.Pipeline()
    pipeline |= pdal.Reader.gdal(filename=dsm, header="Z")
    pipeline |= pdal.Filter.expression(expression=f"Z != {nodata_value}")

    pipeline |= pdal.Filter.ferry(dimensions="=> ground")
    pipeline |= pdal.Filter.assign(assignment="ground[:]=-1")
    pipeline |= pdal.Filter.colorization(dimensions="ground:1:1.0", raster=ground_mask)
    # Keep only points in the area
    pipeline |= pdal.Filter.expression(expression="ground>0")

    # assign class
    pipeline |= pdal.Filter.ferry(dimensions="=>Classification")
    pipeline |= pdal.Filter.assign(assignment=f"Classification[:]={classification}")

    return pipeline


def replace_area(
    target_cloud, pipeline_source, replacement_area, output_cloud, source_pdal_filter="", target_pdal_filter=""
):
    crops = []
    # pipeline to read target_cloud and remove points inside the polygon
    pipeline_target = pdal.Pipeline()
    pipeline_target |= pdal.Reader.las(filename=target_cloud)
    pipeline_target |= pdal.Filter.ferry(dimensions="=> geometryFid")
    # Assign -1 to all points because overlay replaces values from 0 and more
    pipeline_target |= pdal.Filter.assign(assignment="geometryFid[:]=-1")
    if target_pdal_filter:
        pipeline_target |= pdal.Filter.expression(expression=target_pdal_filter)
    pipeline_target |= pdal.Filter.overlay(column="fid", dimension="geometryFid", datasource=replacement_area)
    # Keep only points out of the area
    pipeline_target |= pdal.Filter.expression(expression="geometryFid==-1", tag="A")
    pipeline_target.execute()

    # get input dimensions dtype from target
    if pipeline_target.arrays:
        input_dim_dtype = pipeline_target.arrays[0].dtype
    else:
        # re-read the LAS only if we cant have dimensions with previous pipeline (empty output)
        pipeline_target2 = pdal.Pipeline()
        pipeline_target2 |= pdal.Reader.las(filename=target_cloud)
        pipeline_target2.execute()
        input_dim_dtype = pipeline_target2.arrays[0].dtype

    # get input dimensions names
    input_dimensions = list(input_dim_dtype.fields.keys())

    # do not keep geometryFid
    output_dimensions = [dim for dim in input_dimensions if dim not in "geometryFid"]

    # add target to the result after keeping only the expected dimensions
    if pipeline_target.arrays:
        target_cloud_pruned = pipeline_target.arrays[0][output_dimensions]
        crops.append(target_cloud_pruned)

    # pipeline to read source_cloud and remove points outside the polygon
    pipeline_source |= pdal.Filter.ferry(dimensions="=> geometryFid")
    pipeline_source |= pdal.Filter.assign(assignment="geometryFid[:]=-1")
    if source_pdal_filter:
        pipeline_source |= pdal.Filter.expression(expression=source_pdal_filter)
    pipeline_source |= pdal.Filter.overlay(column="fid", dimension="geometryFid", datasource=replacement_area)
    # Keep only points in the area
    pipeline_source |= pdal.Filter.expression(expression="geometryFid>=0", tag="B")
    pipeline_source.execute()

    # add source to the result
    if pipeline_source.arrays:
        # eventually add dimensions in source to have same dimensions as target cloud
        # we do that in numpy (instead of PDAL filter) to keep dimension types
        source_cloud_crop = pipeline_source.arrays[0]
        nb_points = source_cloud_crop.shape[0]
        source_dims = source_cloud_crop.dtype.fields.keys()
        for dim_name, dim_type in input_dim_dtype.fields.items():
            if dim_name not in source_dims:
                source_cloud_crop = rfn.append_fields(
                    base=source_cloud_crop,
                    names=dim_name,
                    data=np.zeros(nb_points, dtype=dim_type[0]),
                    dtypes=dim_type[0],
                )

        source_cloud_pruned = source_cloud_crop[output_dimensions]
        crops.append(source_cloud_pruned)

    # Merge
    if not crops:
        warnings.warn("WARNING: Empty LAS, extra dims are lost")

    pipeline = pdal.Filter.merge().pipeline(*crops)

    writer_params = get_writer_params(target_cloud)
    pipeline |= pdal.Writer.las(filename=output_cloud, **writer_params)
    pipeline.execute()


if __name__ == "__main__":
    args = argument_parser().parse_args()
    args.func(args)
